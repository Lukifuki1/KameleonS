#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import time
from pathlib import Path
from threading import Lock

from loguru import logger
from orchestrator_shared import KNOWLEDGE_JSON

GOAL_SCORE_FILE = Path("/media/4tb/Kameleon/cell/data/goal_score.json")
GOAL_SCORE_LOCK = Lock()

DECAY_FACTOR = 0.985
REWARD_THRESHOLD = 0.75
PENALTY_THRESHOLD = 0.35


# ----------------------------------------------------------
# VARNI IO BLOKI (atomic read/write, odporni na korupcijo)
# ----------------------------------------------------------
def _safe_read_json(path: Path, fallback):
    try:
        if path.exists() and path.stat().st_size > 0:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"GOALSCORE: poškodovan JSON {path}: {e}")
    return fallback


def _safe_write_json(path: Path, data):
    try:
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except Exception as e:
        logger.error(f"GOALSCORE: zapis ni uspel {path}: {e}")


# ----------------------------------------------------------
# NALOŽI / SHRANI
# ----------------------------------------------------------
def _load_goal_scores():
    with GOAL_SCORE_LOCK:
        return _safe_read_json(GOAL_SCORE_FILE, {})


def _save_goal_scores(data):
    with GOAL_SCORE_LOCK:
        _safe_write_json(GOAL_SCORE_FILE, data)


# ----------------------------------------------------------
# HASH KLJUČ
# ----------------------------------------------------------
def _hash(text: str):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ----------------------------------------------------------
# REGISTRACIJA
# ----------------------------------------------------------
def register_knowledge_entry(entry: str):
    if not entry or not isinstance(entry, str):
        return

    scores = _load_goal_scores()
    h = _hash(entry)

    if h not in scores:
        scores[h] = {
            "text": entry,
            "score": 0.50,
            "timestamp": int(time.time()),
            "usage_count": 0,
            "last_used": 0,
        }
        _save_goal_scores(scores)


# ----------------------------------------------------------
# POSODOBITVE
# ----------------------------------------------------------
def reinforce(entry: str, reward: float = 1.0):
    if not entry:
        return

    scores = _load_goal_scores()
    h = _hash(entry)

    if h in scores:
        s = scores[h]
        s["score"] = min(s["score"] + reward * 0.1, 1.0)
        s["usage_count"] += 1
        s["last_used"] = int(time.time())
        _save_goal_scores(scores)


def penalize(entry: str, penalty: float = 1.0):
    if not entry:
        return

    scores = _load_goal_scores()
    h = _hash(entry)

    if h in scores:
        s = scores[h]
        s["score"] = max(s["score"] - penalty * 0.1, 0.0)
        s["usage_count"] += 1
        s["last_used"] = int(time.time())
        _save_goal_scores(scores)


# ----------------------------------------------------------
# DEKAY
# ----------------------------------------------------------
def decay_all():
    scores = _load_goal_scores()
    now = int(time.time())

    for h, s in scores.items():
        last = s.get("last_used", 0)
        age = max(now - last, 1)
        decay = DECAY_FACTOR ** (age / 3600)
        s["score"] = round(max(s["score"] * decay, 0.0), 5)

    _save_goal_scores(scores)


# ----------------------------------------------------------
# EXPORT
# ----------------------------------------------------------
def export_top_k(k=10):
    scores = _load_goal_scores()
    sorted_entries = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    return sorted_entries[:k]


# ----------------------------------------------------------
# ČIŠČENJE SLABIH
# ----------------------------------------------------------
def cull_low_score():
    scores = _load_goal_scores()
    filtered = {
        h: v for h, v in scores.items() if v.get("score", 0) >= PENALTY_THRESHOLD
    }
    removed = len(scores) - len(filtered)
    _save_goal_scores(filtered)
    logger.info(f"GOALSCORE: odstranjeno {removed} degeneriranih strategij")


# ----------------------------------------------------------
# BOOTSTRAP IZ KNOWLEDGE_JSON
# ----------------------------------------------------------
def bootstrap_from_knowledge():
    if not KNOWLEDGE_JSON.exists():
        return

    data = _safe_read_json(KNOWLEDGE_JSON, [])

    for item in data:
        if isinstance(item, dict) and "text" in item:
            txt = item["text"].strip()
            if txt:
                register_knowledge_entry(txt)
        elif isinstance(item, str) and item.strip():
            register_knowledge_entry(item.strip())


# ----------------------------------------------------------
# SCORING API
# ----------------------------------------------------------
def get_score(text: str) -> float:
    if not text:
        return 0.0

    scores = _load_goal_scores()
    return scores.get(_hash(text), {}).get("score", 0.0)
