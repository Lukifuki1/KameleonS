#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings

import pvporcupine
import pyaudio
import speech_recognition as sr
from loguru import logger
from orchestrator_shared import AUDIO_QUEUE, STOP_EVENT
from voice import start_voice_loop

warnings.filterwarnings("ignore", category=FutureWarning)

WAKE_WORD = "jarvis"  # ✅ zamenjano iz "kameleon" v privzeto podporo


def capture_user_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            logger.info("GOVORI ZDAJ (omejitev 7 sekund)...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)
            text = recognizer.recognize_google(audio, language="sl-SI")
            logger.success(f"PREPOZNANO: {text}")
            AUDIO_QUEUE.put((text, audio.get_raw_data()))
            start_voice_loop()
        except sr.WaitTimeoutError:
            logger.warning("Ni bilo govora.")
        except sr.UnknownValueError:
            logger.warning("Govora ni bilo mogoče prepoznati.")
        except Exception as e:
            logger.error(f"Napaka pri zajemu glasu: {e}")


def wake_word_listener():
    try:
        porcupine = pvporcupine.create(
            access_key="/2rdtqGtfNrFap1h0eJcRz48zHF8P4CfISaJ09F32pBuWaegLVNBFg==",
            keywords=[WAKE_WORD],
        )
    except Exception as e:
        logger.critical(f"❌ WAKE WORD: Napaka pri inicializaciji: {e}")
        return

    pa = pyaudio.PyAudio()

    mic_index = None
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if "GXT 258" in dev["name"] and dev["maxInputChannels"] > 0:
            mic_index = i
            break

    if mic_index is None:
        logger.critical("WAKE_WORD: GXT 258 Microphone ni bil najden.")
        return

    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        input_device_index=mic_index,
        frames_per_buffer=porcupine.frame_length,
    )

    logger.info(f"WAKE WORD: poslušam... (reci: '{WAKE_WORD.upper()}')")

    while not STOP_EVENT.is_set():
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = memoryview(pcm).cast("h")
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            logger.success("WAKE WORD: zaznan → čakam glasovni ukaz")
            capture_user_input()

    stream.stop_stream()
    stream.close()
    pa.terminate()


if __name__ == "__main__":
    try:
        wake_word_listener()
    except KeyboardInterrupt:
        logger.info("⛔ Uporabnik je prekinil program.")
        STOP_EVENT.set()
    except Exception as e:
        logger.critical(f"🔥 Fatala napaka v glavnem zanki: {e}")
