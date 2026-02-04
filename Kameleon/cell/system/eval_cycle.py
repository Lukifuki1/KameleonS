import faiss  # type: ignore
import numpy as np
from loguru import logger
from orchestrator_shared import (
    AGENT_QUEUES,
    FAISS_INDEX_FILE,
    knowledge_bank,
    knowledge_lock,
    sbert,
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


try:
    import faiss
except ImportError as e:
    logger.critical(f"EVAL_CYCLE: FAISS ni na voljo: {e}")
    raise SystemExit(1)

try:
    from agents.goal_score import (
        cull_low_score,
        decay_all,
        register_knowledge_entry,
        reinforce,
    )

    GOALSCORE_ENABLED = True
except Exception as e:
    logger.warning(f"GOALSCORE: modul ni na voljo: {e}")
    GOALSCORE_ENABLED = False

from sis import filter_outputs

# ======================================================
#  EVAL-CYCLE
# ======================================================


def evaluate_and_update_knowledge():
    """Ping agentov → zbiranje outputov → FAISS → dodajanje znanja → GoalScore."""
    outputs = []

    for agent_name, (qin, qout) in AGENT_QUEUES.items():
        try:
            qin.put("__ping__")
            out = qout.get(timeout=2)
            if out and isinstance(out, str):
                outputs.append(out)
        except Exception:
            logger.debug(f"EVAL_CYCLE: agent '{agent_name}' ni odgovoril.")
            continue

    if not outputs:
        logger.debug("EVAL_CYCLE: brez izhodov agentov.")
        return

    # SIS filtriranje
    outputs = filter_outputs(outputs)
    if not outputs:
        logger.debug("EVAL_CYCLE: SIS filtriral vse izhode.")
        return

    # SBERT enkodiranje
    try:
        vecs = sbert.encode(outputs, normalize_embeddings=True)
        vecs = np.asarray(vecs, dtype="float32")
    except Exception as e:
        logger.error(f"EVAL_CYCLE: napaka pri SBERT: {e}")
        return

    # FAISS indeksiranje + knowledge_bank
    try:
        with knowledge_lock:
            knowledge_bank.extend(outputs)

            if FAISS_INDEX_FILE.exists():
                try:
                    index = faiss.read_index(str(FAISS_INDEX_FILE))
                except Exception as e:
                    logger.warning(
                        f"EVAL_CYCLE: FAISS index poškodovan, ustvarjam novega: {e}"
                    )
                    index = faiss.IndexFlatIP(vecs.shape[1])
            else:
                index = faiss.IndexFlatIP(vecs.shape[1])

            index.add(vecs)
            faiss.write_index(index, str(FAISS_INDEX_FILE))

        logger.info(f"EVAL_CYCLE: dodano {len(outputs)} znanj.")
    except Exception as e:
        logger.error(f"EVAL_CYCLE: FAISS napaka: {e}")

    # GoalScore reinforcement
    if GOALSCORE_ENABLED:
        try:
            for item in outputs:
                register_knowledge_entry(item)
                reinforce(item, reward=1.0)

            decay_all()
            cull_low_score()
        except Exception as e:
            logger.error(f"GOALSCORE: napaka: {e}")
