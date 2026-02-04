from system.kameleon import AGENT_QUEUES, spawn_agent


def test_spawn_agent():
    spawn_agent("test_agent")
    assert "test_agent" in AGENT_QUEUES
