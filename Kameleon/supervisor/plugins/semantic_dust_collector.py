# plugins/semantic_dust_collector.py

import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

KNOWLEDGE_DIR = "knowledge_bank/"
GOAL_LOG = "logs/goal_score_success.json"
DUST_REPORT = "logs/semantic_dust_report.json"
USAGE_WINDOW = 200
MIN_REFERENCES = 0  # če entiteta ni bila uporabljena v zadnjih N vnosih

class SemanticDustCollector:
    def __init__(self):
        self.knowledge_index = self.index_knowledge()
        self.recent_usage = self.collect_recent_usage()
        self.dust = []

    def index_knowledge(self):
        concept_counter = Counter()
        pathlist = Path(KNOWLEDGE_DIR).rglob("*.json")

        for path in pathlist:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            concept = entry.get("concept")
                            if concept:
                                concept_counter[concept] += 1
                    elif isinstance(data, dict):
                        concept = data.get("concept")
                        if concept:
                            concept_counter[concept] += 1
            except Exception:
                continue

        return concept_counter

    def collect_recent_usage(self):
        path = Path(GOAL_LOG)
        usage_counter = Counter()

        if not path.exists():
            return usage_counter

        with open(path, "r", encoding="utf-8") as f:
            try:
                entries = json.load(f)[-USAGE_WINDOW:]
            except json.JSONDecodeError:
                return usage_counter

        for entry in entries:
            goal = entry.get("goal", {})
            text = json.dumps(goal, ensure_ascii=False).lower()
            for concept in self.knowledge_index:
                if concept.lower() in text:
                    usage_counter[concept] += 1

        return usage_counter

    def identify_dust(self):
        for concept, count in self.knowledge_index.items():
            if self.recent_usage.get(concept, 0) <= MIN_REFERENCES:
                self.dust.append({
                    "concept": concept,
                    "knowledge_entries": count,
                    "recent_references": self.recent_usage.get(concept, 0),
                    "timestamp": datetime.utcnow().isoformat()
                })

    def save(self):
        with open(DUST_REPORT, "w", encoding="utf-8") as f:
            json.dump(self.dust, f, indent=2, ensure_ascii=False)

    def run(self):
        self.identify_dust()
        self.save()
        return self.dust

collector_instance = SemanticDustCollector()

def hook():
    return collector_instance.run()
