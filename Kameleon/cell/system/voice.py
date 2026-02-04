#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import io
from collections import deque

import pyaudio
import speech_recognition as sr
from loguru import logger
from orchestrator_shared import (
    AUDIO_QUEUE,
    STOP_EVENT,
    handle_voice_command,
    has_permission,
    identify_user,
    tts,
    voice_authenticate,
)

RECORD_SECONDS = 3
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


def record_audio(seconds=RECORD_SECONDS):
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )
    frames = []
    for _ in range(0, int(SAMPLE_RATE / CHUNK * seconds)):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))
    stream.stop_stream()
    stream.close()
    pa.terminate()
    return b"".join(frames)


def transcribe(audio_bytes):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(io.BytesIO(audio_bytes))
    with audio_file as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio, language="sl-SI")


def listen_for_confirmation():
    try:
        audio = record_audio(2)
        response = transcribe(audio)
        return response.lower()
    except Exception as e:
        logger.warning(f"VOICE: napaka pri potrditvi: {e}")
        return input("Potrdi ukaz (da/ne): ").strip().lower()


def safe_tts(msg):
    try:
        tts(msg)
    except Exception as e:
        logger.error(f"TTS napaka: {e}")


def voice_interaction_worker():
    recent = deque(maxlen=10)

    while not STOP_EVENT.is_set():
        try:
            txt, audio_data = AUDIO_QUEUE.get(timeout=1)
        except Exception:
            continue

        if not txt:
            continue

        h = hashlib.sha256(txt.encode()).hexdigest()
        if h in recent:
            safe_tts("Ukaz je že obdelan.")
            continue
        recent.append(h)

        try:
            if not voice_authenticate(audio_data):
                safe_tts("Glasovna avtentikacija ni uspela.")
                continue
        except Exception as e:
            logger.error(f"VOICE: napaka pri avtentikaciji: {e}")
            safe_tts("Napaka pri preverjanju glasu.")
            continue

        try:
            user = identify_user(audio_data)
        except Exception as e:
            logger.error(f"VOICE: identifikacija ni uspela: {e}")
            user = None

        if not user:
            safe_tts("Uporabnik ni prepoznan.")
            continue

        try:
            if not has_permission(user, txt):
                safe_tts("Nimaš dovoljenja.")
                continue
        except Exception as e:
            logger.error(f"VOICE: napaka pri preverjanju dovoljenj: {e}")
            safe_tts("Napaka pri preverjanju dovoljenj.")
            continue

        safe_tts("Prosim potrdi: " + txt)
        c = listen_for_confirmation()

        if c in ("da", "yes", "potrjujem", "confirm", "go", "ok"):
            try:
                out = handle_voice_command(txt)
                if out:
                    safe_tts(out)
            except Exception as e:
                logger.error(f"VOICE: napaka pri izvajanju ukaza: {e}")
                safe_tts("Napaka pri izvajanju.")
        else:
            safe_tts("Ukaz prekinjen.")


def start_voice_loop():
    audio_data = record_audio(RECORD_SECONDS)
    try:
        text = transcribe(audio_data)
        AUDIO_QUEUE.put((text, audio_data))
    except Exception as e:
        logger.error(f"Napaka pri zajemu ali pretvorbi govora: {e}")
        safe_tts("Ni bilo mogoče razumeti ukaza.")


if __name__ == "__main__":
    logger.info("VOICE ENGINE: start")
    try:
        voice_interaction_worker()
    except KeyboardInterrupt:
        logger.info("VOICE ENGINE: prekinjeno ročno.")
    except Exception as e:
        logger.critical(f"VOICE ENGINE: fatala napaka: {e}")
