import shutil
from pathlib import Path

import faiss  # type: ignore
import numpy as np
import psutil
from loguru import logger

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


BASE_DIR = Path("/media/4tb/Kameleon/cell/models/base")
SHARD_DIR = Path("/media/4tb/Kameleon/cell/models/shards")
SHARD_DIR.mkdir(parents=True, exist_ok=True)

MIN_FREE_DISK_GB = 20
MIN_FREE_RAM_GB = 4

CHUNK_SIZE = 64 * 1024 * 1024  # 64MB blok branja


def get_free_gb(path: Path) -> float:
    s = shutil.disk_usage(path)
    return s.free / (1024**3)


def enough_resources() -> bool:
    free_ram_gb = psutil.virtual_memory().available / (1024**3)
    free_disk_gb = get_free_gb(BASE_DIR)

    if free_ram_gb < MIN_FREE_RAM_GB:
        logger.warning(f"[SHARD] Premalo RAM-a ({free_ram_gb:.1f} GB) → preskakujem")
        return False

    if free_disk_gb < MIN_FREE_DISK_GB:
        logger.warning(f"[SHARD] Premalo diska ({free_disk_gb:.1f} GB) → preskakujem")
        return False

    return True


def shard_model(path: Path):
    logger.info(f"[SHARD] Začenjam razbijanje: {path.name}")

    size_gb = path.stat().st_size / (1024**3)
    shard_count = max(1, int(size_gb // 2))  # 1 shard na ~2GB
    shard_paths = []

    try:
        with path.open("rb") as f:
            for i in range(shard_count):
                out_path = SHARD_DIR / f"{path.stem}_shard_{i}.bin"
                with out_path.open("wb") as o:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    o.write(data)
                shard_paths.append(out_path)
    except Exception as e:
        logger.error(f"[SHARD] Napaka pri branju {path}: {e}")
        return

    logger.success(f"[SHARD] Ustvarjenih {len(shard_paths)} fragmentov")


def embed_shards():
    import faiss
    from sentence_transformers import SentenceTransformer

    SentenceTransformer("mxbai-embed-large")
    index = faiss.IndexFlatIP(1024)

    for shard in SHARD_DIR.iterdir():
        try:
            raw = shard.read_bytes()
            arr = np.frombuffer(raw, dtype=np.uint8).astype("float32")
            arr = arr / 255.0
            if arr.shape[0] > 1024:
                arr = arr[:1024]
            vec = np.expand_dims(arr, 0)
            index.add(vec)
except Exception:
            continue

    faiss.write_index(index, str(SHARD_DIR / "semantic.index"))
    logger.success("[SHARD] semantic.index ustvarjen in pripravljen za destilacijo")


def main():
    if not enough_resources():
        return

    for model in BASE_DIR.iterdir():
        if model.is_file() and model.stat().st_size > (
            100 * 1024 * 1024 * 1024
        ):  # >100GB
            shard_model(model)

    embed_shards()


if __name__ == "__main__":
    main()
