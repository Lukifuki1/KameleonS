# plugins/slow_drift_detector.py

import json
import hashlib
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

RESPONSE_LOG = "logs/goal_score_success.json"
DRIFT_LOG = "logs/slow_drift_report.json"
WINDOW = 15  # število zaporednih odzivov na agenta
DRIFT_THRESHOLD = 0.15  # prag za zaznavo počasnega zamika (manj = bolj občutljivo)

class SlowDriftDetector:
    def __init__(self):
        self.data = self.load_log()
        self.report = []

    def load_log(self):
        path = Path(RESPONSE_LOG)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def entropy(self, text):
        freq = defaultdict(int)
        total = 0
        for c in text:
            freq[c] += 1
            total += 1
        if total == 0:
            return 0.0
        probs = [count / total for count in freq.values()]
        return -sum(p * math.log2(p) for p in probs if p > 0)

    def process(self):
        agent_responses = defaultdict(list)

        for entry in self.data:
            agent = entry.get("agent")
            output = entry.get("output") or ""
            if agent:
                agent_responses[agent].append(output.strip())

        for agent_id, responses in agent_responses.items():
            recent = responses[-WINDOW:]
            if len(recent) < WINDOW:
                continue

            entropy_series = [self.entropy(r) for r in recent]
            diffs = [abs(entropy_series[i] - entropy_series[i - 1]) for i in range(1, len(entropy_series))]
            avg_drift = sum(diffs) / len(diffs)

            if avg_drift >= DRIFT_THRESHOLD:
                self.report.append({
                    "agent": agent_id,
                    "avg_entropy_drift": round(avg_drift, 4),
                    "window_size": WINDOW,
                    "timestamp": datetime.utcnow().isoformat()
                })

        self.save()
        return self.report

    def save(self):
        with open(DRIFT_LOG, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

drift_detector_instance = SlowDriftDetector()

def hook():
    return drift_detector_instance.process()
