# plugins/epistemic_trust_index.py

import json
from pathlib import Path
from datetime import datetime

GOAL_SCORE_LOG = "logs/goal_score_success.json"
EVOLUTION_DAG = "logs/evolution_dag_archive.json"
CONSISTENCY_LOG = "logs/theta_consistency_results.json"
TRUST_INDEX_LOG = "logs/epistemic_trust_index.json"

MIN_ENTRIES_REQUIRED = 5

class EpistemicTrustIndex:
    def __init__(self):
        self.trust_index = {}
        self.goal_data = self.load_json(GOAL_SCORE_LOG)
        self.evo_data = self.load_json(EVOLUTION_DAG)
        self.theta_data = self.load_json(CONSISTENCY_LOG)

    def load_json(self, path):
        file = Path(path)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def compute_for_agent(self, agent_id):
        scores = [entry["score"] for entry in self.goal_data if entry.get("agent") == agent_id and "score" in entry]
        evolutions = self.evo_data.get(agent_id, [])
        consistencies = [entry["result"] for entry in self.theta_data if entry.get("agent") == agent_id and "result" in entry]

        if len(scores) < MIN_ENTRIES_REQUIRED:
            return {"agent": agent_id, "status": "insufficient data"}

        success_score = sum(scores) / len(scores)
        stability_score = 1 - (1 / max(1, len(evolutions)))  # več transformacij → manj stabilen
        consistency_score = sum(1 for r in consistencies if r is True) / max(1, len(consistencies))

        trust = round((0.5 * success_score) + (0.25 * stability_score) + (0.25 * consistency_score), 4)

        return {
            "agent": agent_id,
            "success_score": round(success_score, 4),
            "stability_score": round(stability_score, 4),
            "consistency_score": round(consistency_score, 4),
            "trust_index": trust,
            "timestamp": datetime.utcnow().isoformat()
        }

    def compute_all(self):
        agent_ids = list(set(entry["agent"] for entry in self.goal_data if "agent" in entry))
        result = [self.compute_for_agent(agent_id) for agent_id in agent_ids]
        self.trust_index = {entry["agent"]: entry for entry in result if "trust_index" in entry}
        self.save()
        return self.trust_index

    def save(self):
        with open(TRUST_INDEX_LOG, "w", encoding="utf-8") as f:
            json.dump(self.trust_index, f, indent=2, ensure_ascii=False)

trust_calc_instance = EpistemicTrustIndex()

def hook():
    return trust_calc_instance.compute_all()
