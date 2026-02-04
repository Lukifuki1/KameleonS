#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import runpy
import sys
import traceback

from loguru import logger


def load_and_run_script(path, stop_event):
    script_path = str(path.resolve())
    logger.info(f"PLUGIN_LOADER: nalaganje skripte {script_path}")

    try:
        # Dodaj pot do skripte v sys.path
        sys.path.insert(0, str(path.parent.resolve()))
        runpy.run_path(script_path)
    except Exception:
        logger.error(f"PLUGIN_LOADER: napaka pri izvajanju {script_path}")
        logger.error(traceback.format_exc())
    finally:
        # Počakaj, dokler ni izrecno zaustavljeno
        while not stop_event.is_set():
            stop_event.wait(1)
        logger.info(
            f"PLUGIN_LOADER: stop_event prejet, zaključujem skripto {script_path}"
        )
