# contradiction_listener.py

import json
import hashlib
from datetime import datetime
from collections import defaultdict

CONTRADICTION_LOG_PATH = "logs/ontological_contradictions_log.json"

class ContradictionListener:
    def __init__(self):
        self.statements = defaultdict(set)
        self.contradictions = []

    def normalize(self, statement: str):
        return ' '.join(statement.strip().lower().split())

    def hash_concept(self, concept: str):
        return hashlib.sha256(self.normalize(concept).encode("utf-8")).hexdigest()

    def register_statement(self, agent_id, concept, claim: bool):
        concept_key = self.hash_concept(concept)
        claim_str = "affirmed" if claim else "denied"

        if claim_str in self.statements[concept_key]:
            return  # no conflict if same claim already exists

        opposite = "denied" if claim else "affirmed"
        if opposite in self.statements[concept_key]:
            self.log_contradiction(agent_id, concept, claim)

        self.statements[concept_key].add(claim_str)

    def log_contradiction(self, agent_id, concept, new_claim):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "concept": concept,
            "new_claim": "affirmed" if new_claim else "denied",
            "conflict_detected": True
        }
        self.contradictions.append(entry)

    def export_log(self):
        with open(CONTRADICTION_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.contradictions, f, indent=2, ensure_ascii=False)

listener_instance = ContradictionListener()

def hook(agent_id, concept, claim: bool):
    listener_instance.register_statement(agent_id, concept, claim)

def flush():
    listener_instance.export_log()
