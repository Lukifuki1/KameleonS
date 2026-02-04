#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import ssl
import json
import time
import socket
import signal
import shutil
import redis
import psutil
import pyotp
import base64
import hashlib
import logging
import subprocess
import networkx as nx
import statistics
import tempfile
import secrets
import asyncio
import websockets
import requests
import gnupg
import struct
import ctypes
import binascii
import threading
import getpass
import mmap
import platform
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, ed25519, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key, Encoding, PrivateFormat, NoEncryption, PublicFormat
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

# === SIGNAL HANDLER & RAM WIPE ===
def ram_wipe():
    for i in range(len(EPHEMERAL_LEDGER)):
        EPHEMERAL_LEDGER[i] = b"x"*len(EPHEMERAL_LEDGER[i])
    EPHEMERAL_LEDGER.clear()

def secure_shutdown(signum, frame):
    ram_wipe()
    sys.exit(0)

signal.signal(signal.SIGINT, secure_shutdown)
signal.signal(signal.SIGTERM, secure_shutdown)

# === TPM2 SUPPORT ===
try:
    from tpm2_pytss import ESAPI, TPM2B_DIGEST, TPM2B_PUBLIC, TPM2B_PRIVATE, TPM2_NV_COUNTER, TPM2B_NV_PUBLIC, ESYS_TR
    TPM2_SUPPORT = True
    TPM_AVAILABLE = True
except ImportError:
    TPM2_SUPPORT = False
    TPM_AVAILABLE = False

# === PKCS#11 HSM ===
try:
    from PyKCS11 import PyKCS11Lib, PyKCS11Error, CKA_LABEL, CKA_CLASS, CKO_PRIVATE_KEY, CKO_PUBLIC_KEY, Mechanism, CKM_SHA256_RSA_PKCS
    PKCS11_SUPPORT = True
except ImportError:
    PKCS11_SUPPORT = False

# === FIDO2 / WEBAUTHN ===
try:
    from fido2.client import Fido2Client
    from fido2.ctap2 import AttestationObject, AuthenticatorData
    from fido2.hid import CtapHidDevice
    FIDO2_SUPPORT = True
except ImportError:
    FIDO2_SUPPORT = False

ROOT_DIR = Path("/opt/kameleon/orchestrator")
CHAIN_FILE = ROOT_DIR / "hashchain.log"
ACL_FILE = ROOT_DIR / "super_orchestrator.acl.json"
INCIDENT_PROFILE_DIR = ROOT_DIR / "incident_profiles"
TASKS_DIR = Path("/opt/kameleon/intelligence_tasks/")
FOR_DIR = Path("/opt/kameleon/forensics/")
SNAPSHOTS_DIR = Path("/opt/kameleon/snapshots/")
META_FEED = ROOT_DIR / "meta_feed.json"
STATUS_HTML = ROOT_DIR / "status.html"
EVAL_STATS = ROOT_DIR / "eval_stats.json"
REDTEAM_REPORT = ROOT_DIR / "redteam_report.json"
AGENT_EVALS = Path("/opt/cell/evals/")
AGENT_STATE = Path("/opt/cell/knowledge_bank/")
SECRET_SHARES_DIR = ROOT_DIR / "secret_shares"
KEYS_DIR = ROOT_DIR / "keys"
LOCKDOWN_FLAG = Path("/opt/kameleon/LOCKDOWN")
SAFE_MODE_FLAG = Path("/opt/kameleon/SAFE_MODE")
KRL_FILE = ROOT_DIR / "krl.json"
SIEM_URL = "https://siem.example.si/chain"
PLUGIN_DIR = Path("/opt/kameleon/supervisor/plugins/")
LOG_DIR = ROOT_DIR / "logs"
BACKUP_DIR = ROOT_DIR / "backup"
HEALTHCHECKS = ["cpu", "ram", "disk", "process", "network"]
LOG_RETENTION_DAYS = 14

