#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import time
from pathlib import Path

from loguru import logger

try:
    import psutil
except ImportError:
    raise ImportError("Ni mogoče uvoziti 'psutil'. Namesti ga z: pip install psutil")

try:
    import pynvml
except ImportError:
    raise ImportError("Ni mogoče uvoziti 'pynvml'. Namesti ga z: pip install pynvml")


PROFILE_PATH = Path("config/hardware_profile.json")


def load_profile():
    try:
        with PROFILE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("Manjka config/hardware_profile.json")
    except json.JSONDecodeError as e:
        raise ValueError(f"Neveljaven JSON v profilu: {e}") from e


def save_profile(data):
    try:
        with PROFILE_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.success("HARDWARE-AUTOTUNE: profil posodobljen.")
    except OSError as e:
        logger.error(f"HARDWARE-AUTOTUNE: zapis profila ni uspel: {e}")


def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
    except Exception as e:
        logger.warning(f"Ne morem brati CPU temperatur: {e}")
        return None

    if "k10temp" in temps:
        return max(t.current for t in temps["k10temp"])
    if "coretemp" in temps:
        return max(t.current for t in temps["coretemp"])
    return None


def get_gpu_stats():
    try:
        pynvml.nvmlInit()
    except Exception as e:
        logger.warning(f"NVML init neuspešen: {e}")
        return []

    gpus = []
    try:
        count = pynvml.nvmlDeviceGetCount()
    except Exception as e:
        logger.warning(f"NVML: štetje GPU ni uspelo: {e}")
        return gpus

    for i in range(count):
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            util = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        except Exception as e:
            logger.warning(f"NVML: GPU {i} ni dostopen: {e}")
            continue

        gpus.append(
            {
                "id": i,
                "temp": temp,
                "util": util,
                "mem_used": mem.used // (1024 * 1024),
                "mem_total": mem.total // (1024 * 1024),
            }
        )
    return gpus


def autotune_cpu(profile):
    cpu_temp = get_cpu_temp()
    if cpu_temp is None:
        return profile

    limit = profile["cpu"]["max_temp_limit_c"]

    if cpu_temp > limit:
        profile["cpu"]["curve_optimizer"] = max(
            profile["cpu"]["curve_optimizer"] - 1, -30
        )
        logger.warning(
            f"HARDWARE-AUTOTUNE: CPU pretopel ({cpu_temp}°C) → CO = {profile['cpu']['curve_optimizer']}"
        )
    elif cpu_temp < (limit - 10):
        profile["cpu"]["curve_optimizer"] = min(
            profile["cpu"]["curve_optimizer"] + 1, -5
        )
        logger.info(
            f"HARDWARE-AUTOTUNE: CPU stabilen ({cpu_temp}°C) → CO = {profile['cpu']['curve_optimizer']}"
        )

    return profile


def autotune_gpu(profile):
    gpu_stats = get_gpu_stats()
    for gpu in gpu_stats:
        for entry in profile["gpus"]:
            if entry["id"] == gpu["id"]:
                if gpu["temp"] > 82:
                    entry["max_load_percent"] = max(entry["max_load_percent"] - 1, 70)
                    logger.warning(
                        f"HARDWARE-AUTOTUNE: GPU{gpu['id']} pretopel ({gpu['temp']}°C) → max_load = {entry['max_load_percent']}%"
                    )
                elif gpu["temp"] < 70 and entry["max_load_percent"] < 95:
                    entry["max_load_percent"] += 1
                    logger.info(
                        f"HARDWARE-AUTOTUNE: GPU{gpu['id']} hladen ({gpu['temp']}°C) → max_load = {entry['max_load_percent']}%"
                    )
    return profile


def autotune_nvme(profile):
    try:
        nvme_stats = subprocess.run(
            ["lsblk", "-o", "NAME,TEMPERATURE"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout
    except Exception as e:
        logger.warning(f"NVMe branje ni uspelo: {e}")
        return profile

    for line in nvme_stats.splitlines():
        if "nvme" in line and "°C" in line:
            try:
                temp = int(line.split("°")[0].split()[-1])
            except ValueError:
                continue

            if temp > 65:
                profile["scheduler"]["nvme_write_throttle"] = True
                logger.warning(
                    f"HARDWARE-AUTOTUNE: NVMe {temp}°C → write throttle = ON"
                )
            elif temp < 50:
                profile["scheduler"]["nvme_write_throttle"] = False
                logger.info(f"HARDWARE-AUTOTUNE: NVMe {temp}°C → write throttle = OFF")

    return profile


def log_extra_telemetry(profile):
    if not profile.get("monitoring", {}).get("log_temperature", False):
        return

    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
    except Exception as e:
        logger.warning(f"TELEMETRIJA: NVML init ni uspelo: {e}")
        return

    for i in range(count):
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            util = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)

            parts = [
                f"GPU{i}: {temp}°C",
                f"{util}%",
                f"{mem.used // (1024 * 1024)}MB / {mem.total // (1024 * 1024)}MB",
            ]

            if profile["monitoring"].get("log_fan_speed"):
                fan = pynvml.nvmlDeviceGetFanSpeed(h)
                parts.append(f"FAN: {fan}%")

            if profile["monitoring"].get("log_power_draw"):
                power = pynvml.nvmlDeviceGetPowerUsage(h) / 1000
                parts.append(f"POWER: {power:.1f}W")

            logger.info(" | ".join(parts))
        except Exception as e:
            logger.warning(f"TELEMETRIJA: GPU{i} ni mogoče brati: {e}")


def main():
    logger.info("HARDWARE-AUTOTUNE: zagon optimizacije strojnih parametrov.")
    while True:
        try:
            profile = load_profile()
            profile = autotune_cpu(profile)
            profile = autotune_gpu(profile)
            profile = autotune_nvme(profile)
            save_profile(profile)
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("HARDWARE-AUTOTUNE: ročno prekinjeno.")
            break
        except Exception as e:
            logger.error(f"HARDWARE-AUTOTUNE: napaka: {e}")
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"HARDWARE-AUTOTUNE: kritična napaka pri zagonu: {e}")
