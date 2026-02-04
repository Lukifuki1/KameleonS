#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import subprocess
from pathlib import Path

import psutil
from loguru import logger

BASE_DIR = Path("/media/4tb/Kameleon/cell/models/base")
OUT_DIR = Path("/media/4tb/Kameleon/cell/models/quantized")
LLAMA_QUANT = "/usr/local/bin/llama-quantize"

MIN_FREE_DISK_GB = 20
MIN_FREE_RAM_GB = 4

OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_free_gb(path: Path) -> float:
    stat = shutil.disk_usage(path)
    return stat.free / (1024**3)


def detect_vram() -> int | None:
    """Poskus autodetekcije VRAM na Nvidia/AMD/Vulkan."""

    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader"],
            text=True,
        )
        value = out.strip().split()[0]
        return int(value)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        logger.warning(f"[AUTO-Q] Nvidia VRAM ni dostopen: {e}")

    try:
        out = subprocess.check_output(["rocm-smi", "--showmeminfo", "vram"], text=True)
        for line in out.splitlines():
            if "Total VRAM" in line:
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        return int(part)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        logger.warning(f"[AUTO-Q] ROCm VRAM ni dostopen: {e}")

    return None


def choose_quant_level() -> str | None:
    free_ram_gb = psutil.virtual_memory().available / (1024**3)
    vram = detect_vram()

    if free_ram_gb < MIN_FREE_RAM_GB:
        logger.warning(
            f"[AUTO-Q] Malo RAM-a ({free_ram_gb:.1f} GB) → preskakujem kvantizacijo"
        )
        return None

    if vram is None:
        return "Q4_0" if free_ram_gb < 8 else "Q5_K"

    if vram < 4096:
        return "Q4_0"
    if vram < 10240:
        return "Q5_K"
    return "Q8_0"


def quantize_model(model_path: Path, method: str) -> None:
    out_file = OUT_DIR / (model_path.stem + f"-{method}.gguf")

    if not Path(LLAMA_QUANT).is_file():
        logger.warning("[AUTO-Q] Orodje 'llama-quantize' ni najdeno → preskakujem")
        return

    try:
        logger.info(f"[AUTO-Q] Kvantizacija: {model_path.name} → {method}")
        subprocess.run(
            [LLAMA_QUANT, str(model_path), str(out_file), method], check=True
        )
        logger.success(f"[AUTO-Q] Končano: {out_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"[AUTO-Q] Napaka kvantizacije za {model_path.name}: {e}")
    except Exception as e:
        logger.error(f"[AUTO-Q] Nepričakovana napaka pri {model_path.name}: {e}")


def main() -> None:
    free_disk_gb = get_free_gb(BASE_DIR)
    if free_disk_gb < MIN_FREE_DISK_GB:
        logger.warning(
            f"[AUTO-Q] Premalo NVMe prostora ({free_disk_gb:.1f} GB). Preskakujem."
        )
        return

    method = choose_quant_level()
    if not method:
        return

    for model in BASE_DIR.iterdir():
        if model.is_file() and model.suffix.lower() == ".gguf":
            quantize_model(model, method)


if __name__ == "__main__":
    main()
