#!/usr/bin/env python3
import logging
import os
import shutil
import sys
from pathlib import Path

# --- Nastavitve ---
SECTOR_MAP_FILE = "/media/4tb/Kameleon/cell/config/sector_os_map.json"
MODELS_DIR = "/media/4tb/Kameleon/cell/models/active/"
SUPPORTED_EXT = ".distilled"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("auto_fix")


# --- Funkcije ---
def fix_sector_map_path():
    """Popravi klic Path.exists in preveri datoteko."""
    sector_path = Path(SECTOR_MAP_FILE)
    if not sector_path.exists():
        logger.warning(f"{SECTOR_MAP_FILE} ne obstaja. Generiram prazno mapo.")
        sector_path.parent.mkdir(parents=True, exist_ok=True)
        sector_path.write_text("{}")  # prazna mapa
    else:
        logger.info(f"{SECTOR_MAP_FILE} obstaja in je v redu.")


def verify_models():
    """Preveri vse modele, preskoči manjkajoče ali nezdružljive."""
    if not os.path.isdir(MODELS_DIR):
        logger.warning(f"{MODELS_DIR} ne obstaja. Kreiram direktorij.")
        os.makedirs(MODELS_DIR, exist_ok=True)
        return []

    valid_models = []
    for fname in os.listdir(MODELS_DIR):
        fpath = os.path.join(MODELS_DIR, fname)
        if fname.endswith(SUPPORTED_EXT) and Path(fpath).exists():
            valid_models.append(fpath)
        elif fname.endswith(SUPPORTED_EXT):
            logger.warning(f"Model {fname} ne obstaja, preskočeno.")
        else:
            logger.debug(f"Preskočena nepodprta datoteka: {fname}")
    logger.info(f"Validni modeli: {valid_models}")
    return valid_models


def backup_invalid_models():
    """Premakne vse neveljavne modele v backup."""
    backup_dir = Path(MODELS_DIR) / "backup"
    backup_dir.mkdir(exist_ok=True)
    for fname in os.listdir(MODELS_DIR):
        fpath = Path(MODELS_DIR) / fname
        if fpath.is_file() and not fpath.name.endswith(SUPPORTED_EXT):
            shutil.move(str(fpath), backup_dir / fpath.name)
            logger.info(f"Premaknil neveljavno datoteko {fname} v backup.")


def main():
    logger.info("Začetek avtomatskega popravila sistema...")
    fix_sector_map_path()
    backup_invalid_models()
    models = verify_models()
    if not models:
        logger.error(
            "Ni na voljo nobenega veljavnega modela. Sistem bo deloval v SAFE_MODE."
        )
    else:
        logger.info("Vsi modeli preverjeni, sistem pripravljen za zagon.")
    logger.info("Avtomatsko popravilo zaključeno.")


if __name__ == "__main__":
    main()
