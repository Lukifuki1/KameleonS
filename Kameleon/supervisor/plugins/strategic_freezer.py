# plugins/strategic_freezer.py

import json
import hashlib
from collections import Counter
from pathlib import Path
from datetime import datetime

GOAL_LOG = "logs/goal_score_success.json"
FREEZE_SUGGESTIONS_LOG = "logs/strategic_freeze_suggestions.json"

MIN_OCCURRENCE = 3
SUCCESS_THRESHOLD = 0.9

class StrategicFreezer:
    def __init__(self):
        self.goal_data = self.load_goal_log()
        self.suggestions = []

    def load_goal_log(self):
        path = Path(GOAL_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def hash_strategy(self, actions):
        raw = json.dumps(actions, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def analyze(self):
        strategy_counter = Counter()
        strategy_map = {}

        for entry in self.goal_data:
            if entry.get("score", 0) >= SUCCESS_THRESHOLD and "actions" in entry:
                h = self.hash_strategy(entry["actions"])
                strategy_counter[h] += 1
                if h not in strategy_map:
                    strategy_map[h] = {
                        "actions": entry["actions"],
                        "example_agent": entry.get("agent"),
                        "first_seen": entry.get("timestamp", "unknown")
                    }

        for h, count in strategy_counter.items():
            if count >= MIN_OCCURRENCE:
                self.suggestions.append({
                    "strategy_hash": h,
                    "freeze_level": "suggested",
                    "occurrences": count,
                    "example_agent": strategy_map[h]["example_agent"],
                    "first_seen": strategy_map[h]["first_seen"],
                    "actions": strategy_map[h]["actions"],
                    "timestamp": datetime.utcnow().isoformat()
                })

        self.save()
        return self.suggestions

    def save(self):
        with open(FREEZE_SUGGESTIONS_LOG, "w", encoding="utf-8") as f:
            json.dump(self.suggestions, f, indent=2, ensure_ascii=False)

freezer_instance = StrategicFreezer()

def hook():
    return freezer_instance.analyze()
