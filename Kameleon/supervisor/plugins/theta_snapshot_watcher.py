# theta_snapshot_watcher.py

import json
import hashlib
import os
from datetime import datetime
from deepdiff import DeepDiff

THETA_PATH = "data/theta.json"
SNAPSHOT_LOG_PATH = "logs/theta_change_log.json"

class ThetaSnapshotWatcher:
    def __init__(self):
        self.last_hash = None
        self.last_snapshot = {}
        self.log = []
        self.load_last_snapshot()

    def load_last_snapshot(self):
        if not os.path.exists(THETA_PATH):
            return
        with open(THETA_PATH, "r", encoding="utf-8") as f:
            self.last_snapshot = json.load(f)
        self.last_hash = self.hash_snapshot(self.last_snapshot)

    def hash_snapshot(self, data):
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def detect_change(self):
        if not os.path.exists(THETA_PATH):
            return
        with open(THETA_PATH, "r", encoding="utf-8") as f:
            current = json.load(f)

        current_hash = self.hash_snapshot(current)

        if current_hash != self.last_hash:
            delta = DeepDiff(self.last_snapshot, current, ignore_order=True).to_dict()
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "hash": current_hash,
                "delta": delta
            }
            self.log.append(entry)
            self.last_snapshot = current
            self.last_hash = current_hash
            self.save_log()

    def save_log(self):
        with open(SNAPSHOT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.log, f, indent=2, ensure_ascii=False)

watcher_instance = ThetaSnapshotWatcher()

def hook():
    watcher_instance.detect_change()
