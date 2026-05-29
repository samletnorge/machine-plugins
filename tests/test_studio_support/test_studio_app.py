"""Task 9 — Studio app creation and index route tests."""

import json

from studio_support import StudioSupportPlugin
from studio_support.app import create_studio_app
from studio_support.dependencies import (
    build_studio_state,
    get_studio_state,
    reset_studio_state,
    set_studio_state,
)


def test_plugin_class_exists():
    p = StudioSupportPlugin()
    assert hasattr(p, "initialize")
    assert hasattr(p, "setup")
    assert hasattr(p, "shutdown")


def test_manifest_loads():
    from pathlib import Path

    import studio_support as pkg

    package_dir = Path(pkg.__file__).parent
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        manifest_path = package_dir.parent / "manifest.json"

    manifest = json.loads(manifest_path.read_text())
    assert "studio" in manifest["name"]


def test_create_studio_app_returns_fastapi(fake_machine):
    from fastapi import FastAPI

    app = create_studio_app(fake_machine)
    assert isinstance(app, FastAPI)


def test_index_returns_200(studio_client):
    resp = studio_client.get("/")
    assert resp.status_code == 200
    assert "TestMachine" in resp.text


def test_index_lists_agents(studio_client):
    resp = studio_client.get("/")
    assert "greeter" in resp.text


def test_index_lists_tools(studio_client):
    resp = studio_client.get("/")
    assert "echo" in resp.text


def test_index_shows_active_tenant_project_and_environment(studio_client):
    response = studio_client.get("/")

    assert response.status_code == 200
    assert "Active Context" in response.text
    assert "Northwind" in response.text
    assert "Fuel Ops / dev" in response.text
    assert "Northwind / Fuel Ops / dev" in response.text


def test_index_shows_attachment_state(studio_client):
    response = studio_client.get("/")

    assert response.status_code == 200
    assert "Attachment state" in response.text
    assert "<h2>attached</h2>" in response.text
    assert '<span class="status-label">Attachment</span>' in response.text
    assert ">attached</strong>" in response.text


def test_dashboard_renders_context_switcher_shell(studio_client):
    response = studio_client.get("/")

    assert response.status_code == 200
    assert '<header class="studio-topbar">' in response.text
    assert 'class="context-switcher-shell"' in response.text
    assert 'aria-label="Context switcher"' in response.text
    assert response.text.index('<header class="studio-topbar">') < response.text.index(
        '<main class="page-frame">'
    )
    assert response.text.index("context-switcher-shell") < response.text.index(
        '<main class="page-frame">'
    )
    assert response.text.count('class="context-switcher-shell"') == 1
    assert "target-switcher" in response.text
    assert 'data-context-switcher-endpoint="' in response.text
    assert '/api/context"' in response.text
    assert 'name="tenant_slug"' in response.text
    assert 'name="project_slug"' in response.text
    assert 'name="environment_name"' in response.text
    assert (
        '<button type="submit" class="primary-button">Switch</button>' in response.text
    )
    assert 'value="Northwind / Fuel Ops / dev"' in response.text
    assert 'data-environment-name="dev"' in response.text
    assert "selected" in response.text
    assert "Northwind / Fuel Ops / dev" in response.text
    assert "Northwind / Fuel Ops / staging" in response.text
    assert response.text.count('data-environment-name="dev"') == 1
    assert response.text.count('data-environment-name="staging"') == 1


def test_dashboard_shows_requested_failed_context_without_stale_runtime(
    context_aware_studio_client,
):
    state = context_aware_studio_client.app.state.studio_state
    original_resolver = state.attachment_manager._resolver

    def fail_resolver(context):
        if context.environment_id == "env-staging":
            raise RuntimeError("attach failed")
        return original_resolver(context)

    state.attachment_manager._resolver = fail_resolver

    switch_response = context_aware_studio_client.put(
        "/api/context",
        json={
            "tenant_slug": "northwind",
            "project_slug": "fuel-ops",
            "environment_name": "staging",
        },
    )

    assert switch_response.status_code == 200

    response = context_aware_studio_client.get("/")

    assert response.status_code == 200
    assert "Northwind / Fuel Ops / staging" in response.text
    assert "Context attach failed" in response.text
    assert "attach failed" in response.text
    assert "StagingMachine" not in response.text
    assert "designer-agent" not in response.text
    assert "staging-echo" not in response.text
    assert ">No runtime attached</span>" in response.text
    assert ">Fuel Ops</span>" not in response.text


def test_machine_snapshot_uses_honest_unknown_context_placeholders_when_state_missing(
    fake_machine,
):
    from studio_support.ui import machine_snapshot

    previous_state = None
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        pass

    try:
        reset_studio_state()

        snapshot = machine_snapshot()

        assert snapshot["tenant_name"] == "Unknown tenant"
        assert snapshot["project_name"] == "Unknown project"
        assert snapshot["environment"] == "No environment"
        assert snapshot["entry"] == "No entry"
    finally:
        reset_studio_state()
        if previous_state is not None:
            set_studio_state(previous_state)


def test_machine_snapshot_does_not_fabricate_project_targets_when_catalog_empty(
    fake_machine,
):
    from dataclasses import replace

    from studio_support.ui import machine_snapshot

    previous_state = None
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        pass

    set_studio_state(build_studio_state(fake_machine))
    base_state = get_studio_state()
    empty_targets_state = replace(
        base_state,
        catalog=replace(base_state.catalog, projects=[], environments=[]),
    )

    try:
        set_studio_state(empty_targets_state)

        snapshot = machine_snapshot()

        assert snapshot["project_targets"] == []
    finally:
        reset_studio_state()
        if previous_state is not None:
            set_studio_state(previous_state)
