# plugins/evolution_mirroring_archiver.py

import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

EVOLUTION_LOG = "logs/evolution_dag_archive.json"
AGENT_HISTORY_PATH = "data/agent_history/"
MAX_HISTORY_ENTRIES = 500

class EvolutionMirroringArchiver:
    def __init__(self):
        self.archive_path = Path(EVOLUTION_LOG)
        self.evolution_dag = defaultdict(list)
        self.load_existing()

    def load_existing(self):
        if self.archive_path.exists():
            with open(self.archive_path, "r", encoding="utf-8") as f:
                try:
                    raw = json.load(f)
                    self.evolution_dag = defaultdict(list, raw)
                except json.JSONDecodeError:
                    self.evolution_dag = defaultdict(list)

    def save(self):
        with open(self.archive_path, "w", encoding="utf-8") as f:
            json.dump(self.evolution_dag, f, indent=2, ensure_ascii=False)

    def hash_state(self, state_obj):
        encoded = json.dumps(state_obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def track_agent(self, agent_id):
        agent_dir = Path(AGENT_HISTORY_PATH) / agent_id
        if not agent_dir.exists() or not agent_dir.is_dir():
            return

        snapshots = sorted(agent_dir.glob("*.json"))
        snapshots = snapshots[-MAX_HISTORY_ENTRIES:]  # Omeji na zadnje vnose

        last_hash = None

        for snap_path in snapshots:
            with open(snap_path, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f)
                except json.JSONDecodeError:
                    continue

            node = {
                "timestamp": datetime.utcnow().isoformat(),
                "file": str(snap_path.name),
                "state_hash": self.hash_state(state)
            }

            if last_hash:
                node["from"] = last_hash

            self.evolution_dag[agent_id].append(node)
            last_hash = node["state_hash"]

    def track_all_agents(self):
        agent_dirs = [p.name for p in Path(AGENT_HISTORY_PATH).glob("agent_*") if p.is_dir()]
        for agent_id in agent_dirs:
            self.track_agent(agent_id)
        self.save()
        return dict(self.evolution_dag)

archiver_instance = EvolutionMirroringArchiver()

def hook():
    return archiver_instance.track_all_agents()
