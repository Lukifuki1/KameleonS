#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from loguru import logger

# Privzete poti (relativno na kameleonovo strukturo)
# /media/4tb/Kameleon/cell/templates/: vsebuje .docker predloge (ena za vsak model)
# /media/4tb/Kameleon/cell/tmp_vm/:    začasna delovna mapa za kontejnersko izolacijo

DOCKER_TEMPLATE_DIR = Path("/media/4tb/Kameleon/cell/templates")
VM_TMP_ROOT = Path("/media/4tb/Kameleon/cell/tmp_vm")
VM_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def load_template(template_path: Path) -> dict:
    """Naloži docker predlogo za določen model."""
    if not template_path.exists():
        raise FileNotFoundError(f"Manjkajoča predloga: {template_path}")
    with template_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_container_command(template: dict, input_path: Path) -> list[str]:
    """
    Zgradi docker ukaz iz predloge in poda vhodni JSON.
    """
    image = template["image"]
    cmd = template["command"]
    mount_path = template.get("mount_path", "/mnt/input.json")

    full_cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{input_path}:{mount_path}:ro",
        image,
    ]
    full_cmd.extend(cmd)
    return full_cmd


def main():
    parser = argparse.ArgumentParser(
        description="Izoliran zagon modela v sandbox okolju."
    )
    parser.add_argument(
        "--input", required=True, help="Pot do vhodnega JSON (prompt + model)"
    )
    parser.add_argument(
        "--template", required=True, help="Pot do docker predloge (.docker JSON)"
    )
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    template_file = Path(args.template).resolve()

    if not input_file.exists():
        logger.error(f"Vhodni JSON ne obstaja: {input_file}")
        exit(1)

    if not template_file.exists():
        logger.error(f"Docker predloga ne obstaja: {template_file}")
        exit(2)

    # Naloži predlogo
    template = load_template(template_file)

    # Ustvari začasno kopijo vhodne datoteke
    tmp_input = VM_TMP_ROOT / f"{input_file.name}"
    shutil.copy(input_file, tmp_input)

    # Sestavi docker ukaz
    docker_cmd = build_container_command(template, tmp_input)

    try:
        logger.info(f"Zagon modela v izolaciji: {template_file.stem}")
        result = subprocess.run(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
            text=True,
        )
    except subprocess.TimeoutExpired:
        logger.error("Zagon modela je presegel časovno omejitev (timeout).")
        exit(3)

    finally:
        tmp_input.unlink(missing_ok=True)

    if result.returncode != 0:
        logger.error(f"Napaka v docker izvajanju: {result.stderr.strip()}")
        exit(result.returncode)

    print(result.stdout.strip())
    exit(0)


if __name__ == "__main__":
    main()
