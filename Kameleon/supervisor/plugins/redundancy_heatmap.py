# redundancy_heatmap.py

import json
import hashlib
from collections import defaultdict
from datetime import datetime

HEATMAP_LOG_PATH = "logs/redundancy_heatmap_log.json"

class RedundancyHeatmap:
    def __init__(self):
        self.fingerprint_map = defaultdict(list)
        self.heatmap = []

    def normalize_strategy(self, content):
        return ' '.join(content.strip().lower().split())

    def fingerprint(self, content):
        normalized = self.normalize_strategy(content)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def analyze_strategy(self, strategy_id, content):
        fp = self.fingerprint(content)
        self.fingerprint_map[fp].append(strategy_id)

    def generate_heatmap(self):
        self.heatmap.clear()
        for fp, strategy_ids in self.fingerprint_map.items():
            if len(strategy_ids) > 1:
                self.heatmap.append({
                    "hash": fp,
                    "duplicates": strategy_ids,
                    "count": len(strategy_ids)
                })

    def export_heatmap(self):
        self.generate_heatmap()
        with open(HEATMAP_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "redundant_sets": self.heatmap
            }, f, indent=2, ensure_ascii=False)

heatmap_instance = RedundancyHeatmap()

def hook(strategy_id, strategy_content):
    heatmap_instance.analyze_strategy(strategy_id, strategy_content)

def flush():
    heatmap_instance.export_heatmap()
