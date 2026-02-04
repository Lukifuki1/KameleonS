#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import threading
from pathlib import Path
from collections import deque
from loguru import logger
import matplotlib.pyplot as plt
import matplotlib.animation as animation

FAIL_SECURE_LOG = Path("logs/system.log")
DISPLAY_LIMIT = 50
REFRESH_INTERVAL = 10  # sekund
KEYWORDS = ["FAIL-SECURE", "SECURE-FALLBACK", "CRITICAL FAIL-SAFE"]
HISTORY = deque(maxlen=DISPLAY_LIMIT)

lock = threading.Lock()

def parse_fail_secure_logs():
    if not FAIL_SECURE_LOG.exists():
        return []

    entries = []
    try:
        with FAIL_SECURE_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                if any(kw in line.upper() for kw in KEYWORDS):
                    entries.append(line.strip())
    except Exception as e:
        logger.error(f"🪖 REPLAY VIEWER: napaka pri branju logov: {e}")
    return entries

def update_history():
    while True:
        new_data = parse_fail_secure_logs()
        with lock:
            HISTORY.clear()
            HISTORY.extend(new_data[-DISPLAY_LIMIT:])
        time.sleep(REFRESH_INTERVAL)

def animate(i):
    plt.clf()
    with lock:
        data = list(HISTORY)

    if not data:
        plt.text(0.5, 0.5, "Ni FAIL-SECURE dogodkov", ha='center', va='center', fontsize=12)
        return

    y = list(range(len(data)))
    labels = [line[-80:] for line in data]
    plt.barh(y, [1]*len(data), tick_label=labels, color="crimson")
    plt.xlabel("Fail-Secure Dogodki")
    plt.title("🪖 FAIL-SECURE REPLAY VIEWER")
    plt.tight_layout()

def run(stop_event):
    logger.info("🪖 REPLAY VIEWER: aktiviran")
    threading.Thread(target=update_history, daemon=True).start()

    fig = plt.figure("Fail-Secure Dogodki")
    ani = animation.FuncAnimation(fig, animate, interval=REFRESH_INTERVAL * 1000)

    try:
        plt.show()
    except KeyboardInterrupt:
        logger.info("🪖 REPLAY VIEWER: zaustavljen s tipkovnico")
    stop_event.set()
