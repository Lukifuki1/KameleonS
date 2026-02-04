# meta_quantifier_init.py

import json
import statistics
from datetime import datetime

META_QUANT_LOG_PATH = "logs/meta_quantifier_profile.json"
WINDOW = 100

class MetaQuantifier:
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.records = []

    def observe_io(self, input_length, output_length, processing_time):
        if len(self.inputs) >= WINDOW:
            self.inputs.pop(0)
            self.outputs.pop(0)

        self.inputs.append(input_length)
        self.outputs.append((output_length, processing_time))

    def compute_profile(self):
        avg_in = statistics.mean(self.inputs) if self.inputs else 0
        avg_out_len = statistics.mean([o[0] for o in self.outputs]) if self.outputs else 0
        avg_proc = statistics.mean([o[1] for o in self.outputs]) if self.outputs else 0

        io_ratio = round(avg_out_len / avg_in, 3) if avg_in else 0
        complexity_score = round((avg_in + avg_out_len) * avg_proc, 3)

        profile = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_avg_len": round(avg_in, 3),
            "output_avg_len": round(avg_out_len, 3),
            "avg_processing_time": round(avg_proc, 3),
            "io_ratio": io_ratio,
            "complexity_score": complexity_score
        }

        self.records.append(profile)
        return profile

    def export_profile(self):
        profile = self.compute_profile()
        with open(META_QUANT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

quant_instance = MetaQuantifier()

def hook(input_text: str, output_text: str, processing_time: float):
    quant_instance.observe_io(len(input_text), len(output_text), processing_time)

def flush():
    quant_instance.export_profile()
