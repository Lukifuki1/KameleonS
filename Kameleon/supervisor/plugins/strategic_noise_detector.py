# plugins/strategic_noise_detector.py

import json
import hashlib
import random
from pathlib import Path
from datetime import datetime
from collections import defaultdict

GOAL_LOG = "logs/goal_score_success.json"
NOISE_REPORT = "logs/strategic_noise_report.json"
WINDOW_SIZE = 50
VARIATION_COUNT = 3
STABILITY_THRESHOLD = 0.2  # dovoljeno odstopanje v rezultatnosti

class StrategicNoiseDetector:
    def __init__(self):
        self.log_entries = self.load_goals()
        self.noise_report = []

    def load_goals(self):
        path = Path(GOAL_LOG)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)[-WINDOW_SIZE:]
        except json.JSONDecodeError:
            return []

    def mutate_goal(self, goal):
        # mikro spremembe: sprememba vrstnega reda, sinonimi, majhni dodatki
        mutated = {}
        for k, v in goal.items():
            if isinstance(v, str):
                v = v.replace(",", "").replace(".", "")
                tokens = v.split()
                if len(tokens) > 1:
                    random.shuffle(tokens)
                mutated[k] = " ".join(tokens)
            else:
                mutated[k] = v
        return mutated

    def goal_hash(self, goal_obj):
        return hashlib.md5(json.dumps(goal_obj, sort_keys=True).encode("utf-8")).hexdigest()

    def analyze(self):
        goal_clusters = defaultdict(list)

        for entry in self.log_entries:
            agent = entry.get("agent")
            goal = entry.get("goal", {})
            score = entry.get("score", 0.0)

            if not agent or not goal:
                continue

            base_hash = self.goal_hash(goal)
            goal_clusters[(agent, base_hash)].append(score)

            for _ in range(VARIATION_COUNT):
                mutated_goal = self.mutate_goal(goal)
                mutated_hash = self.goal_hash(mutated_goal)
                # simuliramo: če bi tak cilj dal podoben rezultat
                # vzamemo bližnji rezultat iz obstoječih vnosov (če obstaja)
                for e in self.log_entries:
                    if e.get("agent") == agent and self.goal_hash(e.get("goal", {})) == mutated_hash:
                        goal_clusters[(agent, base_hash)].append(e.get("score", 0.0))
                        break

        for (agent, key), scores in goal_clusters.items():
            if len(scores) <= 1:
                continue
            avg = sum(scores) / len(scores)
            stdev = (sum((s - avg) ** 2 for s in scores) / len(scores)) ** 0.5

            if stdev >= STABILITY_THRESHOLD:
                self.noise_report.append({
                    "agent": agent,
                    "base_goal_hash": key,
                    "score_count": len(scores),
                    "stdev": round(stdev, 4),
                    "avg_score": round(avg, 4),
                    "timestamp": datetime.utcnow().isoformat(),
                    "indicator": "strategic_noise"
                })

    def save(self):
        path = Path(NOISE_REPORT)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.noise_report, f, indent=2, ensure_ascii=False)

    def run(self):
        self.analyze()
        self.save()
        return self.noise_report

noise_detector_instance = StrategicNoiseDetector()

def hook():
    return noise_detector_instance.run()
