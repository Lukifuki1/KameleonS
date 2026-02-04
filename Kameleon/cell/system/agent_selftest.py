#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path
from subprocess import PIPE, TimeoutExpired, run

AGENT_DIR = Path("/media/4tb/Kameleon/cell/models/active")
SELFTEST_LOG = Path("/media/4tb/Kameleon/cell/logs/agent_selftest.log")


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    SELFTEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SELFTEST_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def check_agent_main(agent_path: Path) -> bool:
    main_file = agent_path / "agent.py"
    if not main_file.exists():
        log(f"[{agent_path.name}] 🛑 Manjka agent.py")
        return False
    try:
        content = main_file.read_text(encoding="utf-8", errors="ignore")
        return "def main(" in content
    except Exception as e:
        log(f"[{agent_path.name}] Napaka pri branju: {e}")
        return False


def evaluate_agent(agent_path: Path) -> bool:
    try:
        result = run(
            ["python3", str(agent_path / "agent.py")],
            stdout=PIPE,
            stderr=PIPE,
            timeout=10,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="ignore").strip()
            log(f"[{agent_path.name}] 🧨 Napaka pri izvajanju: {stderr}")
            return False
        return True
    except TimeoutExpired:
        log(f"[{agent_path.name}] ⏱️ Timeout – agent se ni odzval")
        return False
    except Exception as e:
        log(f"[{agent_path.name}] ❌ Kritična napaka: {e}")
        return False


def run_selftest():
    log("🔎 Začenjam selftest agentov...")
    total = 0
    success = 0

    for agent in AGENT_DIR.iterdir():
        if not agent.is_dir():
            continue
        total += 1
        name = agent.name
        has_main = check_agent_main(agent)
        works = evaluate_agent(agent) if has_main else False

        if not has_main:
            log(f"[{name}] ❌ Manjka funkcija main() v agent.py")
        elif not works:
            log(f"[{name}] ⚠️  Agent se ni uspešno zagnal")
        else:
            log(f"[{name}] ✅ Agent deluje pravilno")
            success += 1

    log(f"✅ Selftest zaključen: {success}/{total} agentov uspešnih.\n")


if __name__ == "__main__":
    run_selftest()
