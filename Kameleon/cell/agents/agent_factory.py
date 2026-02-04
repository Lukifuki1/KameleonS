#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

from loguru import logger
from orchestrator_shared import (
    AGENT_LAST_USED,
    AGENT_QUEUES,
    AGENT_THREADS,
    AGENTS,
    assign_all_agents_threaded,
    spawn_agent,
)

ROLES_FILE = Path("/opt/cell/agents/agent_roles.json")

# ======================================================
#  ROLE LOADER
# ======================================================


def load_roles() -> list[dict]:
    if not ROLES_FILE.exists():
        logger.error(f"AGENT_FACTORY: datoteka z vlogami ne obstaja → {ROLES_FILE}")
        return []

    try:
        roles = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
        if not isinstance(roles, list):
            logger.error("AGENT_FACTORY: agent_roles.json ni seznam.")
            return []
        return roles
    except Exception as e:
        logger.error(f"AGENT_FACTORY: napaka pri branju agent_roles.json: {e}")
        return []


# ======================================================
#  SPAWN ONE AGENT
# ======================================================


def create_agent(agent_name: str, domain: str):
    if not agent_name or not domain:
        logger.warning("AGENT_FACTORY: prazno ime ali domena agenta, preskakujem.")
        return

    if agent_name in AGENTS:
        logger.warning(f"AGENT_FACTORY: agent '{agent_name}' že obstaja, preskočeno.")
        return

    try:
        spawn_agent(agent_name)
        assign_all_agents_threaded()
        logger.success(
            f"AGENT_FACTORY: agent '{agent_name}' ({domain}) ustvarjen in inicializiran."
        )
    except Exception as e:
        logger.error(
            f"AGENT_FACTORY: napaka pri ustvarjanju agenta '{agent_name}': {e}"
        )


# ======================================================
#  BOOTSTRAP ALL AGENTS
# ======================================================


def bootstrap_agents():
    roles = load_roles()
    if not roles:
        logger.error(
            "AGENT_FACTORY: ni mogoče inicializirati agentov – vloge manjkajo."
        )
        return

    logger.info(f"AGENT_FACTORY: zagon {len(roles)} agentov...")

    for entry in roles:
        name = str(entry.get("name", "")).strip()
        domain = str(entry.get("domain", "")).strip()
        create_agent(name, domain)

    logger.success("AGENT_FACTORY: vsi agenti ustvarjeni in zagnani.")


# ======================================================
#  KILL ALL
# ======================================================


def kill_all_agents():
    logger.warning("AGENT_FACTORY: zaustavljam vse agente...")

    for name, t in AGENT_THREADS.items():
        try:
            q_in, _ = AGENT_QUEUES.get(name, (None, None))
            if q_in:
                q_in.put("__shutdown__")
        except Exception as e:
            logger.error(f"AGENT_FACTORY: napaka pri zaustavitvi agenta {name}: {e}")

    AGENT_THREADS.clear()
    AGENT_QUEUES.clear()
    AGENTS.clear()
    AGENT_LAST_USED.clear()

    logger.success("AGENT_FACTORY: vsi agenti so bili uspešno zaustavljeni.")
