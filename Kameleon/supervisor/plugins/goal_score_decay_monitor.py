# plugins/goal_score_decay_monitor.py

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

GOAL_LOG = "logs/goal_score_success.json"
DECAY_LOG = "logs/goal_score_decay_report.json"
WINDOW_SIZE = 10
DECAY_THRESHOLD = -0.05  # povprečni padec na oceno (negativna vrednost)

class GoalScoreDecayMonitor:
    def __init__(self):
        self.data = self.load_log()
        self.agent_scores = defaultdict(list)
        self.report = []

    def load_log(self):
        path = Path(GOAL_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def collect_scores(self):
        for entry in self.data:
            agent = entry.get("agent")
            score = entry.get("score")
            if agent and isinstance(score, (int, float)):
                self.agent_scores[agent].append(score)

    def analyze(self):
        for agent, scores in self.agent_scores.items():
            if len(scores) < WINDOW_SIZE:
                continue

            window = scores[-WINDOW_SIZE:]
            diffs = [window[i] - window[i - 1] for i in range(1, len(window))]
            avg_decay = sum(diffs) / len(diffs)

            if avg_decay < DECAY_THRESHOLD:
                self.report.append({
                    "agent": agent,
                    "window_size": WINDOW_SIZE,
                    "average_decay": round(avg_decay, 4),
                    "scores": window,
                    "timestamp": datetime.utcnow().isoformat()
                })

    def save(self):
        with open(Path(DECAY_LOG), "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

    def run(self):
        self.collect_scores()
        self.analyze()
        self.save()
        return self.report

decay_monitor_instance = GoalScoreDecayMonitor()

def hook():
    return decay_monitor_instance.run()
