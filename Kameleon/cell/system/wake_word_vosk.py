#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import queue
import sys

import sounddevice as sd
import vosk
from loguru import logger

WAKE_WORD = "good morning"
MODEL_PATH = "/home/kameleon/vosk-model-en-us"  # pot do modela

q = queue.Queue()


def audio_callback(indata, frames, time, status):
    if status:
        logger.warning(status)
    q.put(bytes(indata))


def main():
    logger.info("🧠 Nalagam Vosk model...")
    model = vosk.Model(MODEL_PATH)
    samplerate = 16000
    device = None

    # 🔽 Prepoznava fraze 'good morning'
    rec = vosk.KaldiRecognizer(model, samplerate, '["good morning"]')

    logger.info("🎙 Začenjam poslušanje... Reci 'good morning'")

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        device=device,
        dtype="int16",
        channels=1,
        callback=audio_callback,
    ):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = rec.Result()
                try:
                    text = json.loads(result).get("text", "")
                    logger.debug(f"🔊 zaznano: {text}")
                    if WAKE_WORD in text.lower():
                        logger.success(f"🚨 ZAZNANO: '{WAKE_WORD}'")
                        break
                except Exception as e:
                    logger.error(f"Napaka pri razčlenjevanju rezultata: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Prekinjeno.")
    except Exception as e:
        logger.critical(f"Napaka: {e}")
        sys.exit(1)
