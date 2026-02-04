# meta_stability_tracker.py

import json
import hashlib
from collections import defaultdict
from datetime import datetime

STABILITY_LOG_PATH = "logs/meta_stability_matrix.json"

class MetaStabilityTracker:
    def __init__(self):
        self.matrix = defaultdict(lambda: {"success": 0, "failure": 0})

    def encode_configuration(self, agent_ids, state_signature):
        agents_key = ",".join(sorted(agent_ids))
        full_signature = f"{agents_key}|{state_signature}"
        return hashlib.sha256(full_signature.encode("utf-8")).hexdigest()

    def record_outcome(self, agent_ids, state_signature, success):
        config_hash = self.encode_configuration(agent_ids, state_signature)
        if success:
            self.matrix[config_hash]["success"] += 1
        else:
            self.matrix[config_hash]["failure"] += 1

    def export_matrix(self):
        result = []
        for config_hash, stats in self.matrix.items():
            total = stats["success"] + stats["failure"]
            stability_score = round(stats["success"] / total, 4) if total > 0 else 0
            result.append({
                "configuration_hash": config_hash,
                "success": stats["success"],
                "failure": stats["failure"],
                "total": total,
                "stability_score": stability_score
            })
        with open(STABILITY_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "matrix": result
            }, f, indent=2, ensure_ascii=False)

tracker_instance = MetaStabilityTracker()

def hook(agent_ids, state_signature, success: bool):
    tracker_instance.record_outcome(agent_ids, state_signature, success)

def flush():
    tracker_instance.export_matrix()
