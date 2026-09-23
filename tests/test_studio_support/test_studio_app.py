"""Task 9 — Studio app creation and legacy-redirect tests."""

import json

import pytest
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


@pytest.mark.parametrize(
    ("legacy", "target"),
    [
        ("/", "/app/"),
        ("/dashboard", "/app/"),
        ("/registry", "/app/registry"),
        ("/config", "/app/config"),
        ("/services", "/app/services"),
        ("/account", "/app/context"),
        ("/agents", "/app/runtime"),
        ("/tools", "/app/runtime"),
        ("/workflows", "/app/runtime"),
        ("/chat", "/app/runtime"),
        ("/sections/deploy", "/app/domain/deploy"),
        ("/islands/memory", "/app/domain/memory"),
        ("/docs", "/app/"),
    ],
)
def test_legacy_pages_redirect_into_spa(studio_client, legacy: str, target: str):
    response = studio_client.get(legacy, follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == target


def test_spa_index_served(studio_client):
    response = studio_client.get("/app")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


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


async def test_machine_lifespan_starts_machine_once():
    from studio_support.app import _machine_lifespan

    class StartableMachine:
        def __init__(self) -> None:
            self.started = 0
            self.categories: list[str] = []

        def list_categories(self) -> list[str]:
            return list(self.categories)

        async def start(self) -> None:
            self.started += 1
            self.categories.append("agent")

    machine = StartableMachine()
    lifespan = _machine_lifespan(machine)

    async with lifespan(None):
        pass
    assert machine.started == 1

    # A second startup (host + mounted sub-app) must not start it again.
    async with lifespan(None):
        pass
    assert machine.started == 1
