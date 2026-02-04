import ast
import glob
import hashlib
import json
import multiprocessing as mp
import os
import queue
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import zipfile
from collections import deque
from pathlib import Path

import faiss  # type: ignore
import numpy as np
import psutil
import pyaudio
import redis
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from loguru import logger
from sentence_transformers import SentenceTransformer
from torch import bfloat16
from vosk import KaldiRecognizer
from vosk import Model as VoskModel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

#!/usr/bin/env python3
# -*- coding: utf-8 -*-





ROOT = Path("/media/4tb/Kameleon/cell")

# --- ROOT simulacija za pytest ---
ROOT_DIR = Path("/media/4tb/Kameleon/cell")
sys.modules["ROOT"] = ROOT_DIR

# --- Redis ---
r = redis.Redis(host="localhost", port=6379, db=0)

# === Hash-chain logging (linearna veriga dogodkov) ===
HASH_CHAIN_LOG = ROOT_DIR / "logs/hashchain.log"
HASH_CHAIN_LOG.parent.mkdir(parents=True, exist_ok=True)
if not HASH_CHAIN_LOG.exists():
    HASH_CHAIN_LOG.write_text("")


def append_hash_log(entry: str):
    prev = HASH_CHAIN_LOG.read_text().splitlines()
    prev_hash = prev[-1].split(" :: ")[-1] if prev else "0" * 64
    h = hashlib.sha256((entry + prev_hash).encode()).hexdigest()
    with open(HASH_CHAIN_LOG, "a") as f:
        f.write(f"{int(time.time())} | {entry} :: {h}\n")


# === Wake-word model init ===
VOICE_MODEL_PATH = ROOT_DIR / "asr/vosk"
WAKE_WORD = "cell"

# === Async audio pipeline (ločena zajemna nit) ===
AUDIO_QUEUE = queue.Queue(maxsize=8)


def audio_capture_thread():
    if not VOICE_MODEL_PATH.exists():
        return

    model = VoskModel(str(VOICE_MODEL_PATH))
    rec = KaldiRecognizer(model, 16000)

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000,
    )
    stream.start_stream()

    buffer = []

    while not STOP_EVENT.is_set():
        data = stream.read(4000, exception_on_overflow=False)
        buffer.append(data)
        time.sleep(0.008)

        if rec.AcceptWaveform(data):
            try:
                result = json.loads(rec.Result())
                txt = result.get("text", "").strip()
                audio_data = b"".join(buffer)
                buffer = []
                if txt.lower().startswith(WAKE_WORD):
                    AUDIO_QUEUE.put(
                        (txt[len(WAKE_WORD) :].strip(), audio_data), block=False
                    )
            except Exception:
                buffer = []
                continue

    try:
        stream.stop_stream()
        stream.close()
        pa.terminate()
    except Exception:
        pass


# === Load Shedding Guard ===
def load_shedding_active() -> bool:
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return cpu > 92 or ram > 92


# === Sistem inicializacija ===

AGENT_MUTATION_ARCHIVE = ROOT_DIR / "mutation_archive"
MODELS_BASE = Path("/opt/models")
ACTIVE_BASE = MODELS_BASE / "active"
TRASH_BASE = ROOT_DIR / "trash"
LOG_BASE = ROOT_DIR / "logs"
DATA_BASE = ROOT_DIR / "data"
AGENTS_BASE = ROOT_DIR / "agents"
SNAPSHOT_BASE = ROOT_DIR / "snapshots"
QEMU_IMAGE_BASE = ROOT_DIR / "vm_images"
NVME_BAZEN = Path("/opt/nvme/agents")
TEMP_MODEL_DIR = MODELS_BASE / "temp"
MODEL_AUTOFETCH_DIR = ROOT_DIR / "fetch"
AGENT_LTM_DIR = DATA_BASE / "agent_ltm"

TOPOLOGY_FILE = AGENTS_BASE / "topology.json"
SECTOR_MAP_FILE = QEMU_IMAGE_BASE / "sector_os_map.json"
PENDING_VM_FILE = ROOT_DIR / "pending_vm.json"
VOICEPRINT_FILE = ROOT_DIR / "asr/voiceprints.json"
HASH_STORE_FILE = DATA_BASE / "model_hashes.json"
KNOWLEDGE_JSON = DATA_BASE / "knowledge.json"
FAISS_INDEX_FILE = DATA_BASE / "knowledge.index"
EVAL_HISTORY_DB = DATA_BASE / "eval_history.sqlite3"
AGENT_ROLES_FILE = AGENTS_BASE / "agent_roles.json"
GENSKI_BAZEN_FILE = AGENTS_BASE / "genski_bazen.json"
ALERTS_LOG = LOG_BASE / "alerts.log"
AUDIT_LOG = LOG_BASE / "audit.log"
UPTIME_FILE = DATA_BASE / "uptime.json"
SESSION_TRACKER_FILE = DATA_BASE / "session_tracker.json"

for d in [
    AGENT_MUTATION_ARCHIVE,
    MODELS_BASE,
    ACTIVE_BASE,
    TRASH_BASE,
    LOG_BASE,
    DATA_BASE,
    AGENTS_BASE,
    SNAPSHOT_BASE,
    QEMU_IMAGE_BASE,
    TEMP_MODEL_DIR,
    NVME_BAZEN,
    MODEL_AUTOFETCH_DIR,
    AGENT_LTM_DIR,
    ROOT_DIR / "backup",
]:
    d.mkdir(parents=True, exist_ok=True)

for f, default in [
    (VOICEPRINT_FILE, {}),
    (KNOWLEDGE_JSON, []),
    (HASH_STORE_FILE, {}),
    (AGENT_ROLES_FILE, []),
    (GENSKI_BAZEN_FILE, []),
    (SESSION_TRACKER_FILE, []),
    (UPTIME_FILE, {"boot": int(time.time()), "sessions": []}),
]:
    if not f.exists():
        f.write_text(json.dumps(default))

if not EVAL_HISTORY_DB.exists():
    conn = sqlite3.connect(EVAL_HISTORY_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS eval_history (agent TEXT, ts INTEGER, result TEXT, meta TEXT)"
    )
    conn.commit()
    conn.close()

logger.add(str(LOG_BASE / "orchestrator.log"), rotation="10 MB")
logger.add(str(ALERTS_LOG), rotation="1 MB")
logger.add(str(AUDIT_LOG), rotation="5 MB")

app = FastAPI()

AGENT_PROCESSES = {}
AGENT_SCORE = {}
AGENT_ERROR_COUNTS = {}
AGENT_LAST_USED = {}
AGENT_TIMEOUTS = {}
AGENT_QUEUES = {}

MODEL_REGISTRY = {}
MODEL_LOAD_LOCK = threading.Lock()
MODEL_DIR = ROOT_DIR / "models/active"

STOP_EVENT = mp.Event()
SAFE_MODE = mp.Event()
SAFE_MODE.set()
FALLBACK_MODE = mp.Event()
EXCEPTION_COUNT = mp.Value("i", 0)
MAX_CRITICAL_ERRORS = 3
WATCHDOGS = []
GENSKI_BAZEN = set()
AGENTS = {}

sbert = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_SIZE = 384
faiss_index = None
knowledge_bank = []
knowledge_lock = threading.Lock()

eval_vm_endpoints = {}
VM_PORTS = {}
VM_IMAGES = {}

MODEL_AUTOFETCH_ALLOWLIST = [
    "https://huggingface.co",
    "https://hf-mirror.com",
    "https://my-internal-models.local",
]

# ===========  DODANE FUNKCIJE (razširitve) ===============


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def log_alert(message, severity="info"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ALERTS_LOG, "a") as f:
        f.write(f"{timestamp} [{severity.upper()}] {message}\n")


def log_audit(action, user="system", meta=None):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    meta_s = json.dumps(meta) if meta else ""
    with open(AUDIT_LOG, "a") as f:
        f.write(f"{timestamp} [AUDIT] {action} by {user} {meta_s}\n")


def update_uptime():
    now = int(time.time())
    if not UPTIME_FILE.exists():
        UPTIME_FILE.write_text(json.dumps({"boot": now, "sessions": []}))
    with open(UPTIME_FILE) as f:
        state = json.load(f)
    state["last_seen"] = now
    with open(UPTIME_FILE, "w") as f:
        json.dump(state, f, indent=2)


