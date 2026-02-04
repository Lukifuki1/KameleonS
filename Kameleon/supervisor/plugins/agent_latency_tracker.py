# plugins/agent_latency_tracker.py

import time
import json
from datetime import datetime
from pathlib import Path

AGENT_SOCKET_DIR = "sockets/"
LATENCY_LOG = "logs/agent_latency_log.json"
TIMEOUT_SECONDS = 5
PING_PAYLOAD = {"ping": True}
PING_COMMAND = "latency_ping"

class AgentLatencyTracker:
    def __init__(self):
        self.latency_data = {}
        self.log_path = Path(LATENCY_LOG)
        self.ensure_log_exists()

    def ensure_log_exists(self):
        if not self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def ping_agent(self, agent_id):
        socket_path = Path(AGENT_SOCKET_DIR) / f"{agent_id}.sock"
        if not socket_path.exists():
            return None, "Socket not found"

        import socket
        try:
            start = time.time()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(TIMEOUT_SECONDS)
                s.connect(str(socket_path))
                s.sendall(json.dumps(PING_PAYLOAD).encode("utf-8"))
                s.recv(1)  # expecting any minimal valid response
            end = time.time()
            latency = round((end - start) * 1000, 2)  # v ms
            return latency, None
        except Exception as e:
            return None, str(e)

    def track_all_agents(self):
        results = []
        for sock_file in Path(AGENT_SOCKET_DIR).glob("agent_*.sock"):
            agent_id = sock_file.stem
            latency, error = self.ping_agent(agent_id)
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent_id,
                "latency_ms": latency,
                "error": error
            }
            results.append(record)

        self.append_log(results)
        return results

    def append_log(self, records):
        with open(self.log_path, "r+", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
            logs.extend(records)
            f.seek(0)
            json.dump(logs, f, indent=2, ensure_ascii=False)
            f.truncate()

tracker_instance = AgentLatencyTracker()

def hook():
    return tracker_instance.track_all_agents()
