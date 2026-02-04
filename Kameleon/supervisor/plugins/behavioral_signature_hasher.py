# plugins/behavioral_signature_hasher.py

import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

GOAL_LOG = "logs/goal_score_success.json"
SIGNATURE_LOG = "logs/behavioral_signatures.json"
WINDOW_SIZE = 20  # število zadnjih vedenj za hash

class BehavioralSignatureHasher:
    def __init__(self):
        self.goal_data = self.load_goals()
        self.signatures = defaultdict(list)
        self.load_existing()

    def load_goals(self):
        path = Path(GOAL_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def load_existing(self):
        path = Path(SIGNATURE_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    self.signatures = defaultdict(list, json.load(f))
                except json.JSONDecodeError:
                    self.signatures = defaultdict(list)

    def hash_behavior(self, actions_list):
        joined = " | ".join(json.dumps(a, sort_keys=True, ensure_ascii=False) for a in actions_list)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def process(self):
        agent_behaviors = defaultdict(list)

        for entry in self.goal_data:
            agent = entry.get("agent")
            actions = entry.get("actions")
            if agent and actions:
                agent_behaviors[agent].append(actions)

        snapshot = {}

        for agent, behaviors in agent_behaviors.items():
            recent = behaviors[-WINDOW_SIZE:]
            if len(recent) < WINDOW_SIZE:
                continue
            bhash = self.hash_behavior(recent)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "signature": bhash,
                "window_size": WINDOW_SIZE
            }
            self.signatures[agent].append(entry)
            snapshot[agent] = entry

        self.save()
        return snapshot

    def save(self):
        with open(SIGNATURE_LOG, "w", encoding="utf-8") as f:
            json.dump(self.signatures, f, indent=2, ensure_ascii=False)

signature_hasher_instance = BehavioralSignatureHasher()

def hook():
    return signature_hasher_instance.process()
