# agent_communication_logger.py

import json
import time
from collections import defaultdict
from datetime import datetime

COMM_LOG_PATH = "logs/agent_communication_log.json"

class AgentCommunicationLogger:
    def __init__(self):
        self.links = defaultdict(lambda: defaultdict(int))
        self.events = []

    def register_signal(self, sender_id, receiver_id):
        if sender_id == receiver_id:
            return
        self.links[sender_id][receiver_id] += 1
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "from": sender_id,
            "to": receiver_id
        })

    def export_log(self):
        communication_matrix = []
        for sender, receivers in self.links.items():
            for receiver, count in receivers.items():
                communication_matrix.append({
                    "from": sender,
                    "to": receiver,
                    "count": count
                })

        with open(COMM_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "matrix": communication_matrix,
                "events": self.events
            }, f, indent=2, ensure_ascii=False)

logger_instance = AgentCommunicationLogger()

def hook(sender_id, receiver_id):
    logger_instance.register_signal(sender_id, receiver_id)

def flush():
    logger_instance.export_log()
