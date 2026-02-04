#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import signal
import subprocess
import threading
import time
import traceback
from collections import defaultdict
from pathlib import Path

import auto_fix
from hardware_autotune import apply_hardware_profile
from kameleon import start_orchestrator
from loguru import logger
from orchestrator_shared import STOP_EVENT
from scheduler import start_scheduler
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

RESTART_THRESHOLD = 3
RESTART_WINDOW = 60
MONITOR_INTERVAL = 60
FORCE_RESTART_FLAG = Path("/media/4tb/Kameleon/cell/force_restart.flag")
WATCHED_DIR = Path("/media/4tb/Kameleon/cell/system")

RUNNING: dict[str, bool] = {}
RESTART_TIME: dict[str, list[float]] = defaultdict(list)
THREAD_OBJS: dict[str, threading.Thread] = {}
POPEN_PROCS: dict[str, subprocess.Popen] = {}

# convert_llama_ggml_to_gguf.py
from pathlib import Path
from subprocess import run


def convert_all_distilled_models():
    input_dir = Path("cell/models/active")
    for f in input_dir.glob("*.distilled"):
        out_file = f.with_suffix(".gguf")
        if not out_file.exists():
            print(f"[INFO] Konvertiram {f.name} → {out_file.name}")
            run(["llama-convert", str(f), str(out_file)], check=True)


def rotate_log(logfile: Path, max_mb: int = 10):
    if logfile.exists() and logfile.stat().st_size > max_mb * 1024 * 1024:
        base = logfile.with_suffix("")
        for i in reversed(range(1, 5)):
            old = base.with_name(f"{base.name}.{i}.log")
            nxt = base.with_name(f"{base.name}.{i + 1}.log")
            if old.exists():
                old.rename(nxt)
        logfile.rename(base.with_name(f"{base.name}.1.log"))
        logfile.touch()


def start_thread(name: str, target):
    def wrapper():
        try:
            logger.info(f"{name}: zagon niti")
            target()
        except Exception as e:
            logger.critical(f"{name}: neobvladana napaka: {e}")
            logger.debug(traceback.format_exc())
        finally:
            RUNNING[name] = False

    t = threading.Thread(target=wrapper, daemon=True)
    RUNNING[name] = True
    THREAD_OBJS[name] = t
    t.start()


def start_process(name: str, command: list[str]):
    logger.info(f"{name}: zaganjam proces: {command}")
    try:
        proc = subprocess.Popen(command)
        RUNNING[name] = True
        POPEN_PROCS[name] = proc
    except Exception as e:
        logger.error(f"{name}: napaka pri Popen zagonu: {e}")
        RUNNING[name] = False


def should_restart(name: str) -> bool:
    if name in ("VOICE", "WAKE_WORD"):
        return False

    now = time.time()
    RESTART_TIME[name] = [t for t in RESTART_TIME[name] if now - t < RESTART_WINDOW]
    RESTART_TIME[name].append(now)

    if FORCE_RESTART_FLAG.exists():
        logger.warning(f"{name}: FORCE_RESTART_FLAG omogoča zagon kljub limitu.")
        return True

    if len(RESTART_TIME[name]) > RESTART_THRESHOLD:
        logger.critical(
            f"{name}: prekoračen prag restartov znotraj {RESTART_WINDOW}s. Zaklep."
        )
        return False

    return True


def monitor_status():
    while not STOP_EVENT.is_set():
        active = [
            n
            for n, state in RUNNING.items()
            if state and n not in ("VOICE", "WAKE_WORD")
        ]
        inactive = [
            n
            for n, state in RUNNING.items()
            if not state and n not in ("VOICE", "WAKE_WORD")
        ]
        logger.info(f"STATUS: Aktivne: {active} | Neaktivne: {inactive}")
        time.sleep(MONITOR_INTERVAL)


def handle_sigterm(signum, frame):
    logger.warning("SYSTEM: prejet SIGTERM, zaustavitev...")
    STOP_EVENT.set()


class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            path = Path(event.src_path).resolve()
            logger.warning(f"WATCHDOG: Sprememba zaznana: {path}")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            path = Path(event.src_path).resolve()
            logger.info(f"WATCHDOG: Nova datoteka zaznana: {path}")

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            path = Path(event.src_path).resolve()
            logger.info(f"WATCHDOG: Izbrisana datoteka: {path}")

    def on_moved(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            src = Path(event.src_path).resolve()
            dest = Path(event.dest_path).resolve()
            logger.info(f"WATCHDOG: Premik datoteke: {src} → {dest}")


def start_watchdog():
    if not WATCHED_DIR.exists():
        logger.warning(f"WATCHDOG: mapa ne obstaja: {WATCHED_DIR}")
        return
    observer = Observer()
    observer.schedule(ChangeHandler(), str(WATCHED_DIR), recursive=True)
    observer.daemon = True
    observer.start()
    logger.info(f"WATCHDOG: spremljam {WATCHED_DIR}")


signal.signal(signal.SIGTERM, handle_sigterm)

if __name__ == "__main__":
    log_path = Path("cell.log")
    rotate_log(log_path)
    logger.info("SYSTEM: zaganjanje vseh komponent")
    apply_hardware_profile()

    import orchestrator_shared

    orchestrator_shared.register_all_models()  # ← dodaj sem

    THREADS = {
        "ORCHESTRATOR": lambda: start_thread("ORCHESTRATOR", start_orchestrator),
        "SCHEDULER": lambda: start_thread("SCHEDULER", start_scheduler),
        "SIS_MONITOR": lambda: start_process(
            "SIS_MONITOR",
            ["python3", "/media/4tb/Kameleon/cell/system/sis_fallback_monitor.py"],
        ),
    }

    for starter in THREADS.values():
        starter()

    threading.Thread(target=monitor_status, daemon=True).start()
    start_watchdog()

    try:
        while not STOP_EVENT.is_set():
            for name, starter in THREADS.items():
                alive = (name in THREAD_OBJS and THREAD_OBJS[name].is_alive()) or (
                    name in POPEN_PROCS and POPEN_PROCS[name].poll() is None
                )

                if not alive:
                    RUNNING[name] = False
                    if should_restart(name):
                        logger.warning(f"{name}: nit/proces padel, ponovno zaganjam...")
                        starter()
                    else:
                        logger.error(
                            f"{name}: onemogočen ponovni zagon zaradi prevelikega števila izpadov."
                        )
            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("SYSTEM: prekinjeno ročno (CTRL+C)")
        STOP_EVENT.set()
    except Exception as e:
        logger.critical(f"SYSTEM: fatala napaka: {e}")
        logger.debug(traceback.format_exc())
        STOP_EVENT.set()

    time.sleep(2)
    logger.info("SYSTEM: vse komponente ustavljene.")
