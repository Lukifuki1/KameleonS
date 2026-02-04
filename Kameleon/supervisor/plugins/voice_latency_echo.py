# voice_latency_echo.py

import json
import time
import uuid
from datetime import datetime

VOICE_LATENCY_LOG_PATH = "logs/voice_latency_log.json"

class VoiceLatencyEcho:
    def __init__(self):
        self.pings = []

    def send_ping(self):
        ping_id = str(uuid.uuid4())
        timestamp = time.time()
        self.pings.append({
            "id": ping_id,
            "sent_at": timestamp,
            "status": "pending"
        })
        return ping_id, timestamp

    def receive_echo(self, ping_id):
        received_time = time.time()
        for ping in self.pings:
            if ping["id"] == ping_id and ping["status"] == "pending":
                ping["received_at"] = received_time
                ping["latency"] = round(received_time - ping["sent_at"], 4)
                ping["status"] = "responded"
                break

    def export_log(self):
        log_ready = [
            {
                "id": ping["id"],
                "sent_at": datetime.utcfromtimestamp(ping["sent_at"]).isoformat(),
                "received_at": datetime.utcfromtimestamp(ping["received_at"]).isoformat() if "received_at" in ping else None,
                "latency": ping.get("latency"),
                "status": ping["status"]
            }
            for ping in self.pings if ping["status"] == "responded"
        ]
        with open(VOICE_LATENCY_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log_ready, f, indent=2, ensure_ascii=False)

echo_instance = VoiceLatencyEcho()

def send_echo():
    return echo_instance.send_ping()

def receive_echo(ping_id):
    echo_instance.receive_echo(ping_id)

def flush():
    echo_instance.export_log()
