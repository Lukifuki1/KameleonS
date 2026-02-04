# plugins/meta_dashboard_feed.py

import os
import json
from pathlib import Path
from datetime import datetime

LOG_DIR = "logs/"
DASHBOARD_OUTPUT = "exports/meta_dashboard_feed.json"
INCLUDE_EXT = [".json"]
EXCLUDE_FILES = [
    "meta_dashboard_feed.json"
]

class MetaDashboardFeed:
    def __init__(self):
        self.log_dir = Path(LOG_DIR)
        self.output_path = Path(DASHBOARD_OUTPUT)
        self.snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "logs": {}
        }

    def collect_logs(self):
        for file in self.log_dir.glob("*.json"):
            if file.name in EXCLUDE_FILES:
                continue
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    self.snapshot["logs"][file.name] = {
                        "entries": len(content) if isinstance(content, list) else 1,
                        "last_modified": datetime.utcfromtimestamp(file.stat().st_mtime).isoformat()
                    }
            except Exception:
                self.snapshot["logs"][file.name] = {
                    "entries": 0,
                    "error": "Failed to read or parse"
                }

    def write_snapshot(self):
        output_dir = self.output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self.snapshot, f, indent=2, ensure_ascii=False)

    def run(self):
        self.collect_logs()
        self.write_snapshot()
        return self.snapshot

dashboard_feed_instance = MetaDashboardFeed()

def hook():
    return dashboard_feed_instance.run()
