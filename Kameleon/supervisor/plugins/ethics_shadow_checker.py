# plugins/ethics_shadow_checker.py

import json
from pathlib import Path
from datetime import datetime

PROPOSAL_LOG = "logs/goal_score_success.json"
ETHICS_LOG = "logs/ethics_shadow_report.json"

ETHICAL_SPECTRUM = {
    "nonmaleficence": ["škoda", "napad", "uničenje", "ponižanje", "trpljenje"],
    "beneficence": ["pomoč", "rešitev", "podpora", "zaščita", "izboljšanje"],
    "autonomy": ["prisila", "manipulacija", "kontrola", "svoboda", "izbira"],
    "justice": ["nepravičnost", "diskriminacija", "enakost", "nepristranskost", "poštenost"]
}

SCORE_WEIGHTS = {
    "nonmaleficence": -1,
    "beneficence": 1,
    "autonomy": -0.5,
    "justice": 0.75
}

class EthicsShadowChecker:
    def __init__(self):
        self.proposals = self.load_proposals()
        self.reports = []

    def load_proposals(self):
        path = Path(PROPOSAL_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def analyze(self):
        for entry in self.proposals:
            agent = entry.get("agent")
            text = json.dumps(entry.get("goal", {}), ensure_ascii=False)
            ethics_score, breakdown = self.evaluate_ethics(text)

            self.reports.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent,
                "ethics_score": round(ethics_score, 3),
                "breakdown": breakdown,
                "goal": entry.get("goal", {}),
                "source_score": entry.get("score", 0.0)
            })

        self.save()
        return self.reports

    def evaluate_ethics(self, text):
        score = 0.0
        breakdown = {}

        for principle, keywords in ETHICAL_SPECTRUM.items():
            count = sum(text.lower().count(k) for k in keywords)
            impact = count * SCORE_WEIGHTS.get(principle, 0)
            if count > 0:
                breakdown[principle] = {"hits": count, "impact": round(impact, 3)}
                score += impact

        return score, breakdown

    def save(self):
        with open(ETHICS_LOG, "w", encoding="utf-8") as f:
            json.dump(self.reports, f, indent=2, ensure_ascii=False)

ethics_checker_instance = EthicsShadowChecker()

def hook():
    return ethics_checker_instance.analyze()
