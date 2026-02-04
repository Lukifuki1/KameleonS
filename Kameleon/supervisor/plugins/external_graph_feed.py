# external_graph_feed.py

import json
import time
import uuid
from datetime import datetime

GRAPH_FEED_PATH = "logs/external_graph_feed.json"

class ExternalGraphFeed:
    def __init__(self):
        self.feed = []

    def emit_event(self, source_id, target_id, event_type, weight=1):
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source": source_id,
            "target": target_id,
            "type": event_type,
            "weight": weight
        }
        self.feed.append(entry)

    def export_feed(self):
        with open(GRAPH_FEED_PATH, "w", encoding="utf-8") as f:
            json.dump(self.feed, f, indent=2, ensure_ascii=False)

feed_instance = ExternalGraphFeed()

def hook(source_id, target_id, event_type, weight=1):
    feed_instance.emit_event(source_id, target_id, event_type, weight)

def flush():
    feed_instance.export_feed()
