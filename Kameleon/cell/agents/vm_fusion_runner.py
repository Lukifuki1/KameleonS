#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

from security.cell_airgap_lockdown import enforce_airgap
from security.cellsystem_init import init_cell_env

DOCKER_TEMPLATE_DIR = Path("/media/4tb/Kameleon/cell/templates")
SANDBOX_SCRIPT = Path("/media/4tb/Kameleon/cell/scripts/sandbox_runner.py")
TIMEOUT_SECONDS = 180


def run_vm_models(prompt: str, model_names: list[str]) -> list[dict]:
    """
    Izvede modele znotraj izolirane VM kontejnerske seje.

    :param prompt: vhodni ukaz
    :param model_names: imena modelov, ki jih želimo zagnati
    :return: seznam rezultatov z model output-i
    """
    logger.info("VM-FUSION: zagon modelov v varni VM okolici")
    init_cell_env()
    enforce_airgap()

    results = []

    for model_name in model_names:
        try:
            logger.debug(f"VM-FUSION: ustvarjanje VM za model: {model_name}")
            result = _run_single_model(prompt, model_name)
            if result:
                results.append({"model": model_name, "output": result.strip()})
        except Exception as e:
            logger.error(f"VM-FUSION: napaka pri modelu {model_name} → {e}")

    return results


def _run_single_model(prompt: str, model_name: str) -> str:
    """
    Izvede en sam model v izolaciji z uporabo docker predloge in sandbox runnerja.

    :param prompt: ukaz za obdelavo
    :param model_name: ime modela
    :return: surov izhod iz modela
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as tf:
        input_data = {"prompt": prompt, "model": model_name}
        json.dump(input_data, tf, ensure_ascii=False)
        tf_path = tf.name

    try:
        cmd = [
            "python3",
            str(SANDBOX_SCRIPT),
            "--input",
            tf_path,
            "--template",
            str(DOCKER_TEMPLATE_DIR / f"{model_name}.docker"),
        ]

        logger.debug(f"VM-FUSION: zaganjam docker: {cmd}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
            text=True,
        )

        os.unlink(tf_path)

        if result.returncode != 0:
            logger.warning(f"VM-FUSION: napaka {result.stderr.strip()}")
            return ""

        return result.stdout

    except subprocess.TimeoutExpired:
        logger.error(f"VM-FUSION: model {model_name} je presegel časovno omejitev")
        os.unlink(tf_path)
        return ""

    except Exception:
        logger.exception(f"VM-FUSION: splošna napaka za {model_name}")
        os.unlink(tf_path)
        return ""
