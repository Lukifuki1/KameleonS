#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import threading
from pathlib import Path
from loguru import logger
from plugin_loader import load_and_run_script

REGISTRY_FILE = Path("scripts_registry.json")
PLUGIN_DIR = Path("plugins")
RUNNING_THREADS = {}
STOP_EVENTS = {}

def scheduler_loop():
    while True:
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception as e:
            logger.critical(f"SCHEDULER: napaka pri branju {REGISTRY_FILE}: {e}")
            time.sleep(10)
            continue

        for script in registry.get("scripts", []):
            name = script.get("name")
            path = PLUGIN_DIR / Path(script.get("path", "")).name
            enabled = script.get("enabled", True)

            if not name or not path.exists() or not enabled:
                continue

            if name in RUNNING_THREADS and RUNNING_THREADS[name].is_alive():
                continue

            logger.info(f"SCHEDULER: zaganjam modul {name}")
            stop_event = threading.Event()
            STOP_EVENTS[name] = stop_event
            t = threading.Thread(target=load_and_run_script, args=(path, stop_event), daemon=True)
            t.start()
            RUNNING_THREADS[name] = t

        time.sleep(10)

if __name__ == "__main__":
    logger.info("SCHEDULER: sistemski nadzornik zagnan")
    try:
        scheduler_loop()
    except KeyboardInterrupt:
        logger.warning("SCHEDULER: prekinjeno ročno")
        for stop_event in STOP_EVENTS.values():
            stop_event.set()
    except Exception as e:
        logger.critical(f"SCHEDULER: fatala napaka: {e}")
