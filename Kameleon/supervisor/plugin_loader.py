#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
from loguru import logger

def load_and_run_script(script_path, stop_event):
    try:
        spec = importlib.util.spec_from_file_location("plugin", script_path)
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)

        if hasattr(plugin, "run") and callable(plugin.run):
            plugin.run(stop_event)
        else:
            logger.error(f"{script_path.name}: manjkajoča funkcija 'run(stop_event)'")
    except Exception as e:
        logger.error(f"{script_path.name}: napaka pri nalaganju/izvajanju: {e}")
