# plugins/behavioral_dna_diffuser.py

import json
import random
import hashlib
from pathlib import Path
from datetime import datetime

GOAL_SCORE_LOG = "logs/goal_score_success.json"
DNA_DIFFUSION_LOG = "logs/behavioral_dna_diffusion.json"
MAX_DIFFUSIONS_PER_AGENT = 3
MIN_SCORE_THRESHOLD = 0.85

class BehavioralDNADiffuser:
    def __init__(self):
        self.success_log = self.load_json(GOAL_SCORE_LOG)
        self.diffusion_log = self.load_json(DNA_DIFFUSION_LOG)
        self.diffused = set((entry["source"], entry["target"]) for entry in self.diffusion_log)

    def load_json(self, path):
        file = Path(path)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save_diffusion_log(self):
        with open(DNA_DIFFUSION_LOG, "w", encoding="utf-8") as f:
            json.dump(self.diffusion_log, f, indent=2, ensure_ascii=False)

    def extract_dna(self, action_sequence):
        joined = " > ".join(action_sequence)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def select_successful_dna(self):
        candidates = []
        for entry in self.success_log:
            if entry.get("score", 0) >= MIN_SCORE_THRESHOLD and "agent" in entry and "actions" in entry:
                dna = self.extract_dna(entry["actions"])
                candidates.append((entry["agent"], dna, entry["actions"]))
        return candidates

    def diffuse(self):
        candidates = self.select_successful_dna()
        agent_ids = list(set([entry[0] for entry in candidates]))

        diffusion_events = []

        for src_agent, dna, actions in candidates:
            potential_targets = [aid for aid in agent_ids if aid != src_agent]
            random.shuffle(potential_targets)
            count = 0

            for target in potential_targets:
                if (src_agent, target) in self.diffused:
                    continue
                diffusion_events.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": src_agent,
                    "target": target,
                    "dna_hash": dna,
                    "actions": actions
                })
                self.diffused.add((src_agent, target))
                count += 1
                if count >= MAX_DIFFUSIONS_PER_AGENT:
                    break

        if diffusion_events:
            self.diffusion_log.extend(diffusion_events)
            self.save_diffusion_log()

        return diffusion_events

diffuser_instance = BehavioralDNADiffuser()

def hook():
    return diffuser_instance.diffuse()
