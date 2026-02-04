# plugins/agent_diagnostics_exporter.py

import os
import json
from pathlib import Path
from datetime import datetime

AGENTS_DIR = "agents/"
EXPORT_DIR = "exports/diagnostics/"
EXPORT_FILE = "agent_diagnostics_snapshot.json"
PROFILE_FILENAME = "profile.json"
EXPORT_FIELDS = [
    "agent_id", "status", "uptime", "last_goal", "last_score",
    "spawn_time", "model_version", "core_type", "energy_state",
    "active_threads", "execution_count"
]

class AgentDiagnosticsExporter:
    def __init__(self):
        self.export_dir = Path(EXPORT_DIR)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.export_path = self.export_dir / EXPORT_FILE

    def load_profile(self, agent_path):
        profile_path = agent_path / PROFILE_FILENAME
        if not profile_path.exists():
            return None

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return None

        diagnostics = {
            "agent_id": agent_path.name,
            "timestamp": datetime.utcnow().isoformat()
        }

        for field in EXPORT_FIELDS:
            if field in data:
                diagnostics[field] = data[field]

        return diagnostics

    def export_all(self):
        diagnostics_report = []

        for agent_folder in Path(AGENTS_DIR).glob("agent_*"):
            if agent_folder.is_dir():
                entry = self.load_profile(agent_folder)
                if entry:
                    diagnostics_report.append(entry)

        self.save(diagnostics_report)
        return diagnostics_report

    def save(self, data):
        with open(self.export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

diagnostic_exporter_instance = AgentDiagnosticsExporter()

def hook():
    return diagnostic_exporter_instance.export_all()
