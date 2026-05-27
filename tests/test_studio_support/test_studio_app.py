"""Task 9 — Studio app creation and index route tests."""

import json
from studio_support import StudioSupportPlugin
from studio_support.app import create_studio_app


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
