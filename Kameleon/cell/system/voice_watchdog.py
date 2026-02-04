#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import traceback

import sounddevice as sd

LOGFILE = "/media/4tb/Kameleon/cell/cell_logs/voice_watchdog.log"
CHECK_INTERVAL = 20  # sekund


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def check_microphone():
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        if not input_devices:
            log("[!] ⚠️  Ni aktivnega mikrofona.")
            return False

        # Preizkus snemanja
        try:
            recording = sd.rec(int(0.5 * 16000), samplerate=16000, channels=1)
            sd.wait()
            if recording.max() < 0.001:
                log("[!] ⚠️  Mikrofon zaznan, a brez signala.")
                return False
            log("[+] 🎙️ Mikrofon OK.")
            return True
        except Exception as rec_err:
            log(f"[!] Napaka snemanja: {rec_err}")
            return False

    except Exception as e:
        log(f"[!] Napaka zaznavanja naprav: {e}")
        log(traceback.format_exc())
        return False


def watchdog_loop():
    log("🛡️ Začenjam voice_watchdog zanko...")
    while True:
        check_microphone()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    watchdog_loop()
