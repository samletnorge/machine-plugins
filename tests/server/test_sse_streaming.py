"""Tests for SSE streaming."""

import pytest
import json


def test_stream_agent(test_client):
    """Test that /stream returns SSE-formatted events."""
    resp = test_client.post(
        "/api/agent/chat/stream",
        json={"prompt": "Hello"},
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = []
    for line in resp.text.strip().split("\n"):
        if line.startswith("data: "):
            data = line[6:]
            if data.strip():
                events.append(json.loads(data))

    types = [e["type"] for e in events]
    assert "text_delta" in types
    assert "final" in types


def test_stream_agent_not_found(test_client):
    resp = test_client.post(
        "/api/agent/nonexistent/stream",
        json={"prompt": "Hello"},
    )
    assert resp.status_code == 404
