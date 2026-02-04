# audit_log_merger.py

import json
import os
from datetime import datetime

LOG_DIRECTORIES = [
    "logs/",  # glavna mapa z log datotekami
]
LOG_EXTENSION = ".json"
MERGED_LOG_PATH = "logs/audit_merged_log.json"

class AuditLogMerger:
    def __init__(self):
        self.entries = []

    def collect_logs(self):
        for directory in LOG_DIRECTORIES:
            for filename in os.listdir(directory):
                if filename.endswith(LOG_EXTENSION) and filename != os.path.basename(MERGED_LOG_PATH):
                    filepath = os.path.join(directory, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                self.entries.extend(data)
                            elif isinstance(data, dict):
                                self.entries.append(data)
                    except Exception:
                        continue  # preskoči poškodovane ali neveljavne datoteke

    def export_merged_log(self):
        merged = {
            "timestamp": datetime.utcnow().isoformat(),
            "entry_count": len(self.entries),
            "log": self.entries
        }
        with open(MERGED_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)

merger_instance = AuditLogMerger()

def hook():
    merger_instance.collect_logs()

def flush():
    merger_instance.export_merged_log()