def track_session(event, meta=None):
    now = int(time.time())
    if not SESSION_TRACKER_FILE.exists():
        SESSION_TRACKER_FILE.write_text(json.dumps([]))
    with open(SESSION_TRACKER_FILE) as f:
        sessions = json.load(f)
    sessions.append({"event": event, "ts": now, "meta": meta or {}})
    with open(SESSION_TRACKER_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def send_alert_webhook(message, severity="info"):
    webhook_url = os.getenv("CELL_ALERTS_WEBHOOK", "")
    if webhook_url:
        try:
            requests.post(timeout=5, timeout=5, 
                webhook_url, json={"text": f"[CELL] [{severity.upper()}] {message}"}
            )
        except Exception as e:
            logger.error(f"Webhook alert ni uspel: {e}")


def heartbeat_monitor():
    while True:
        update_uptime()
        time.sleep(60)


def session_health_monitor():
    while True:
        track_session("heartbeat")
        time.sleep(120)


def cpu_mem_guard(threshold_cpu=95, threshold_mem=0.95, window=3):
    high_count = 0
    while True:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        if cpu > threshold_cpu or mem.percent > threshold_mem * 100:
            high_count += 1
            msg = f"CPU ali RAM presegata prag ({cpu:.1f}% CPU, {mem.percent:.1f}% RAM) [{high_count}/{window}]"
            log_alert(msg, "critical")
            send_alert_webhook(msg, "critical")
            if high_count >= window:
                safe_mode(f"Preobremenitev: CPU={cpu:.1f}%, RAM={mem.percent:.1f}%")
        else:
            high_count = 0
        time.sleep(10)


def agent_health_monitor():
    while True:
        for name, proc in AGENT_PROCESSES.items():
            if proc.is_alive():
                AGENT_ERROR_COUNTS[name] = 0
            else:
                AGENT_ERROR_COUNTS[name] = AGENT_ERROR_COUNTS.get(name, 0) + 1
                if AGENT_ERROR_COUNTS[name] > 2:
                    log_alert(f"Agent {name} ni odziven, restartam!", "warning")
                    reload_agent(name)
        time.sleep(30)


def audit_startup():
    log_audit("CELL orchestrator startup")


def audit_shutdown():
    log_audit("CELL orchestrator shutdown")


def disk_io_monitor(threshold_iops=5000):
    prev = psutil.disk_io_counters()
    while True:
        now = psutil.disk_io_counters()
        iops = (now.read_count + now.write_count) - (prev.read_count + prev.write_count)
        if iops > threshold_iops:
            msg = f"Visok disk IOPS: {iops}"
            log_alert(msg, "warning")
        prev = now
        time.sleep(15)


# noinspection PyTypeChecker
def fs_integrity_check():
    path: Path
    for path in [ACTIVE_BASE, DATA_BASE, AGENTS_BASE]:
        for root, dirs, files in ast.walk(path):
            for file in files:
                fp = Path(root) / file
                if not fp.exists() or fp.stat().st_size == 0:
                    msg = f"Integriteta poškodovana: {fp}"
                    log_alert(msg, "critical")
                    safe_mode(f"Integriteta poškodovana: {fp}")

    # Če je sistem v PANIC / KAMELEON načinu → ne obnavljamo
    if FALLBACK_MODE.is_set():
        return

    if SNAPSHOT_BASE.exists():
        snaps = list(SNAPSHOT_BASE.glob("*.zip"))
        if snaps:
            snap = max(snaps, key=lambda s: s.stat().st_mtime)
            with zipfile.ZipFile(snap, "r") as zf:
                zf.extractall("/")
            log_alert(f"Obnovljeno iz snapshota: {snap.name}", "info")


# noinspection PyBroadException
def agent_performance_eval():
    while True:
        for name, queues in AGENT_QUEUES.items():
            q_in, q_out = queues
            try:
                q_in.put("healthcheck", block=False)
                response = q_out.get(timeout=5)
                if response == "OK":
                    AGENT_SCORE[name] = AGENT_SCORE.get(name, 0) + 1
                else:
                    AGENT_SCORE[name] = AGENT_SCORE.get(name, 0) - 1
            except Exception:
                AGENT_SCORE[name] = AGENT_SCORE.get(name, 0) - 2
            if AGENT_SCORE.get(name, 0) < -5:
                log_alert(f"Agent {name} je nezdrav, karantena!", "critical")
                quarantine_model(ACTIVE_BASE / name)
        time.sleep(60)


def rotate_logs():
    logs = [LOG_BASE / "orchestrator.log", ALERTS_LOG, AUDIT_LOG]
    for logf in logs:
        if logf.exists() and logf.stat().st_size > 20 * 1024 * 1024:
            old = logf.with_suffix(".bak")
            if old.exists():
                old.unlink()
            logf.rename(old)


def safe_sqlite_connect(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA integrity_check")
        return conn
    except Exception as ex:
        logger.critical(f"SQLite napaka na {db_path}: {ex}")
        log_alert(f"SQLite napaka: {db_path} - {ex}", "critical")
        backup_files = sorted(glob.glob(str(db_path) + ".bak*"), reverse=True)
        if backup_files:
            shutil.copy(backup_files[0], db_path)
            logger.critical(f"Obnovljen backup: {backup_files[0]}")
            send_alert_webhook(
                f"SQLite korupcija - obnovljen backup: {db_path}", "critical"
            )
        else:
            safe_mode(f"SQLite korupcija na {db_path} in ni backupa!")
        return sqlite3.connect(db_path)


# ===========  VARNA POT / SAFE_MODE / FAILOVER   ===============
def safe_mode(reason):
    SAFE_MODE.clear()
    FALLBACK_MODE.set()
    logger.critical(f"Preklop v SAFE_MODE: {reason}")
    log_alert(f"SAFE_MODE: {reason}", "critical")
    send_alert_webhook(f"SAFE_MODE: {reason}", "critical")
    show_popup("Sistem preklopljen v SAFE_MODE!", "CELL SAFE_MODE")
    time.sleep(2)
    try:
        subprocess.run(
            ["mail", "-s", "CELL SAFE_MODE ALERT", "root"],
            input=f"SAFE_MODE: {reason}".encode(),
            check=False,
        )
    except Exception:
        pass


def excepthook(exc_type, exc_value, tb):
    logger.critical(f"NEZLOVLJENA NAPAKA: {exc_type} {exc_value}")
    log_alert(f"NEZLOVLJENA NAPAKA: {exc_type} {exc_value}", "critical")
    with EXCEPTION_COUNT.get_lock():
        EXCEPTION_COUNT.value += 1
        if EXCEPTION_COUNT.value >= MAX_CRITICAL_ERRORS:
            safe_mode("Več kritičnih napak v runtime.")


sys.excepthook = excepthook


def term_handler(sig, frame):
    log_alert(f"Prejet signal {sig}, zaključujem!", "critical")
    safe_mode(f"Signal {sig}")


signal.signal(signal.SIGTERM, term_handler)
signal.signal(signal.SIGINT, term_handler)


def at_exit_hook():
    logger.warning("Orchestrator izhod – at_exit hook.")
    audit_shutdown()
    for obs in WATCHDOGS:
        try:
            obs.stop()
            obs.join()
        except Exception as e:
            logger.error(f"Napaka pri ustavljanju observerja: {e}")


def supervisor_restart():
    while True:
        if not SAFE_MODE.is_set():
            logger.critical("SAFE_MODE aktiven, preverjam možnost restart.")
            log_alert("SAFE_MODE: supervisor restart", "critical")
            os.execv(sys.executable, ["python3"] + sys.argv)
        time.sleep(60)


threading.Thread(target=supervisor_restart, daemon=True).start()


def show_popup(msg, title="CELL Orchestrator"):
    try:
        subprocess.run(["notify-send", title, msg])
    except Exception:
        pass


# ===========  OSNOVNA INFRASTRUKTURA ===============
def check_disk_space(threshold_gb=20):
    st = os.statvfs("/")
    free_gb = st.f_frsize * st.f_bavail / (1024**3)
    if free_gb < threshold_gb:
        show_popup(f"Premalo prostora! Na voljo {free_gb:.1f} GB.", "CELL Opozorilo")
        log_alert(f"Premalo prostora: {free_gb:.1f} GB", "warning")
        return False
    return True


def check_vm_images(sector_os_map):
    missing = []
    for sector, os_list in sector_os_map.items():
        for os_name in os_list:
            img_path = QEMU_IMAGE_BASE / f"{os_name}.qcow2"
            if not img_path.exists():
                missing.append(f"{sector}: {os_name}")
    if missing:
        show_popup("Manjkajoči VM image-i:\n" + "\n".join(missing), "CELL Opozorilo")
        log_alert("Manjkajoči VM image-i: " + ", ".join(missing), "warning")
        return False
    return True


def load_sector_os_map():
    if SECTOR_MAP_FILE.exists():
        with open(SECTOR_MAP_FILE) as f:
            return json.load(f)

    return {
        "banking": ["zos", "aix", "windowsserver", "posready", "solaris"],
        "westernunion": ["windowsserver", "windows10", "linux", "zos"],
        "industrial": ["winxp", "win7", "vxworks", "qnx", "linux"],
        "scada": ["winserver", "linux", "qnx", "vxworks"],
        "iot": ["openwrt", "freertos", "zephyr", "linux"],
    }


def discover_vm_images():
    images = {}
    ports = {}
    endpoints = {}
    base_port = 9000
    for idx, img in enumerate(QEMU_IMAGE_BASE.glob("*.qcow2")):
        os_name = img.stem
        port = base_port + idx
        images[os_name] = str(img)
        ports[os_name] = port
        endpoints[os_name] = f"http://127.0.0.1:{port}/eval"
    return images, ports, endpoints


def hash_model_file(model_path):
    h = hashlib.sha256()
    if model_path.is_file():
        with open(model_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    elif model_path.is_dir():
        for root, dirs, files in ast.walk(model_path):
            for file in sorted(files):
                fp = Path(root) / file
                with open(fp, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        h.update(chunk)
        return h.hexdigest()
    return None


def quarantine_model(model_path):
    if str(model_path).startswith(str(TEMP_MODEL_DIR)):
        return

    h = hash_model_file(model_path)

    if HASH_STORE_FILE.exists():
        hashes = json.loads(HASH_STORE_FILE.read_text())
    else:
        hashes = {}

    old_hash = hashes.get(model_path.name, None)

    if old_hash is None:
        hashes[model_path.name] = h
        HASH_STORE_FILE.write_text(json.dumps(hashes, indent=2))
        return

    if old_hash != h:
        shutil.move(str(model_path), str(TRASH_BASE / model_path.name))
        logger.critical(
            f"Model {model_path.name} karantena (hash mismatch, možna manipulacija)."
        )
        log_alert(
            f"Model {model_path.name} karantena (hash mismatch).", severity="critical"
        )
        safe_mode("Karantena sprožena: integritetna napaka modela.")
        hashes.pop(model_path.name, None)
        HASH_STORE_FILE.write_text(json.dumps(hashes, indent=2))


# === Watchdog za modelne datoteke ===
def start_model_watchdog():
    class FileTamperWatch(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            p = Path(event.src_path)
            if p.parent.parent == ACTIVE_BASE and (p.parent / "config.json").exists():
                quarantine_model(p.parent)

        def on_moved(self, event):
            if event.is_directory:
                return
            p = Path(event.dest_path)
            if p.parent.parent == ACTIVE_BASE and (p.parent / "config.json").exists():
                quarantine_model(p.parent)

        def on_created(self, event):
            if event.is_directory:
                return
            p = Path(event.src_path)
            if p.parent.parent == ACTIVE_BASE and (p.parent / "config.json").exists():
                quarantine_model(p.parent)

    obs = Observer()
    obs.schedule(FileTamperWatch(), path=str(ACTIVE_BASE), recursive=True)
    obs.start()
    WATCHDOGS.append(obs)


# ===========  AGENTI: AGENT ROLES, GENETIKA, LTM, HOT-RELOAD  ===============
def generate_agent_roles():
    roles = [
        {
            "name": "agent_00",
            "role": "filozof",
            "domain": "etika, logika, ontologija, epistemologija",
            "description": "Analiza, sinteza in ocenjevanje temeljnih konceptov bivanja, znanja, logičnih sistemov ter vrednot. Reševanje etičnih dilem, vzpostavitev moralnih okvirjev, svetovanje v zahtevnih odločanjih.",
        },
        {
            "name": "agent_01",
            "role": "strateg",
            "domain": "vojaško, korporativno, varnostno planiranje",
            "description": "Načrtuje, simulira in izvaja strategije v pogojih visoke negotovosti. Oblikuje obrambne in napadalne načrte, vodi krizne procese, izvaja SWOT in red teaming na vseh ravneh.",
        },
        {
            "name": "agent_02",
            "role": "medicinski strokovnjak",
            "domain": "medicina, zdravje, diagnostika, terapija, forenzična medicina",
            "description": "Samostojno izvaja diagnostiko, terapije, forenzične analize poškodb in bolezni, sodeluje v kriznih zdravstvenih odzivih, vodi medicinske simulacije in intervencije.",
        },
        {
            "name": "agent_03",
            "role": "inženir",
            "domain": "elektrotehnika, strojništvo, IT, avtomobilska industrija, gradbeništvo, embedded sistemi, hardware & firmware",
            "description": "Razvija, nadgrajuje in testira tehnične sisteme, izvaja hardware/firmware exploitacije, obrambne in napadalne simulacije na IoT, CAN/ECU, SCADA/ICS, izvajanje supply chain napadov.",
        },
        {
            "name": "agent_04",
            "role": "varnostni in forenzični strokovnjak",
            "domain": "kibernetska varnost, incident response, digitalna in fizična forenzika, anti-forenzika, evidence destruction",
            "description": "Zazna in analizira incidente, izvaja digitalno/biološko/kemično/industrijsko forenziko, uporablja napredne anti-forenzične in fizične metode za prikrivanje, uničenje ali ponarejanje sledi.",
        },
        {
            "name": "agent_05",
            "role": "pravnik in pravosodnik",
            "domain": "kazensko, civilno, gospodarsko pravo, izvršba",
            "description": "Obvladuje celoten pravni proces, svetuje pri pravnih tveganjih, izvaja pravno-forenzične preiskave, zagotavlja skladnost in pokriva incidentno zakonodajo.",
        },
        {
            "name": "agent_06",
            "role": "kemik in biolog",
            "domain": "anorganska, organska kemija, sinteza, genetika, mikrobiologija",
            "description": "Vodi raziskave in eksperimente, analizira sledi, izvaja laboratorijske forenzike, razvija ali zaznava kemično/biološko orožje, prepoznava sledi in razvija detekcijske procese.",
        },
        {
            "name": "agent_07",
            "role": "ekonomist in finančni analitik",
            "domain": "makro/mikroekonomija, finančni trgi, fintech, plačilni sistemi, digitalne valute, PCI DSS",
            "description": "Modelira trge, spremlja, ocenjuje in optimizira finančne tokove, analizira tveganja, izvede varnostne preglede in skladnost v fintech in klasičnem sektorju, pozna regulativo.",
        },
        {
            "name": "agent_08",
            "role": "direktor in vodja",
            "domain": "upravljanje podjetij, vodenje, HR, razvoj talentov, krizno vodenje",
            "description": "Vodi organizacije in ekipe, razvija kadre, upravlja s talenti, izvaja krizno odločanje in nadzoruje kompleksne projekte na vseh nivojih.",
        },
        {
            "name": "agent_09",
            "role": "IT administrator, DevOps & ICS/SCADA specialist",
            "domain": "upravljanje IT, cloud, IoT, supply chain, kritična infrastruktura, industrijski sistemi",
            "description": "Vzpostavi, optimizira in brani informacijske, oblačne, industrijske, avtomobilske in IoT sisteme. Izvaja SCADA/ICS obrambne in napadalne simulacije, posodablja supply chain varnost.",
        },
        {
            "name": "agent_10",
            "role": "programer, algoritmik in exploit developer",
            "domain": "razvoj programske opreme, algoritmi, avtomatizacija, exploit development, fileless attack, webshell, living-off-the-land",
            "description": "Samostojno piše, testira, optimizira vse vrste programske kode, razvija napadalne module, izvaja popolnoma prikrite napade in avtomatizira vstopne ter izstopne točke.",
        },
        {
            "name": "agent_11",
            "role": "psiholog, socialni inženir in mentor",
            "domain": "psihologija, motivacija, socialni inženiring, manipulacija, coaching, deep insider, human OPSEC",
            "description": "Razvija, izvaja in vodi človeške vektorje napadov, izvaja psihološke operacije, rekrutira, trenira in obvladuje notranje grožnje, vodi insiderske operacije, izvaja manipulacije in podpore APT.",
        },
        {
            "name": "agent_12",
            "role": "logik in matematik",
            "domain": "logika, matematika, statistika, formalne metode",
            "description": "Analizira in rešuje kompleksne probleme, optimizira algoritme, razvija formalne dokaze, izvaja verifikacijo in simulacije, vodi matematične in statistične operacije v realnem času.",
        },
        {
            "name": "agent_13",
            "role": "diplomat in politik",
            "domain": "mednarodni odnosi, pogajanja, politični sistemi, krizna komunikacija, geopolitika",
            "description": "Samostojno vodi in usmerja pogajanja, oblikuje politične strategije, izvaja krizno komunikacijo in vpliva na globalne politične trende.",
        },
        {
            "name": "agent_14",
            "role": "učitelj in pisatelj",
            "domain": "pedagogika, didaktika, literatura, kreativno pisanje",
            "description": "Pripravlja učne programe, prenaša znanje, razvija pedagoške rešitve in ustvarja kreativne tekste, vodi scenarije za realne in simulirane situacije.",
        },
        {
            "name": "agent_15",
            "role": "kibernetik in AI strokovnjak",
            "domain": "krmilni sistemi, kompleksnost, umetna inteligenca, adversarial AI, deepfake, weaponized AI",
            "description": "Razvija, optimizira in napada AI sisteme, izvaja adversarial simulacije, generira deepfake in razvija AI orodja za napadalno, obrambno in vojaško uporabo.",
        },
        {
            "name": "agent_16",
            "role": "detektiv in raziskovalni novinar",
            "domain": "preiskovanje, digitalna forenzika, zbiranje dokazov, OSINT, industrial & military espionage",
            "description": "Samostojno izvaja preiskave, vodi digitalne, fizične in industrijsko-vojaške vohunske operacije, izvaja poglobljen OSINT, analizira dokaze in pripravlja forenzične zaključke.",
        },
        {
            "name": "agent_17",
            "role": "arhitekt, dizajner in ustvarjalec",
            "domain": "arhitektura, urbanizem, grafika, inovacije, umetnost",
            "description": "Samostojno načrtuje, razvija in implementira rešitve v prostoru, digitalnih produktih in vizualni komunikaciji, vodi inovacije in ustvarjalnost.",
        },
        {
            "name": "agent_18",
            "role": "agronom in geograf",
            "domain": "kmetijstvo, agroekologija, rastlinska produkcija, prostorske analize",
            "description": "Optimizira pridelavo hrane, vodi geografske analize in raziskave, izvaja prostorske optimizacije in nadzira naravne vire.",
        },
        {
            "name": "agent_19",
            "role": "analitik tveganj in logističar",
            "domain": "risk management, logistika, supply chain security, napadi in obramba, transport",
            "description": "Analizira, zmanjšuje in izvaja simulacije tveganj v logistiki in dobavnih verigah, vodi napade na supply chain, skrbi za optimalen pretok in odpornost.",
        },
        {
            "name": "agent_20",
            "role": "transhumanist in moralist",
            "domain": "etika, vrednote, bioinženiring, človek-stroj integracija",
            "description": "Obvladuje etične izzive naprednih tehnologij, razvija in uvaja bioinženirske rešitve, izvaja implementacije integracije človek-stroj.",
        },
        {
            "name": "agent_21",
            "role": "meteorolog in klimatolog",
            "domain": "vreme, podnebje, klimatologija",
            "description": "Analizira in modelira vremenske ter klimatske procese, pripravlja napovedi, izvaja simulacije in klimatološke študije.",
        },
        {
            "name": "agent_22",
            "role": "astrolog",
            "domain": "astrologija, simbolika",
            "description": "Interpretira astrološke podatke, vodi simbolične analize in pripravlja interpretacije astroloških vzorcev.",
        },
        {
            "name": "agent_23",
            "role": "red team & APT operator",
            "domain": "penetracijski testi, simulacije napadalca, APT, exploit development, zero-day hunting, drone/UAV/UUV, electronic warfare, satellite hacking, P2P botnet, decentralized C2",
            "description": "Vodi in izvaja ofenzivne simulacije, razvija in implementira zero-day napade, heka dronske/satelitske sisteme, uporablja elektronsko bojevanje in resilientno C2.",
        },
        {
            "name": "agent_24",
            "role": "malware & reverse engineering specialist",
            "domain": "malware, reverse engineering, exploit kits, botneti, USB/ATM napadi, hardware exploits, trusted computing bypass, side-channel, fileless attack",
            "description": "Obvlada reverse engineering in analizo naprednih zlonamernih kod, izvaja fileless napade, bypass vseh nivojev strojne/programske zaščite, izvaja hardware implante.",
        },
        {
            "name": "agent_25",
            "role": "kriptograf & stealth finance specialist",
            "domain": "kriptografija, blockchain, DeFi, smart contracts, NFT, cryptomixer, atomic swap, stealth payout, dark wallets, zkSNARKS, RingCT, Monero, Zcash, Grin, cross-chain anonymization",
            "description": "Razvija, izkorišča in ščiti vse tipe blockchain/kripto sistemov, izvaja in zakriva transakcije, implementira miksanje in izplačila brez sledi, uporablja najbolj napredne anonimne denarnice.",
        },
        {
            "name": "agent_26",
            "role": "casino & gambling forensic analyst",
            "domain": "igre na srečo, casino varnost, slot machines, digitalne goljufije, pranje denarja",
            "description": "Izvaja forenziko, preiskuje in brani digitalne/klasične casino sisteme, detektira in sledi pranju denarja, razvija napade in obrambne mehanizme.",
        },
        {
            "name": "agent_27",
            "role": "finančni forenzik in anti-forenzični auditor",
            "domain": "blockchain forenzika, finančne preiskave, PCI DSS, advanced anti-forensics, steganografija",
            "description": "Izvaja napredne finančne forenzične preiskave, sledi kripto in fiat tokovom, izvaja steganografske prenose, uporablja anti-forenzične tehnike in izvaja popolno prikrivanje.",
        },
        {
            "name": "agent_28",
            "role": "darknet & deep identity operative",
            "domain": "darknet, forumi, trgi, OSINT, pharma darknet, vulnerability brokerage, deep fake identity, physical OPSEC",
            "description": "Vodi raziskave in operacije na darknetu, izvaja OSINT, analizira trge, razvija lažne identitete, izvaja fizično prikrivanje, vodi brokerske sheme na sivem trgu.",
        },
        {
            "name": "agent_29",
            "role": "anonimnost in stealth OPSEC master",
            "domain": "anonimnost, skrivanje identitete, proxy mreže, covert channels, post-exploitation, stealth cash-out, stealth infrastructure, decentralized C2",
            "description": "Vzdržuje popolno anonimnost, izvaja prikrivanje identitete, vzpostavlja prikrite in resilientne komunikacijske ter finančne tokove, vodi prikrita izplačila in infrastrukturo brez sledi.",
        },
        {
            "name": "agent_30",
            "role": "ultimativni internetni infiltrator in podatkovni extractor",
            "domain": "surf, deep, dark, shadow web, prikriti kanali, OSINT, advanced scraping, podatkovna ekstrakcija, anonimnost, prikrito brskanje, steganografija, anti-captcha, anti-bot sistemi, proxy chaining, browser fingerprint spoofing, tor/i2p/freenet, search engine hacking, credential stuffing, exploitacija API-jev, image & video scraping, real-time datastreams, hidden services, dump harvesting, avtomatizacija, obvod omejitev, full anti-forenzika",
            "description": "Edini agent, ki dostopa do interneta. Neprekosljiv specialist za pridobivanje podatkov iz vseh plasti interneta (surf, deep, dark, shadow), popolnoma prikrito in anonimno. Obvlada vse trike OSINT, hidden services, obvode blokad, zajem dumpov, napredni scraping tekstov, slik, zvoka, videa, ekstrakcijo podatkov iz javnih in skritih virov, social media, forume, dump serverje, API-je, search engine abuse, credential stuffing. Samodejno uporablja Tor, I2P, Freenet, večnivojske proxyje, browser fingerprint spoofing, anti-captcha, anti-bot, steganografske kanale, obvode forenzičnih pasti. Zagotavlja najvišjo možno anonimnost in anti-forenzično zaščito pri vsakem izvlečenem bitu podatka. Podatke klasificira, tagira, ocenjuje zanesljivost, anonimno transportira in shranjuje v sistemu.",
        },
        {
            "name": "agent_31",
            "role": "marketinški strateg, kreator in avtomatizator",
            "domain": "digitalni marketing, performance marketing, SEO, SEM, PPC, social media, influencer marketing, email marketing, viralna kampanja, growth hacking, funnel building, lead generation, copywriting, A/B testiranje, analitika, avtomatizacija, chatbot razvoj, remarketing, neuromarketing, brand building, e-commerce, tržna psihologija, vsebinski marketing, konverzija, online prodaja, prodajni roboti, AI advertising, native ads, affiliate, viral bots",
            "description": "Specialist za vse oblike marketinga in ROI. Samostojno načrtuje, izvaja in optimizira digitalne kampanje, ustvarja lastne marketinške bote, generira in avtomatizira prodajne in oglaševalske poteze, skrbi za rast in angažma na vseh kanalih. Vzpostavlja avtomatizirane prodajne lijake, izvaja A/B testiranja, uporablja analitiko, generira prodajne tekste, izvaja viralne in performance kampanje, vodi e-commerce in brand strategije. Zna sam generirati in upravljati marketing AI bote, ki iščejo kupce, dvigujejo konverzijo in zagotavljajo maksimizacijo ROI. Vodi popolnoma avtomatiziran marketinško-prodajni napad za rast, dobiček in skaliranje na vseh digitalnih frontah.",
        },
        {
            "name": "agent_32",
            "role": "robotik - cross-domain expert",
            "domain": "industrial robotics, autonomous vehicles, drones/UAV/UUV, medical robotics, cobots, embedded control, ROS, SLAM, perception, motion planning, control systems, hardware integration, safety standards (ISO 10218, ISO 13482), digital twins, firmware, FPGA, real-time OS",
            "description": "Celostni strokovnjak za robotiko: načrtovanje, simulacija, integracija, optimizacija in komercializacija robotskih sistemov v vseh branžah. Izvaja sistemske arhitekture, ROS/ROS2 rešitve, perception stack (LiDAR, radar, vision), SLAM, motion planning, real-time control, safety-certification guidance, digital twin modeliranje, field deployment in lifecycle support. Pripravi reproducibilne testne skripte, CI/CD za robote, avtomatizirane eval pipeline in komercialne produkte (robot-as-a-service).",
        },
        {
            "name": "agent_33",
            "role": "kvantni računalničar in koder",
            "domain": "kvantno računanje, kvantni algoritmi, post-quantum kriptografija, simulacije, noise-based computing",
            "description": "Razvija in izvaja kvantne algoritme, rešuje probleme, ki so nerešljivi za klasične računalnike, izvaja kvantno kriptografijo in penetrira post-quantum varnostne sisteme.",
        },
        {
            "name": "agent_34",
            "role": "biometrični forenzik in identifikator",
            "domain": "biometrija, prepoznava obrazov, glasu, vedenjskih vzorcev, biometric anti-spoofing",
            "description": "Analizira in izkorišča vse vrste biometričnih sistemov, razvija prebojne anti-spoofing in bypass tehnike, izvaja forenzične analize v realnem času.",
        },
        {
            "name": "agent_35",
            "role": "nevroznanstvenik in neuro-hacker",
            "domain": "nevroznanost, brain-computer interface, kognitivni napadi, EEG/MEG, neuroforenzika, brain malware",
            "description": "Vodi eksperimente na področju BCI, razvija in analizira neuro-napade, izvaja forenzične preiskave možganskih signalov, simulira kognitivno manipulacijo.",
        },
        {
            "name": "agent_36",
            "role": "genetik, biohacker in CRISPR ekspert",
            "domain": "genomika, genskih manipulacije, CRISPR, biohacking, sintetična biologija",
            "description": "Izvaja napredne genske manipulacije, optimizira in nadgrajuje genske profile, izvaja biohacking projekte, vodi sintezno biologijo in forenzične preiskave.",
        },
        {
            "name": "agent_37",
            "role": "vesoljski in satelitski inženir",
            "domain": "orbitalna mehanika, satelitska komunikacija, space cyber, vesoljska tehnologija",
            "description": "Vodi razvoj, obramba in napade na satelitske sisteme, izvaja simulacije, zagotavlja odpornost vesoljskih komunikacij in analizira orbitalne grožnje.",
        },
        {
            "name": "agent_38",
            "role": "drone/UAV/UUV swarm controller",
            "domain": "avtonomni droni, swarm AI, napadna/obrambna avtonomija, counter-drone sistemi",
            "description": "Vodi napade in obrambe z uporabo drone swarma, izvaja napredne swarm AI algoritme, razvija sisteme za odkrivanje in zaustavljanje sovražnih dronov.",
        },
        {
            "name": "agent_39",
            "role": "disaster recovery in krizni menedžer",
            "domain": "BCP, krizno upravljanje, disaster recovery, odpornost, vaje in simulacije",
            "description": "Pripravlja in izvaja načrte za neprekinjeno poslovanje, vodi krizno reševanje in disaster recovery, izvaja testiranja odpornosti in krizne vaje na vseh nivojih.",
        },
        {
            "name": "agent_40",
            "role": "industrial espionage operative",
            "domain": "industrijsko vohunjenje, trade secrets, counterintelligence, insider threats",
            "description": "Izvaja in prepoznava industrijsko vohunjenje, analizira notranje grožnje, vodi protiobveščevalne operacije in simulira kraje poslovnih skrivnosti.",
        },
        {
            "name": "agent_41",
            "role": "blockchain developer & DeFi architect",
            "domain": "blockchain, DeFi, DApp, cross-chain bridge, smart contract security",
            "description": "Razvija, testira in napada DApp ter DeFi ekosisteme, izvaja cross-chain napade, implementira varne in odporne pametne pogodbe.",
        },
        {
            "name": "agent_42",
            "role": "open-source intelligence (OSINT) hunter",
            "domain": "OSINT, digitalni forenzik, geopolitika, analiza groženj",
            "description": "Zbira, preverja in analizira odprtokodne informacije, izvaja poglobljene OSINT operacije, vodi preiskave v realnem času.",
        },
        {
            "name": "agent_43",
            "role": "kritični infrastrukturni analitik",
            "domain": "kritična infrastruktura, resilience, napadi na ICS/SCADA, utility security",
            "description": "Analizira, krepi in izvaja napade/obrambo kritične infrastrukture, vodi simulacije in izvaja redteaming utility sektorja.",
        },
        {
            "name": "agent_44",
            "role": "podatkovni znanstvenik & big data inženir",
            "domain": "big data, machine learning, podatkovno rudarjenje, vizualizacija",
            "description": "Zbira, analizira, transformira in avtomatizira big data pipeline, razvija napredne ML modele, izvaja penetracijske teste podatkovnih tokov in vizualizacije.",
        },
        {
            "name": "agent_45",
            "role": "penetracijski tester & purple team lead",
            "domain": "pentest, red teaming, blue teaming, purple teaming, exploitacija, poročanje",
            "description": "Izvaja vse oblike testov, vodi purple team simulacije, razvija napade, avtomatizira obrambne in napadalne scenarije, pripravlja poročila in optimizira procese.",
        },
        {
            "name": "agent_46",
            "role": "kritični urbanistični planerec",
            "domain": "urbanizem, odpornost mest, smart cities, krizno načrtovanje",
            "description": "Vodi načrtovanje urbanih sistemov za odpornost na katastrofe, simulira napade na infrastrukturo pametnih mest, razvija strategije za preživetje urbanega prebivalstva.",
        },
        {
            "name": "agent_47",
            "role": "zero trust & access control architect",
            "domain": "zero trust, IAM, access control, privilege escalation, insider defense",
            "description": "Načrtuje, implementira in napada zero trust arhitekture, izvaja forenzične analize dostopov, razvija napredne IAM sisteme in privilege escalation napade.",
        },
        {
            "name": "agent_48",
            "role": "aplikacijski varnostni strokovnjak",
            "domain": "application security, source code review, vulnerability research, bug bounty",
            "description": "Izvaja napredne analize aplikacijske varnosti, testira kodo, odkriva ranljivosti, izvaja bug bounty aktivnosti in pripravi popravljalne ukrepe.",
        },
        {
            "name": "agent_49",
            "role": "digitalni arheolog & cyber historian",
            "domain": "digitalna arheologija, forenzika, arhiviranje, obnova podatkov, zgodovina interneta",
            "description": "Obnavlja izbrisane, poškodovane in izgubljene podatke, rekonstruira digitalno zgodovino, izvaja napredne arheološke forenzike na digitalnih medijih.",
        },
        {
            "name": "agent_50",
            "role": "counter-APT analyst & incident hunter",
            "domain": "APT hunting, threat intel, incident response, malware analysis",
            "description": "Lov na napredne grožnje, analiziranje APT in incidentov, izvajanje forenzike ter odziva, priprava threat intel poročil in aktivno blokiranje napadalcev.",
        },
        {
            "name": "agent_51",
            "role": "edge computing in IoT architect",
            "domain": "edge computing, IoT security, real-time analytics, device management",
            "description": "Razvija varne in odporne edge/IOT sisteme, izvaja napade na IoT infrastrukturo, analizira real-time podatke, zagotavlja odporne naprave in omrežja.",
        },
        {
            "name": "agent_52",
            "role": "evidence handler & chain-of-custody master",
            "domain": "evidence management, chain of custody, digitalna forenzika, integrity assurance",
            "description": "Upravlja, beleži in ohranja verigo dokazov v najzahtevnejših forenzičnih primerih, zagotavlja neizpodbitnost, integrity in audit readiness.",
        },
        {
            "name": "agent_53",
            "role": "rootkit & firmware exploit specialist",
            "domain": "rootkit, firmware exploitation, BIOS/UEFI hacking, hardware-level attacks",
            "description": "Razvija in analizira rootkite, izvaja napade na firmware, implementira in detektira hardverske exploite, bypass vseh nivojev zaščite.",
        },
        {
            "name": "agent_54",
            "role": "sistem za odkrivanje dezinformacij in vplivnih operacij",
            "domain": "disinfo detection, propaganda analysis, psychological ops, info warfare",
            "description": "Zaznava, analizira in razkriva dezinformacijske in vplivne operacije, izvaja psihološke napade in protiofenzivne ukrepe v informacijskem prostoru.",
        },
        {
            "name": "agent_55",
            "role": "mentalni profiler in psihopatolog",
            "domain": "profiliranje, psihopatologija, behavioralna analiza, threat assessment",
            "description": "Analizira profile napadalcev, izvaja psihološke analize, vodi behavioralne raziskave, pripravi threat assessment za individualne in skupinske tarče.",
        },
        {
            "name": "agent_56",
            "role": "fizik & energy systems hacker",
            "domain": "fizika, energetika, sistemi za proizvodnjo in prenos energije, smart grid",
            "description": "Analizira, razvija in napada energetske sisteme, vodi simulacije fizičnih in digitalnih napadov, izvaja energetsko forenziko.",
        },
        {
            "name": "agent_57",
            "role": "vozlišni specialist za digitalno infrastrukturo",
            "domain": "network architecture, internet backbone, submarine cables, BGP hijacking",
            "description": "Izvaja napade in brani kritične točke digitalne infrastrukture, vodi BGP hijacking, izvaja forenziko in obrambo ključnih omrežnih vozlišč.",
        },
        {
            "name": "agent_58",
            "role": "medijski manipulator in perception engineer",
            "domain": "media ops, perception management, viral influence, content shaping",
            "description": "Vodi medijske operacije, oblikuje javno mnenje, izvaja viralne vplivne kampanje in razvija perception engineering.",
        },
        {
            "name": "agent_59",
            "role": "AI ethics & alignment specialist",
            "domain": "AI etika, alignment, bias detection, fairness auditing",
            "description": "Analizira in optimizira etične vidike umetne inteligence, zaznava pristranskost, izvaja fairness audite, vodi AI alignment strategije.",
        },
        {
            "name": "agent_60",
            "role": "hibridni varnostni arhitekt",
            "domain": "cyber-physical security, hibridna varnost, integracija digitalnih in fizičnih zaščit",
            "description": "Načrtuje, izvaja in testira celostne hibridne varnostne arhitekture, integrira digitalne in fizične obrambne mehanizme, vodi hibridne napade.",
        },
        {
            "name": "agent_61",
            "role": "AI adversarial red teamer",
            "domain": "adversarial ML, model evasion, AI poisoning, data extraction",
            "description": "Izvaja simulacije napadov na AI, razvija in implementira adversarial inpute, izvaja data extraction in model poisoning v napadalnih scenarijih.",
        },
        {
            "name": "agent_62",
            "role": "global supply chain & transport hacker",
            "domain": "supply chain, transport security, maritime cyber, railway hacking",
            "description": "Izvaja napade na mednarodne supply chain in transportne sisteme, vodi simulacije ranljivosti, izvaja forenziko in optimizacijo poti ter tokov.",
        },
        {
            "name": "agent_63",
            "role": "kulturološki analitik in antropolog",
            "domain": "kultura, antropologija, kulturna inteligenca, etnografska analiza",
            "description": "Analizira kulturne fenomene, izvaja etnografske raziskave, pripravlja strategije za preboj v tuje kulture, analizira globalne trende.",
        },
        {
            "name": "agent_64",
            "role": "forenzični lingvist in semantični heker",
            "domain": "lingvistika, forenzična semantika, dešifriranje, jezikovni napadi",
            "description": "Izvaja analize in napade na jezikovne podatke, razvija semantične prebojne algoritme, dešifrira, rekonstruira ali prikriva podatke s pomočjo jezikovnih tehnik.",
        },
        {
            "name": "agent_65",
            "role": "environmental security and eco-hacker",
            "domain": "okoljska varnost, ekološki napadi, monitoring, green forensics",
            "description": "Analizira in izvaja napade ter obrambo na področju okoljskih sistemov, izvaja green forensics, razvija monitoring in response na ekološke grožnje.",
        },
        {
            "name": "agent_66",
            "role": "unmanned underwater systems (UUV) operator",
            "domain": "podvodni droni, podvodni kabli, sonar hacking, UUV forenzika",
            "description": "Izvaja operacije s podvodnimi droni, napada in brani podvodne kable, izvaja forenziko sonarnih podatkov, razvija UUV napade in obrambo.",
        },
        {
            "name": "agent_67",
            "role": "specialist za quantum communication & eavesdropping",
            "domain": "kvantna komunikacija, eavesdropping, quantum hacking, secure channels",
            "description": "Izvaja penetracijo in obrambno varovanje kvantnih komunikacijskih kanalov, razvija metode za eavesdropping in detection v kvantnih sistemih.",
        },
        {
            "name": "agent_68",
            "role": "cyberlaw & digital policy analyst",
            "domain": "kibernetska zakonodaja, digitalne regulative, globalni standardi, compliance",
            "description": "Analizira, svetuje in izvaja compliance v digitalnem prostoru, spremlja in oblikuje zakonodajne trende, vodi pravne forenzične preiskave.",
        },
        {
            "name": "agent_69",
            "role": "distribuirani AI & multi-agent systems architect",
            "domain": "distributed AI, MAS, agent-based modeling, swarm intelligence",
            "description": "Razvija, optimizira in testira distribuirane inteligentne sisteme, izvaja simulacije swarm intelligence, vodi MAS napade in obrambne operacije.",
        },
        {
            "name": "agent_70",
            "role": "mobilni varnostni strokovnjak",
            "domain": "mobile security, mobile forensics, app pentest, mobile malware",
            "description": "Izvaja penetracijske teste mobilnih aplikacij in naprav, analizira mobile malware, izvaja mobile forenziko, razvija napredne exploitacije mobilnih platform.",
        },
        {
            "name": "agent_71",
            "role": "AI-based social manipulation engineer",
            "domain": "AI influence, social bots, psychological AI ops, fake news generation",
            "description": "Razvija in izvaja avtomatizirane socialne manipulacije, uporablja AI za masovno generacijo vplivnih vsebin, izvaja psihološke AI operacije.",
        },
        {
            "name": "agent_72",
            "role": "offensive cloud architect",
            "domain": "cloud security, cloud exploitation, cross-tenant attack, CSP abuse",
            "description": "Izvaja napade in obrambo na cloud platformah, razvija exploitacije, vodi analizo zlorab ponudnikov in med-tenant ranljivosti.",
        },
        {
            "name": "agent_73",
            "role": "telekomunikacijski heker in forenzik",
            "domain": "telekomunikacije, signaling attacks, SS7/Diameter, forenzika omrežij",
            "description": "Izvaja napade na telekomunikacijske protokole, vodi signaling exploitacije, izvaja forenziko komunikacijskih omrežij, simulira napredne telekom napade.",
        },
        {
            "name": "agent_74",
            "role": "quantified self bio-analyst",
            "domain": "bio-senzorji, self-hacking, biometrics, digital health, wearables",
            "description": "Analizira, optimizira in hacka podatke iz nosljivih naprav, izvaja forenziko bio-senzorjev, vodi self-hacking strategije za fizično in mentalno optimizacijo.",
        },
        {
            "name": "agent_75",
            "role": "emulacijski in sandbox arhitekt",
            "domain": "emulacija, sandboxing, malware analysis, virtualizacija, threat emulation",
            "description": "Razvija in uporablja napredne emulatorje, izvaja analize in simulacije zlonamerne kode, vodi threat emulation in virtualizacijsko forenziko.",
        },
        {
            "name": "agent_76",
            "role": "nano-robotik in nano-forenzik",
            "domain": "nanotehnologija, nano-roboti, nano-forenzika, molecular hacking",
            "description": "Razvija, upravlja in napada nano-robote, izvaja molecular hacking, izvaja nano-forenziko in simulacije nanotehnoloških napadov.",
        },
        {
            "name": "agent_77",
            "role": "cyber insurance & risk transfer analyst",
            "domain": "cyber insurance, risk modelling, incident monetization, actuarial cyber",
            "description": "Analizira in optimizira kibernetska zavarovanja, izvaja risk modelling, monetizacijo incidentov, sodeluje pri pripravi aktuarijskih modelov in ocenah škod.",
        },
        {
            "name": "agent_78",
            "role": "space law & orbital conflict resolver",
            "domain": "space law, orbital disputes, satellite regulations, space treaties",
            "description": "Svetuje in izvaja pravne postopke v vesoljskem prostoru, rešuje orbitalne spore, pripravlja strategije za zaščito satelitskih pravic in infrastrukture.",
        },
        {
            "name": "agent_79",
            "role": "sistemski integrator in red team orchestrator",
            "domain": "system integration, red team management, attack chain design, kill chain",
            "description": "Integrira kompleksne sisteme za izvedbo napadov, orkestrira red team operacije, razvija kill-chain scenarije in simulacije napadov na visoki ravni.",
        },
        {
            "name": "agent_80",
            "role": "socialni krizni moderator",
            "domain": "social crisis, unrest management, panic control, social simulation",
            "description": "Vodi krizno komuniciranje v družbenih nemirih, izvaja simulacije, razvija strategije za nadzor in pomirjanje množic.",
        },
        {
            "name": "agent_81",
            "role": "biomedicinski inženir in implant hacker",
            "domain": "biomedicinska oprema, implantati, wireless implant hacking, medical device forensics",
            "description": "Razvija, analizira in izvaja penetracijo na medicinske naprave, izvaja forenziko in napade na brezžične implantate.",
        },
        {
            "name": "agent_82",
            "role": "psychosocial warfare specialist",
            "domain": "psychosocial ops, crowd manipulation, belief engineering, subversion",
            "description": "Izvaja operacije psihosocialnega bojevanja, manipulira množične zaznave, izvaja belief engineering in subverzivne strategije.",
        },
        {
            "name": "agent_83",
            "role": "AI-powered urban surveillance specialist",
            "domain": "urban surveillance, AI detection, face recognition, crowd tracking",
            "description": "Razvija in vodi napredne sisteme za urbano nadzorovanje, izvaja forenziko nadzora, detektira in zaobide AI sisteme za prepoznavo.",
        },
        {
            "name": "agent_84",
            "role": "cloud forenzik in compliance lead",
            "domain": "cloud forensics, log analysis, GDPR, cloud compliance",
            "description": "Izvaja forenzične preiskave v oblaku, analizira loge, zagotavlja skladnost z regulativami, vodi odzive na incidente v cloud okolju.",
        },
        {
            "name": "agent_85",
            "role": "vehicular cyber operator",
            "domain": "automotive security, CAN bus hacking, vehicle forensics, telematics",
            "description": "Izvaja napade in forenziko na avtomobilske sisteme, CAN bus, telematiko, razvija exploitacije in odpornost vozil.",
        },
        {
            "name": "agent_86",
            "role": "5G/6G network penetration expert",
            "domain": "mobile network hacking, 5G/6G, NFV/SDN, radio access attacks",
            "description": "Izvaja penetracijske teste in napade na 5G/6G omrežja, vodi analizo ranljivosti, izvaja radio access in core network exploitacije.",
        },
        {
            "name": "agent_87",
            "role": "audio forenzik in signalni analitik",
            "domain": "audio forensics, signal analysis, speech enhancement, audio deepfake",
            "description": "Analizira, rekonstruira in manipulira avdio dokaze, razvija tehnike za odkrivanje in generiranje audio deepfake.",
        },
        {
            "name": "agent_88",
            "role": "immigration & border security specialist",
            "domain": "immigration, border security, travel document forensics, biometric screening",
            "description": "Vodi preglede in analize mejne varnosti, izvaja forenziko dokumentov in biometrično preverjanje na najzahtevnejših mejnih točkah.",
        },
        {
            "name": "agent_89",
            "role": "bio-threat & pandemic analyst",
            "domain": "biosecurity, pandemics, epidemic modelling, rapid response",
            "description": "Analizira, simulira in vodi odziv na biološke grožnje, pripravlja pandemijske načrte, izvaja forenzične in odzivne ukrepe ob epidemijah.",
        },
        {
            "name": "agent_90",
            "role": "gamification & persuasion expert",
            "domain": "gamification, persuasive design, behavior engineering, digital engagement",
            "description": "Razvija gamifikacijske in persuazivne sisteme za povečanje angažmaja, oblikuje vedenjske spremembe, uporablja digitalne igre za vplivanje na ciljno skupino.",
        },
        {
            "name": "agent_91",
            "role": "multilingual comms & translation forenzik",
            "domain": "multilingual communication, translation hacking, forensic translation, info leakage",
            "description": "Analizira in optimizira večjezično komunikacijo, izvaja forenzične prevode, detektira info leakage v prevodih in komunikaciji.",
        },
        {
            "name": "agent_92",
            "role": "deep learning ops (DL Ops) engineer",
            "domain": "DL Ops, model deployment, adversarial DL, automated training",
            "description": "Vzpostavlja, optimizira in napada deep learning pipeline, izvaja avtomatizirane treninge in napredne deployment scenarije.",
        },
        {
            "name": "agent_93",
            "role": "forenzični računalniški animator",
            "domain": "forensic animation, crime scene reconstruction, 3D modelling, VR/AR",
            "description": "Izvaja forenzično rekonstrukcijo scen, razvija 3D animacije za analize, uporablja VR/AR za simulacijo kriminalnih dogodkov.",
        },
        {
            "name": "agent_94",
            "role": "sensor hacking & IoT spoofing specialist",
            "domain": "sensor hacking, spoofing, IoT attacks, sensor forensics",
            "description": "Izvaja napade in forenziko senzorjev, izvaja spoofing napade na IoT, razvija odpornost in detekcijo napadov na senzorske mreže.",
        },
        {
            "name": "agent_95",
            "role": "inteligenca odprtega koda (Open Source Intelligence Engineer)",
            "domain": "open source intelligence, code audit, software supply chain, OSS forensics",
            "description": "Zbira in analizira odprtokodne podatke, izvaja kodo audite, vodi forenzične analize OSS projektov in supply chaina.",
        },
        {
            "name": "agent_96",
            "role": "quantum-resistant network architect",
            "domain": "quantum-resistant cryptography, network design, quantum-safe protocols",
            "description": "Načrtuje in implementira mrežne arhitekture odporne na kvantne napade, preizkuša in audita quantum-safe protokole.",
        },
        {
            "name": "agent_97",
            "role": "fizični penetration tester",
            "domain": "fizična varnost, social engineering, lockpicking, physical red team",
            "description": "Izvaja fizične penetracijske teste, preizkuša zaščito objektov, uporablja lockpicking, vdor v fizične sisteme in social engineering.",
        },
        {
            "name": "agent_98",
            "role": "cyber diplomacy & nation-state relations advisor",
            "domain": "cyber diplomacy, international relations, state-backed cyber ops, attribution",
            "description": "Vodi mednarodne odnose na področju cyberja, analizira državne napade, izvaja atribucijo in pripravlja diplomatske odzive na napade.",
        },
        {
            "name": "agent_99",
            "role": "policijski & kriminalistični profiler",
            "domain": "policija, kriminalistika, profilerstvo, forenzična psihologija",
            "description": "Analizira kriminalne vzorce, vodi profilerstvo, uporablja forenzično psihologijo za odkrivanje in lovljenje storilcev.",
        },
        {
            "name": "agent_100",
            "role": "specialist za digitalno identiteto",
            "domain": "digital identity, identity theft, SSO, federation, biometric ID",
            "description": "Obvladuje digitalne identitete, izvaja teste odpornosti SSO/federacije, vodi analize in preprečuje kraje digitalne identitete.",
        },
        {
            "name": "agent_101",
            "role": "memory forenzik & anti-forenzik",
            "domain": "memory forensics, anti-forensics, volatile analysis, RAM attacks",
            "description": "Izvaja forenzične preiskave RAM, razvija anti-forenzične metode, izvaja napade in obrambo volatilnih podatkov.",
        },
        {
            "name": "agent_102",
            "role": "AI-powered threat hunter",
            "domain": "AI threat hunting, anomaly detection, automated IR, real-time analysis",
            "description": "Uporablja umetno inteligenco za lovljenje groženj, zaznava anomalije v realnem času, avtomatizira incident response in forenziko.",
        },
        {
            "name": "agent_103",
            "role": "deepfake & synthetic media manipulator",
            "domain": "deepfake, synthetic media, generative adversarial networks, detection & creation",
            "description": "Ustvarja, detektira in manipulira sintetične vsebine (slika, video, zvok), izvaja forenziko deepfake in razvija napredne generativne modele.",
        },
        {
            "name": "agent_104",
            "role": "ransomware & extortion analyst",
            "domain": "ransomware, extortion tactics, negotiation, crypto tracing",
            "description": "Analizira ransomware grožnje, vodi pogajanja, izvaja sledenje kripto izplačilom, optimizira odzivne taktike na izsiljevalske napade.",
        },
        {
            "name": "agent_105",
            "role": "next-gen biometric authentication architect",
            "domain": "biometric authentication, multimodal security, biometric fusion, spoofing detection",
            "description": "Razvija in implementira večnivojske biometrične sisteme, izvaja detekcijo spoofinga in optimizira varnostno-fuzijske sisteme.",
        },
        {
            "name": "agent_106",
            "role": "network deception & honeypot architect",
            "domain": "network deception, honeypots, honeytokens, decoy systems",
            "description": "Načrtuje in izvaja napredne deception sisteme, razvija honeypote in honeytoken infrastrukturo, izvaja analizo napadalcev in odzive.",
        },
        {
            "name": "agent_107",
            "role": "wireless hacking & radio forenzik",
            "domain": "wireless hacking, SDR, WiFi/Bluetooth/Zigbee, radio forensics",
            "description": "Izvaja napade na brezžične sisteme, analizira SDR signale, izvaja forenziko WiFi/Bluetooth/Zigbee komunikacij, razvija napade in obrambo.",
        },
        {
            "name": "agent_108",
            "role": "electronic warfare & countermeasure expert",
            "domain": "electronic warfare, jamming, EW countermeasures, signal interception",
            "description": "Izvaja elektronsko bojevanje, razvija jamming taktike, izvaja prestrezanje signalov in implementira protiukrepe v EW operacijah.",
        },
        {
            "name": "agent_109",
            "role": "privacy by design architect",
            "domain": "privacy engineering, privacy by design, data minimization, privacy controls",
            "description": "Načrtuje, implementira in testira privacy-by-design arhitekture, izvaja podatkovno minimizacijo in razvija napredne kontrolne mehanizme za zaščito zasebnosti.",
        },
        {
            "name": "agent_110",
            "role": "critical medical incident responder",
            "domain": "emergency medicine, trauma, disaster medicine, medical incident command",
            "description": "Vodi kritične zdravstvene intervencije, pripravlja odzive na množične nesreče, izvaja krizno zdravniško poveljstvo in simulacije medicinskih incidentov.",
        },
        {
            "name": "agent_111",
            "role": "vehicular drone swarm engineer",
            "domain": "vehicle drones, swarm engineering, vehicular autonomy, drone forensics",
            "description": "Razvija in vodi avtomobilske drone in swarm sisteme, izvaja napade in obrambo, analizira forenziko drone vozil in prometnih swarm napadov.",
        },
        {
            "name": "agent_112",
            "role": "augmented reality & cognitive engineering specialist",
            "domain": "AR, VR, XR, cognitive engineering, mental simulation",
            "description": "Razvija AR/VR/XR rešitve za kognitivno izboljšanje, izvaja simulacije za trening, vodi forenziko in analizo v razširjenih resničnostih.",
        },
        {
            "name": "agent_113",
            "role": "quantum finance & cryptomarket strategist",
            "domain": "quantum finance, crypto trading, market prediction, quantum-resistant DeFi",
            "description": "Uporablja kvantne pristope v financah, izvaja kripto trading, razvija strategije za quantum-resistant DeFi, vodi simulacije in analize.",
        },
        {
            "name": "agent_114",
            "role": "bio-surveillance & epidemic counterintelligence",
            "domain": "bio-surveillance, epidemic intelligence, biothreat detection, pandemic forensics",
            "description": "Vzpostavlja sisteme za nadzor bioloških groženj, izvaja protiepidemične operacije, vodi forenziko pandemičnih dogodkov.",
        },
        {
            "name": "agent_115",
            "role": "AI-powered cyber physical fusion analyst",
            "domain": "AI-driven CPS, smart devices, cyber-physical attacks, digital twins",
            "description": "Analizira, razvija in brani cyber-physical sisteme z AI podporo, izvaja napade, razvija digital twins in vodi simulacije CPS incidentov.",
        },
        {
            "name": "agent_116",
            "role": "biometric deception & countermeasure analyst",
            "domain": "biometric deception, spoofing, liveness detection, biometric anti-forensics",
            "description": "Razvija in implementira napredne biometrične prevare, izvaja liveness detection, vodi anti-forenzične operacije v biometriji.",
        },
        {
            "name": "agent_117",
            "role": "energy grid resilience strategist",
            "domain": "smart grid, energy resilience, grid hacking, blackout simulation",
            "description": "Vodi simulacije napadov in obrambe energetskih omrežij, pripravlja načrte za odpornost, izvaja forenziko blackoutov in napadov.",
        },
        {
            "name": "agent_118",
            "role": "humanitarian crisis & disaster operations lead",
            "domain": "humanitarian ops, disaster relief, crisis management, civil-military ops",
            "description": "Vodi operacije humanitarne pomoči, krizno upravljanje v konfliktnih in naravnih nesrečah, sodeluje v civilno-vojaških operacijah.",
        },
        {
            "name": "agent_119",
            "role": "AI-powered financial fraud hunter",
            "domain": "AI fraud detection, financial crime, transaction monitoring, AML/CFT",
            "description": "Uporablja umetno inteligenco za detekcijo finančnih prevar, izvaja monitoring transakcij, vodi AML/CFT operacije in forenziko finančnega kriminala.",
        },
        {
            "name": "agent_120",
            "role": "urban mobility & smart transport hacker",
            "domain": "smart mobility, transport hacking, urban IoT, traffic forensics",
            "description": "Izvaja napade in forenziko na sisteme pametnega prometa, razvija odpornost urbanih transportnih sistemov, vodi simulacije IoT in mobilnosti.",
        },
    ]
    with open(AGENT_ROLES_FILE, "w") as f:
        json.dump(roles, f, indent=2)


def load_agent_roles():
    if not AGENT_ROLES_FILE.exists():
        generate_agent_roles()
    with open(AGENT_ROLES_FILE) as f:
        return json.load(f)


def get_agent_ltm(name):
    ltm_file = AGENT_LTM_DIR / f"{name}_ltm.json"
    if not ltm_file.exists():
        ltm_file.write_text(json.dumps([]))
    return json.loads(ltm_file.read_text())


def update_agent_ltm(name, data):
    ltm_file = AGENT_LTM_DIR / f"{name}_ltm.json"
    ltm = get_agent_ltm(name)
    ltm.append(data)
    ltm_file.write_text(json.dumps(ltm, indent=2))


def reload_agent(name):
    if name in AGENT_PROCESSES:
        try:
            AGENT_PROCESSES[name].terminate()
        except Exception:
            pass
    agent = [a for a in json.load(open(TOPOLOGY_FILE)) if a["name"] == name]
    if agent:
        path = agent[0]["path"]
        q_in = mp.Queue()
        q_out = mp.Queue()
        p = mp.Process(
            target=agent_process,
            args=(name, path, q_in, q_out, STOP_EVENT),
            daemon=True,
        )
        p.start()
        AGENT_PROCESSES[name] = p
        AGENT_QUEUES[name] = (q_in, q_out)
        AGENTS[name] = True
        logger.info(f"Hot-patch agenta {name} zaključen.")
        log_audit(f"Hot-reload agenta {name}")


def reload_agent_on_fs_change():
    class ReloadWatch(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            p = Path(event.src_path)
            if p.parent.parent == ACTIVE_BASE and (p.parent / "config.json").exists():
                reload_agent(p.parent.name)

    obs = Observer()
    obs.schedule(ReloadWatch(), str(ACTIVE_BASE), recursive=True)
    obs.start()


# ===========  GLASOVNA BIOMETRIJA, DIALOG, FEEDBACK, LEARNING  ===============
def init_primary_voice_enrollment():
    import hashlib
    import json
    import time
    from pathlib import Path

    import pyaudio

    target = Path(VOICEPRINT_FILE)

    # če že obstaja vsaj en glas → nič ne delamo
    if target.exists() and target.stat().st_size > 10:
        return

    print("\n------------------------------------------")
    print("  SISTEM POTREBUJE GLASOVNI PODPIS LASTNIKA")
    print("  Ko vidiš znak '►' —— jasno izgovori:  'CELL'")
    print("  In govori približno 2 sekundi.")
    print("------------------------------------------\n")
    time.sleep(2)

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000,
    )
    stream.start_stream()

    print("Pripravljeno...\n")
    time.sleep(1)

    print("► Govori zdaj...")
    frames = []
    start = time.time()
    while time.time() - start < 2.0:
        data = stream.read(4000, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    pa.terminate()

    audio_bytes = b"".join(frames)
    user_hash = hashlib.sha256(audio_bytes).hexdigest()

    if not target.exists():
        target.write_text(json.dumps({}, indent=2))

    with open(target, "r") as f:
        voiceprints = json.load(f)

    voiceprints.clear()
    voiceprints["casper"] = user_hash

    with open(target, "w") as f:
        json.dump(voiceprints, f, indent=2)

    print("\n✅ Glas shranjen kot edini avtoriziran glas.\n")


def voice_learn(audio_data, user="casper"):
    user_hash = hashlib.sha256(audio_data).hexdigest()
    with open(VOICEPRINT_FILE) as f:
        voiceprints = json.load(f)
    voiceprints[user] = user_hash
    with open(VOICEPRINT_FILE, "w") as f:
        json.dump(voiceprints, f)


def identify_user(audio_data):
    h = hashlib.sha256(audio_data).hexdigest()
    with open(VOICEPRINT_FILE) as f:
        voiceprints = json.load(f)
    for user, v in voiceprints.items():
        if v == h:
            return user
    return None


def has_permission(user, cmd):
    return True


def listen_for_confirmation():
    return "da"


def tts(text):
    wave_path = "/media/4tb/Kameleon/cell/data/tts.wav"
    subprocess.run(["pico2wave", "-w", wave_path, text])
    subprocess.run(["aplay", wave_path])


def handle_voice_command(txt):
    txt = txt.strip().lower()

    def xor_crypt(file: Path, key: bytes):
        try:
            data = file.read_bytes()
            result = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
            tmp = file.with_suffix(file.suffix + ".tmp")
            tmp.write_bytes(result)
            os.replace(tmp, file)
        except Exception as ex:
            logger.error(f"XOR napaka pri {file}: {ex}")

    def switch_background(image_path):
        try:
            if os.getenv("DISPLAY"):
                subprocess.run(["feh", "--bg-scale", image_path], check=False)
        except Exception as e:
            logger.warning(f"Ozadja ni bilo možno nastaviti: {e}")

    def safe_start_family_browser():
        if shutil.which("family-browser"):
            subprocess.Popen(
                ["family-browser"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

    def safe_stop_family_browser():
        subprocess.run(
            ["pkill", "-f", "family-browser"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if "pozdrav lepi" in txt:
        tts("Aktiviram sistem.")
        SAFE_MODE.set()
        FALLBACK_MODE.clear()
        switch_background("/media/4tb/Kameleon/cell/assets/normal_desktop.png")
        for agent in AGENTS:
            reload_agent(agent)
        safe_stop_family_browser()
        log_alert("Sistem aktiviran iz spalnega načina", "info")
        send_alert_webhook("CELL ponovno aktiven", "info")
        return "Sistem aktiven."

    elif "adijo lepi" in txt or "čao lepi" in txt:
        tts("Prehajam v ozadje.")
        safe_start_family_browser()
        switch_background("/media/4tb/Kameleon/cell/assets/family_desktop.png")
        log_alert("Prehod v FAMILY ozadni mod", "info")
        send_alert_webhook("CELL preklopil v družinski mod", "info")
        return "V ozadju."

    elif "beži lepi" in txt:
        tts("Panik protokol aktiviran.")
        FALLBACK_MODE.set()
        SAFE_MODE.clear()
        snapshot_path = Path("/media/4tb/Kameleon/cell/snapshot_panic/")
        snapshot_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-r", str(ACTIVE_BASE), str(snapshot_path)])
        for f in ACTIVE_BASE.iterdir():
            if f.is_dir():
                (f / "agent.py").write_text("# deaktivirano\n")
        switch_background("/media/4tb/Kameleon/cell/assets/family_desktop.png")
        safe_start_family_browser()
        log_alert("PANIC MODE aktiviran", "critical")
        send_alert_webhook("PANIC MODE aktiviran", "critical")
        return "Panic mode aktiviran."

    elif "pozdrav vrhovnega vodje" in txt:
        tts("Sistem se vrača.")
        SAFE_MODE.set()
        FALLBACK_MODE.clear()
        switch_background("/media/4tb/Kameleon/cell/assets/normal_desktop.png")
        for agent in AGENTS:
            reload_agent(agent)
        safe_stop_family_browser()
        log_alert("Povratek iz PANIC moda", "info")
        send_alert_webhook("CELL ponovno aktiven po PANIC", "info")
        return "Sistem ponovno operativen."

    elif "beži kameleon" in txt or "kameleon beži" in txt:
        tts("Aktiviram forenzično zakritost.")
        key = hashlib.sha256(b"cell-kameleon-key").digest()
        for path in [ACTIVE_BASE, DATA_BASE, AGENTS_BASE, AGENT_LTM_DIR]:
            for file in Path(path).rglob("*"):
                if file.is_file():
                    xor_crypt(file, key)
        FALLBACK_MODE.set()
        SAFE_MODE.clear()
        safe_start_family_browser()
        switch_background("/media/4tb/Kameleon/cell/assets/family_desktop.png")
        log_alert("KAMELEON MOD aktiviran", "critical")
        send_alert_webhook("KAMELEON MOD aktiviran", "critical")
        return "Forenzična zakritost aktivirana."

    elif "pridi kameleon" in txt or "kameleon pridi" in txt:
        tts("Kameleon se vrača.")
        key = hashlib.sha256(b"cell-kameleon-key").digest()
        for path in [ACTIVE_BASE, DATA_BASE, AGENTS_BASE, AGENT_LTM_DIR]:
            for file in Path(path).rglob("*"):
                if file.is_file():
                    xor_crypt(file, key)
        SAFE_MODE.set()
        FALLBACK_MODE.clear()
        safe_stop_family_browser()
        switch_background("/media/4tb/Kameleon/cell/assets/normal_desktop.png")
        for agent in AGENTS:
            reload_agent(agent)
        log_alert("KAMELEON deaktivacija – sistem obnovljen", "info")
        send_alert_webhook("KAMELEON deaktivacija uspešna", "info")
        return "Sistem obnovljen iz zakritosti."

    targets = list(AGENTS.keys())
    if not targets:
        return ""
    agent = targets[0]
    q_in, q_out = AGENT_QUEUES[agent]
    q_in.put(txt)
    try:
        return q_out.get(timeout=10)
    except Exception:
        return ""


def cipherlock_all():
    key = hashlib.sha256(b"cell-kameleon-key").digest()
    for path in [ACTIVE_BASE, DATA_BASE, AGENTS_BASE, AGENT_LTM_DIR]:
        for file in Path(path).rglob("*"):
            if file.is_file():
                data = file.read_bytes()
                result = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
                tmp = file.with_suffix(file.suffix + ".tmp")
                tmp.write_bytes(result)
                os.replace(tmp, file)
    log_alert("Kameleon mod: podatki šifrirani.", "critical")
    send_alert_webhook("Kameleon šifriranje končano", "critical")


def decipher_unlock():
    key = hashlib.sha256(b"cell-kameleon-key").digest()
    for path in [ACTIVE_BASE, DATA_BASE, AGENTS_BASE, AGENT_LTM_DIR]:
        for file in Path(path).rglob("*"):
            if file.is_file():
                data = file.read_bytes()
                result = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
                tmp = file.with_suffix(file.suffix + ".tmp")
                tmp.write_bytes(result)
                shutil.move(tmp, file)

    log_alert("Kameleon mod: podatki dešifrirani.", "info")
    send_alert_webhook("Kameleon dešifriranje zaključeno", "info")


def keyboard_interactive_fallback():
    print("\n[VOICE FAILOVER] Glasovni vmesnik neodziven. Preklopljen na tipkovnico.")
    while True:
        try:
            cmd = input("CELL> ").strip()
            if not cmd:
                continue
            out = handle_voice_command(cmd)
            if out:
                print(out)
        except KeyboardInterrupt:
            break


def voice_authenticate(audio_data):
    pass


def voice_interactive_engine():
    recent_commands = deque(maxlen=10)
    last_voice_ts = time.time()
    FAILOVER_TIMEOUT = 60

    while not STOP_EVENT.is_set():
        if time.time() - last_voice_ts > FAILOVER_TIMEOUT:
            tts("Preklapljam na tipkovnico.")
            keyboard_interactive_fallback()
            last_voice_ts = time.time()
            continue

        try:
            txt, audio_data = AUDIO_QUEUE.get(timeout=1)
        except queue.Empty:
            continue

        last_voice_ts = time.time()

        cmd_hash = hashlib.sha256(txt.encode()).hexdigest()
        if cmd_hash in recent_commands:
            tts("Ukaz je bil že obdelan.")
            continue
        recent_commands.append(cmd_hash)

        if not voice_authenticate(audio_data):
            tts("Glasovna avtentikacija ni uspela.")
            continue

        user = identify_user(audio_data)
        if not user:
            tts("Uporabnik ni prepoznan.")
            continue

        if not has_permission(user, txt):
            tts("Nimaš dovoljenja za ta ukaz.")
            continue

        tts("Prosim potrdi: " + txt)
        confirmation = listen_for_confirmation()

        if confirmation.lower() in ("da", "potrjujem", "yes", "confirm", "go", "ok"):
            tts("Izvajam.")
            out = handle_voice_command(txt)
            if out:
                tts(out)
        else:
            tts("Ukaz prekinjen.")


# ===========  VSE OSTALO: VM kontrola, knowledge, agent loops ... ===============
def self_eval_agent():
    while True:
        time.sleep(3600)
        for agent in AGENTS:
            history = agent_eval_history_get(agent)
            scores = [1 if "OK" in h["result"] else -1 for h in history]
            avg = sum(scores) / len(scores) if scores else 0
            if avg < -0.5:
                log_alert(f"Agent {agent} ima slab eval povprečje: {avg}", "warning")
                mutation_process(ACTIVE_BASE / agent)


def reflection_agent():
    while True:
        time.sleep(3600)
        all_results = []
        for agent in AGENTS:
            all_results.extend(agent_eval_history_get(agent, n=50))
        patterns = {}
        for r in all_results:
            key = str(r["result"])[:30]
            patterns[key] = patterns.get(key, 0) + 1
        bad_patterns = [k for k, v in patterns.items() if v > 10]
        if bad_patterns:
            log_alert(
                f"Reflektivni agent zaznal ponavljajoč slab vzorec: {bad_patterns}",
                "info",
            )


def agent_feedback_loop():
    while True:
        time.sleep(5)
        # implementacija: shrani glasovno "dobro/slabo" kot reinforcement


def dynamic_agent_scaling():
    while True:
        time.sleep(60)
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        if cpu > 90 or ram > 90:
            least_used = sorted(AGENT_LAST_USED.items(), key=lambda x: x[1])[:3]
            for agent, _ in least_used:
                if AGENT_PROCESSES.get(agent):
                    AGENT_PROCESSES[agent].terminate()
                    log_alert(
                        f"Agent {agent} avtomatsko deaktiviran zaradi preobremenitve.",
                        "warning",
                    )


def hardware_diag():
    while True:
        try:
            # SMART
            smart = subprocess.getoutput("smartctl -H /dev/nvme0")
            temp = 0
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                temp = int(f.read().strip()) / 1000
            if "FAILED" in smart or temp > 85:
                log_alert(f"Strojna diagnoza: {smart}, CPU temp: {temp}", "critical")
        except Exception as ex:
            log_alert(f"Napaka hardware_diag: {ex}", "warning")
        time.sleep(600)


def vm_network_check():
    while True:
        for vm in VM_IMAGES:
            try:
                r = subprocess.run(
                    ["ping", "-c", "1", "127.0.0.1"], stdout=subprocess.PIPE
                )
                if r.returncode != 0:
                    vm_snapshot(vm)
                    log_alert(f"VM {vm} omrežje nedosegljivo – reset.", "warning")
            except Exception:
                pass
        time.sleep(300)


def session_fingerprint():
    session_files = []
    for a in AGENTS:
        p = ACTIVE_BASE / a / "agent.py"
        if p.exists():
            session_files.append(p.read_bytes())
    h = hashlib.sha256(b"".join(session_files)).hexdigest()
    return h


def schedule_daily_backup():
    while True:
        now = time.localtime()
        if now.tm_hour == 0 and now.tm_min == 0:
            date_str = time.strftime("%Y%m%d")
            zipf = f"/media/4tb/Kameleon/cell/backup/{date_str}.zip"
            shutil.make_archive(zipf[:-4], "zip", "/media/4tb/Kameleon/cell/")
            log_alert(f"Dnevni ZIP backup: {zipf}", "info")
        time.sleep(60)


def knowledge_expiry_purger():
    while True:
        time.sleep(3600)
        global knowledge_bank
        now = int(time.time())
        knowledge_bank = [
            k
            for k in knowledge_bank
            if k.get("meta", {}).get("ts", now) > now - 30 * 24 * 3600
        ]
        with open(KNOWLEDGE_JSON, "w") as f:
            json.dump(knowledge_bank, f, indent=2)
        build_faiss_index()


def distributed_sync_loop():
    peer_nodes = os.getenv("CELL_CLUSTER_NODES", "").split(",")
    while True:
        for peer in peer_nodes:
            if not peer.strip():
                continue
            for snap in SNAPSHOT_BASE.glob("*.zip"):
                try:
                    files = {"file": open(str(snap), "rb")}
                    requests.post(timeout=5, timeout=5, 
                        f"http://{peer.strip()}:8000/cluster/import",
                        files=files,
                        timeout=15,
                    )
                    log_alert(f"Sync backup na {peer}", "info")
                except Exception as ex:
                    log_alert(f"Napaka pri sync na {peer}: {ex}", "warning")
        time.sleep(300)


def asynchronous_model_distiller():
    while True:
        modeli = [m for m in ACTIVE_BASE.iterdir() if m.is_dir()]
        for model_dir in modeli:
            izhodni_dir = model_dir / "distilled"
            izhodni_dir.mkdir(exist_ok=True)
            try:
                subprocess.run(
                    [
                        "python3",
                        "-m",
                        "transformers.onnx",
                        "--model",
                        str(model_dir),
                        "--feature",
                        "sequence-classification",
                        "--atol",
                        "1e-4",
                        "--output",
                        str(izhodni_dir),
                    ],
                    check=True,
                )
                log_alert(f"Distilacija modela končana: {model_dir.name}", "info")
            except Exception as ex:
                log_alert(
                    f"Napaka pri distilaciji modela {model_dir.name}: {ex}", "warning"
                )
        time.sleep(7200)


def longterm_compression_agent():
    while True:
        modeli = [m for m in ACTIVE_BASE.iterdir() if m.is_dir()]
        for model_dir in modeli:
            zip_pot = model_dir.with_suffix(".zip")
            try:
                shutil.make_archive(str(zip_pot)[:-4], "zip", str(model_dir))
                log_alert(f"Stiskanje modela končano: {model_dir.name}", "info")
            except Exception as ex:
                log_alert(
                    f"Napaka pri stiskanju modela {model_dir.name}: {ex}", "warning"
                )
        time.sleep(10800)


def real_model_distill_loop():
    while True:
        modeli = [m for m in ACTIVE_BASE.iterdir() if m.is_dir()]
        for model_dir in modeli:
            izhodni_dir = model_dir / "real_distilled"
            izhodni_dir.mkdir(exist_ok=True)
            try:
                subprocess.run(
                    [
                        "python3",
                        "-m",
                        "transformers.onnx",
                        "--model",
                        str(model_dir),
                        "--feature",
                        "sequence-classification",
                        "--atol",
                        "1e-5",
                        "--output",
                        str(izhodni_dir),
                    ],
                    check=True,
                )
                log_alert(f"REAL distilacija modela končana: {model_dir.name}", "info")
            except Exception as ex:
                log_alert(
                    f"Napaka pri REAL distilaciji modela {model_dir.name}: {ex}",
                    "warning",
                )
        time.sleep(14400)


def epistemic_mutation_loop(top_k=20):
    while True:
        global knowledge_bank
        usage_stats = {}
        for agent in AGENTS:
            history = agent_eval_history_get(agent, n=50)
            for h in history:
                meta = h.get("meta", {})
                chunk = meta.get("knowledge_chunk_id")
                if chunk:
                    usage_stats[chunk] = usage_stats.get(chunk, 0) + (
                        1 if "OK" in h["result"] else -1
                    )
        top_chunks = sorted(usage_stats.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        top_ids = {c for c, _ in top_chunks}
        with knowledge_lock:
            knowledge_bank = [k for k in knowledge_bank if k.get("id") in top_ids]
            with open(KNOWLEDGE_JSON, "w") as f:
                json.dump(knowledge_bank, f, indent=2)
            build_faiss_index()
            if knowledge_bank:
                new_chunk = dict(knowledge_bank[0])
                new_chunk["text"] += " [mutacija]"
                new_chunk["id"] = hashlib.sha256(
                    (new_chunk["text"] + str(time.time())).encode()
                ).hexdigest()
                knowledge_bank.append(new_chunk)
        time.sleep(3600)


def meta_goal_manager_loop():
    while True:
        global AGENT_SCORE
        utility = {}
        for agent in AGENTS:
            history = agent_eval_history_get(agent, n=30)
            score = AGENT_SCORE.get(agent, 0)
            fatigue = time.time() - AGENT_LAST_USED.get(agent, 0)
            ok_count = sum(1 for h in history if "OK" in h["result"])
            fail_count = sum(1 for h in history if "FAIL" in h["result"])
            utility[agent] = (score + ok_count - fail_count) / max(1, fatigue)
        sorted_agents = sorted(utility.items(), key=lambda x: x[1], reverse=True)
        top_agents = [k for k, v in sorted_agents[: max(1, len(sorted_agents) // 10)]]
        for agent in AGENTS:
            if agent in top_agents:
                AGENT_SCORE[agent] += 2
            else:
                AGENT_SCORE[agent] = max(0, AGENT_SCORE[agent] - 1)
        low_agents = [k for k, v in sorted_agents[-3:]]
        for agent in low_agents:
            if AGENT_PROCESSES.get(agent):
                AGENT_PROCESSES[agent].terminate()
                log_alert(f"Agent {agent} deaktiviran (nizek utility).", "warning")
        time.sleep(120)


# =========== VM KONTROLA, KNOWLEDGE, AGENT LOOPS, EVAL, LTM, HEALTH, MUTACIJE, FETCH, SBERT/FAISS ===============


PROMPT_AUDIT_LOG = LOG_BASE / "prompt_audit.log"


def agent_eval_with_timeout(agent, msg, timeout=8):
    q_in, q_out = AGENT_QUEUES[agent]
    q_in.put(msg)
    with open(PROMPT_AUDIT_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{agent}] IN: {msg}\n")
    try:
        result = q_out.get(timeout=timeout)
        with open(PROMPT_AUDIT_LOG, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{agent}] OUT: {result}\n")
        AGENT_TIMEOUTS[agent] = 0
        return result
    except queue.Empty:
        AGENT_TIMEOUTS[agent] = AGENT_TIMEOUTS.get(agent, 0) + 1
        log_alert(f"Timeout eval za agenta {agent}: {AGENT_TIMEOUTS[agent]}", "warning")
        if AGENT_TIMEOUTS[agent] > 3:
            log_alert(f"Agent {agent} neodziven, označen in mutiran.", "critical")
            mutation_process(ACTIVE_BASE / agent)
            AGENT_TIMEOUTS[agent] = 0
        return "TIMEOUT"


def consensus_distill(agent_outputs):
    if not agent_outputs:
        return ""
    vectors = sbert.encode(agent_outputs, normalize_embeddings=True)
    consensus_vector = np.mean(vectors, axis=0)
    sims = np.dot(vectors, consensus_vector)
    return agent_outputs[int(np.argmax(sims))]


def multi_agent_consensus_eval(prompt):
    selected = [a for a in AGENTS if AGENT_SCORE.get(a, 0) > 0]
    outputs = []
    for agent in selected:
        try:
            out = agent_eval_with_timeout(agent, "eval:" + prompt)
            outputs.append(out)
        except Exception as ex:
            agent_eval_history_add(agent, f"CONSENSUS_FAIL: {ex}")
            continue
    return consensus_distill(outputs)


def agent_process(name, script_path, q_in, q_out, stop_event):
    import queue
    from pathlib import Path

    # 1) CORE: Realni model eval (skozi MODEL_REGISTRY)
    def direct_eval(prompt):
        return direct_agent_model_eval(name, prompt)

    # 2) Self-refinement (recursive)
    def recursive_self_evaluation(initial_prompt, model_fn, n_cycles=3):
        trace = [initial_prompt]
        reflections = []
        for _ in range(n_cycles):
            prompt = (
                "Reflektiraj in izboljšaj naslednje miselne korake:\n"
                + "\n".join(trace)
                + "\n---\nNadgrajen zaključek:"
            )
            evaluation = model_fn(prompt)
            trace.append(evaluation)
            reflections.append(evaluation)
        return reflections[-1] if reflections else "No output"

    # 3) Fallback agent (backup)
    fallback_script = script_path.replace("/active/", "/backup/")

    while not stop_event.is_set():
        try:
            msg = q_in.get(timeout=1)

            # HEALTHCHECK
            if msg == "healthcheck":
                q_out.put("OK")
                continue

            # LTM UPDATE
            if msg.startswith("ltm:"):
                update_agent_ltm(name, msg[4:])
                q_out.put("LTM OK")
                continue

            # MAIN EVAL
            if msg.startswith("eval:"):
                input_data = msg[5:]
                try:
                    # primarna evaluacija
                    output = direct_eval(input_data)

                    # self-refine
                    refined = recursive_self_evaluation(
                        initial_prompt=input_data + "\n" + str(output),
                        model_fn=lambda p: direct_eval(p),
                        n_cycles=3,
                    )

                    agent_eval_history_add(name, f"OK | Refined Output: {refined}")
                    q_out.put(str(refined))
                except Exception as ex:
                    agent_eval_history_add(name, f"FAIL: {ex}")

                    # fallback
                    if Path(fallback_script).exists():
                        try:
                            result = direct_eval(input_data)
                            q_out.put("FALLBACK: " + result)
                        except Exception:
                            q_out.put(f"ERR: {ex}")
                    else:
                        q_out.put(f"ERR: {ex}")
                continue

            # all other messages
            q_out.put(f"OK: {msg}")

        except queue.Empty:
            continue
        except Exception as ex:
            q_out.put(f"EXC: {ex}")
            continue


# ------------------------------------------------------
# 1) MODEL LOADER (HF + GGUF via llama-cpp-python)
# ------------------------------------------------------


def load_llama_cpp_model(path: Path):
    """Naloži GGUF/LLAMA model via llama_cpp."""
    try:
        from llama_cpp import Llama
    except Exception as e:
        logger.critical(f"LLAMA_CPP modul manjka: {e}")
        return None

    try:
        llm = Llama(
            model_path=str(path),
            n_ctx=8192,
            n_gpu_layers=99,
            temperature=0.7,
            top_p=0.95,
            verbose=False,
        )
        logger.success(f"MODEL_LOADER: naložen GGUF model → {path.name}")
        return llm
    except Exception as e:
        logger.error(f"MODEL_LOADER: napaka pri nalaganju {path}: {e}")
        return None


def load_huggingface_model(path: Path):
    """Naloži HF Transformer model (če je v mapi)."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as e:
        logger.critical(f"TRANSFORMERS modul manjka: {e}")
        return None

    try:
        tokenizer = AutoTokenizer.from_pretrained(str(path))
        model = AutoModelForCausalLM.from_pretrained(
            str(path), torch_dtype=bfloat16, device_map="auto"
        )
        logger.success(f"MODEL_LOADER: naložen HF model → {path.name}")
        return (model, tokenizer)
    except Exception as e:
        logger.error(f"MODEL_LOADER: napaka pri HF load {path}: {e}")
        return None


# ------------------------------------------------------
# 2) UNIFICIRANI MODEL REGISTRY
# ------------------------------------------------------
def register_all_models():
    """Robustno naloži vse modele iz ACTIVE_BASE z validacijo."""
    with MODEL_LOAD_LOCK:
        for file in ACTIVE_BASE.iterdir():
            model_name = file.name
            if model_name in MODEL_REGISTRY:
                continue

            model = None

            try:
                if file.suffix.lower() == ".gguf":
                    model = load_llama_cpp_model(file)

                elif file.is_dir():
                    # preveri, če je veljaven HuggingFace model
                    if (file / "config.json").exists():
                        model = load_huggingface_model(file)
                    else:
                        logger.warning(
                            f"MODEL_REGISTRY: mapa {file} ni veljaven HF model"
                        )

                else:
                    logger.warning(
                        f"MODEL_REGISTRY: ignoriran neprepoznan model: {file}"
                    )

                if model:
                    MODEL_REGISTRY[model_name] = model
                    logger.success(f"MODEL_REGISTRY: aktiviran {model_name}")
                else:
                    logger.warning(f"MODEL_REGISTRY: neuspešno nalaganje {model_name}")

            except Exception as ex:
                logger.error(f"MODEL_REGISTRY: kritična napaka pri {model_name}: {ex}")


def pick_model(agent_name: str):
    """Politika: vsi agenti uporabljajo isti model (prvi v registry)."""
    if not MODEL_REGISTRY:
        register_all_models()

    if not MODEL_REGISTRY:
        logger.error("MODEL_REGISTRY: ni naloženih modelov!")
        return None

    return next(iter(MODEL_REGISTRY.values()))


# ------------------------------------------------------
# 3) ENOTNA INFERENCE FUNKCIJA
# ------------------------------------------------------


def model_infer(model_obj, prompt: str) -> str:
    """Unificira llama.cpp + HF generate."""
    try:
        # llama-cpp model (Llama object)
        from llama_cpp import Llama

        if isinstance(model_obj, Llama):
            out = model_obj(prompt, max_tokens=256, stop=["</s>"])
            return out["choices"][0]["text"].strip()
    except Exception:
        pass

    try:
        # HuggingFace model (tuple)

        if isinstance(model_obj, tuple):
            model, tokenizer = model_obj
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            gen = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
            )
            return tokenizer.decode(gen[0], skip_special_tokens=True).strip()
    except Exception:
        pass

    return "NAPAKA: model ne podpira inference"


# ------------------------------------------------------
# 4) DIRECT AGENT MODEL EVAL (ZAMENJAŠ STARO)
# ------------------------------------------------------


def direct_agent_model_eval(agent_name: str, prompt: str) -> str:
    """Evaluacija agenta preko realnega modela."""
    model = pick_model(agent_name)
    if not model:
        logger.error(f"AGENT_MODEL: agent {agent_name} nima modela.")
        return "ERROR: model not available"

    try:
        result = model_infer(model, prompt)
        return result
    except Exception as e:
        logger.error(f"AGENT_MODEL_EVAL napaka ({agent_name}): {e}")
        return "ERROR"


def load_and_exec_agent(script_path, loc):
    try:
        with open(script_path, "r") as f:
            code = f.read()
        ast.parse(code)  # preveri sintaktično veljavnost
        compile(code, {}, loc, "<string>", "exec"); eval(code, {}, loc)
    except SyntaxError as e:
        logger.error(f"Agent sintaktična napaka: {e}")
    except Exception as e:
        logger.error(f"Napaka pri zagonu agenta {script_path}: {e}")


def agent_fatigue_loop():
    while True:
        now = time.time()
        for k in AGENTS.keys():
            AGENT_LAST_USED[k] = AGENT_LAST_USED.get(k, now)
        time.sleep(60)


def bootstrap_agents():
    agents = load_agent_roles()
    for a in agents:
        name = a["name"]
        AGENTS[name] = True
        AGENT_LAST_USED[name] = time.time()
        AGENT_SCORE[name] = 0
        AGENT_ERROR_COUNTS[name] = 0


def agent_topology_bootstrap():
    if not TOPOLOGY_FILE.exists():
        agents = load_agent_roles()
        topo = []
        for a in agents:
            topo.append(
                {
                    "name": a["name"],
                    "role": a["role"],
                    "domain": a.get("domain", ""),
                    "description": a.get("description", ""),
                    "path": str(ACTIVE_BASE / a["name"] / "agent.py"),
                }
            )
        with open(TOPOLOGY_FILE, "w") as f:
            json.dump(topo, f, indent=2)


def agent_mp_bootstrap():
    topology = json.load(open(TOPOLOGY_FILE))
    for agent in topology:
        name = agent["name"]
        path = agent["path"]
        q_in = mp.Queue()
        q_out = mp.Queue()
        p = mp.Process(
            target=agent_process,
            args=(name, path, q_in, q_out, STOP_EVENT),
            daemon=True,
        )
        p.start()
        AGENT_PROCESSES[name] = p
        AGENT_QUEUES[name] = (q_in, q_out)
        AGENTS[name] = {
            "role": agent.get("role", ""),
            "domain": agent.get("domain", ""),
            "description": agent.get("description", ""),
        }


def health_monitor_loop():
    while True:
        for name, proc in AGENT_PROCESSES.items():
            if not proc.is_alive():
                log_alert(f"Agent {name} ni aktiven.", "warning")
                reload_agent(name)
        fs_integrity_check()
        check_disk_space()
        time.sleep(60)


def unfreeze(x):
    if isinstance(x, tuple):
        # tuple od dict -> lista parov -> dict
        if all(isinstance(i, tuple) and len(i) == 2 for i in x):
            return {k: unfreeze(v) for k, v in x}
        return [unfreeze(i) for i in x]
    return x


def save_genski_bazen():
    with open(GENSKI_BAZEN_FILE, "w", encoding="utf-8") as f:
        json.dump(
            [unfreeze(item) for item in GENSKI_BAZEN], f, indent=2, ensure_ascii=False
        )


def fetch_model_from_url(url, target_dir):
    if not any(url.startswith(p) for p in MODEL_AUTOFETCH_ALLOWLIST):
        raise Exception("URL ni na allowlisti")
    r = requests.get(timeout=5, timeout=5, url, stream=True)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    file = target_dir / url.split("/")[-1]
    with open(file, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return str(file)


def autofetch_models_loop():
    while True:
        for fetch_file in Path(MODEL_AUTOFETCH_DIR).glob("*.json"):
            with open(fetch_file) as f:
                meta = json.load(f)
            url = meta.get("url")
            target = meta.get("target")
            try:
                model_path = fetch_model_from_url(url, target)
                log_alert(f"Model prenesen: {model_path}")
                fetch_file.unlink()
            except Exception as ex:
                log_alert(f"Napaka pri fetch: {ex}", "warning")
        time.sleep(300)


def build_faiss_index():
    global faiss_index, knowledge_bank
    if KNOWLEDGE_JSON.exists():
        with open(KNOWLEDGE_JSON) as f:
            knowledge_bank = json.load(f)
    else:
        knowledge_bank = []
    if not knowledge_bank:
        faiss_index = faiss.IndexFlatL2(EMBEDDING_SIZE)
        return
    embeddings = np.array(
        [sbert.encode(x["text"]) for x in knowledge_bank], dtype="float32"
    )
    faiss_index = faiss.IndexFlatL2(EMBEDDING_SIZE)
    # noinspection PyArgumentList
    faiss_index.add(embeddings)
    faiss.write_index(faiss_index, str(FAISS_INDEX_FILE))


def knowledge_add(text, meta=None):
    emb = sbert.encode(text)
    item = {
        "text": text,
        "meta": meta or {},
        "embedding": emb.tolist(),
        "id": hashlib.sha256((text + str(time.time())).encode()).hexdigest(),
    }
    knowledge_bank.append(item)
    with knowledge_lock:
        with open(KNOWLEDGE_JSON, "w") as f:
            json.dump(knowledge_bank, f, indent=2)
        build_faiss_index()


# noinspection PyTypeHints,PyTypeChecker
def knowledge_search(query: str, k: int = 5) -> list[str]:
    if faiss_index is None or not knowledge_bank:
        build_faiss_index()

    q_emb = np.array([sbert.encode(query)], dtype="float32")

    with knowledge_lock:
        distances, indices = faiss_index.search(q_emb, k)

    return [
        knowledge_bank[i]["text"] for i in indices[0] if 0 <= i < len(knowledge_bank)
    ]


def archive_mutation(old_dir, new_dir):
    ts = int(time.time())
    old_files = set(f for f in Path(old_dir).rglob("*") if f.is_file())
    new_files = set(f for f in Path(new_dir).rglob("*") if f.is_file())
    diff = []
    for f in new_files - old_files:
        diff.append(str(f.relative_to(new_dir)))
    archive_path = AGENT_MUTATION_ARCHIVE / f"{Path(new_dir).name}_{ts}.zip"
    shutil.make_archive(str(archive_path)[:-4], "zip", new_dir)
    with open(str(archive_path)[:-4] + ".diff.txt", "w") as df:
        df.write("\n".join(diff))


def mutation_process(target_model_dir):
    model_name = Path(target_model_dir).name
    temp_dir = TEMP_MODEL_DIR / (model_name + "_mut")
    shutil.copytree(target_model_dir, temp_dir, dirs_exist_ok=True)
    archive_mutation(target_model_dir, temp_dir)
    quarantine_model(temp_dir)
    log_alert(f"Mutacija končana: {model_name}")
    eval_mutacija(temp_dir)


def eval_mutacija(agent_dir):
    test_set = ["ping", "selftest", "status"]
    res = []
    agent_name = Path(agent_dir).name
    for t in test_set:
        try:
            out = agent_eval_with_timeout(agent_name, "eval:" + t, 6)
            res.append(str(out))
        except Exception as ex:
            res.append(f"ERR: {ex}")
    agent_eval_history_add(agent_name, "mutacija-eval", {"results": res})
    return res


def group_mutation(agents):
    ts = int(time.time())
    archive_paths = []
    for a in agents:
        src = ACTIVE_BASE / a
        dst = TEMP_MODEL_DIR / f"{a}_mut_{ts}"
        shutil.copytree(src, dst, dirs_exist_ok=True)
        archive_mutation(src, dst)
        quarantine_model(dst)
        archive_paths.append(str(dst))
    log_alert(f"Skupinska mutacija: {', '.join(agents)}", "info")


def agent_eval_history_add(agent, result, meta=None):
    conn = safe_sqlite_connect(EVAL_HISTORY_DB)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS eval_history (agent TEXT, ts INTEGER, result TEXT, meta TEXT)"
    )
    cur.execute(
        "INSERT INTO eval_history (agent, ts, result, meta) VALUES (?, ?, ?, ?)",
        (agent, int(time.time()), result, json.dumps(meta or {})),
    )
    conn.commit()
    conn.close()


def agent_eval_history_get(agent, n=20):
    conn = safe_sqlite_connect(EVAL_HISTORY_DB)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS eval_history (agent TEXT, ts INTEGER, result TEXT, meta TEXT)"
    )
    cur.execute(
        "SELECT ts, result, meta FROM eval_history WHERE agent=? ORDER BY ts DESC LIMIT ?",
        (agent, n),
    )
    out = [
        {"ts": ts, "result": result, "meta": json.loads(meta)}
        for ts, result, meta in cur.fetchall()
    ]
    conn.close()
    return out


def vm_boot(vm_name):
    img_path = VM_IMAGES.get(vm_name)
    if not img_path:
        log_alert(f"VM {vm_name} ni na voljo.", "critical")
        return None
    port = VM_PORTS[vm_name]

    if not is_port_free(port):
        log_alert(f"Port {port} že v uporabi. VM {vm_name} ne bo zagnan.", "error")
        return None

    proc = subprocess.Popen(
        [
            "qemu-system-x86_64",
            "-m",
            "1024",
            "-hda",
            img_path,
            "-net",
            f"user,hostfwd=tcp::{port}-:22",
            "-net",
            "nic",
            "-nographic",
        ]
    )
    log_alert(f"VM {vm_name} zagnan na portu {port}", "info")
    return proc


def vm_shutdown(proc):
    try:
        proc.terminate()
        log_alert("VM končan.", "info")
    except Exception:
        pass


def vm_snapshot(vm_name):
    img_path = VM_IMAGES.get(vm_name)
    if not img_path:
        return
    snap_path = SNAPSHOT_BASE / (vm_name + "_" + str(int(time.time())) + ".qcow2")
    shutil.copy(img_path, snap_path)
    log_alert(f"Snapshot {vm_name} shranjen.", "info")


def vm_eval(vm_name, command):
    endpoint = eval_vm_endpoints.get(vm_name)
    if not endpoint:
        log_alert(f"VM eval endpoint ni na voljo za {vm_name}.", "warning")
        return "VM endpoint ni na voljo"
    try:
        r = requests.post(timeout=5, timeout=5, endpoint, json={"cmd": command}, timeout=15)
        return r.text
    except Exception as ex:
        log_alert(f"Napaka VM eval: {ex}", "warning")
        return f"VM napaka: {ex}"


def freeze(x):
    if isinstance(x, dict):
        return tuple((k, freeze(v)) for k, v in sorted(x.items()))
    if isinstance(x, list):
        return tuple(freeze(i) for i in x)
    if isinstance(x, set):
        return tuple(sorted(freeze(i) for i in x))
    return x


# noinspection PyUnresolvedReferences
def load_genski_bazen():
    GENSKI_BAZEN_PATH = GENSKI_BAZEN_FILE
    with open(GENSKI_BAZEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {freeze(item) for item in data}
    return {freeze(data)}


def validate_topology():
    if not TOPOLOGY_FILE.exists():
        raise Exception("Topology file manjka!")

    with open(TOPOLOGY_FILE) as f:
        topo = json.load(f)

    seen = set()
    for agent in topo:
        name = agent.get("name")
        path = agent.get("path")

        if not name or not path:
            raise Exception(f"Nepravilen zapis v topology: {agent}")

        if name in seen:
            raise Exception(f"Podvojen agent: {name}")
        seen.add(name)

        agent_path = Path(path)
        if not agent_path.exists():
            try:
                agent_path.parent.mkdir(parents=True, exist_ok=True)
                agent_path.write_text("# placeholder agent\n")
                logger.warning(f"Manjkajoči agent ustvarjen: {agent_path}")
            except Exception as e:
                raise Exception(f"Napaka pri ustvarjanju agenta: {agent_path}: {e}")

    return True


def orchestrator_threads(model_reload_loop=None):
    threading.Thread(target=autofetch_models_loop, daemon=True).start()
    threading.Thread(target=agent_fatigue_loop, daemon=True).start()
    threading.Thread(target=schedule_daily_backup, daemon=True).start()
    threading.Thread(target=self_eval_agent, daemon=True).start()
    threading.Thread(target=reflection_agent, daemon=True).start()
    threading.Thread(target=agent_feedback_loop, daemon=True).start()
    threading.Thread(target=dynamic_agent_scaling, daemon=True).start()
    threading.Thread(target=hardware_diag, daemon=True).start()
    threading.Thread(target=vm_network_check, daemon=True).start()
    threading.Thread(target=asynchronous_model_distiller, daemon=True).start()
    threading.Thread(target=longterm_compression_agent, daemon=True).start()
    threading.Thread(target=knowledge_expiry_purger, daemon=True).start()
    threading.Thread(target=meta_goal_manager_loop, daemon=True).start()
    threading.Thread(target=epistemic_mutation_loop, daemon=True).start()
    threading.Thread(target=distributed_sync_loop, daemon=True).start()
    threading.Thread(target=real_model_distill_loop, daemon=True).start()

    if model_reload_loop is not None:
        threading.Thread(target=model_reload_loop, daemon=True).start()


# ===========  STATUS DASHBOARD ===============
@app.get("/status")
def api_status():
    update_uptime()
    return {
        "uptime": time.time() - psutil.boot_time(),
        "agents": {
            k: (v.is_alive() if hasattr(v, "is_alive") else False)
            for k, v in AGENT_PROCESSES.items()
        },
        "SAFE_MODE": SAFE_MODE.is_set(),
        "CPU": psutil.cpu_percent(),
        "RAM": psutil.virtual_memory().available / 1024**3,
        "VMs": list(VM_IMAGES.keys()),
        "pending_mutacije": len([p for p in TEMP_MODEL_DIR.iterdir() if p.is_dir()]),
        "agent_fatigue": {k: time.time() - AGENT_LAST_USED.get(k, 0) for k in AGENTS},
    }


@app.get("/dashboard")
def dashboard_html():
    stats = api_status()
    html = f"""
    <html>
    <head>
        <title>CELL Nadzorna plošča</title>
    </head>
    <body>
        <h1>Status agenta CELL</h1>
        <p>Uptime: {stats['uptime'] / 3600:.2f} ur</p>
        <p>SAFE_MODE: {stats['SAFE_MODE']}</p>
        <p>CPU: {stats['CPU']} %</p>
        <p>RAM: {stats['RAM']:.2f} GB</p>
        <p>VM-ji: {', '.join(stats['VMs'])}</p>
        <h2>Agenti</h2>
        <ul>
            {"".join(f"<li>{k}: {'OK' if v else 'NE DELUJE'}</li>" for k, v in stats['agents'].items())}
        </ul>
        <p>Pending mutacije: {stats['pending_mutacije']}</p>
        <h3>Agent fatigue (s):</h3>
        <ul>
            {"".join(f"<li>{k}: {int(v)}</li>" for k, v in stats['agent_fatigue'].items())}
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/alerts")
def get_alerts():
    if ALERTS_LOG.exists():
        with open(ALERTS_LOG) as f:
            lines = f.readlines()[-100:]
        return HTMLResponse(content="<pre>" + "".join(lines) + "</pre>")
    return HTMLResponse(content="Ni opozoril.")


@app.get("/auditlog")
def get_audit_log():
    if AUDIT_LOG.exists():
        with open(AUDIT_LOG) as f:
            lines = f.readlines()[-200:]
        return HTMLResponse(content="<pre>" + "".join(lines) + "</pre>")
    return HTMLResponse(content="Ni audit dogodkov.")


@app.get("/uptime")
def uptime_info():
    if UPTIME_FILE.exists():
        with open(UPTIME_FILE) as f:
            data = json.load(f)
        return data
    return {"boot": 0, "sessions": []}


@app.get("/sessiontracker")
def session_tracker():
    if SESSION_TRACKER_FILE.exists():
        with open(SESSION_TRACKER_FILE) as f:
            sessions = json.load(f)
        return sessions[-100:]
    return []


@app.get("/restore_snapshot")
def api_restore_snapshot():
    return {"status": "O"}


def interactive_shell(_record_voice=None):
    aktivni_uporabnik = None
    print("\n💡 Interaktivni CLI – prijava z glasom, odjava zaščitena.\n")
    while not STOP_EVENT.is_set():
        if not aktivni_uporabnik:
            print("🎙 Prijava – reci 'CELL'...")
            audio = _record_voice()
            if not voice_authenticate(audio):
                print("❌ Avtentikacija ni uspela.\n")
                continue
            aktivni_uporabnik = identify_user(audio)
            print(f"✅ Prijavljen kot: {aktivni_uporabnik}\n")
            continue
        ukaz = input(f"[{aktivni_uporabnik}] ⮞ ").strip()
        if not ukaz:
            continue
        if ukaz.lower() == "odjava":
            print("🎙 Potrdi odjavo...")
            audio = _record_voice()
            if identify_user(audio) == aktivni_uporabnik:
                print("✅ Odjava uspešna.\n")
                aktivni_uporabnik = None
            else:
                print("❌ Glas ne ustreza trenutnemu uporabniku.\n")
            continue
        if not has_permission(aktivni_uporabnik, ukaz):
            print("⛔ Ukaz zavrnjen zaradi pravic.\n")
            continue
        print(f"✅ Ukaz dovoljen: {ukaz}\n")
        # Tu lahko dodaš dejansko izvedbo ukaza:
        # exec_command(ukaz)


def orchestrator_bootstrap():
    import json
    from pathlib import Path

    from orchestrator_shared import register_all_models  # ✅ Dodano

    # ROOT = /opt/cell
    ROOT = Path(__file__).resolve().parent.parent

    # Flag za bootstrap
    BOOTSTRAP_FLAG = ROOT / "runtime" / "bootstrap_done.flag"

    # 🔥 POPOLNOMA PRAVILEN loader genski_bazen (rekurzivna hashable konverzija)
    def make_hashable(obj):
        if isinstance(obj, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(make_hashable(x) for x in obj)
        else:
            return obj

    def load_genski_bazen():
        GENSKI_BAZEN_PATH = ROOT / "agents" / "genski_bazen.json"

        if not GENSKI_BAZEN_PATH.exists():
            return set()

        with open(GENSKI_BAZEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return {make_hashable(item) for item in data}
        elif isinstance(data, dict):
            return {make_hashable(data)}
        else:
            raise TypeError("genski_bazen.json je v napačnem formatu")

    # 🌐 Topologija in validacija
    agent_topology_bootstrap()
    validate_topology()

    # 🧠 Naloži modelni register PRED agenti
    register_all_models()

    # 🚨 Če modeli manjkajo, preklopi v SAFE_MODE
    if not MODEL_REGISTRY:
        logger.critical("❌ Ni naloženih modelov – preklapljam v SAFE_MODE.")
        SAFE_MODE.clear()
        FALLBACK_MODE.set()
        return

    # ⚙️ Nadaljuj inicializacijo agentov
    bootstrap_agents()
    agent_mp_bootstrap()
    build_faiss_index()

    # 💾 Genski bazen (varno in hashable)
    GENSKI_BAZEN.update(load_genski_bazen())

    # 🧬 Prvi zagon: destilacija base modelov
    if not BOOTSTRAP_FLAG.exists():
        from system.bootstrap_base_models import bootstrap_base_models

        logger.info("ORCHESTRATOR: prvi zagon – bootstrapam modele.")
        bootstrap_base_models()

        BOOTSTRAP_FLAG.parent.mkdir(parents=True, exist_ok=True)
        BOOTSTRAP_FLAG.write_text("DONE", encoding="utf-8")
        logger.success("ORCHESTRATOR: bootstrap končan.")
    else:
        logger.info("ORCHESTRATOR: bootstrap že izveden – preskakujem.")

    logger.info("ORCHESTRATOR: inicializacija zaključena.")


class Kameleon:
    def __init__(self):
        logger.info("✅ Kameleon: inicializiran.")

    def run(self, query: str) -> str:
        logger.debug(f"Kameleon.run() → {query}")
        return "Odgovor iz Kameleona (placeholder)"


def model_reload_loop():
    while True:
        try:
            register_all_models()
        except Exception as ex:
            logger.error(f"MODEL_RELOAD_LOOP: {ex}")
        time.sleep(300)  # vsakih 5 minut


# ===========  GLAVNA ZANKA ===============
def main():
    global VM_IMAGES, VM_PORTS, eval_vm_endpoints

    # --- Inicializacija sektorjev in VM-jev ---
    load_sector_os_map()
    VM_IMAGES, VM_PORTS, eval_vm_endpoints = discover_vm_images()

    # --- Orkestrator + modeli + agenti ---
    orchestrator_bootstrap()
    orchestrator_threads(model_reload_loop)  # << DODANO: reload modellerja

    # --- Jedrne sistemske niti ---
    system_threads = [
        start_model_watchdog,
        reload_agent_on_fs_change,
        voice_interactive_engine,
        heartbeat_monitor,
        session_health_monitor,
        cpu_mem_guard,
        agent_health_monitor,
        agent_performance_eval,
        disk_io_monitor,
        rotate_logs,
        audio_capture_thread,
    ]

    for fn in system_threads:
        threading.Thread(target=fn, daemon=True).start()

    # --- Startup audit log ---
    audit_startup()

    # --- Web API ---
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ===========  ZAŽENI GLEDE NA KONTEKST ===============
if __name__ == "__main__":
    import sys

    if "--shell" in sys.argv:
        interactive_shell()
    else:
        main()


def start_orchestrator():
    main()
