# task_dispatch_auditor.py

import json
import time
from datetime import datetime

DISPATCH_LOG_PATH = "logs/task_dispatch_log.json"

class TaskDispatchAuditor:
    def __init__(self):
        self.dispatches = []

    def record_dispatch(self, task_id, agent_id):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "agent_id": agent_id
        }
        self.dispatches.append(entry)

    def export_log(self):
        with open(DISPATCH_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.dispatches, f, indent=2, ensure_ascii=False)

auditor_instance = TaskDispatchAuditor()

def hook(task_id, agent_id):
    auditor_instance.record_dispatch(task_id, agent_id)

def flush():
    auditor_instance.export_log()
