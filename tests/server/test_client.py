"""Tests for the dynamic OpenAPI-based client SDK."""

import pytest
from machine_core.plugins.server_support.client import MachineClient


def test_client_discovers_namespaces(test_client):
    """Client auto-discovers categories from OpenAPI."""
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    assert hasattr(client, "agent")
    assert hasattr(client, "tool")
    assert hasattr(client, "workflow")
    assert hasattr(client, "memory")


def test_client_list_agents(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    agents = client.agent.list()
    assert isinstance(agents, list)
    assert len(agents) == 2


def test_client_get_agent(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    agent = client.agent.get("chat")
    assert agent["name"] == "chat"


def test_client_run_agent(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    result = client.agent.run("chat", prompt="Hello")
    assert isinstance(result, dict)


def test_client_list_tools(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    tools = client.tool.list()
    assert isinstance(tools, list)
    assert len(tools) == 2


def test_client_execute_tool(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    result = client.tool.execute("web_search", query="test")
    assert isinstance(result, dict)


def test_client_start_workflow(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    result = client.workflow.start("data_pipeline", x=1)
    assert "run_id" in result


def test_client_memory_create_thread(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    thread = client.memory.create_thread("manager", metadata={"user": "alice"})
    assert "id" in thread


def test_client_memory_list_threads(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    threads = client.memory.list_threads("manager")
    assert isinstance(threads, list)


def test_client_memory_delete_thread(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    # Should not raise
    client.memory.delete_thread("manager", thread_id="thread-1")


def test_client_unknown_namespace(test_client):
    client = MachineClient(base_url="http://testserver", http_client=test_client)
    with pytest.raises(AttributeError):
        client.nonexistent
