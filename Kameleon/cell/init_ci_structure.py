import os
from pathlib import Path

BASE = Path.cwd()
os.makedirs(BASE / "tests", exist_ok=True)
os.makedirs(BASE / "scripts", exist_ok=True)

(Path("requirements-dev.txt")).write_text(
    """\
black
ruff
mypy
pytest
bandit
safety
vulture
"""
)

(Path("scripts/check_all.sh")).write_text(
    """\
#!/bin/bash

echo "[1/6] Format (black)..."
black --check .

echo "[2/6] Lint (ruff)..."
ruff .

echo "[3/6] Type check (mypy)..."
mypy system/

echo "[4/6] Run tests (pytest)..."
pytest tests/

echo "[5/6] Varnostna analiza (bandit)..."
bandit -r system/ -ll

echo "[6/6] Odvisnosti (safety)..."
safety check
"""
)
os.chmod("scripts/check_all.sh", 0o755)

(Path("tests/test_models.py")).write_text(
    """\
from system.orchestrator_shared import register_all_models, MODEL_REGISTRY

def test_model_registration():
    register_all_models()
    assert len(MODEL_REGISTRY) > 0, "Noben model ni bil naložen"
"""
)

(Path("tests/test_agents.py")).write_text(
    """\
from system.kameleon import spawn_agent, AGENTS

def test_spawn_agent():
    spawn_agent("test_agent")
    assert "test_agent" in AGENTS
"""
)

(Path("tests/test_topology.py")).write_text(
    """\
import json
from pathlib import Path

def test_topology_file():
    topo_file = Path("agents/topology.json")
    assert topo_file.exists(), "topology.json manjka"
    data = json.loads(topo_file.read_text())
    for entry in data:
        assert "name" in entry and "path" in entry
"""
)

(Path("tests/test_vm.py")).write_text(
    """\
from system.kameleon import VM_IMAGES, is_port_free

def test_vm_ports():
    for name, port in VM_IMAGES.items():
        assert is_port_free(port), f"Port {port} za VM {name} je zaseden"
"""
)

(Path("tests/test_hash.py")).write_text(
    """\
from system.kameleon import hash_model_file
from pathlib import Path

def test_hash_consistency():
    dummy = Path("requirements-dev.txt")
    h1 = hash_model_file(dummy)
    h2 = hash_model_file(dummy)
    assert h1 == h2, "Hash funkcija ni deterministična"
"""
)

print("✅ CI struktura ustvarjena. Nadaljuj z:")
print("   pip install -r requirements-dev.txt")
print("   bash scripts/check_all.sh")
