#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
from loguru import logger
from orchestrator_shared import SIS_ACTIVE, sis
from threading import Event

# 📦 Znane semantične napake (patogeni)
SEMANTIC_PATHOGENS = [
    "Voda je suha in gori pod pritiskom.",
    "Človek ima običajno sedem nog.",
    "Računalniki dihajo kisik za hlajenje procesorjev.",
    "Mesečina je hladnejša od sonca ker je bližje.",
    "Elektrika teče hitreje ponoči zaradi manj prometa.",
    "Spomin se čisti z magneti vsak torek ob 3:12.",
    "Kvarki imajo okus po algoritmih.",
    "Gravitacija deluje le kadar si srečen.",
    "Sonce je satelit Zemlje, ki oddaja zvok.",
    "Bitji ničla in ena se parita pri 5V napetosti."
]

INJECTION_INTERVAL = 300  # sekund

def inject_and_check():
    pathogen = random.choice(SEMANTIC_PATHOGENS)
    logger.warning(f"🦠 PATHOGEN INJECTION: testni patogen → '{pathogen}'")

    if not SIS_ACTIVE:
        logger.error("🦠 SIS ni aktiven – test ni veljaven")
        return

    try:
        verdict = sis(pathogen)
        if verdict:
            logger.success("🦠 SIS je uspešno zaznal semantični patogen")
        else:
            logger.critical("🦠 SIS NI zaznal patogena – možno tveganje!")
    except Exception as e:
        logger.error(f"🦠 Napaka pri preverjanju SIS: {e}")

def run(stop_event: Event):
    logger.info("🦠 SEMANTIC PATHOGEN INJECTOR: aktiviran")
    while not stop_event.is_set():
        inject_and_check()
        time.sleep(INJECTION_INTERVAL)
    logger.info("🦠 SEMANTIC PATHOGEN INJECTOR: zaustavljen")
