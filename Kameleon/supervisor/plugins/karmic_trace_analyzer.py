#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
from pathlib import Path
from loguru import logger
from collections import defaultdict

STRATEGY_LOG = Path("logs/strategy.log")
KARMA_INDEX = Path("runtime/karmic_trace_index.json")

REFRESH_INTERVAL = 300  # sekund

# Uteži za oceno
WEIGHTS = {
    "success": +1.5,
    "failure": -2.0,
    "timeout": -1.0,
    "stability": +0.75,
    "interference": -1.5,
    "reuse": +1.0,
    "goal_aligned": +2.0
}

def parse_strategy_events():
    if not STRATEGY_LOG.exists():
        return []

    events = []
    try:
        with STRATEGY_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                if "STRATEGY_EVENT:" in line:
                    try:
                        payload = json.loads(line.strip().split("STRATEGY_EVENT:")[1].strip())
                        events.append(payload)
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"KARMA: napaka pri branju strategij: {e}")
    return events

def compute_karma(events):
    karma = defaultdict(lambda: {
        "score": 0.0,
        "count": 0,
        "details": defaultdict(int)
    })

    for e in events:
        sid = e.get("strategy_id")
        outcome = e.get("outcome")
        if not sid or not outcome:
            continue

        weight = WEIGHTS.get(outcome, 0)
        karma[sid]["score"] += weight
        karma[sid]["count"] += 1
        karma[sid]["details"][outcome] += 1

    # Povprečna ocena
    for sid, entry in karma.items():
        if entry["count"] > 0:
            entry["average"] = round(entry["score"] / entry["count"], 3)
        else:
            entry["average"] = 0.0

    return karma

def save_karma_index(karma):
    try:
        with KARMA_INDEX.open("w", encoding="utf-8") as f:
            json.dump(karma, f, indent=2)
        logger.info("KARMA: indeks shranjen")
    except Exception as e:
        logger.error(f"KARMA: napaka pri shranjevanju: {e}")

def run(stop_event):
    logger.info("🪬 KARMA: analizator aktiviran")
    while not stop_event.is_set():
        events = parse_strategy_events()
        karma = compute_karma(events)
        save_karma_index(karma)
        time.sleep(REFRESH_INTERVAL)
    logger.info("🪬 KARMA: zaustavljen")
