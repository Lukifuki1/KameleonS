# goal_queue_monitor.py

import json
import time
from datetime import datetime

GOAL_LOG_PATH = "logs/goal_queue_log.json"

class GoalQueueMonitor:
    def __init__(self):
        self.queue = {}
        self.history = []

    def register_goal(self, goal_id, agent_id):
        self.queue[goal_id] = {
            "agent": agent_id,
            "registered_at": time.time(),
            "status": "pending"
        }

    def complete_goal(self, goal_id):
        if goal_id in self.queue:
            entry = self.queue.pop(goal_id)
            entry["completed_at"] = time.time()
            entry["status"] = "completed"
            entry["duration"] = round(entry["completed_at"] - entry["registered_at"], 3)
            self.history.append(entry)

    def reject_goal(self, goal_id):
        if goal_id in self.queue:
            entry = self.queue.pop(goal_id)
            entry["rejected_at"] = time.time()
            entry["status"] = "rejected"
            entry["duration"] = round(entry["rejected_at"] - entry["registered_at"], 3)
            self.history.append(entry)

    def export_log(self):
        with open(GOAL_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "completed": [h for h in self.history if h["status"] == "completed"],
                "rejected": [h for h in self.history if h["status"] == "rejected"],
                "pending": list(self.queue.values())
            }, f, indent=2, ensure_ascii=False)

monitor_instance = GoalQueueMonitor()

def hook_register(goal_id, agent_id):
    monitor_instance.register_goal(goal_id, agent_id)

def hook_complete(goal_id):
    monitor_instance.complete_goal(goal_id)

def hook_reject(goal_id):
    monitor_instance.reject_goal(goal_id)

def flush():
    monitor_instance.export_log()
