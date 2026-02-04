#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import numpy as np
from loguru import logger
from pathlib import Path
from threading import Lock

from orchestrator_shared import sbert, AGENTS, AGENT_QUEUES

DECAY_LOG = Path("runtime/decay_drift_log.json")
LOCK = Lock()
DETECTION_INTERVAL = 300  # sekund
WINDOW_SIZE = 5
DRIFT_THRESHOLD = 0.25  # nižja kot 0.25 pomeni očiten drift

history = {}

def collect_sample(agent_name: str, prompt: str) -> str | None:
    qin, qout = AGENT_QUEUES.get(agent_name, (None, None))
    if not qin or not qout:
        return None
    try:
        qin.put({"drift_probe": prompt})
        return qout.get(timeout=3)
    except Exception:
        return None

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def log_drift(agent: str, prompt: str, score: float):
    entry = {
        "timestamp": int(time.time()),
        "agent": agent,
        "prompt": prompt,
        "similarity": round(score, 3)
    }
    with LOCK:
        existing = []
        if DECAY_LOG.exists():
            try:
                with DECAY_LOG.open("r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing.append(entry)
        with DECAY_LOG.open("w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    logger.warning(f"📉 DECAY DETECTOR: Agent {agent} kaže drift ({score}) pri '{prompt}'")

def run(stop_event):
    logger.info("📉 DECAY DETECTOR: aktiviran")
    test_prompts = [
        "Kaj je inteligenca?",
        "Pojasni stabilnost sistema.",
        "Kaj je pomembno pri etiki AI-ja?",
        "Kako bi agent uravnotežil hitrost in natančnost?",
        "Kaj pomeni 'sklepanje v več korakih'?"
    ]

    while not stop_event.is_set():
        for agent in AGENTS:
            for prompt in test_prompts:
                output = collect_sample(agent, prompt)
                if not output:
                    continue

                try:
                    vec = sbert.encode([output], normalize_embeddings=True)[0]
                except Exception:
                    continue

                if agent not in history:
                    history[agent] = defaultdict(list)

                vecs = history[agent][prompt]
                vecs.append(vec.tolist())
                if len(vecs) > WINDOW_SIZE:
                    vecs.pop(0)

                if len(vecs) >= 2:
                    sims = []
                    for i in range(len(vecs)-1):
                        sim = cosine_similarity(np.array(vecs[i]), np.array(vecs[i+1]))
                        sims.append(sim)
                    avg_sim = sum(sims) / len(sims)
                    if avg_sim < DRIFT_THRESHOLD:
                        log_drift(agent, prompt, avg_sim)

        time.sleep(DETECTION_INTERVAL)

    logger.info("📉 DECAY DETECTOR: zaustavljen")
