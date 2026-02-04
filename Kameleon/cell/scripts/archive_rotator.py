#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import time
from pathlib import Path

from loguru import logger

# Poti in nastavitve
ARCHIVE_ROOT = Path("/media/4tb/Kameleon/cell/archive")
TARGETS = [
    Path("/media/4tb/Kameleon/cell/data/knowledge.json"),
    Path("/media/4tb/Kameleon/cell/data/goal_score.json"),
    Path("/media/4tb/Kameleon/cell/data/elixir_store.json"),
    Path("/media/4tb/Kameleon/cell/data/distillation_output.json"),
    Path("/media/4tb/Kameleon/cell/data/model_hashes.json"),
    Path("/media/4tb/Kameleon/cell/data/knowledge.index"),
    Path("/media/4tb/Kameleon/cell/data/safe_mode_reason.txt"),
]
MAX_BACKUPS = 10
ROTATION_INTERVAL = 3600  # 1h


def rotate_file(file_path: Path):
    if not file_path.exists():
        return

    try:
        ts = time.strftime("%Y%m%d-%H%M%S")
        archive_dir = ARCHIVE_ROOT / file_path.name
        archive_dir.mkdir(parents=True, exist_ok=True)

        backup_file = archive_dir / f"{ts}.bak"
        shutil.copy2(file_path, backup_file)
        logger.info(f"ROTATOR: {file_path.name} → {backup_file.name}")
    except Exception as e:
        logger.error(f"ROTATOR: napaka pri arhiviranju {file_path.name}: {e}")

    # rotacija starih
    backups = sorted(archive_dir.glob("*.bak"), reverse=True)
    for old in backups[MAX_BACKUPS:]:
        try:
            old.unlink()
            logger.debug(f"ROTATOR: odstranjen {old.name}")
        except Exception as e:
            logger.warning(f"ROTATOR: napaka pri brisanju {old.name}: {e}")


def archive_rotation_loop():
    logger.info("ROTATOR: zanka aktivna")
    while True:
        for f in TARGETS:
            rotate_file(f)
        time.sleep(ROTATION_INTERVAL)


if __name__ == "__main__":
    try:
        archive_rotation_loop()
    except KeyboardInterrupt:
        logger.info("ROTATOR: prekinjeno ročno")
    except Exception as e:
        logger.critical(f"ROTATOR: fatala napaka: {e}")
