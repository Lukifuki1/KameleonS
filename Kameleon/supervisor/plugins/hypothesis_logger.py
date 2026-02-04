# plugins/hypothesis_logger.py

import json
from pathlib import Path
from datetime import datetime

HYPOTHESIS_LOG = "logs/hypothesis_log.json"

class HypothesisLogger:
    def __init__(self):
        self.log_path = Path(HYPOTHESIS_LOG)
        self.ensure_log_exists()

    def ensure_log_exists(self):
        if not self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def log_hypothesis(self, agent_id, hypothesis_text, context=None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_id,
            "hypothesis": hypothesis_text.strip(),
            "context": context or {}
        }

        with open(self.log_path, "r+", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()

        return entry

hypothesis_logger_instance = HypothesisLogger()

def hook(agent_id, hypothesis_text, context=None):
    return hypothesis_logger_instance.log_hypothesis(agent_id, hypothesis_text, context)
