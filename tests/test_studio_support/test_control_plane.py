"""Studio control-plane route tests."""

from __future__ import annotations

import json

from studio_support import ui


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
