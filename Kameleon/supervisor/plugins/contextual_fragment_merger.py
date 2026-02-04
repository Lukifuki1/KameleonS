# plugins/contextual_fragment_merger.py

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

KNOWLEDGE_SNAPSHOTS = "exports/diagnostics/agent_diagnostics_snapshot.json"
FRAGMENTS_DIR = "fragments/"
MERGED_CONTEXT_LOG = "logs/contextual_merged_fragments.json"
SIMILARITY_THRESHOLD = 0.75

class ContextualFragmentMerger:
    def __init__(self):
        self.snapshot_path = Path(KNOWLEDGE_SNAPSHOTS)
        self.fragments = defaultdict(list)
        self.merged_contexts = []

    def load_fragments(self):
        if not self.snapshot_path.exists():
            return

        with open(self.snapshot_path, "r", encoding="utf-8") as f:
            try:
                agent_profiles = json.load(f)
            except json.JSONDecodeError:
                agent_profiles = []

        for profile in agent_profiles:
            agent_id = profile.get("agent_id")
            if not agent_id:
                continue

            fragment_path = Path(FRAGMENTS_DIR) / f"{agent_id}_fragments.json"
            if not fragment_path.exists():
                continue

            try:
                with open(fragment_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.fragments[agent_id].extend(data)
            except json.JSONDecodeError:
                continue

    def similarity(self, a, b):
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    def merge_fragments(self):
        pool = []
        for agent_id, entries in self.fragments.items():
            for f in entries:
                pool.append({
                    "source_agent": agent_id,
                    "text": f.get("text", "").strip()
                })

        visited = set()

        for i, frag in enumerate(pool):
            if i in visited or not frag["text"]:
                continue

            cluster = [frag]
            visited.add(i)

            for j, other in enumerate(pool):
                if j in visited or i == j or not other["text"]:
                    continue

                if self.similarity(frag["text"], other["text"]) >= SIMILARITY_THRESHOLD:
                    cluster.append(other)
                    visited.add(j)

            if len(cluster) >= 2:
                merged_texts = [x["text"] for x in cluster]
                context = {
                    "merged_context": " | ".join(merged_texts),
                    "agents_involved": list(set(x["source_agent"] for x in cluster)),
                    "fragment_count": len(cluster),
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.merged_contexts.append(context)

    def save(self):
        path = Path(MERGED_CONTEXT_LOG)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.merged_contexts, f, indent=2, ensure_ascii=False)

    def run(self):
        self.load_fragments()
        self.merge_fragments()
        self.save()
        return self.merged_contexts

merger_instance = ContextualFragmentMerger()

def hook():
    return merger_instance.run()
