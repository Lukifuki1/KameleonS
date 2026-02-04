#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import threading
import time
from pathlib import Path

from plugin_loader import load_and_run_script
from scheduler import RUNNING_THREADS, STOP_EVENTS

CHECK_INTERVAL = 30  # sekund
LOGFILE = Path("/media/4tb/Kameleon/cell/logs/plugin_health_monitor.log")
REGISTRY_FILE = Path("/media/4tb/Kameleon/cell/system/scripts_registry.json")

# Maksimalno dovoljeni restarti plugina v časovnem oknu
RESTART_LIMIT = 3
RESTART_WINDOW = 300  # 5 minut
RESTART_TRACK = {}  # {plugin_name: [timestamps]}


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def load_registry():
    if not REGISTRY_FILE.exists():
        log("[CRITICAL] scripts_registry.json manjka!")
        return []

    try:
        data = json.loads(REGISTRY_FILE.read_text())
        return data.get("scripts", [])
    except Exception as e:
        log(f"[CRITICAL] Napaka pri branju registry: {e}")
        return []


def restart_allowed(name):
    now = time.time()
    RESTART_TRACK.setdefault(name, [])
    RESTART_TRACK[name] = [t for t in RESTART_TRACK[name] if now - t < RESTART_WINDOW]
    RESTART_TRACK[name].append(now)

    if len(RESTART_TRACK[name]) > RESTART_LIMIT:
        log(
            f"[BLOCKED] Plugin '{name}' restartan prevečkrat. Zaklep za {RESTART_WINDOW}s."
        )
        return False

    return True


def monitor_plugins():
    log("📡 Začenjam nadzor plugin modulov...")

    while True:
        registry = load_registry()

        for entry in registry:
            name = entry.get("name")
            path = Path(entry.get("path"))
            enabled = entry.get("enabled", False)

            # Le aktivni plugin-i
            if not enabled:
                continue

            # Če nit ne obstaja, jo ustvari
            thread = RUNNING_THREADS.get(name)

            if thread is None or not thread.is_alive():
                log(f"[!] Plugin '{name}' je izpadel ali še ni zagnan.")

                if not restart_allowed(name):
                    continue

                if not path.exists():
                    log(f"[!] Plugin '{name}': datoteka ne obstaja → {path}")
                    continue

                try:
                    stop_event = threading.Event()
                    STOP_EVENTS[name] = stop_event

                    t = threading.Thread(
                        target=load_and_run_script, args=(path, stop_event), daemon=True
                    )
                    t.start()
                    RUNNING_THREADS[name] = t

                    log(f"[+] Plugin '{name}' ponovno zagnan iz {path}")

                except Exception as e:
                    log(f"[CRITICAL] Napaka pri ponovnem zagonu plugina '{name}': {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor_plugins()
