# plugins/inference_chain_auditor.py

import json
from pathlib import Path
from datetime import datetime

CHAIN_LOG = "logs/inference_chains.json"
AUDIT_LOG = "logs/inference_chain_audit_report.json"
DEPTH_THRESHOLD = 5  # prag za zaznavo preglobokih verig

class InferenceChainAuditor:
    def __init__(self):
        self.chain_data = self.load_chain_data()
        self.report = []

    def load_chain_data(self):
        path = Path(CHAIN_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def analyze(self):
        for entry in self.chain_data:
            agent = entry.get("agent")
            chain = entry.get("inference_chain", [])
            depth = len(chain)

            if depth > DEPTH_THRESHOLD:
                self.report.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": agent,
                    "depth": depth,
                    "chain": chain,
                    "indicator": "deep_inference_chain"
                })

        self.save()
        return self.report

    def save(self):
        with open(AUDIT_LOG, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

auditor_instance = InferenceChainAuditor()

def hook():
    return auditor_instance.analyze()
