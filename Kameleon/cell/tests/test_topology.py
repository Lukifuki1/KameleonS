import json
from pathlib import Path


def test_topology_file():
    topo_file = Path("agents/topology.json")
    assert topo_file.exists(), "topology.json manjka"
    data = json.loads(topo_file.read_text())
    for entry in data:
        assert "name" in entry and "path" in entry
