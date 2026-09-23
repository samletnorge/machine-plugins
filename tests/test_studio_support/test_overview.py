"""Tests for the Studio overview endpoint used by the SPA dashboard."""

from __future__ import annotations


def test_overview_returns_snapshot(studio_client):
    response = studio_client.get("/api/overview")

    assert response.status_code == 200
    payload = response.json()
    assert "machine_name" in payload
    assert isinstance(payload["category_counts"], dict)
    assert isinstance(payload["runtime_agents"], list)
    assert isinstance(payload["manifests"], list)
