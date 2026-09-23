"""Tests for the Studio plugin store API."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from studio_support import security
from studio_support.control import store as store_module
from studio_support.session import SESSION_COOKIE, new_session


class FakeStore:
    def __init__(self, root: Path) -> None:
        self.project_root = root
        self.pyproject = root / "pyproject.toml"
        self.pyproject.write_text(
            '[tool.machine-core]\nplugins = ["agent_support"]\n', encoding="utf-8"
        )

    def declared_plugins(self) -> list[str]:
        return ["agent_support"]

    def installed_plugins(self) -> list[str]:
        return []

    async def catalog(self) -> list[dict[str, object]]:
        return [
            {
                "name": "agent_support",
                "version": "0.1.0",
                "description": "agents",
                "tier": "framework",
                "runtime": "python",
                "source": {"type": "registry", "path": "framework/agent_support"},
                "declared": True,
                "installed": False,
            }
        ]

    async def install(self, name: str, *, dev: bool = False):
        return SimpleNamespace(
            name=name, declared=True, installed=True, commands=[["uv", "add", name]], output="ok"
        )

    async def uninstall(self, name: str):
        return SimpleNamespace(
            name=name,
            declared=False,
            installed=False,
            commands=[["uv", "remove", name]],
            output="",
        )


def test_store_catalog(studio_client, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "_store", lambda: FakeStore(tmp_path))

    response = studio_client.get("/api/store")

    assert response.status_code == 200
    payload = response.json()
    assert payload["declared"] == ["agent_support"]
    assert payload["plugins"][0]["name"] == "agent_support"
    assert payload["has_pyproject"] is True


def test_store_install(studio_client, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "_store", lambda: FakeStore(tmp_path))

    response = studio_client.post("/api/store/install", json={"name": "auth_support"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "auth_support"
    assert payload["declared"] is True
    assert payload["commands"] == [["uv", "add", "auth_support"]]


def test_store_uninstall(studio_client, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "_store", lambda: FakeStore(tmp_path))

    response = studio_client.post("/api/store/uninstall", json={"name": "agent_support"})

    assert response.status_code == 200
    assert response.json()["declared"] is False


def test_store_surfaces_registry_errors(studio_client, tmp_path, monkeypatch):
    class BrokenStore(FakeStore):
        async def catalog(self):
            raise RuntimeError("no registry")

    monkeypatch.setattr(store_module, "_store", lambda: BrokenStore(tmp_path))

    response = studio_client.get("/api/store")

    assert response.status_code == 502


def _login_as(studio_client, roles: list[str]) -> None:
    studio_client.cookies.set(
        SESSION_COOKIE, new_session({"sub": "user-1", "email": "a@b", "roles": roles})
    )


def test_install_requires_auth_when_configured(studio_client, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "_store", lambda: FakeStore(tmp_path))
    monkeypatch.setattr(security, "auth_configured", lambda: True)

    response = studio_client.post("/api/store/install", json={"name": "auth_support"})

    assert response.status_code == 401


def test_install_rejects_non_admin(studio_client, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "_store", lambda: FakeStore(tmp_path))
    monkeypatch.setattr(security, "auth_configured", lambda: True)
    _login_as(studio_client, ["editor"])

    response = studio_client.post("/api/store/install", json={"name": "auth_support"})

    assert response.status_code == 403


def test_install_allows_admin(studio_client, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "_store", lambda: FakeStore(tmp_path))
    monkeypatch.setattr(security, "auth_configured", lambda: True)
    _login_as(studio_client, ["admin"])

    response = studio_client.post("/api/store/install", json={"name": "auth_support"})

    assert response.status_code == 200
    assert response.json()["declared"] is True
