#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from loguru import logger
from orchestrator_shared import knowledge_bank, theta_resonance_check
from threading import Event

CHECK_INTERVAL = 180  # sekund

def evaluate_resonance():
    logger.debug("🔍 RESONANCE SCANNER: preverjam resonanco...")

    unstable = []
    total = 0

    for entry in knowledge_bank[-100:]:  # samo zadnjih 100
        try:
            total += 1
            if not theta_resonance_check(entry):
                unstable.append(entry)
        except Exception as e:
            logger.error(f"🔍 Napaka pri preverjanju resonance: {e}")

    percent = (len(unstable) / total * 100) if total else 0

    if percent > 10:
        logger.warning(f"🔍 Resonanca nizka: {len(unstable)}/{total} ({percent:.1f}%) ne rezonira z Θ")
    else:
        logger.info(f"🔍 Resonanca stabilna: {100 - percent:.1f}% znanja rezonira z Θ")

def run(stop_event: Event):
    logger.info("🔍 RESONANCE SCANNER: aktiviran")
    while not stop_event.is_set():
        evaluate_resonance()
        time.sleep(CHECK_INTERVAL)
    logger.info("🔍 RESONANCE SCANNER: zaustavljen")
