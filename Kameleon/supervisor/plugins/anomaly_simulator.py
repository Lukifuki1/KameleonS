# plugins/anomaly_simulator.py

import json
import random
from datetime import datetime
from pathlib import Path

SIMULATION_OUTPUT = "simulations/synthetic_anomalies.json"
ANOMALY_TYPES = ["spike", "drift", "noise_injection", "null_zone", "inversion"]
TARGET_DOMAINS = ["sensor_data", "signal_flow", "decision_path", "memory_trace"]
INSTANCES = 25

class AnomalySimulator:
    def __init__(self):
        self.generated = []

    def generate_anomaly(self):
        anomaly_type = random.choice(ANOMALY_TYPES)
        domain = random.choice(TARGET_DOMAINS)

        anomaly = {
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly_type": anomaly_type,
            "domain": domain,
            "payload": self.generate_payload(anomaly_type),
            "synthetic": True,
            "simulated_by": "anomaly_simulator"
        }
        return anomaly

    def generate_payload(self, anomaly_type):
        if anomaly_type == "spike":
            return {"values": [random.uniform(0.1, 0.3)] * 5 + [random.uniform(0.9, 1.2)] + [random.uniform(0.1, 0.3)] * 5}
        elif anomaly_type == "drift":
            start = random.uniform(0.2, 0.4)
            return {"values": [start + i * 0.05 for i in range(12)]}
        elif anomaly_type == "noise_injection":
            return {"values": [random.uniform(-0.5, 1.5) for _ in range(12)]}
        elif anomaly_type == "null_zone":
            return {"values": [0] * 12}
        elif anomaly_type == "inversion":
            base = [random.uniform(0.2, 0.8) for _ in range(6)]
            return {"values": base + list(reversed(base))}
        else:
            return {"values": []}

    def run(self):
        for _ in range(INSTANCES):
            self.generated.append(self.generate_anomaly())
        self.save()
        return self.generated

    def save(self):
        path = Path(SIMULATION_OUTPUT)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.generated, f, indent=2, ensure_ascii=False)

simulator_instance = AnomalySimulator()

def hook():
    return simulator_instance.run()
