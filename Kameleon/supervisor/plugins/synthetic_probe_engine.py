# synthetic_probe_engine.py

import json
import uuid
import random
import time
from datetime import datetime

PROBE_LOG_PATH = "logs/synthetic_probe_log.json"

class SyntheticProbeEngine:
    def __init__(self):
        self.probes = []

    def generate_probe(self):
        probe_id = str(uuid.uuid4())
        probe = {
            "id": probe_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": random.choice(["logic", "pattern", "memory", "math", "language"]),
            "difficulty": random.randint(1, 5),
            "status": "dispatched"
        }
        self.probes.append(probe)
        return probe

    def observe_response(self, probe_id, success, latency):
        for probe in self.probes:
            if probe["id"] == probe_id:
                probe["status"] = "completed"
                probe["success"] = bool(success)
                probe["latency"] = round(latency, 3)
                probe["completed_at"] = datetime.utcnow().isoformat()
                break

    def export_log(self):
        with open(PROBE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.probes, f, indent=2, ensure_ascii=False)

engine_instance = SyntheticProbeEngine()

def dispatch_probe():
    return engine_instance.generate_probe()

def register_result(probe_id, success, latency):
    engine_instance.observe_response(probe_id, success, latency)

def flush():
    engine_instance.export_log()