os.makedirs(ROOT_DIR, exist_ok=True)
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
os.makedirs(SECRET_SHARES_DIR, exist_ok=True)
os.makedirs(KEYS_DIR, exist_ok=True)
os.makedirs(INCIDENT_PROFILE_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(FOR_DIR, exist_ok=True)
os.makedirs(AGENT_EVALS, exist_ok=True)
os.makedirs(AGENT_STATE, exist_ok=True)
os.makedirs(PLUGIN_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

CHANNELS = {
    "incidents": "incident_bus",
    "supervisor": "supervisor_feedback",
    "eval": "agent_eval_feedback",
    "control": "orchestrator_control",
    "plugin_audit": "plugin_audit",
    "dag_events": "dag_theta",
    "health": "health_check",
    "config": "config_channel"
}

PUBKEY_FILE = ROOT_DIR / "super_orchestrator.pub"
PRIVKEY_FILE = ROOT_DIR / "super_orchestrator.key"
ED25519_PUB = ROOT_DIR / "super_orchestrator_ed25519.pub"
AGENT_PROXY_CERT = ROOT_DIR / "agent_proxy.crt"
AGENT_PROXY_KEY = ROOT_DIR / "agent_proxy.key"
AGENT_PROXY_HOST = "127.0.0.1"
AGENT_PROXY_PORT = 9443
OOB_WEBHOOK_URL = "https://oob-beacon.local/alert"
MISP_URL = "https://misp.example.si"
MISP_KEY = "APIKEY"
FERNET_KEY = Fernet.generate_key()
RAM_FERNET = Fernet(FERNET_KEY)
EPHEMERAL_LEDGER = []
GPG_HOME = str(ROOT_DIR / "gpg")
GPG = gnupg.GPG(gnupghome=GPG_HOME)
REDIS_HOST = 'localhost'
REDIS_PORT = 6380
REDIS_TLS = True

CA_CERT = str(ROOT_DIR / "ca.crt")
TPM_PCR_INDEX = 7

thread_locks = {
    "chain": Lock(),
    "snapshots": Lock(),
    "plugin_audit": Lock()
}

def tpm_load_key():
    if not TPM_AVAILABLE:
        raise SystemExit("TPM/HSM ni na voljo – disk key load ni dovoljen.")
    return None

def tpm_monotonic_counter():
    if TPM_AVAILABLE:
        return int(time.time())
    else:
        return int(time.time())

def tpm_pcr_digest():
    if TPM_AVAILABLE:
        tpm = ESAPI()
        return hashlib.sha3_512(b"PCR_SIM").digest()
    else:
        return hashlib.sha3_512(b"NOPCR").digest()

def merkle_root(leaves):
    if not leaves: return b''
    lvl = [l if isinstance(l, bytes) else l.encode() for l in leaves]
    while len(lvl) > 1:
        nxt = []
        for i in range(0, len(lvl), 2):
            a = lvl[i]
            b = lvl[i+1] if i+1 < len(lvl) else lvl[i]
            nxt.append(hashlib.sha3_512(a+b).digest())
        lvl = nxt
    return lvl[0] if lvl else b''

def pgp_sign(data):
    signed = GPG.sign(data, detach=True)
    return str(signed)

def pgp_verify(data, sig):
    with tempfile.NamedTemporaryFile(delete=False) as tmp_data, tempfile.NamedTemporaryFile(delete=False) as tmp_sig:
        tmp_data.write(data.encode())
        tmp_data.flush()
        tmp_sig.write(sig.encode())
        tmp_sig.flush()
        verified = GPG.verify_file(open(tmp_sig.name, 'rb'), tmp_data.name)
        os.unlink(tmp_data.name)
        os.unlink(tmp_sig.name)
        return verified.valid

def raft_apply(value):
    import raftos
    asyncio.get_event_loop().run_until_complete(raftos.commit("hashchain", value))

def load_privkey():
    if TPM_AVAILABLE:
        return tpm_load_key()
    ledger = HashChainLedger(CHAIN_FILE)
    ledger.append("TPM/HSM ni na voljo – shutdown!", pgp_sign("TPM/HSM unavailable"))
    oob_beacon("TPM/HSM unavailable, critical shutdown")
    ram_wipe()
    raise SystemExit("Strojna podpora (TPM/HSM) za ključe je obvezna!")

def load_ed25519_priv():
    raise SystemExit("Ed25519 private key ni na disku – FIDO2/TPM podpora je obvezna.")

def load_pubkey():
    with open(PUBKEY_FILE, "rb") as f:
        return load_pem_public_key(f.read(), backend=default_backend())

def load_ed25519_pub():
    with open(ED25519_PUB, "rb") as f:
        return ed25519.Ed25519PublicKey.from_public_bytes(f.read())

def get_redis():
    if REDIS_TLS:
        return redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, ssl=True, ssl_certfile=str(AGENT_PROXY_CERT), ssl_keyfile=str(AGENT_PROXY_KEY))
    return redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
REDIS = get_redis()

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s', 
    handlers=[
        logging.FileHandler(LOG_DIR / "orchestrator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

class HashChainLedger:
    def __init__(self, path, chain_id="KAMELEON"):
        self.path = Path(path)
        self.chain_id = chain_id
        self.prev_hash = "0"*128
        self.index = 0
        self._load_last()
        self.monotonic_counter = tpm_monotonic_counter()
    def _load_last(self):
        if not self.path.exists():
            return
        with open(self.path) as f:
            for line in f:
                entry = json.loads(line)
                self.prev_hash = entry["current_hash"]
                self.index = entry["index"]
                if "tpm_counter" in entry:
                    self.monotonic_counter = max(self.monotonic_counter, entry["tpm_counter"])
    def append(self, event, signature=""):
        with thread_locks["chain"]:
            self.monotonic_counter += 1
            entry = {
                "chain_id": self.chain_id,
                "index": self.index + 1,
                "prev_hash": self.prev_hash,
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "tpm_counter": self.monotonic_counter
            }
            entry_bytes = json.dumps(entry, sort_keys=True).encode()
            entry["current_hash"] = hashlib.sha3_512(entry_bytes).hexdigest()
            entry["signature"] = signature
            if TPM_AVAILABLE:
                pcr = tpm_pcr_digest()
                entry["pcr"] = base64.b64encode(pcr).decode()
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self.prev_hash = entry["current_hash"]
            self.index += 1
            raft_apply(json.dumps(entry))
            ram_append(entry)
    def verify_chain(self):
        prev_hash = "0"*128
        idx = 0
        monotonic_counter = 0
        with open(self.path) as f:
            for line in f:
                entry = json.loads(line)
                assert entry["prev_hash"] == prev_hash, "Hash verige ne drži!"
                data = dict(entry)
                sig = data.pop("signature", "")
                curr_hash = data.get("current_hash")
                del data["current_hash"]
                if "tpm_counter" in data:
                    assert data["tpm_counter"] > monotonic_counter, "TPM monotonic counter violated!"
                    monotonic_counter = data["tpm_counter"]
                entry_bytes = json.dumps(data, sort_keys=True).encode()
                assert curr_hash == hashlib.sha3_512(entry_bytes).hexdigest(), "Nepravilen hash!"
                prev_hash = curr_hash
                idx += 1
        return idx

def ram_append(entry):
    crypted = RAM_FERNET.encrypt(json.dumps(entry).encode())
    EPHEMERAL_LEDGER.append(crypted)

def log_rotate():
    now = time.time()
    for file in LOG_DIR.glob("*.log"):
        if file.stat().st_mtime < now - LOG_RETENTION_DAYS*86400:
            file.unlink()

def check_integrity(ledger):
    paths = ["/opt/cell/agent"] + list(Path("/opt/cell/models/").glob("*.pt"))
    for p in paths:
        if not os.path.exists(p): continue
        hashfile = str(p) + ".sha3"
        current = hashlib.sha3_512(open(p, "rb").read()).hexdigest()
        if os.path.exists(hashfile):
            stored = open(hashfile).read().strip()
            if current != stored:
                ledger.append(f"INTEGRITY FAIL {p}", pgp_sign(current))
                requests.post(OOB_WEBHOOK_URL, json={"msg": f"Integrity FAIL: {p}"})
                SAFE_MODE_FLAG.touch()
                LOCKDOWN_FLAG.touch()
                oob_beacon(f"Integrity FAIL: {p}")
        else:
            with open(hashfile, "w") as f:
                f.write(current)

def monitor_config_integrity(ledger):
    while True:
        config_paths = list(ROOT_DIR.glob("*.json")) + list(ROOT_DIR.glob("*.conf")) + list(KEYS_DIR.glob("*.pem"))
        for cfg in config_paths:
            hashfile = str(cfg) + ".sha3"
            current = hashlib.sha3_512(open(cfg, "rb").read()).hexdigest()
            if os.path.exists(hashfile):
                stored = open(hashfile).read().strip()
                if current != stored:
                    ledger.append(f"CONFIG INTEGRITY FAIL {cfg}", pgp_sign(current))
                    oob_beacon(f"CONFIG INTEGRITY FAIL: {cfg}")
                    SAFE_MODE_FLAG.touch()
                    LOCKDOWN_FLAG.touch()
            else:
                with open(hashfile, "w") as f:
                    f.write(current)
        time.sleep(120)

def memory_snapshot(ledger):
    with thread_locks["snapshots"]:
        for aid in os.listdir(AGENT_STATE):
            src = AGENT_STATE / aid
            dest = SNAPSHOTS_DIR / aid / str(int(time.time()))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest)

            key = Fernet.generate_key()
            fernet = Fernet(key)
            for dirpath, _, filenames in os.walk(dest):
                for fname in filenames:
                    fpath = Path(dirpath) / fname
                    with open(fpath, "rb") as file:
                        enc = fernet.encrypt(file.read())
                    with open(fpath, "wb") as file:
                        file.write(enc)

            manifest = {"files": {}}
            for dirpath, _, filenames in os.walk(dest):
                for fname in filenames:
                    fpath = Path(dirpath) / fname
                    manifest["files"][str(Path(fpath).relative_to(dest))] = hashlib.sha256(open(fpath, "rb").read()).hexdigest()

            mpath = dest / "manifest.json"
            with open(mpath, "w") as mf:
                json.dump(manifest, mf, indent=2)

            sig = pgp_sign(open(mpath).read())
            with open(str(mpath)+".asc", "w") as sigf:
                sigf.write(sig)

            ledger.append(f"Snapshot: {aid}", pgp_sign(str(dest)))

            # 🔐 Avtomatski chainpack za ustvarjen snapshot
            try:
                subprocess.run([
                    "python3",
                    "/opt/cell/system/chainpack_generator.py",
                    str(dest),
                    aid
                ], check=True)
                ledger.append(f"Chainpack auto-generated for {aid}", pgp_sign(aid))
            except Exception as e:
                ledger.append(f"Chainpack auto-gen FAIL for {aid}: {e}", pgp_sign(str(e)))


def snapshot_restore(agent_id, version):
    from subprocess import run, PIPE

    zip_path = SNAPSHOTS_DIR / f"{agent_id}.snapshot.zip"
    if zip_path.exists():
        result = run(["python3", "/opt/cell/system/snapshot_chainpack_verifier.py", str(zip_path)], stdout=PIPE, stderr=PIPE)
        if result.returncode != 0:
            SAFE_MODE_FLAG.touch()
            LOCKDOWN_FLAG.touch()
            raise SystemExit("❌ Snapshot ZIP ni preverjen! Obnova ustavljena.")
    
    with thread_locks["snapshots"]:
        src = SNAPSHOTS_DIR / agent_id / version
        mpath = src / "manifest.json"
        sigpath = str(mpath) + ".asc"
        manifest = json.load(open(mpath))
        assert pgp_verify(open(mpath).read(), open(sigpath).read()), "Manifest PGP signature fail!"
        for f in manifest["files"]:
            real_sha = hashlib.sha256(open(str(src/f), "rb").read()).hexdigest()
            assert manifest["files"][f] == real_sha, f"Snapshot integrity failed on {f}!"
        dst = AGENT_STATE / agent_id
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)


async def raft_init():
    import raftos
    await raftos.configure({
        'log_path': '/tmp/raft-log',
        'serializer': raftos.serializers.JSONSerializer()
    })

def websocket_server():
    async def handler(websocket, path):
        while True:
            try:
                with open(META_FEED) as f:
                    await websocket.send(f.read())
                await asyncio.sleep(3)
            except Exception:
                break
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(websockets.serve(handler, "0.0.0.0", 9000))
    loop.run_forever()

def sign_envelope(obj):
    payload = json.dumps(obj, sort_keys=True)
    signature = pgp_sign(payload)
    return {"payload": obj, "signature": signature}

def verify_envelope(env):
    payload = json.dumps(env["payload"], sort_keys=True)
    return pgp_verify(payload, env["signature"])

def oob_beacon(msg):
    try:
        requests.post(OOB_WEBHOOK_URL, json={"msg": msg}, timeout=5)
    except:
        pass

def export_chainpack(ledger):
    data = open(CHAIN_FILE).read()
    sig = pgp_sign(data)
    leaves = [json.loads(line)["current_hash"] for line in data.strip().split("\n")]
    root = merkle_root(leaves)
    fname = f"/tmp/chainpack_{int(time.time())}.asc"
    with open(fname, "w") as f:
        f.write(data)
        f.write("\n\n-----BEGIN PGP SIGNATURE-----\n")
        f.write(sig)
        f.write("\n-----END PGP SIGNATURE-----\n")
        f.write("\n\n-----BEGIN MERKLE ROOT-----\n")
        f.write(root.hex())
        f.write("\n-----END MERKLE ROOT-----\n")
    ledger.append(f"Chainpack exported: {fname}", pgp_sign(fname))

def export_chain_to_siem():
    with open(CHAIN_FILE) as f:
        chain_data = f.read()
    try:
        requests.post(SIEM_URL, data=chain_data, verify=CA_CERT, timeout=10)
    except Exception as e:
        pass

def siem_health_check():
    try:
        r = requests.get(SIEM_URL, verify=CA_CERT, timeout=5)
        return r.status_code == 200
    except:
        return False

def siem_health_monitor(ledger):
    while True:
        if not siem_health_check():
            ledger.append("SIEM UNREACHABLE", pgp_sign("SIEM UNREACHABLE"))
            oob_beacon("SIEM UNREACHABLE")
        time.sleep(600)

def rotate_keys_if_needed():
    while True:
        try:
            key_age = time.time() - os.path.getmtime(PRIVKEY_FILE)
            if key_age > 90*24*3600:
                ledger = HashChainLedger(CHAIN_FILE)
                ledger.append("KEY ROTATION NEEDED", pgp_sign("KEY ROTATION NEEDED"))
                oob_beacon("KEY ROTATION NEEDED")
            time.sleep(86400)
        except Exception as e:
            pass

def backup_configuration():
    ts = int(time.time())
    for f in ROOT_DIR.glob("*.*"):
        shutil.copy2(f, BACKUP_DIR / f"{f.name}.{ts}.bak")

def misp_enrich_incident(incident):
    headers = {"Authorization": MISP_KEY}
    try:
        r = requests.get(f"{MISP_URL}/events/restSearch/text:{incident}", headers=headers, timeout=10)
        if r.status_code == 200 and r.json():
            return r.json()[0].get("threat_level_id", "unknown")
    except:
        pass
    return "unknown"

def calculate_risk_score(stats, drift, anomaly_map):
    scores = {}
    for aid in stats:
        tr = [x[1] for x in stats[aid][-10:]]
        drift_val = drift.get(aid, {}).get("drift", 0)
        zscore = drift.get(aid, {}).get("zscore", 0)
        median = statistics.median(tr) if tr else 0
        mad = statistics.median([abs(x-median) for x in tr]) if tr else 0
        mean_anomaly = sum(x["anomaly"] for x in anomaly_map.get(aid, [])[-10:]) / 10 if anomaly_map.get(aid) else 0
        deficit = 1 if min(tr, default=1) < 0.6 else 0
        scores[aid] = 0.3*drift_val + 0.3*abs(zscore) + 0.2*mean_anomaly + 0.2*mad + 0.1*deficit
    return scores

def audit_plugin_manipulation(ledger):
    with thread_locks["plugin_audit"]:
        hashes = {}
        for f in PLUGIN_DIR.glob("*.py"):
            with open(f, "rb") as fp:
                hashes[f.name] = hashlib.sha3_512(fp.read()).hexdigest()
        hashfile = PLUGIN_DIR / "plugin_hashes.json"
        if hashfile.exists():
            old = json.load(open(hashfile))
            for k, v in hashes.items():
                if k in old and old[k] != v:
                    ledger.append(f"Plugin manipulated: {k}", pgp_sign(k))
        with open(hashfile, "w") as f:
            json.dump(hashes, f, indent=2)

def acl_check(uid):
    with open(ACL_FILE, "r") as f:
        return json.load(f).get(uid, False)

def validate_deficits(deficits):
    if isinstance(deficits, list):
        for d in deficits:
            if not isinstance(d, (str, dict, list)):
                return False
            if isinstance(d, dict) or isinstance(d, list):
                if not validate_deficits(d):
                    return False
        return True
    elif isinstance(deficits, dict):
        for v in deficits.values():
            if not validate_deficits(v):
                return False
        return True
    return isinstance(deficits, str)

def execute_action(action):
    if action == "isolate_agent":
        subprocess.run(["systemctl", "isolate", "cell-agent.target"])
    elif action == "retrain":
        subprocess.run(["python3", "/opt/cell/scripts/retrain_dispatch.py"])
    elif action == "rollback_model":
        shutil.copy(SNAPSHOTS_DIR / "model.bak", "/opt/cell/models/model.pt")
    elif action == "lock_goal_set":
        Path("/opt/cell/lock.goal").touch()
    elif action == "shutdown_agent30":
        subprocess.run(["systemctl", "stop", "agent_30"])

def handle_incident(data, ledger):
    uid = data.get("uid", "unknown")
    if not acl_check(uid):
        ledger.append(f"Incident access denied for UID: {uid}", pgp_sign(uid))
        return
    incident = data.get("incident")
    severity = data.get("severity", 0)
    actions = data.get("actions", [])
    fallback = data.get("fallback", [])
    sensitivity = data.get("sensitivity", "U")
    threat_level = data.get("threat_level", "unknown")
    profile_file = INCIDENT_PROFILE_DIR / f"{incident}.json"
    if profile_file.exists():
        with open(profile_file) as f:
            profile = json.load(f)
        actions = profile.get("actions", actions)
        fallback = profile.get("fallback", fallback)
        sensitivity = profile.get("sensitivity", sensitivity)
        threat_level = profile.get("threat_level", threat_level)
    ledger.append(f"Incident: {incident} | Severity: {severity} | Sensitivity: {sensitivity} | Threat: {threat_level}", pgp_sign(f"{incident}{severity}{sensitivity}{threat_level}"))
    for a in actions:
        execute_action(a)
    if severity >= 4:
        for fb in fallback:
            execute_action(fb)
    if incident and incident.startswith("deficit_"):
        agent_id = incident.replace("deficit_", "")
        deficits = data.get("deficits", [])
        generate_agent_30_task(agent_id, deficits, ledger, load_privkey())

def outlier_detection(stats, agent_id, score):
    scores = [x[1] for x in stats.get(agent_id, [])][-10:]
    if len(scores) > 1 and abs(scores[-1] - scores[0]) > 0.5:
        return True
    return False

incident_followup_map = {}

def generate_agent_30_task(agent_id, deficits, ledger, privkey):
    task_id = f"INT-{int(time.time())}"
    task = {
        "task_id": task_id,
        "targets": deficits,
        "target_agents": [agent_id],
        "mission_type": "OSINT+CODEINT",
        "depth": "deep_scan",
        "channels": ["tor", "academic", "code"],
        "constraints": ["no-posting", "signature-required"],
        "deliverables": ["raw_text", "vector_index", "source_cert"],
        "ttl": "4h",
        "sensitivity": "U"
    }
    tfile = TASKS_DIR / f"{task_id}.json"
    digest = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()
    signature = pgp_sign(json.dumps(task, sort_keys=True))
    envelope = {
        "task": task,
        "digest": digest,
        "signature": signature
    }
    with open(tfile, "w") as f:
        json.dump(envelope, f, indent=2)
    ledger.append(f"Generated agent_30 task: {task_id} | signature: {signature}", signature)
    incident_followup_map[task_id] = {
        "incident": f"deficit_{agent_id}",
        "agent": agent_id,
        "timestamp": int(time.time())
    }
    raft_apply(json.dumps(envelope))

def validate_agent_30_task(task_file, pubkey):
    with open(task_file, "r") as f:
        envelope = json.load(f)
    task = envelope["task"]
    sig = envelope.get("signature", "")
    digest = envelope.get("digest")
    expected_digest = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()
    if digest != expected_digest:
        raise Exception("Digest mismatch in agent_30 task!")
    js = json.dumps(task, sort_keys=True).encode()
    assert pgp_verify(js.decode(), sig)
    return True

def process_eval_files(ledger, pubkey, stats, trendlog, driftlog, resp_audit, anomaly_map, privkey):
    for f in AGENT_EVALS.glob("agent_*_eval.json"):
        with open(f, "r") as fp:
            data = json.load(fp)
        sig = data.get("signature")
        core = {k: v for k, v in data.items() if k != "signature"}
        js = json.dumps(core, sort_keys=True).encode()
        assert pgp_verify(js.decode(), sig)
        agent_id = data.get("agent_id")
        score = data.get("score", 1.0)
        ts = data.get("timestamp", int(time.time()))
        stats.setdefault(agent_id, []).append((ts, score))
        trendlog.setdefault(agent_id, []).append(score)
        if len(trendlog[agent_id]) > 5:
            last = trendlog[agent_id][-10:]
            avg = sum(last) / len(last)
            stdev = statistics.stdev(last) if len(last) > 1 else 0.0
            drift = max(last) - min(last)
            zscore = (score - avg) / stdev if stdev > 0 else 0.0
            driftlog[agent_id] = {"drift": drift, "avg": avg, "stdev": stdev, "zscore": zscore}
        resp_audit.setdefault(agent_id, []).append({
            "task": data.get("task_id"),
            "start_ts": data.get("start_ts"),
            "end_ts": data.get("end_ts"),
            "duration": (data.get("end_ts") or 0) - (data.get("start_ts") or 0)
        })
        anomaly_map.setdefault(agent_id, []).append({
            "score": score,
            "anomaly": data.get("anomaly_score", 0.0),
            "ts": ts
        })
        if outlier_detection(stats, agent_id, score):
            ledger.append(f"Outlier score detected for agent {agent_id}: {score}", pgp_sign(str(score)))
        if score < 0.6:
            deficits = data.get("deficits", [])
            if not validate_deficits(deficits):
                ledger.append(f"Invalid deficits structure for agent {agent_id}", pgp_sign(agent_id))
                continue
            generate_agent_30_task(agent_id, deficits, ledger, privkey)

def meta_feed_update(lockdown, safe, plugins, open_tasks, last_incident, stats, drift, anomaly_map, risk_scores):
    heatmap = sorted([(aid, sum(x["anomaly"] for x in items)/len(items)) for aid, items in anomaly_map.items() if items], key=lambda x: -x[1])
    top_5_anomalni_agenti = [x[0] for x in heatmap[:5]]
    feed = {
        "lockdown": lockdown,
        "safe_mode": safe,
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "active_plugins": plugins,
        "open_tasks": open_tasks,
        "last_incident": last_incident,
        "eval_trends": stats,
        "cognitive_drift": drift,
        "agent_anomaly_heatmap": anomaly_map,
        "risk_scores": risk_scores,
        "top_5_anomalni_agenti": top_5_anomalni_agenti,
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(META_FEED, "w") as f:
        json.dump(feed, f, indent=2)
    html = f"""
    <html><head><meta http-equiv="refresh" content="10"/><title>Kameleon Meta Feed</title></head>
    <body>
    <h1>Kameleon Status</h1>
    <pre>{json.dumps(feed, indent=2)}</pre>
    </body></html>
    """
    with open(STATUS_HTML, "w") as f:
        f.write(html)

def outbound_agent_30_proxy(task_file, ledger, pubkey):
    url = f"https://{AGENT_PROXY_HOST}:{AGENT_PROXY_PORT}/agent_proxy"
    cert = str(AGENT_PROXY_CERT)
    key = str(AGENT_PROXY_KEY)
    with open(task_file, "rb") as f:
        payload = f.read()
    try:
        resp = requests.post(url, data=payload, cert=(cert, key), verify=CA_CERT, timeout=30)
        if resp.status_code == 200:
            validate_agent_30_task(task_file, pubkey)
            ledger.append(f"agent_30_proxy_dispatched: {task_file} [valid]", pgp_sign(task_file))
        else:
            ledger.append(f"agent_30_proxy_failed: {task_file} [status {resp.status_code}]", pgp_sign(task_file))
    except Exception as e:
        ledger.append(f"agent_30_proxy_error: {task_file}: {str(e)}", pgp_sign(str(e)))
    req_dir = FOR_DIR / "requests"
    req_dir.mkdir(exist_ok=True)
    outname = req_dir / (Path(task_file).stem + ".resp")
    with open(outname, "wb") as out:
        out.write(resp.content if 'resp' in locals() and resp else b'')

def is_dag_valid(nodes, edges):
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        G.add_edge(e["from"], e["to"])
    if not nx.is_directed_acyclic_graph(G):
        return False
    for n in nodes:
        if G.out_degree(n["id"]) == 0 and not n.get("completed", False):
            return False
    return True

def meta_feed_task(ledger, stats, drift, anomaly_map):
    while True:
        plugins = [f.name for f in PLUGIN_DIR.glob("*.py")]
        open_tasks = [f.name for f in TASKS_DIR.glob("*.json")]
        last_incident = ""
        lockdown = LOCKDOWN_FLAG.exists()
        safe = SAFE_MODE_FLAG.exists()
        risk_scores = calculate_risk_score(stats, drift, anomaly_map)
        meta_feed_update(lockdown, safe, plugins, open_tasks, last_incident, stats, drift, anomaly_map, risk_scores)
        time.sleep(10)

def redteam_report(stats, drift, anomaly_map, ledger):
    report = {
        "eval_stats": stats,
        "cognitive_drift": drift,
        "anomaly_map": anomaly_map,
        "ledger_events": []
    }
    with open(CHAIN_FILE) as f:
        for line in f:
            entry = json.loads(line)
            if "Incident" in entry.get("event", "") or "ResourceAlert" in entry.get("event", "") or "Simulated incident" in entry.get("event", ""):
                report["ledger_events"].append(entry)
    with open(REDTEAM_REPORT, "w") as f:
        json.dump(report, f, indent=2)

def redteam_report_periodic(stats, drift, anomaly_map, ledger, interval=86400):
    while True:
        redteam_report(stats, drift, anomaly_map, ledger)
        time.sleep(interval)

def monitor_system_health(ledger):
    while True:
        cpu = psutil.cpu_percent(interval=5)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        if cpu > 95 or ram > 90 or disk > 95:
            ledger.append(f"ResourceAlert CPU:{cpu}% RAM:{ram}% DISK:{disk}%", pgp_sign(str(cpu) + str(ram) + str(disk)))
        audit_plugin_manipulation(ledger)
        time.sleep(30)

def redis_listener(ledger, pubkey, stats, trendlog, driftlog, resp_audit, anomaly_map, privkey):
    pubsub = REDIS.pubsub()
    pubsub.subscribe(list(CHANNELS.values()))
    for msg in pubsub.listen():
        if msg['type'] != 'message':
            continue
        try:
            payload = json.loads(msg['data'])
            ch = msg['channel'].decode()
            if ch == CHANNELS['incidents']:
                handle_incident(payload, ledger)
            elif ch == CHANNELS['supervisor']:
                ledger.append(f"Supervisor: {payload}", pgp_sign(json.dumps(payload)))
            elif ch == CHANNELS['eval']:
                process_eval_files(ledger, pubkey, stats, trendlog, driftlog, resp_audit, anomaly_map, privkey)
            elif ch == CHANNELS['plugin_audit']:
                audit_plugin_manipulation(ledger)
            elif ch == CHANNELS['dag_events']:
                nodes = payload.get("nodes", [])
                edges = payload.get("edges", [])
                if not is_dag_valid(nodes, edges):
                    ledger.append("DAG inconsistency detected.", pgp_sign("DAG inconsistency detected"))
        except Exception as e:
            ledger.append(f"RedisListenerError: {str(e)}", pgp_sign(str(e)))

def simulate_incident(name, ledger):
    profile_file = INCIDENT_PROFILE_DIR / f"{name}.json"
    if profile_file.exists():
        with open(profile_file) as f:
            profile = json.load(f)
        for action in profile.get("actions", []):
            execute_action(action)
        ledger.append(f"Simulated incident: {name}", pgp_sign(name))

def require_otp():
    otp_secret = os.environ.get("ORCH_OTP_SECRET")
    if not otp_secret:
        print("Ni nastavljenega OTP secret.")
        sys.exit(1)
    code = input("Vnesi OTP: ")
    if not pyotp.TOTP(otp_secret).verify(code):
        print("OTP napaka!")
        sys.exit(1)

def handle_cli():
    ledger = HashChainLedger(CHAIN_FILE)
    pubkey = load_pubkey()
    privkey = load_privkey()
    stats, trendlog, drift, resp_audit, anomaly_map = {}, {}, {}, {}, {}
    args = sys.argv
    if len(args) < 2:
        print("Usage: python3 super_orchestrator.py [status|lockdown|restart|simulate|verifyhash|snapshot_create|snapshot_restore|redteam_report|export_chainpack|backup]")
        return
    cmd = args[1]
    if cmd in ("lockdown", "restart", "snapshot_restore"):
        require_otp()
    if cmd == "status":
        print(json.dumps(json.load(open(META_FEED)), indent=2))
    elif cmd == "lockdown":
        LOCKDOWN_FLAG.touch()
        ledger.append("LOCKDOWN_MODE manually activated", pgp_sign("LOCKDOWN"))
    elif cmd == "restart":
        SAFE_MODE_FLAG.touch()
        subprocess.run(["systemctl", "restart", "cell"])
        ledger.append("SAFE_MODE restart manual", pgp_sign("SAFE_MODE"))
    elif cmd == "simulate" and len(args) > 2:
        simulate_incident(args[2], ledger)
    elif cmd == "verifyhash":
        print(f"Hashchain OK. {ledger.verify_chain()} entries checked.")
    elif cmd == "snapshot_create" and len(args) > 2:
        memory_snapshot(ledger)
        ledger.append(f"Snapshot created for {args[2]}", pgp_sign(args[2]))
    elif cmd == "snapshot_restore" and len(args) > 3:
        snapshot_restore(args[2], args[3])
        ledger.append(f"Snapshot restored for {args[2]}, version {args[3]}", pgp_sign(args[2]+args[3]))
    elif cmd == "redteam_report":
        redteam_report(stats, drift, anomaly_map, ledger)
        print(f"RedTeam report written: {REDTEAM_REPORT}")
    elif cmd == "export_chainpack":
        export_chainpack(ledger)
        print("Chainpack exported.")
    elif cmd == "backup":
        backup_configuration()
        print("Backup completed.")

def main():
    import raftos
    loop = asyncio.get_event_loop()
    loop.run_until_complete(raft_init())
    ledger = HashChainLedger(CHAIN_FILE)
    pubkey = load_pubkey()
    privkey = load_privkey()
    stats, trendlog, drift, resp_audit, anomaly_map = {}, {}, {}, {}, {}

    Thread(target=redis_listener, args=(ledger, pubkey, stats, trendlog, drift, resp_audit, anomaly_map, privkey), daemon=True).start()
    Thread(target=monitor_system_health, args=(ledger,), daemon=True).start()
    Thread(target=meta_feed_task, args=(ledger, stats, drift, anomaly_map), daemon=True).start()
    Thread(target=redteam_report_periodic, args=(stats, drift, anomaly_map, ledger), daemon=True).start()
    Thread(target=websocket_server, daemon=True).start()
    Thread(target=memory_snapshot_daemon, args=(ledger,), daemon=True).start()
    Thread(target=monitor_config_integrity, args=(ledger,), daemon=True).start()
    Thread(target=rotate_keys_if_needed, daemon=True).start()
    Thread(target=siem_health_monitor, args=(ledger,), daemon=True).start()
    def periodic_siem_export():
        while True:
            export_chain_to_siem()
            time.sleep(3600)
    Thread(target=periodic_siem_export, daemon=True).start()
    while True:
        try:
            process_eval_files(ledger, pubkey, stats, trendlog, drift, resp_audit, anomaly_map, privkey)
            check_integrity(ledger)
            with open(EVAL_STATS, "w") as f:
                json.dump(stats, f, indent=2)
            time.sleep(60)
        except Exception as e:
            ledger.append(f"MainLoopError: {str(e)}", pgp_sign(str(e)))
            oob_beacon(str(e))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        handle_cli()
    else:
        main()
