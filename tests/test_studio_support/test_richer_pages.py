"""Studio richer page interaction tests."""

from __future__ import annotations


def test_registry_page_exposes_search_and_refresh_controls(studio_client):
    response = studio_client.get("/registry")

    assert response.status_code == 200
    assert 'hx-get="/api/registry/search"' in response.text
    assert 'hx-get="/api/registry/plugins"' in response.text


def test_config_page_exposes_env_refresh_control(studio_client):
    response = studio_client.get("/config")

    assert response.status_code == 200
    assert 'hx-get="/api/config/env"' in response.text


def test_services_page_exposes_restart_action(studio_client):
    response = studio_client.get("/services")

    assert response.status_code == 200
    assert 'hx-post="/api/services/restart"' in response.text


def test_chat_page_points_island_to_thread_endpoints(studio_client):
    response = studio_client.get("/chat")

    assert response.status_code == 200
    assert "Operator workbench" in response.text
    assert 'class="panel chat-panel"' in response.text
    assert 'class="chat-page-header"' in response.text
    assert "Runtime console" in response.text
    assert "How this console works" in response.text
    assert "<details" in response.text
    assert 'class="operator-notes"' in response.text
    assert 'data-threads-endpoint="/api/chat/threads"' in response.text
    assert (
        'data-messages-endpoint="/api/chat/threads/default/messages"' in response.text
    )
    assert 'data-sessions-endpoint="/api/chat/sessions"' in response.text
    assert 'data-render-markdown="true"' in response.text
    assert 'data-chat-tabs="agents,runtimes"' in response.text
    assert 'hx-post="/chat/send"' not in response.text
    assert 'id="agent-select"' not in response.text
    assert response.text.count('<article class="panel chat-panel">') == 1


def test_tool_page_points_island_to_tool_detail_endpoint(studio_client):
    response = studio_client.get("/tools/echo")

    assert response.status_code == 200
    assert 'data-detail-endpoint="/api/tools/echo"' in response.text


def test_workflows_page_points_island_to_graph_endpoint(studio_client):
    response = studio_client.get("/workflows")

    assert response.status_code == 200
    assert 'data-graph-endpoint="/api/workflows/sequence"' in response.text
    assert 'data-runs-endpoint="/api/workflows/sequence/runs"' in response.text


def test_workflows_page_hides_island_when_no_runtime_workflows(
    studio_client, monkeypatch
):
    from studio_support import ui

    original_runtime_items = ui._runtime_items

    def fake_runtime_items(category: str):
        if category == "workflow":
            return []
        return original_runtime_items(category)

    monkeypatch.setattr(ui, "_runtime_items", fake_runtime_items)

    response = studio_client.get("/workflows")

    assert response.status_code == 200
    assert 'id="workflow-island"' not in response.text
