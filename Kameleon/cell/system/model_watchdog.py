#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil
from pathlib import Path

from loguru import logger
from orchestrator_shared import (
    ACTIVE_BASE,
    HASH_STORE_FILE,
    TEMP_MODEL_DIR,
    TRASH_BASE,
    hash_model_file,
    log_alert,
    safe_mode,
)


def quarantine_model(model_path: Path):
    # Izključi modele iz temp imenika
    try:
        if model_path.resolve().is_relative_to(TEMP_MODEL_DIR.resolve()):
            return
    except AttributeError:
        if str(model_path).startswith(str(TEMP_MODEL_DIR)):
            return

    # Izključi neinferenčne .distilled datoteke
    if model_path.suffix == ".distilled":
        return

    try:
        h = hash_model_file(model_path)
    except Exception as e:
        logger.error(f"WATCHDOG: napaka pri hashiranju {model_path}: {e}")
        return

    try:
        if HASH_STORE_FILE.exists():
            hashes = json.loads(HASH_STORE_FILE.read_text())
        else:
            hashes = {}
    except Exception as e:
        logger.error(f"WATCHDOG: napaka pri branju HASH_STORE_FILE: {e}")
        hashes = {}

    old = hashes.get(model_path.name)

    # Če ni obstoječega hasha, ga dodaj
    if old is None:
        hashes[model_path.name] = h
        try:
            HASH_STORE_FILE.write_text(json.dumps(hashes, indent=2))
            logger.info(f"WATCHDOG: dodan hash za {model_path.name}")
        except Exception as e:
            logger.error(f"WATCHDOG: napaka pri zapisovanju hash datoteke: {e}")
        return

    # Če je hash spremenjen, premakni v karanteno
    if old != h:
        try:
            quarantine_target = TRASH_BASE / model_path.name
            TRASH_BASE.mkdir(parents=True, exist_ok=True)
            shutil.move(str(model_path), str(quarantine_target))
            logger.critical(f"MODEL WATCHDOG: {model_path.name} premaknjen v karanteno")
            log_alert(f"Model {model_path.name} hash mismatch", "critical")
            safe_mode("Model integritetna napaka.")
        except Exception as e:
            logger.error(
                f"WATCHDOG: premik v karanteno spodletel za {model_path.name}: {e}"
            )

        hashes.pop(model_path.name, None)
        try:
            HASH_STORE_FILE.write_text(json.dumps(hashes, indent=2))
        except Exception as e:
            logger.error(
                f"WATCHDOG: napaka pri posodabljanju hash datoteke po karanteni: {e}"
            )
    else:
        logger.info(f"WATCHDOG: {model_path.name} OK")


def verify_all_models():
    logger.info("WATCHDOG: preverjam modele v ACTIVE_BASE...")
    for m in ACTIVE_BASE.rglob("*"):
        if m.is_file():
            quarantine_model(m)
    logger.info("WATCHDOG: preverjanje zaključeno.")


if __name__ == "__main__":
    verify_all_models()
