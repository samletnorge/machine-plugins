"""Tests for the FastAPI app factory."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client(mock_machine):
    from machine_core.plugins.server_support.app import create_app

    app = create_app(mock_machine)
    return TestClient(app)


def test_create_app_returns_fastapi(mock_machine):
    from machine_core.plugins.server_support.app import create_app

    app = create_app(mock_machine)
    assert app.title == "Machine Core API"


def test_health_check(test_client):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_openapi_schema_generated(test_client):
    resp = test_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    # Only routers with actual endpoints appear in OpenAPI
    assert "/api/agent" in schema["paths"]
    assert "/health" in schema["paths"]


def test_cors_headers(test_client):
    resp = test_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200


def test_request_id_header(test_client):
    resp = test_client.get("/health")
    assert "x-request-id" in resp.headers


def test_404_returns_json(test_client):
    resp = test_client.get("/api/nonexistent")
    assert resp.status_code in (404, 405)
    assert "detail" in resp.json()
