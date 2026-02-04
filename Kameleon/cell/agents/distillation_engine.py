#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
from pathlib import Path
from threading import Lock

from elixir_extractor import export_elixir
from loguru import logger
from orchestrator_shared import knowledge_bank, knowledge_lock
from sis import filter_outputs

from agents.goal_score import get_score
from agents.vm_fusion_runner import run_vm_models

__all__ = ["distill_prompt", "run_full_distillation", "distill_file"]

DISTILLATION_LOG = Path("data/distillation_output.json")
DISTILLATION_LOCK = Lock()

MIN_CONSENSUS_MODELS = 3
MIN_SCORE_THRESHOLD = 0.8


# ======================================================
#  CONSENSUS CHECK
# ======================================================


def verify_output_consistency(outputs: list[str]) -> str | None:
    counts = {}
    for o in outputs:
        text = o.strip()
        if text:
            counts[text] = counts.get(text, 0) + 1

    if not counts:
        return None

    consensus, freq = max(counts.items(), key=lambda x: x[1])
    return consensus if freq >= 2 else None


# ======================================================
#  DISTILL PROMPT
# ======================================================


def distill_prompt(prompt: str, models: list[str]) -> str | None:
    if not prompt or not models:
        logger.warning("DISTILL: prazna zahteva za destilacijo, preskakujem.")
        return None

    logger.info(f"DISTILL: obdelujem prompt → {prompt[:60]}...")

    try:
        results = run_vm_models(prompt=prompt, model_names=models)
        outputs = [r["output"].strip() for r in results if r.get("output")]
    except Exception as e:
        logger.error(f"DISTILL: napaka pri poizvedbi modelov: {e}")
        return None

    if len(outputs) < MIN_CONSENSUS_MODELS:
        logger.warning("DISTILL: premalo odgovorov za konsenz.")
        return None

    consensus = verify_output_consistency(outputs)
    if not consensus:
        logger.info("DISTILL: ni bilo konsenza med modeli.")
        return None

    if not filter_outputs([consensus]):
        logger.info("DISTILL: izhod zavrnjen s strani SIS.")
        return None

    score = get_score(consensus)
    if score < MIN_SCORE_THRESHOLD:
        logger.info(f"DISTILL: prenizek score ({score:.3f})")
        return None

    try:
        with knowledge_lock:
            if isinstance(knowledge_bank, dict):
                entries = knowledge_bank.setdefault("entries", [])
                if consensus in entries:
                    logger.info(
                        "DISTILL: konsenz že obstaja v knowledge_bank['entries']."
                    )
                    return None
                entries.append(consensus)
            elif isinstance(knowledge_bank, list):
                if consensus in knowledge_bank:
                    logger.info("DISTILL: konsenz že obstaja v knowledge_bank.")
                    return None
                knowledge_bank.append(consensus)
            else:
                logger.warning("DISTILL: neznana struktura knowledge_bank.")
                return None

        _log_distillation(prompt, consensus, models, score)
        logger.success("DISTILL: uspešno dodano znanje.")
        return consensus

    except Exception as e:
        logger.error(f"DISTILL: napaka pri zapisovanju v knowledge_bank: {e}")
        return None


# ======================================================
#  FULL DISTILLATION (ELIXIR)
# ======================================================


def run_full_distillation(models: list[str], max_items: int = 25):
    logger.info("DISTILL: zagon celovite destilacije")

    try:
        prompts = export_elixir()
    except Exception as e:
        logger.error(f"DISTILL: napaka pri uvozu eliksirja: {e}")
        return

    count = 0
    for p in prompts:
        if count >= max_items:
            break
        if distill_prompt(p, models=models):
            count += 1

    logger.success(f"DISTILL: uspešno dodanih {count} vnosov.")


# ======================================================
#  MODEL CHUNK DISTILLATION (BOOTSTRAP)
# ======================================================


def distill_file(source_path: Path, output_path: Path) -> bool:
    try:
        source_path = Path(source_path)
        output_path = Path(output_path)

        if not source_path.exists():
            logger.error(f"DISTILL_FILE: chunk ne obstaja: {source_path}")
            return False

        raw = source_path.read_bytes()
        digest = hashlib.sha256(raw).digest()
        distilled = digest + raw[:256]

        temp = output_path.with_suffix(".tmp")
        temp.write_bytes(distilled)
        temp.replace(output_path)

        logger.success(f"DISTILL_FILE: uspešno zapisano → {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"DISTILL_FILE: napaka pri zapisovanju: {e}")
        return False


# ======================================================
#  LOGGING DESTILLATION
# ======================================================


def _log_distillation(prompt: str, output: str, models: list[str], score: float):
    entry = {
        "prompt": prompt,
        "output": output,
        "models": models,
        "score": round(score, 4),
    }

    with DISTILLATION_LOCK:
        try:
            if DISTILLATION_LOG.exists():
                data = json.loads(DISTILLATION_LOG.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
            else:
                data = []
        except Exception:
            data = []

        data.append(entry)
        try:
            DISTILLATION_LOG.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"DISTILL: napaka pri logiranju destilacije: {e}")


# ======================================================
#  DIRECT RUN
# ======================================================

if __name__ == "__main__":
    MODELI = [
        "llama3.1-70b",
        "deepseek-r1-32b",
        "qwen3-coder-480b",
        "glm-4.6",
        "gpt-oss-120b",
    ]
    run_full_distillation(models=MODELI, max_items=20)
