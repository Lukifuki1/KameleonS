#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import traceback

from convergence_loop import convergence_loop
from loguru import logger
from model_autofetch import autofetch_if_needed
from model_integrity_guard import run_integrity_check
from model_watchdog import verify_all_models
from orchestrator_shared import AGENT_LAST_USED, AGENTS, SAFE_MODE

# ======================================================
#  SCHEDULER LOOP
# ======================================================


def scheduler_loop():
    logger.info("SCHEDULER: zanka aktivna")
    cycle = 0

    while True:
        if not SAFE_MODE.is_set():
            logger.debug("SCHEDULER: SAFE_MODE ni aktiviran, čakam...")
            time.sleep(2)
            continue

        logger.debug(f"SCHEDULER: cikel {cycle} se začenja.")

        try:
            verify_all_models()
        except Exception as e:
            logger.error(f"SCHEDULER: verify_all_models napaka: {e}")
            logger.debug(traceback.format_exc())

        try:
            autofetch_if_needed()
        except Exception as e:
            logger.error(f"SCHEDULER: autofetch_if_needed napaka: {e}")
            logger.debug(traceback.format_exc())

        try:
            convergence_loop()
        except Exception as e:
            logger.error(f"SCHEDULER: convergence_loop napaka: {e}")
            logger.debug(traceback.format_exc())

        if cycle % 12 == 0:  # vsakih približno 60 sekund
            try:
                run_integrity_check()
            except Exception as e:
                logger.error(f"SCHEDULER: model_integrity_guard napaka: {e}")
                logger.debug(traceback.format_exc())

        now = int(time.time())
        for agent in AGENTS:
            AGENT_LAST_USED[agent] = now

        cycle += 1
        time.sleep(5)


# ======================================================
#  ENTRY POINT
# ======================================================

if __name__ == "__main__":
    logger.info("SCHEDULER: zagon")
    try:
        scheduler_loop()
    except KeyboardInterrupt:
        logger.warning("SCHEDULER: ročna prekinitev.")
    except Exception as e:
        logger.critical(f"SCHEDULER: fatala napaka: {e}")
        logger.debug(traceback.format_exc())

# ======================================================
#  EXTERNAL CALL
# ======================================================


def start_scheduler():
    scheduler_loop()


def RUNNING_THREADS():
    return None


def STOP_EVENTS():
    return None
