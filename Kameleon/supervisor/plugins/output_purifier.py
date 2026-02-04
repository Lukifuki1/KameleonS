# plugins/output_purifier.py

import json
import re
from pathlib import Path
from datetime import datetime

RAW_OUTPUT_LOG = "logs/goal_score_success.json"
PURIFIED_OUTPUT_LOG = "logs/purified_outputs.json"
WINDOW_SIZE = 100

class OutputPurifier:
    def __init__(self):
        self.raw_entries = self.load_raw_outputs()
        self.purified = []

    def load_raw_outputs(self):
        path = Path(RAW_OUTPUT_LOG)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
                return entries[-WINDOW_SIZE:]
        except json.JSONDecodeError:
            return []

    def clean_output(self, text):
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"(?i)\b(note|disclaimer|tip|info|remember|please note):?.*?$", "", text)
        text = re.sub(r"(?i)\b(for example|e\.g\.|i\.e\.)\s+", "", text)
        text = re.sub(r"\s*[\[\(]source:.*?[\]\)]", "", text)
        return text.strip()

    def process(self):
        for entry in self.raw_entries:
            agent = entry.get("agent")
            output = entry.get("output", "")
            if not agent or not output.strip():
                continue

            purified = self.clean_output(output)
            self.purified.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent,
                "purified_output": purified,
                "original_output": output.strip()
            })

        self.save()
        return self.purified

    def save(self):
        path = Path(PURIFIED_OUTPUT_LOG)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.purified, f, indent=2, ensure_ascii=False)

purifier_instance = OutputPurifier()

def hook():
    return purifier_instance.process()
