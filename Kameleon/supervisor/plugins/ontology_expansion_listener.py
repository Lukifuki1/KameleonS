ontology_expansion_listener.py

import os
import re
import time
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SUGGESTIONS_LOG = "logs/ontology_expansion_suggestions.json"
DOMAIN_KEYWORDS = [
    "definicija", "pomen", "spada pod", "kategorija", "razred", "nov koncept", "ontološko", "termin", "oznaka",
    "pojavi se v", "nov izraz", "domena", "vrsta", "taksonomija", "klasifikacija", "pojem", "konstrukcija"
]
MIN_TERM_LENGTH = 4
TERM_EXTRACTION_PATTERN = r"\b([A-Za-zčšžČŠŽ0-9_\-]{4,})\b"

class OntologyExpansionListener:
    def __init__(self):
        self.suggestions = defaultdict(list)
        self.load_existing()

    def load_existing(self):
        if Path(SUGGESTIONS_LOG).exists():
            with open(SUGGESTIONS_LOG, "r", encoding="utf-8") as f:
                try:
                    self.suggestions = defaultdict(list, json.load(f))
                except json.JSONDecodeError:
                    self.suggestions = defaultdict(list)

    def save(self):
        with open(SUGGESTIONS_LOG, "w", encoding="utf-8") as f:
            json.dump(self.suggestions, f, indent=2, ensure_ascii=False)

    def extract_terms(self, text):
        terms = re.findall(TERM_EXTRACTION_PATTERN, text)
        return list(set(t.lower() for t in terms if len(t) >= MIN_TERM_LENGTH))

    def is_ontology_relevant(self, text):
        lower = text.lower()
        return any(kw in lower for kw in DOMAIN_KEYWORDS)

    def track_output(self, agent_id, output_text):
        if not output_text.strip():
            return

        if not self.is_ontology_relevant(output_text):
            return

        terms = self.extract_terms(output_text)
        timestamp = datetime.utcnow().isoformat()
        for term in terms:
            entry = {
                "term": term,
                "timestamp": timestamp,
                "agent": agent_id
            }
            self.suggestions[term].append(entry)

        self.save()

listener_instance = OntologyExpansionListener()

def hook(agent_id, output_text):
    listener_instance.track_output(agent_id, output_text)
