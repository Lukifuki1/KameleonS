#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import subprocess
from pathlib import Path

from loguru import logger
from orchestrator_shared import (ACTIVE_BASE, MODEL_AUTOFETCH_ALLOWLIST,
                                 MODEL_AUTOFETCH_DIR, REGISTRY_PATH)

AUTO_QUANT = "/media/4tb/Kameleon/cell/scripts/auto_quantize.py"
GENERATE_TEMPLATES = "/media/4tb/Kameleon/cell/scripts/generate_runtime_templates.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def register_model(model_path: Path):
    reg = json.load(open(REGISTRY_PATH, "r"))
    name = model_path.name

    reg["base"][name] = {
        "path": str(model_path),
        "type": "general",
        "format": "blob",
        "sha256": sha256_file(model_path),
        "active": True,
    }

    json.dump(reg, open(REGISTRY_PATH, "w"), indent=2)
    logger.success(f"AUTOFETCH: model '{name}' dodan v registry.json")


def post_process_model(model_path: Path):
    try:
        logger.info(f"AUTOFETCH: kvantizacija {model_path.name}")
        subprocess.run(["python3", AUTO_QUANT, str(model_path)], check=False)
    except Exception as e:
        logger.warning(f"AUTOFETCH: kvantizacija ni uspela: {e}")

    try:
        logger.info("AUTOFETCH: generiram runtime docker predloge")
        subprocess.run(["python3", GENERATE_TEMPLATES], check=False)
    except Exception as e:
        logger.warning(f"AUTOFETCH: predloge niso bile posodobljene: {e}")

    logger.success(f"AUTOFETCH: model {model_path.name} pripravljen za destilacijo")


def autofetch_if_needed():
    for src in MODEL_AUTOFETCH_ALLOWLIST:
        try:
            import requests

            r = requests.get(timeout=5, timeout=5, src, timeout=3)
            if r.status_code != 200 or not r.content:
                logger.warning(f"AUTOFETCH: neveljaven odziv za {src}")
                continue

            name = src.split("/")[-1]
            temp_path = MODEL_AUTOFETCH_DIR / name
            final_path = ACTIVE_BASE / name

            temp_path.write_bytes(r.content)
            final_path.write_bytes(r.content)

            logger.info(f"AUTOFETCH: {name} prenesen")

            register_model(final_path)
            post_process_model(final_path)

        except Exception as e:
            logger.warning(f"AUTOFETCH: napaka pri {src}: {e}")
