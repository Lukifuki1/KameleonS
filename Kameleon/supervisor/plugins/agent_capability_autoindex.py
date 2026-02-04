# plugins/agent_capability_autoindex.py

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

GOAL_LOG = "logs/goal_score_success.json"
INDEX_OUTPUT = "exports/agent_capability_index.json"
SCORE_THRESHOLD = 0.85
WINDOW_SIZE = 100

class AgentCapabilityAutoindex:
    def __init__(self):
        self.log_data = self.load_recent_goals()
        self.capability_index = defaultdict(set)

    def load_recent_goals(self):
        path = Path(GOAL_LOG)
        if not path.exists():
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
                return entries[-WINDOW_SIZE:]
        except json.JSONDecodeError:
            return []

    def extract_capabilities(self):
        for entry in self.log_data:
            agent = entry.get("agent")
            goal = entry.get("goal", {})
            score = entry.get("score", 0.0)

            if not agent or score < SCORE_THRESHOLD:
                continue

            if isinstance(goal, dict):
                for key, value in goal.items():
                    fragment = f"{key}:{str(value).strip().lower()}"
                    self.capability_index[agent].add(fragment)

    def serialize(self):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {
                agent: sorted(list(capabilities))
                for agent, capabilities in self.capability_index.items()
            }
        }

    def save(self, data):
        path = Path(INDEX_OUTPUT)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def run(self):
        self.extract_capabilities()
        data = self.serialize()
        self.save(data)
        return data

autoindex_instance = AgentCapabilityAutoindex()

def hook():
    return autoindex_instance.run()
