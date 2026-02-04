#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from loguru import logger
from threading import Lock
from orchestrator_shared import knowledge_bank, knowledge_lock

import re
import string
from hashlib import sha256

FILTER_INTERVAL = 120  # sekund
MEMETIC_NOISE_PATTERNS = [
    r"(?i)\b(človeštvo|uporabnik|internet|OpenAI|kakor veste|če ste online)\b",
    r"(?i)\b(prihodnost bo pokazala|po mojem mnenju|čeprav nisem prepričan)\b",
    r"(?i)\b(vesolje|nezemljani|mistika|dimenzije|manifestacija)\b",
]

MAX_ACCEPTABLE_ENTROPY = 5.0  # prag memetične razpršenosti
LOCK = Lock()
FILTERED = []

def clean_text(text: str) -> str:
    return text.lower().translate(str.maketrans('', '', string.punctuation))

def is_noise(text: str) -> bool:
    for pattern in MEMETIC_NOISE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def calc_shannon_entropy(text: str) -> float:
    prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
    return -sum([p * (p and math.log(p, 2)) for p in prob])

def hash_content(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:12]

def run(stop_event):
    logger.info("🔏 EPISTEMIC FILTER: aktiviran")
    while not stop_event.is_set():
        to_filter = []

        with knowledge_lock:
            for item in knowledge_bank:
                if not isinstance(item, str):
                    continue
                h = hash_content(item)
                if h in FILTERED:
                    continue
                FILTERED.append(h)

                cleaned = clean_text(item)

                if is_noise(cleaned):
                    logger.warning(f"🔏 FILTRIRANO: memetični šum zaznan v: {item[:50]}...")
                    continue

                entropy = calc_shannon_entropy(cleaned)
                if entropy > MAX_ACCEPTABLE_ENTROPY:
                    logger.warning(f"🔏 FILTRIRANO: visoka entropija ({round(entropy,2)}) – {item[:50]}...")
                    continue

                to_filter.append(h)

        time.sleep(FILTER_INTERVAL)

    logger.info("🔏 EPISTEMIC FILTER: zaustavljen")
