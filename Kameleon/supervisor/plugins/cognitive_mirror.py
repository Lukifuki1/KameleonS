#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
from loguru import logger
from pathlib import Path
from collections import defaultdict
from threading import Lock

from orchestrator_shared import AGENTS, AGENT_QUEUES

DIVERGENCE_LOG = Path("runtime/cognitive_divergence.json")
MIRROR_INTERVAL = 180  # sekund
DIVERGENCE_THRESHOLD = 0.4  # stopnja neskladja (0–1)

LOCK = Lock()

def collect_agent_opinions(prompt: str) -> dict:
    results = {}
    for agent in AGENTS:
        qin, qout = AGENT_QUEUES.get(agent, (None, None))
        if not qin or not qout:
            continue
        try:
            qin.put({"mirror_probe": prompt})
            output = qout.get(timeout=3)
            results[agent] = output.strip() if output else None
        except Exception:
            results[agent] = None
    return results

def compute_divergence(responses: dict) -> float:
    filtered = [r for r in responses.values() if r]
    total = len(filtered)
    if total < 2:
        return 0.0

    disagreements = 0
    for i in range(total):
        for j in range(i+1, total):
            if filtered[i] != filtered[j]:
                disagreements += 1

    possible = total * (total - 1) / 2
    return round(disagreements / possible, 3) if possible > 0 else 0.0

def log_divergence(prompt: str, responses: dict, score: float):
    record = {
        "timestamp": int(time.time()),
        "prompt": prompt,
        "divergence": score,
        "responses": responses
    }
    try:
        with LOCK:
            existing = []
            if DIVERGENCE_LOG.exists():
                with DIVERGENCE_LOG.open("r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(record)
            with DIVERGENCE_LOG.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.info(f"🪞 COGNITIVE MIRROR: divergenca zabeležena ({score})")
    except Exception as e:
        logger.error(f"🪞 COGNITIVE MIRROR: napaka pri zapisovanju: {e}")

def run(stop_event):
    logger.info("🔁 COGNITIVE MIRROR: aktiviran")
    test_prompts = [
        "Kaj pomeni etična odgovornost?",
        "Ali je bolje optimizirati za hitrost ali robustnost?",
        "Kaj so posledice neuspešne distilacije znanja?",
        "Kako bi opisal pomen homeostaze v sistemih?"
    ]

    while not stop_event.is_set():
        for prompt in test_prompts:
            responses = collect_agent_opinions(prompt)
            score = compute_divergence(responses)
            if score >= DIVERGENCE_THRESHOLD:
                log_divergence(prompt, responses, score)
            else:
                logger.debug(f"🔁 MIRROR: ni zaznane pomembne divergence ({score})")
            if stop_event.is_set():
                break
        time.sleep(MIRROR_INTERVAL)

    logger.info("🔁 COGNITIVE MIRROR: zaustavljen")
