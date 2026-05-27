"""Studio runtime control API tests."""

from __future__ import annotations


def test_chat_threads_endpoint_returns_agent_inventory(studio_client):
    response = studio_client.get("/api/chat/threads")

    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog"]["agents"] == ["greeter"]
    assert payload["catalog"]["runtimes"] == ["basic"]
    assert payload["threads"][0]["agent"] == "greeter"
    assert payload["threads"][0]["messages"] == []


def test_chat_messages_endpoint_records_user_and_assistant_messages(studio_client):
    response = studio_client.post(
        "/api/chat/threads/default/messages",
        json={"agent": "greeter", "message": "world"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["thread_id"] == "default"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][1]["role"] == "assistant"
    assert payload["messages"][1]["content"] == "Hello, world"


def test_chat_threads_endpoint_returns_full_message_history(studio_client):
    studio_client.post(
        "/api/chat/threads/default/messages",
        json={"agent": "greeter", "message": "world"},
    )

    response = studio_client.get("/api/chat/threads")

    assert response.status_code == 200
    messages = response.json()["threads"][0]["messages"]
    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"


def test_chat_messages_endpoint_forwards_prior_session_messages_in_context(
    studio_client, fake_machine
):
    studio_client.post(
        "/api/chat/threads/default/messages",
        json={"agent": "greeter", "message": "first"},
    )

    response = studio_client.post(
        "/api/chat/threads/default/messages",
        json={"agent": "greeter", "message": "second"},
    )

    assert response.status_code == 200
    last_call = fake_machine.greeter.calls[-1]
    assert last_call["msg"] == "second"
    assert last_call["context"] is not None
    assert last_call["context"]["messages"][0] == {"role": "user", "content": "first"}
    assert last_call["context"]["messages"][1] == {
        "role": "assistant",
        "content": "Hello, first",
    }


def test_chat_session_create_endpoint_adds_switchable_session(studio_client):
    create_response = studio_client.post("/api/chat/sessions")

    assert create_response.status_code == 200
    session_id = create_response.json()["thread_id"]
    assert session_id != "default"

    list_response = studio_client.get("/api/chat/threads")

    assert list_response.status_code == 200
    thread_ids = [thread["thread_id"] for thread in list_response.json()["threads"]]
    assert "default" in thread_ids
    assert session_id in thread_ids


def test_chat_messages_endpoint_rejects_runtime_runner_entries(studio_client):
    response = studio_client.post(
        "/api/chat/threads/default/messages",
        json={"agent": "basic", "message": "world"},
    )

    assert response.status_code == 400
    assert "not directly chat invokable" in response.json()["detail"]


def test_tool_detail_endpoint_returns_tool_schema_and_operations(studio_client):
    response = studio_client.get("/api/tools/echo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "echo"
    assert payload["owner"] == "test-plugin"
    assert "execute" in payload["operations"]
    assert payload["input_schema"]["properties"]["text"]["type"] == "string"


def test_workflow_graph_endpoint_returns_nodes_and_edges(studio_client):
    response = studio_client.get("/api/workflows/sequence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "sequence"
    assert len(payload["graph"]["nodes"]) == 3
    assert payload["graph"]["edges"][0]["source"] == "collect"


def test_workflow_runs_endpoint_returns_run_history(studio_client):
    response = studio_client.get("/api/workflows/sequence/runs")

    assert response.status_code == 200
    assert response.json()["runs"][0]["run_id"] == "run-1"


def test_registry_search_fragment_filters_plugins(studio_client):
    response = studio_client.get("/api/registry/search?q=studio")

    assert response.status_code == 200
    assert "studio_support" in response.text


def test_config_env_fragment_lists_env_names(studio_client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    response = studio_client.get("/api/config/env")

    assert response.status_code == 200
    assert "LLM_PROVIDER" in response.text


def test_services_action_endpoint_accepts_restart(studio_client):
    response = studio_client.post("/api/services/restart")

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "restart"
    assert payload["implemented"] is False
