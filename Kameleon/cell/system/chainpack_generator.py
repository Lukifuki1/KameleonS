#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from loguru import logger

CHAINPACK_DIR = Path("/media/4tb/Kameleon/cell/snapshots/")
HASHCHAIN_LOG = Path("/media/4tb/Kameleon/cell/logs/hashchain.log")
GPG_KEY_ID = "cell@localhost"


def sha256_file(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build_merkle_root(files: list[Path]) -> str:
    hashes = [sha256_file(p) for p in sorted(files)]
    if not hashes:
        raise ValueError("Ni datotek za izračun Merkle root.")
    layer = hashes
    while len(layer) > 1:
        temp = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            combined = hashlib.sha256((left + right).encode()).hexdigest()
            temp.append(combined)
        layer = temp
    return layer[0]


def archive_directory(source_dir: Path, output_zip: Path):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(source_dir):
            for filename in filenames:
                filepath = Path(foldername) / filename
                arcname = filepath.relative_to(source_dir)
                zipf.write(filepath, arcname)
    logger.info(f"[+] Snapshot arhiviran: {output_zip}")


def sign_file(path: Path):
    try:
        subprocess.run(
            [
                "gpg",
                "--yes",
                "--batch",
                "--output",
                f"{path}.sig",
                "--default-key",
                GPG_KEY_ID,
                "--detach-sign",
                str(path),
            ],
            check=True,
        )
        logger.info(f"[+] Podpis ustvarjen: {path}.sig")
    except subprocess.CalledProcessError as e:
        logger.error(f"[!] Napaka pri podpisovanju: {e}")


def gpg_key_exists(key_id: str) -> bool:
    result = subprocess.run(
        ["gpg", "--list-keys", key_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return result.returncode == 0


def log_hashchain(merkle_root: str, label: str):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = f"{timestamp} {label} {merkle_root}"
    HASHCHAIN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HASHCHAIN_LOG.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")
    logger.info(f"[+] Hashchain zabeležen: {entry}")


def main():
    if len(sys.argv) != 3:
        print("Uporaba: python3 chainpack_generator.py /pot/do/mape agent-123")
        sys.exit(1)

    source = Path(sys.argv[1])
    agent_id = sys.argv[2]

    if not source.exists() or not source.is_dir():
        print(f"Napaka: mapa {source} ne obstaja.")
        sys.exit(1)

    if not gpg_key_exists(GPG_KEY_ID):
        logger.error(f"GPG ključ '{GPG_KEY_ID}' ne obstaja.")
        sys.exit(1)

    files = [p for p in source.rglob("*") if p.is_file()]
    if not files:
        logger.error("Ni datotek za snapshot.")
        sys.exit(1)

    try:
        merkle_root = build_merkle_root(files)
    except Exception as e:
        logger.error(f"Napaka pri gradnji Merkle root: {e}")
        sys.exit(1)

    label = f"CHAINPACK_{agent_id.upper()}"
    zip_path = CHAINPACK_DIR / f"{agent_id}.snapshot.zip"

    try:
        CHAINPACK_DIR.mkdir(parents=True, exist_ok=True)
        archive_directory(source, zip_path)
        sign_file(zip_path)
        log_hashchain(merkle_root, label)
        logger.success(f"[✓] Snapshot {agent_id} uspešno zaključen.")
    except Exception as e:
        logger.critical(f"[!] Nepričakovana napaka: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
