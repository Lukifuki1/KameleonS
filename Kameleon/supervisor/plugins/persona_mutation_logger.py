# plugins/persona_mutation_logger.py

import re
import time
import json
import math
import hashlib
from collections import defaultdict
from datetime import datetime

LOG_PATH = "logs/persona_mutation_log.json"
PROFILE_BASELINE_PATH = "data/personality_baseline.json"
SAMPLE_WINDOW = 20
ENTROPY_THRESHOLD = 0.25
STYLE_CHANGE_THRESHOLD = 3

class PersonaMutationLogger:
    def __init__(self):
        self.samples = defaultdict(list)
        self.load_baseline()
        self.mutation_log = []
        self.load_existing_log()

    def load_baseline(self):
        try:
            with open(PROFILE_BASELINE_PATH, "r", encoding="utf-8") as f:
                self.baseline = json.load(f)
        except FileNotFoundError:
            self.baseline = {}

    def load_existing_log(self):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                self.mutation_log = json.load(f)
        except FileNotFoundError:
            self.mutation_log = []

    def save_log(self):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.mutation_log, f, indent=2, ensure_ascii=False)

    def track_agent_output(self, agent_id, output_text):
        if not output_text.strip():
            return

        entropy = self.calculate_entropy(output_text)
        fingerprint = self.fingerprint_text(output_text)
        self.samples[agent_id].append({
            "text": output_text,
            "entropy": entropy,
            "fingerprint": fingerprint,
            "timestamp": time.time()
        })

        if len(self.samples[agent_id]) >= SAMPLE_WINDOW:
            self.analyze(agent_id)
            self.samples[agent_id] = []

    def calculate_entropy(self, text):
        freq = defaultdict(int)
        total = 0
        for c in text:
            freq[c] += 1
            total += 1
        probs = [f / total for f in freq.values()]
        entropy = -sum(p * (0 if p == 0 else math.log2(p)) for p in probs)
        return entropy

    def fingerprint_text(self, text):
        clean = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    def detect_mutation(self, agent_id, fingerprints):
        if agent_id not in self.baseline:
            self.baseline[agent_id] = {
                "style_set": set(fingerprints),
                "entropy_avg": 0,
                "count": 0
            }

        baseline = self.baseline[agent_id]
        new_styles = sum(1 for fp in fingerprints if fp not in baseline["style_set"])

        avg_entropy = sum(s["entropy"] for s in self.samples[agent_id]) / SAMPLE_WINDOW
        entropy_drift = abs(avg_entropy - baseline["entropy_avg"]) if baseline["count"] > 0 else 0

        # Update baseline
        baseline["style_set"].update(fingerprints)
        baseline["entropy_avg"] = ((baseline["entropy_avg"] * baseline["count"]) + avg_entropy) / (baseline["count"] + 1)
        baseline["count"] += 1

        return new_styles >= STYLE_CHANGE_THRESHOLD or entropy_drift >= ENTROPY_THRESHOLD

    def analyze(self, agent_id):
        fingerprints = [s["fingerprint"] for s in self.samples[agent_id]]
        mutation_detected = self.detect_mutation(agent_id, fingerprints)
        if mutation_detected:
            self.log_mutation(agent_id)

    def log_mutation(self, agent_id):
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "agent_id": agent_id,
            "timestamp": timestamp,
            "type": "persona_mutation",
            "sample_count": SAMPLE_WINDOW
        }
        self.mutation_log.append(log_entry)
        self.save_log()

logger_instance = PersonaMutationLogger()

def hook(agent_id, output_text):
    logger_instance.track_agent_output(agent_id, output_text)
