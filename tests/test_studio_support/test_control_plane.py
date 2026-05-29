"""Studio control-plane route tests."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from studio_support import ui
from studio_support.context_models import StudioProject, StudioTenant


def test_studio_health_endpoint_returns_ok(studio_client):
    response = studio_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "studio-control"}


def test_registry_plugins_endpoint_returns_manifest_inventory(
    studio_client, tmp_path, monkeypatch
):
    plugin_dir = tmp_path / "plugins" / "agent_support"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "agent_support",
                "version": "0.5.0",
                "schema_version": "1.0.0",
                "description": "Agent plugin",
            }
        )
    )
    monkeypatch.setattr(ui, "CONFIG_PLUGIN_DIR", tmp_path / "plugins")

    response = studio_client.get("/api/registry/plugins")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "agent_support"


def test_config_endpoint_returns_project_and_environment_snapshot(
    studio_client, tmp_path, monkeypatch
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.machine-core]
entry = "src.main:machine"
environment = "dev"
plugins = ["agent_support"]
""".strip()
    )
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "google")

    response = studio_client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_config"]["environment"] == "dev"
    assert "LLM_PROVIDER" in payload["env_names"]


def test_services_status_endpoint_returns_runtime_summary(studio_client):
    response = studio_client.get("/api/services/status")

    assert response.status_code == 200
    assert response.json()["studio_mount"] == "/_studio"
    assert response.json()["runtime_api"] == "/api/*"


def test_context_endpoint_returns_active_context_and_attachment(studio_client):
    response = studio_client.get("/api/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["project_slug"] == "fuel-ops"
    assert payload["attachment"]["status"] == "attached"


def test_put_context_switches_active_environment(studio_client):
    response = studio_client.put(
        "/api/context",
        json={
            "tenant_slug": "northwind",
            "project_slug": "fuel-ops",
            "environment_name": "staging",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["environment_name"] == "staging"
    assert payload["attachment"]["status"] == "attached"


def test_tenants_projects_and_environments_endpoints_return_catalog(studio_client):
    tenants = studio_client.get("/api/tenants")
    projects = studio_client.get("/api/tenants/northwind/projects")
    environments = studio_client.get("/api/projects/fuel-ops/environments")

    assert tenants.status_code == 200
    assert tenants.json()[0]["slug"] == "northwind"
    assert projects.status_code == 200
    assert projects.json()[0]["slug"] == "fuel-ops"
    assert environments.status_code == 200
    assert environments.json()[0]["name"] == "dev"


def test_config_endpoint_returns_context_aware_payload(studio_client):
    response = studio_client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["tenant_slug"] == "northwind"
    assert payload["attachment"]["status"] == "attached"


def test_config_endpoint_includes_supported_provider_env_names(
    studio_client, monkeypatch
):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("GROK_API_KEY", "test-grok")

    response = studio_client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert "GROQ_API_KEY" in payload["env_names"]
    assert "GROK_API_KEY" in payload["env_names"]


def test_config_endpoint_reflects_active_context_after_switch(studio_client):
    switch_response = studio_client.put(
        "/api/context",
        json={
            "tenant_slug": "northwind",
            "project_slug": "fuel-ops",
            "environment_name": "staging",
        },
    )

    assert switch_response.status_code == 200

    response = studio_client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["environment_name"] == "staging"
    assert payload["attachment"]["status"] == "attached"


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        (
            "/api/tenants/missing-tenant/projects",
            "Tenant 'missing-tenant' not found",
        ),
        (
            "/api/projects/missing-project/environments",
            "Project 'missing-project' not found",
        ),
    ],
)
def test_listing_endpoints_return_404_for_unknown_lookup_values(
    studio_client, path, detail
):
    response = studio_client.get(path)

    assert response.status_code == 404
    assert response.json() == {"detail": detail}


def test_environments_endpoint_returns_409_for_ambiguous_project_slug(studio_client):
    state = studio_client.app.state.studio_state
    duplicate_tenant = StudioTenant(
        id="tenant-contoso",
        slug="contoso",
        name="Contoso",
    )
    duplicate_project = StudioProject(
        id="project-contoso-fuel-ops",
        tenant_id=duplicate_tenant.id,
        slug="fuel-ops",
        name="Fuel Ops Clone",
        entry="test.clone:machine",
        capability_summary={"agents": 1, "tools": 0},
    )
    state.catalog = replace(
        state.catalog,
        tenants=[*state.catalog.tenants, duplicate_tenant],
        projects=[*state.catalog.projects, duplicate_project],
    )

    response = studio_client.get("/api/projects/fuel-ops/environments")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Project slug 'fuel-ops' is ambiguous across tenants"
    }


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (
            {
                "tenant_slug": "missing-tenant",
                "project_slug": "fuel-ops",
                "environment_name": "staging",
            },
            "Tenant 'missing-tenant' not found",
        ),
        (
            {
                "tenant_slug": "northwind",
                "project_slug": "missing-project",
                "environment_name": "staging",
            },
            "Project 'missing-project' not found",
        ),
        (
            {
                "tenant_slug": "northwind",
                "project_slug": "fuel-ops",
                "environment_name": "missing-environment",
            },
            "Environment 'missing-environment' not found",
        ),
    ],
)
def test_put_context_returns_404_for_unknown_lookup_values(
    studio_client, payload, detail
):
    response = studio_client.put("/api/context", json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": detail}
