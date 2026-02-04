#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import os
from pathlib import Path

from loguru import logger

CHECKSUMS_DB = Path("/media/4tb/Kameleon/cell/knowledge_bank/model_checksums.json")
MODELS_DIR = Path("/media/4tb/Kameleon/cell/models")


def _hash_file(path: Path) -> str:
    """
    Izračuna SHA-256 hash datoteke.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_existing_checksums() -> dict:
    """
    Naloži obstoječo bazo zgoščenk modelov.
    """
    if CHECKSUMS_DB.exists():
        with open(CHECKSUMS_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_checksums(data: dict):
    """
    Shrani zgoščene vrednosti v lokalno bazo.
    """
    CHECKSUMS_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKSUMS_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def verify_models_integrity() -> list[dict]:
    """
    Preveri celovitost vseh modelov v imeniku MODELS_DIR.
    Vrne seznam rezultatov preverjanja.
    """
    logger.info("INTEGRITY: preverjanje modelov v teku...")
    results = []
    stored_checksums = _load_existing_checksums()

    for root, _, files in os.walk(MODELS_DIR):
        for file in files:
            model_path = Path(root) / file
            model_rel_path = str(model_path.relative_to(MODELS_DIR))

            try:
                actual_hash = _hash_file(model_path)
                expected_hash = stored_checksums.get(model_rel_path)

                if expected_hash:
                    status = "OK" if actual_hash == expected_hash else "MISMATCH"
                else:
                    status = "NEW"
                    stored_checksums[model_rel_path] = actual_hash

                results.append(
                    {"model": model_rel_path, "status": status, "hash": actual_hash}
                )

                logger.debug(f"INTEGRITY: {model_rel_path} → {status}")

            except Exception as e:
                logger.error(f"INTEGRITY: napaka pri {model_rel_path} → {e}")
                results.append(
                    {"model": model_rel_path, "status": "ERROR", "hash": None}
                )

    _save_checksums(stored_checksums)
    return results
