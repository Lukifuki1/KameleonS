# stress_pulse_scheduler.py

import json
import uuid
import time
from datetime import datetime

STRESS_LOG_PATH = "logs/stress_pulse_log.json"
PULSE_INTERVAL_SECONDS = 300  # 5 minut

class StressPulseScheduler:
    def __init__(self):
        self.pulses = []
        self.last_pulse_time = 0

    def should_pulse(self):
        return time.time() - self.last_pulse_time >= PULSE_INTERVAL_SECONDS

    def trigger_pulse(self):
        pulse_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        pulse = {
            "pulse_id": pulse_id,
            "timestamp": timestamp,
            "status": "dispatched"
        }
        self.pulses.append(pulse)
        self.last_pulse_time = time.time()
        return pulse_id

    def confirm_response(self, pulse_id, latency, result_ok):
        for pulse in self.pulses:
            if pulse["pulse_id"] == pulse_id and pulse["status"] == "dispatched":
                pulse["status"] = "completed"
                pulse["latency"] = round(latency, 4)
                pulse["result_ok"] = bool(result_ok)
                pulse["response_timestamp"] = datetime.utcnow().isoformat()
                break

    def export_log(self):
        with open(STRESS_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.pulses, f, indent=2, ensure_ascii=False)

scheduler_instance = StressPulseScheduler()

def tick():
    if scheduler_instance.should_pulse():
        return scheduler_instance.trigger_pulse()
    return None

def respond(pulse_id, latency, result_ok):
    scheduler_instance.confirm_response(pulse_id, latency, result_ok)

def flush():
    scheduler_instance.export_log()
