"""Studio domain slice and hub seam tests."""

from __future__ import annotations

import pytest

from studio_support.ui import studio_layout


def test_studio_layout_exposes_hub_context_seams():
    layout = studio_layout(page_title="Dashboard", active_nav="dashboard")

    assert "project_name" in layout
    assert "environment" in layout
    assert "nav_sections" in layout
    assert "workspace_name" in layout
    assert "organization_name" in layout
    assert "project_targets" in layout


@pytest.mark.parametrize(
    ("path", "domain"),
    [
        ("/api/deploy/targets", "deploy"),
        ("/api/auth/keys", "auth"),
        ("/api/observe/traces", "observe"),
        ("/api/memory/threads", "memory"),
        ("/api/rag/pipelines", "rag"),
        ("/api/evals/runs", "evals"),
        ("/api/pubsub/events", "pubsub"),
        ("/api/storage/files", "storage"),
        ("/api/workspace/files", "workspace"),
        ("/api/browser/sessions", "browser"),
        ("/api/voice/voices", "voice"),
    ],
)
def test_domain_endpoints_return_stub_payloads(studio_client, path: str, domain: str):
    response = studio_client.get(path)

    assert response.status_code == 200
    assert response.json() == {"items": [], "implemented": False, "domain": domain}


def test_planned_section_renders_domain_payload(studio_client):
    response = studio_client.get("/sections/deploy")

    assert response.status_code == 200
    assert '"implemented": false' in response.text
    assert '"next": "deploy"' in response.text
