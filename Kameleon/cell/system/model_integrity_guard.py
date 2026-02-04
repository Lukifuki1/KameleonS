#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

from loguru import logger
from orchestrator_shared import (
    ACTIVE_BASE,
    HASH_STORE_FILE,
    TRASH_BASE,
    hash_model_file,
    log_alert,
    safe_mode,
)

# ======================================================
#  LOAD HASHES
# ======================================================


def load_stored_hashes() -> dict:
    if not HASH_STORE_FILE.exists():
        logger.warning("INTEGRITY: HASH_STORE_FILE ne obstaja.")
        return {}
    try:
        return json.loads(HASH_STORE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"INTEGRITY: napaka pri branju HASH_STORE_FILE: {e}")
        return {}


# ======================================================
#  VERIFY HASH
# ======================================================


def verify_model(path: Path, expected_hash: str) -> bool:
    try:
        actual_hash = hash_model_file(path)
        return actual_hash == expected_hash
    except Exception as e:
        logger.error(f"INTEGRITY: napaka pri preverjanju {path.name}: {e}")
        return False


# ======================================================
#  QUARANTINE
# ======================================================


def quarantine_model(model_path: Path):
    try:
        TRASH_BASE.mkdir(parents=True, exist_ok=True)
        quarantine_path = TRASH_BASE / model_path.name
        model_path.rename(quarantine_path)
        logger.critical(f"INTEGRITY: {model_path.name} premaknjen v karanteno.")
    except Exception as e:
        logger.error(f"INTEGRITY: premik modela {model_path.name} ni uspel: {e}")


# ======================================================
#  RUN INTEGRITY CHECK
# ======================================================


def run_integrity_check():
    logger.info("INTEGRITY: zagon preverjanja aktivnih modelov.")
    stored = load_stored_hashes()
    corrupted = []

    for model_path in ACTIVE_BASE.glob("*"):
        if not model_path.is_file():
            continue

        expected_hash = stored.get(model_path.name)
        if not expected_hash:
            logger.warning(f"INTEGRITY: model {model_path.name} nima zapisanega hasha.")
            continue

        if not verify_model(model_path, expected_hash):
            logger.error(f"INTEGRITY: hash neusklajen za {model_path.name}")
            corrupted.append(model_path)

    if corrupted:
        for model_path in corrupted:
            quarantine_model(model_path)
            # Tu lahko integriraš funkcijo restore_model(model_path), če obstaja
            # Primer:
            # restored = restore_model(model_path)
            # if restored:
            #     logger.success(f"INTEGRITY: {model_path.name} obnovljen.")
            #     continue

        log_alert(
            f"Poškodovani modeli: {', '.join(m.name for m in corrupted)}", "critical"
        )
        safe_mode("Zaznana poškodba modelov.")
    else:
        logger.success("INTEGRITY: vsi aktivni modeli so skladni.")


# ======================================================
#  MAIN
# ======================================================

if __name__ == "__main__":
    run_integrity_check()
