# plugins/epistemic_redundancy_eliminator.py

import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

KNOWLEDGE_DIR = "knowledge_bank/"
REDUNDANCY_LOG = "logs/epistemic_redundancy_report.json"
SIMILARITY_THRESHOLD = 0.85

class EpistemicRedundancyEliminator:
    def __init__(self):
        self.entries = []
        self.redundant_pairs = []

    def normalize_text(self, text):
        text = re.sub(r'\W+', ' ', text.lower()).strip()
        return text

    def jaccard_similarity(self, a, b):
        set_a = set(self.normalize_text(a).split())
        set_b = set(self.normalize_text(b).split())
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    def load_knowledge(self):
        pathlist = Path(KNOWLEDGE_DIR).rglob("*.json")
        for path in pathlist:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            if "concept" in entry and "content" in entry:
                                self.entries.append({
                                    "path": str(path),
                                    "concept": entry["concept"],
                                    "content": entry["content"]
                                })
                    elif isinstance(data, dict):
                        if "concept" in data and "content" in data:
                            self.entries.append({
                                "path": str(path),
                                "concept": data["concept"],
                                "content": data["content"]
                            })
            except Exception:
                continue

    def detect_redundancy(self):
        checked = set()
        for i in range(len(self.entries)):
            for j in range(i + 1, len(self.entries)):
                key = (i, j)
                if key in checked:
                    continue
                a = self.entries[i]
                b = self.entries[j]
                if a["concept"] == b["concept"]:
                    continue  # skip same concept
                sim = self.jaccard_similarity(a["content"], b["content"])
                if sim >= SIMILARITY_THRESHOLD:
                    self.redundant_pairs.append({
                        "concept_a": a["concept"],
                        "concept_b": b["concept"],
                        "similarity": round(sim, 4),
                        "source_a": a["path"],
                        "source_b": b["path"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "action": "suggest_merge"
                    })
                checked.add(key)

    def save(self):
        path = Path(REDUNDANCY_LOG)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.redundant_pairs, f, indent=2, ensure_ascii=False)

    def run(self):
        self.load_knowledge()
        self.detect_redundancy()
        self.save()
        return self.redundant_pairs

eliminator_instance = EpistemicRedundancyEliminator()

def hook():
    return eliminator_instance.run()
