import json
import time
from datetime import datetime
from pathlib import Path

import faiss  # type: ignore
from elixir_extractor import elixir_count
from loguru import logger
from orchestrator_shared import (
    AGENTS,
    FAISS_INDEX_FILE,
    FALLBACK_MODE,
    SAFE_MODE,
    STOP_EVENT,
    knowledge_bank,
    knowledge_lock,
)
from sis import CONSISTENCY_INDEX, IMMUNE_MEMORY, QUARANTINE

from agents.goal_score import export_top_k

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


DASHBOARD_OUTPUT = Path("data/system_dashboard.json")


def get_safe_mode_status():
    return {
        "safe_mode": SAFE_MODE.is_set(),
        "fallback_mode": FALLBACK_MODE.is_set(),
        "stop_event": STOP_EVENT.is_set(),
    }


def get_agent_status():
    return {
        "total_agents": len(AGENTS),
        "active_agents": sum(1 for a in AGENTS.values() if a.is_alive()),
        "agent_ids": list(AGENTS.keys()),
    }


def get_knowledge_status():
    with knowledge_lock:
        kb_snapshot = list(knowledge_bank)
    return {
        "knowledge_bank_size": len(kb_snapshot),
        "knowledge_bank_preview": kb_snapshot[-5:] if kb_snapshot else [],
    }


def get_elixir_status():
    return {"elixir_count": elixir_count()}


def get_goal_score_status():
    top = export_top_k(k=5)
    return {
        "top_goals": [
            {"score": round(entry["score"], 4), "text": entry["text"][:120]}
            for entry in top
        ]
    }


def get_sis_status():
    return {
        "quarantine_size": len(QUARANTINE),
        "immune_memory_size": len(IMMUNE_MEMORY),
        "consistency_index_size": len(CONSISTENCY_INDEX),
    }


def get_faiss_status():
    if not FAISS_INDEX_FILE.exists():
        return {"faiss_index": "not found"}

    try:
        import faiss

        index = faiss.read_index(str(FAISS_INDEX_FILE))
        return {
            "faiss_index": "available",
            "faiss_vectors": index.ntotal,
            "faiss_dimensions": index.d if hasattr(index, "d") else "unknown",
        }
    except Exception as e:
        logger.warning(f"DASHBOARD: FAISS napaka: {e}")
        return {"faiss_index": "error", "error": str(e)}


def collect_dashboard_data():
    timestamp = datetime.utcnow().isoformat()
    return {
        "timestamp": timestamp,
        "safe_mode": get_safe_mode_status(),
        "agents": get_agent_status(),
        "knowledge": get_knowledge_status(),
        "elixir": get_elixir_status(),
        "goal_score": get_goal_score_status(),
        "sis": get_sis_status(),
        "faiss": get_faiss_status(),
    }


def save_dashboard(data: dict):
    try:
        DASHBOARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        DASHBOARD_OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("DASHBOARD: stanje sistema zapisano v dashboard")
    except Exception as e:
        logger.error(f"DASHBOARD: napaka pri shranjevanju: {e}")


def main_loop(interval_sec=60):
    logger.info("DASHBOARD: zagon nadzorne zanke")
    try:
        while not STOP_EVENT.is_set():
            data = collect_dashboard_data()
            save_dashboard(data)
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        logger.info("DASHBOARD: prekinjeno ročno (CTRL+C)")
    except Exception as e:
        logger.critical(f"DASHBOARD: fatala napaka: {e}")


if __name__ == "__main__":
    main_loop()
