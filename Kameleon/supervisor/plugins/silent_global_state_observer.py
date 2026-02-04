# silent_global_state_observer.py

import json
import time
from datetime import datetime

GLOBAL_STATE_LOG_PATH = "logs/global_state_snapshot.json"

class SilentGlobalStateObserver:
    def __init__(self):
        self.snapshots = []

    def capture_state(self, system_state):
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "state": system_state
        }
        self.snapshots.append(snapshot)

    def export_log(self):
        with open(GLOBAL_STATE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.snapshots, f, indent=2, ensure_ascii=False)

observer_instance = SilentGlobalStateObserver()

def hook(system_state):
    observer_instance.capture_state(system_state)

def flush():
    observer_instance.export_log()
