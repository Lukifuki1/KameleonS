#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import sys
import time
from pathlib import Path

from loguru import logger

HASHCHAIN_LOG = Path("/media/4tb/Kameleon/cell/logs/hashchain.log")


def calculate_merkle_root(paths):
    def sha256_file(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    hashes = [sha256_file(p) for p in sorted(paths)]
    if not hashes:
        return None

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


def log_merkle_root(root, label="DISTILL_SNAPSHOT"):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = f"{timestamp} {label} {root}"
    with open(HASHCHAIN_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
    logger.info(f"[+] Zabeležen Merkle root v hashchain: {entry}")


def find_files_in_dir(directory):
    return [str(p) for p in Path(directory).rglob("*") if p.is_file()]


def main():
    if len(sys.argv) != 2:
        print("Uporaba: python3 hashchain_logger.py /pot/do/snapshot_mape")
        sys.exit(1)

    target_dir = Path(sys.argv[1])
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Napaka: mapa {target_dir} ne obstaja ali ni veljavna.")
        sys.exit(1)

    files = find_files_in_dir(target_dir)
    if not files:
        print("Ni najdenih datotek za hash.")
        sys.exit(1)

    root = calculate_merkle_root(files)
    if not root:
        print("Napaka pri izračunu Merkle root.")
        sys.exit(1)

    log_merkle_root(root)


if __name__ == "__main__":
    main()
