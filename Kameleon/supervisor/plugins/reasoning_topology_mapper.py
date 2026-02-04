# reasoning_topology_mapper.py

import json
import time
from collections import defaultdict
from datetime import datetime

TOPOLOGY_LOG_PATH = "logs/reasoning_topology_graph.json"

class ReasoningTopologyMapper:
    def __init__(self):
        self.graph = defaultdict(lambda: defaultdict(int))
        self.last_nodes = {}

    def observe_transition(self, agent_id, from_node, to_node):
        if not from_node or not to_node or from_node == to_node:
            return
        self.graph[(agent_id, from_node)][to_node] += 1
        self.last_nodes[agent_id] = to_node

    def export_graph(self):
        serializable = []
        for (agent_id, from_node), targets in self.graph.items():
            for to_node, weight in targets.items():
                serializable.append({
                    "agent": agent_id,
                    "from": from_node,
                    "to": to_node,
                    "count": weight
                })
        with open(TOPOLOGY_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "edges": serializable
            }, f, indent=2, ensure_ascii=False)

mapper_instance = ReasoningTopologyMapper()

def hook(agent_id, reasoning_step):
    from_node = reasoning_step.get("from")
    to_node = reasoning_step.get("to")
    mapper_instance.observe_transition(agent_id, from_node, to_node)

def flush():
    mapper_instance.export_graph()
