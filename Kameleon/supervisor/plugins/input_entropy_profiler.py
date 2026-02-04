# input_entropy_profiler.py

import json
import math
import hashlib
import time
from collections import defaultdict
from datetime import datetime

INPUT_LOG_PATH = "logs/input_entropy_log.json"
WINDOW_SIZE = 100

class InputEntropyProfiler:
    def __init__(self):
        self.inputs = []
        self.frequency = defaultdict(int)
        self.log = []

    def record_input(self, input_text):
        if not input_text.strip():
            return

        self.inputs.append(input_text)
        normalized = input_text.strip().lower()
        self.frequency[normalized] += 1

        if len(self.inputs) >= WINDOW_SIZE:
            self.analyze()
            self.inputs.clear()
            self.frequency.clear()

    def calculate_entropy(self):
        total = sum(self.frequency.values())
        if total == 0:
            return 0.0
        probs = [freq / total for freq in self.frequency.values()]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        return round(entropy, 4)

    def analyze(self):
        entropy = self.calculate_entropy()
        diversity = len(self.frequency)
        hash_window = hashlib.sha256("||".join(self.inputs).encode("utf-8")).hexdigest()

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "entropy": entropy,
            "distinct_inputs": diversity,
            "window_size": len(self.inputs),
            "hash": hash_window
        }

        self.log.append(entry)
        self.export_log()

    def export_log(self):
        with open(INPUT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.log, f, indent=2, ensure_ascii=False)

profiler_instance = InputEntropyProfiler()

def hook(input_text):
    profiler_instance.record_input(input_text)
