#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
from pathlib import Path

from loguru import logger

LLAMA_CPP_CONVERT = Path.home() / "llama.cpp" / "convert.py"
ACTIVE_DIR = Path("/media/4tb/Kameleon/cell/models/active")
SUPPORTED_INPUT_EXTENSIONS = {".distilled", ".bin", ".pth", ".model"}


def convert_to_gguf(input_path: Path):
    if not input_path.exists():
        logger.error(f"Vhodna datoteka ne obstaja: {input_path}")
        return False

    if input_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        logger.error(f"Nepodprta končnica: {input_path.suffix}")
        return False

    if not LLAMA_CPP_CONVERT.exists():
        logger.critical(f"Manjka konverzijska skripta: {LLAMA_CPP_CONVERT}")
        return False

    output_path = input_path.with_suffix(".gguf")

    if output_path.exists():
        logger.info(f"Preskakujem — .gguf že obstaja: {output_path.name}")
        return True

    cmd = [
        sys.executable,
        str(LLAMA_CPP_CONVERT),
        "--outfile",
        str(output_path),
        str(input_path),
    ]

    try:
        logger.info(f"Pretvarjam {input_path.name} → {output_path.name}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.success(f"Konverzija OK: {output_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Konverzija spodletela ({input_path.name}): {e.stderr.strip()}")
        return False


def convert_all_distilled_models():
    models = sorted(ACTIVE_DIR.glob("*.distilled"))
    if not models:
        logger.warning("Ni .distilled modelov za pretvorbo.")
        return

    for model in models:
        convert_to_gguf(model)


def main():
    logger.info("Začenjam masovno pretvorbo vseh .distilled modelov…")
    convert_all_distilled_models()
    logger.info("Konverzija zaključena.")


if __name__ == "__main__":
    main()
