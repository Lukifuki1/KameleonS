#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path

LOGFILE = "/media/4tb/Kameleon/cell/cell_logs/sis_fallback_monitor.log"
SIS_LOG = "/media/4tb/Kameleon/cell/cell_logs/sis_filter.log"  # mora obstajati / biti zapisovan v sis.py
THRESHOLD = 5  # število zaporednih zavrnjenih promptov
CHECK_INTERVAL = 15  # sekund


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def count_recent_rejections():
    if not Path(SIS_LOG).exists():
        log("[!] SIS log ne obstaja.")
        return 0

    try:
        with open(SIS_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()[-50:]  # zadnjih 50 vrstic
            rejections = [line for line in lines if "REJECTED" in l]
            return len(rejections)
    except Exception as e:
        log(f"[!] Napaka pri branju SIS loga: {e}")
        return 0


def watchdog_loop():
    log("🛡️ Začenjam SIS fallback monitor...")
    while True:
        rejected_count = count_recent_rejections()
        if rejected_count >= THRESHOLD:
            log(f"[!] ⚠️  Detektiran prekomeren SIS filter: {rejected_count} zavrnitev.")
            # možnost: aktiviraj fallback (npr. shrani primer za ročni pregled)
            with open("/media/4tb/Kameleon/cell/logs/sis_fallback.flag", "w") as f:
                f.write("SIS_OVERFILTER_DETECTED")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    watchdog_loop()
