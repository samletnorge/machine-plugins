"""Studio frontend workspace and island mount tests."""

from __future__ import annotations

from pathlib import Path


def test_studio_frontend_workspace_exists():
    root = (
        Path(__file__).resolve().parents[2]
        / "framework/studio_support/studio_support/frontend"
    )

    assert (root / "package.json").exists()
    assert (root / "vite.config.ts").exists()
    assert (root / "tsconfig.json").exists()


def test_chat_page_contains_island_mount(studio_client):
    response = studio_client.get("/chat")

    assert response.status_code == 200
    assert 'id="chat-island"' in response.text
    assert "/static/chat.js" in response.text


def test_tool_page_contains_island_mount(studio_client):
    response = studio_client.get("/tools/echo")

    assert response.status_code == 200
    assert 'id="tool-island"' in response.text
    assert "/static/tools.js" in response.text


def test_workflows_page_contains_island_mount(studio_client):
    response = studio_client.get("/workflows")

    assert response.status_code == 200
    assert 'id="workflow-island"' in response.text
    assert "/static/workflows.js" in response.text
