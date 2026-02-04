#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import time
from pathlib import Path
from threading import Lock

from loguru import logger  # ⬅️ Manjkajoči uvoz
from orchestrator_shared import knowledge_bank, knowledge_lock
from sis import is_repeatable

from agents.goal_score import get_score

# Trajni eliksir (trajni spomin) – ločen od knowledge_bank
ELIXIR_FILE = Path("data/elixir_store.json")
ELIXIR_LOCK = Lock()
TTL_SECONDS = 30 * 86400  # 30 dni
SCORE_THRESHOLD = 0.82
FORCE_COMMIT_SCORE = 0.95


def _hash_entry(entry: str) -> str:
    return hashlib.sha256(entry.encode("utf-8")).hexdigest()


def _load_elixir():
    if not ELIXIR_FILE.exists():
        return {}
    try:
        with ELIXIR_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"ELIXIR: napaka pri branju eliksirja: {e}")
        return {}


def _save_elixir(data: dict):
    try:
        with ELIXIR_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ELIXIR: napaka pri shranjevanju eliksirja: {e}")


def extract_elixir():
    """Analizira knowledge_bank in shrani preverjeno znanje v eliksir."""
    logger.info("ELIXIR: zagon procesa ekstrakcije")

    with knowledge_lock:
        snapshot = list(knowledge_bank)

    if not snapshot:
        logger.info("ELIXIR: ni znanja za obdelavo")
        return

    elixir = _load_elixir()
    now = int(time.time())
    committed = 0

    for entry in snapshot:
        h = _hash_entry(entry)
        if h in elixir:
            continue  # že prisotno

        score = get_score(entry)
        if score < SCORE_THRESHOLD:
            continue

        if not is_repeatable(entry):
            logger.debug(f"ELIXIR: '{entry[:40]}...' ni ponovljiv → preskočeno")
            continue

        elixir[h] = {
            "text": entry,
            "score": score,
            "timestamp": now,
            "confirmed": score >= FORCE_COMMIT_SCORE,
        }
        committed += 1

    _save_elixir(elixir)
    logger.success(f"ELIXIR: dodano {committed} vnosov v eliksir")


def purge_stale_entries():
    """Odstrani vnose iz eliksirja, ki so prestari ali izgubili vrednost."""
    logger.info("ELIXIR: preverjanje zastarelih vnosov")
    elixir = _load_elixir()
    now = int(time.time())
    removed = 0

    for h in list(elixir.keys()):
        e = elixir[h]
        age = now - e["timestamp"]
        if age > TTL_SECONDS or e["score"] < SCORE_THRESHOLD * 0.85:
            del elixir[h]
            removed += 1

    _save_elixir(elixir)
    logger.success(f"ELIXIR: odstranjenih {removed} zastarelih vnosov")


def export_elixir():
    """Vrne trenutno vsebino eliksirja za kameleon.py in druge module."""
    elixir = _load_elixir()
    return [e["text"] for e in elixir.values() if e.get("confirmed", False)]


def elixir_count():
    """Vrne število shranjenih eliksir vnosov."""
    return len(_load_elixir())


if __name__ == "__main__":
    extract_elixir()
    purge_stale_entries()
