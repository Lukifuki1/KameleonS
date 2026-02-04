# plugins/agent_dependency_mapper.py

import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

INTERACTION_LOG = "logs/goal_score_success.json"
DEPENDENCY_MAP_PATH = "logs/agent_dependency_map.json"
MIN_DEPENDENCY_COUNT = 2  # prag za zanesljivo povezavo

class AgentDependencyMapper:
    def __init__(self):
        self.interactions = self.load_log()
        self.dependencies = defaultdict(lambda: defaultdict(int))

    def load_log(self):
        path = Path(INTERACTION_LOG)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def extract_dependencies(self):
        for entry in self.interactions:
            agent = entry.get("agent")
            used = entry.get("used_agents", [])  # mora biti seznam ID-jev

            if not agent or not isinstance(used, list):
                continue

            for target in used:
                if target != agent:
                    self.dependencies[agent][target] += 1

    def finalize_map(self):
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "edges": []
        }

        for agent, targets in self.dependencies.items():
            for target, count in targets.items():
                if count >= MIN_DEPENDENCY_COUNT:
                    result["edges"].append({
                        "source": agent,
                        "target": target,
                        "weight": count
                    })

        return result

    def save(self, data):
        with open(DEPENDENCY_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def run(self):
        self.extract_dependencies()
        result = self.finalize_map()
        self.save(result)
        return result

mapper_instance = AgentDependencyMapper()

def hook():
    return mapper_instance.run()
