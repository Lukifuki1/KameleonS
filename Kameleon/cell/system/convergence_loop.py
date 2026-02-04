#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import statistics
import time

from eval_cycle import evaluate_and_update_knowledge
from loguru import logger
from orchestrator_shared import SAFE_MODE

from agents.goal_score import cull_low_score, decay_all, export_top_k

STABILITY_WINDOW = 12  # Število ciklov za opazovanje stabilnosti
STABILITY_THRESHOLD = 0.003  # Maksimalno dovoljen drift za stabilnost
MIN_EPOCHS = 25  # Najmanjše število ciklov pred oceno konvergence


def convergence_loop():
    logger.info("CONVERGENCE: zagon konvergenčnega cikla")
    score_history = []
    epoch = 0

    while SAFE_MODE.is_set():
        epoch += 1
        evaluate_and_update_knowledge()

        try:
            top = export_top_k(k=25)
        except Exception as e:
            logger.error(f"CONVERGENCE: napaka pri pridobivanju top K: {e}")
            time.sleep(2)
            continue

        if not top:
            logger.debug("CONVERGENCE: ni na voljo zadostnih rezultatov.")
            time.sleep(2)
            continue

        try:
            scores = [
                float(x["score"])
                for x in top
                if isinstance(x.get("score"), (int, float))
            ]
        except Exception as e:
            logger.error(f"CONVERGENCE: napaka pri razčlenjevanju ocen: {e}")
            time.sleep(2)
            continue

        if not scores:
            logger.debug("CONVERGENCE: prazne ocene.")
            time.sleep(2)
            continue

        avg = statistics.mean(scores)
        score_history.append(avg)

        logger.debug(f"CONVERGENCE: epoch={epoch}, avg_score={avg:.5f}")

        if len(score_history) > STABILITY_WINDOW:
            recent = score_history[-STABILITY_WINDOW:]
            drift = max(recent) - min(recent)

            logger.debug(
                f"CONVERGENCE: drift={drift:.6f} over last {STABILITY_WINDOW} epochs"
            )

            if drift <= STABILITY_THRESHOLD and epoch >= MIN_EPOCHS:
                logger.success(
                    f"CONVERGENCE: stabilnost dosežena po {epoch} ciklih (drift={drift:.6f})"
                )
                try:
                    cull_low_score()
                    decay_all()
                except Exception as e:
                    logger.error(f"CONVERGENCE: napaka pri cull/decay: {e}")
                return

        try:
            decay_all()
            cull_low_score()
        except Exception as e:
            logger.error(f"CONVERGENCE: napaka pri cull/decay: {e}")

        time.sleep(3)

    logger.warning("CONVERGENCE: prekinjeno zaradi izklopa SAFE_MODE")
