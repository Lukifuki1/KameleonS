#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from loguru import logger
from collections import Counter
from threading import Lock
from orchestrator_shared import knowledge_bank, knowledge_lock

DIVERSITY_SIGNAL_FILE = "runtime/diversity_injection.signal"
HOMOGENEITY_THRESHOLD = 0.75  # Če > 75% izhodov so vsebinsko enaki → homogenost
CHECK_WINDOW = 50  # Koliko zadnjih sklepov naj primerja
CHECK_INTERVAL = 300  # sekund
lock = Lock()

def calculate_homogeneity(outputs: list[str]) -> float:
    if not outputs:
        return 0.0
    normalized = [o.strip().lower() for o in outputs]
    counter = Counter(normalized)
    most_common = counter.most_common(1)[0][1]
    return most_common / len(normalized)

def trigger_diversity_signal():
    try:
        with open(DIVERSITY_SIGNAL_FILE, "w") as f:
            f.write("inject_diversity")
        logger.warning("🌀 PRESSURE VALVE: sprožena raznolikostna injekcija!")
    except Exception as e:
        logger.error(f"🌀 PRESSURE VALVE: napaka pri zapisovanju injekcijskega signala: {e}")

def run(stop_event):
    logger.info("🌀 PRESSURE VALVE: aktiviran")
    while not stop_event.is_set():
        recent_outputs = []
        with knowledge_lock:
            if len(knowledge_bank) > CHECK_WINDOW:
                recent_outputs = knowledge_bank[-CHECK_WINDOW:]
            else:
                recent_outputs = list(knowledge_bank)

        homo = calculate_homogeneity(recent_outputs)
        logger.debug(f"🌀 PRESSURE VALVE: trenutna homogenost = {round(homo * 100, 2)}%")

        if homo >= HOMOGENEITY_THRESHOLD:
            trigger_diversity_signal()

        time.sleep(CHECK_INTERVAL)

    logger.info("🌀 PRESSURE VALVE: zaustavljen")
