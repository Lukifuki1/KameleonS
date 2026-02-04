#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from loguru import logger

def run(stop_event):
    logger.info("🧠 SEMANTIC MAPPER: aktiviran")
    while not stop_event.is_set():
        # Semantična analiza entropije (placeholder za dejansko logiko)
        logger.debug("🧠 SEMANTIC MAPPER: analiza entropije...")
        time.sleep(60)
    logger.info("🧠 SEMANTIC MAPPER: zaustavljen")
