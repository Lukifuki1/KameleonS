plugins/agent_skill_manifest.py

import json
import os
from pathlib import Path
from datetime import datetime

AGENT_DIR = "agents/"
SKILL_LOG_PATH = "logs/agent_skill_manifest.json"
MANIFEST_KEYS = ["skills", "capabilities", "functions", "tools", "strategies", "modules"]
SCAN_INTERVAL = 60  # sekund, če bo scheduler želel klicati periodično

class AgentSkillManifest:
    def __init__(self):
        self.manifest = {}
        self.agent_paths = list(Path(AGENT_DIR).glob("agent_*/profile.json"))

    def extract_skills(self, agent_profile_path):
        try:
            with open(agent_profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            skills = []

            for key in MANIFEST_KEYS:
                if key in profile and isinstance(profile[key], list):
                    skills.extend(profile[key])

            return list(set(skills))
        except Exception:
            return []

    def build_manifest(self):
        result = {}
        now = datetime.utcnow().isoformat()

        for path in self.agent_paths:
            agent_id = path.parts[-2]  # e.g., agent_01
            skills = self.extract_skills(path)
            result[agent_id] = {
                "skills": skills,
                "timestamp": now
            }

        self.manifest = result
        self.save_manifest()

    def save_manifest(self):
        with open(SKILL_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

    def get_manifest(self):
        return self.manifest

manifest_instance = AgentSkillManifest()

def hook():
    manifest_instance.build_manifest()
