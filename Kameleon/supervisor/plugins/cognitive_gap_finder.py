# plugins/cognitive_gap_finder.py

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

KNOWLEDGE_DIR = "knowledge_bank/"
GOAL_LOG = "logs/goal_score_success.json"
GAP_LOG = "logs/cognitive_gap_report.json"

MIN_KNOWLEDGE_ENTRIES = 5
MAX_GOAL_LOOKBACK = 200
GAP_THRESHOLD = 0.02  # če je pokritost domene < 2 %

class CognitiveGapFinder:
    def __init__(self):
        self.knowledge_data = self.load_knowledge_bank()
        self.goal_data = self.load_goal_log()
        self.report = []

    def load_knowledge_bank(self):
        domain_counts = Counter()
        pathlist = Path(KNOWLEDGE_DIR).rglob("*.json")
        for path in pathlist:
            parts = path.parts
            if "knowledge_bank" in parts:
                idx = parts.index("knowledge_bank")
                if idx + 1 < len(parts):
                    domain = parts[idx + 1]
                    domain_counts[domain] += 1
        return domain_counts

    def load_goal_log(self):
        path = Path(GOAL_LOG)
        if not path.exists():
            return []

        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)[-MAX_GOAL_LOOKBACK:]
            except json.JSONDecodeError:
                return []

    def analyze(self):
        domain_usage = Counter()
        for entry in self.goal_data:
            goal = entry.get("goal", {})
            domain = goal.get("target_domain")
            if domain:
                domain_usage[domain] += 1

        total_goals = sum(domain_usage.values())
        suggested_gaps = []

        for domain, count in domain_usage.items():
            if self.knowledge_data.get(domain, 0) < MIN_KNOWLEDGE_ENTRIES:
                relative = count / total_goals if total_goals else 0
                if relative >= GAP_THRESHOLD:
                    suggested_gaps.append({
                        "domain": domain,
                        "goal_frequency": count,
                        "knowledge_entries": self.knowledge_data.get(domain, 0),
                        "suggestion": f"Potrebna distilacija v domeni '{domain}'",
                        "timestamp": datetime.utcnow().isoformat()
                    })

        self.report = suggested_gaps
        self.save()
        return self.report

    def save(self):
        with open(GAP_LOG, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

gap_finder_instance = CognitiveGapFinder()

def hook():
    return gap_finder_instance.analyze()
