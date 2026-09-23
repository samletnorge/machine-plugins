"""Studio domain slice and control-plane seam tests."""

from __future__ import annotations

import pytest


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
def test_domain_endpoints_return_domain_payloads(studio_client, path: str, domain: str):
    response = studio_client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert payload["domain"] == domain
    assert "installed" in payload
    assert "categories" in payload
    assert "items" in payload


@pytest.mark.parametrize("section", ["deploy", "memory", "observe", "not-a-domain"])
def test_legacy_sections_redirect_to_spa(studio_client, section: str):
    response = studio_client.get(f"/sections/{section}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith("/app")
