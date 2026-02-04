#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import time
from pathlib import Path

PLUGIN_DIR = Path("/media/4tb/Kameleon/cell/system/")
HASH_DIR = Path("/media/4tb/Kameleon/cell/system/hashes/")
LOGFILE = Path("/media/4tb/Kameleon/cell/logs/plugin_integrity_guard.log")
LOCKDOWN_FLAG = Path("/media/4tb/Kameleon/cell/LOCKDOWN")

# hash konfiguracija
ALGO = hashlib.sha3_512
EXT = ".py"
HASH_EXT = ".sha3"
CHECK_INTERVAL = 300  # sekund


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def hash_file(path):
    return ALGO(path.read_bytes()).hexdigest()


def verify_plugin_integrity():
    if not PLUGIN_DIR.exists():
        log("PLUGIN DIR ne obstaja.")
        return

    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    HASH_DIR.mkdir(parents=True, exist_ok=True)

    for plugin_path in PLUGIN_DIR.glob(f"*{EXT}"):
        plugin_name = plugin_path.name
        hash_path = HASH_DIR / (plugin_name + HASH_EXT)

        current_hash = hash_file(plugin_path)

        if not hash_path.exists():
            hash_path.write_text(current_hash)
            log(f"[INIT] Hash ustvarjen za: {plugin_name}")
            continue

        stored_hash = hash_path.read_text().strip()

        if current_hash != stored_hash:
            log(f"[!] INTEGRITY FAIL za {plugin_name}")
            LOCKDOWN_FLAG.touch()
        else:
            log(f"[OK] {plugin_name}")


def integrity_monitor_loop():
    log("🔐 Zagon integrity monitorja za plugine")
    while True:
        verify_plugin_integrity()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    integrity_monitor_loop()
