# hardware_thermal_profile.py

import json
import time
import psutil
import platform
from datetime import datetime

THERMAL_LOG_PATH = "logs/hardware_thermal_profile_log.json"
SAMPLE_INTERVAL = 60  # sekund

class ThermalLoadWatcher:
    def __init__(self):
        self.samples = []

    def collect_sample(self):
        timestamp = datetime.utcnow().isoformat()

        # CPU temperatura (če podprta)
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        cpu_temp = None
        if "coretemp" in temps:
            core_temps = temps["coretemp"]
            cpu_temp = sum(t.current for t in core_temps if t.label.startswith("Core")) / len(core_temps)

        # CPU obremenitev in RAM
        cpu_load = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()

        sample = {
            "timestamp": timestamp,
            "cpu_load_percent": round(cpu_load, 2),
            "memory_used_percent": round(mem.percent, 2),
            "cpu_temp_celsius": round(cpu_temp, 2) if cpu_temp else None,
            "platform": platform.platform()
        }

        self.samples.append(sample)

    def export_log(self):
        with open(THERMAL_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.samples, f, indent=2, ensure_ascii=False)

watcher_instance = ThermalLoadWatcher()

def tick():
    watcher_instance.collect_sample()

def flush():
    watcher_instance.export_log()
