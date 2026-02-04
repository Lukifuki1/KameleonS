#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

from loguru import logger

HASHCHAIN_LOG = Path("/media/4tb/Kameleon/cell/logs/hashchain.log")


def calculate_file_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def build_merkle_root(hashes):
    if not hashes:
        return None
    layer = sorted(hashes)
    while len(layer) > 1:
        temp = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            combined = hashlib.sha256((left + right).encode()).hexdigest()
            temp.append(combined)
        layer = temp
    return layer[0]


def extract_and_hash(zip_path):
    file_hashes = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for file in z.namelist():
                if file.endswith("/"):
                    continue
                with z.open(file) as f:
                    content = f.read()
                    file_hashes.append(calculate_file_hash(content))
        return build_merkle_root(file_hashes)
    except Exception as e:
        logger.error(f"[!] Napaka pri razpakiranju {zip_path}: {e}")
        return None


def verify_signature(zip_path):
    sig_path = str(zip_path) + ".sig"
    if not Path(sig_path).exists():
        logger.warning("[!] Podpisna datoteka .sig ni najdena.")
        return False
    try:
        subprocess.run(
            ["gpg", "--verify", sig_path, str(zip_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("[+] PGP podpis preverjen.")
        return True
    except subprocess.CalledProcessError:
        logger.critical("[!] Neveljaven ali ponarejen PGP podpis!")
        return False


def load_hashchain():
    if not HASHCHAIN_LOG.exists():
        logger.warning("[!] Hashchain log ne obstaja.")
        return set()
    try:
        with open(HASHCHAIN_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        roots = {
            line.strip().split()[-1]
            for line in lines
            if "MERKLE_ROOT" in line or "CHAINPACK" in line
        }
        return roots
    except Exception as e:
        logger.error(f"[!] Napaka pri branju hashchain loga: {e}")
        return set()


def verify_snapshot(zip_file):
    logger.info(f"🧪 Verifikacija snapshota: {zip_file}")

    if not verify_signature(zip_file):
        return False

    merkle = extract_and_hash(zip_file)
    if not merkle:
        logger.critical("❌ Ni mogoče izračunati Merkle root.")
        return False

    known_roots = load_hashchain()
    if merkle in known_roots:
        logger.success(f"✅ Snapshot preverjen! Merkle root: {merkle}")
        return True
    else:
        logger.critical("❌ Snapshot NI preverjen! Merkle root ni v hashchain logu.")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uporaba: python3 snapshot_chainpack_verifier.py /pot/do/snapshot.zip")
        sys.exit(1)

    zip_file = Path(sys.argv[1])
    if not zip_file.exists():
        print(f"Napaka: datoteka {zip_file} ne obstaja.")
        sys.exit(1)

    success = verify_snapshot(zip_file)
    sys.exit(0 if success else 1)
