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
    hash_model_file,
    log_alert,
)

from agents.distillation_engine import distill_file

CHUNK_SIZE = 4 * 1024 * 1024 * 1024  # 4GB

BASE_DIR = Path("/media/4tb/Kameleon/cell/models/base")
DISTILLED_DIR = Path("/media/4tb/Kameleon/cell/models/distilled")

DISTILLED_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_BASE.mkdir(parents=True, exist_ok=True)
TEMP_MODEL_DIR.mkdir(parents=True, exist_ok=True)


def split_model(path: Path):
    path.stat().st_size
    chunks = []
    with path.open("rb") as f:
        index = 0
        while True:
            part = f.read(CHUNK_SIZE)
            if not part:
                break
            chunk_path = TEMP_MODEL_DIR / f"{path.name}.chunk{index}"
            with chunk_path.open("wb") as cf:
                cf.write(part)
            chunks.append(chunk_path)
            index += 1
    return chunks


# noinspection PyTypeChecker
def merge_chunks(chunks, output_path: Path):
    with output_path.open("wb") as out:
        for c in chunks:
            with c.open("rb") as cf:
                shutil.copyfileobj(cf, out)


def update_hash_store(model_path: Path):
    try:
        h = hash_model_file(model_path)
        hashes = (
            json.loads(HASH_STORE_FILE.read_text()) if HASH_STORE_FILE.exists() else {}
        )
        hashes[model_path.name] = h
        HASH_STORE_FILE.write_text(json.dumps(hashes, indent=2))
    except Exception as e:
        logger.error(f"HASH UPDATE: napaka: {e}")


def process_model(model_path: Path):
    size = model_path.stat().st_size
    logger.info(f"BOOTSTRAP: obdelujem {model_path.name} ({size / (1024**3):.2f} GB)")

    try:
        # model ≤ 4GB
        if size <= CHUNK_SIZE:
            out = DISTILLED_DIR / f"{model_path.name}.distilled"
            distill_file(model_path, out)
            final = ACTIVE_BASE / out.name
            shutil.move(str(out), str(final))
            update_hash_store(final)
            logger.success(f"BOOTSTRAP: {model_path.name} → ACTIVE")
            return True

        # model > 4GB (razbitje + distilacija)
        chunks = split_model(model_path)
        distilled = []

        for c in chunks:
            o = TEMP_MODEL_DIR / f"{c.name}.distilled"
            distill_file(c, o)
            distilled.append(o)

        merged = DISTILLED_DIR / f"{model_path.name}.distilled"
        merge_chunks(distilled, merged)

        final = ACTIVE_BASE / merged.name
        shutil.move(str(merged), str(final))
        update_hash_store(final)

        for f in chunks + distilled:
            f.unlink(missing_ok=True)

        logger.success(f"BOOTSTRAP: {model_path.name} (razbit + distiliran) → ACTIVE")
        return True

    except Exception as e:
        logger.error(f"BOOTSTRAP: napaka pri obdelavi {model_path.name}: {e}")
        return False


def main():
    allowed_ext = {".gguf", ".bin"}
    models = [
        m for m in BASE_DIR.glob("*") if m.is_file() and m.suffix.lower() in allowed_ext
    ]

    if not models:
        logger.warning("BOOTSTRAP: Ni modelov v /models/base/ z dovoljenimi končnicami")
        return

    failures = []

    for m in models:
        ok = process_model(m)
        if not ok:
            failures.append(m.name)

    if failures:
        log_alert(f"BOOTSTRAP: neuspešni modeli: {', '.join(failures)}", "warning")
    else:
        log_alert("ZAČETNI MODELNI BAZEN AKTIVEN", "info")

    logger.success("BOOTSTRAP: Končano.")


def bootstrap_base_models():
    main()


if __name__ == "__main__":
    main()
