"""Server lifecycle and request hooks must fire."""

from __future__ import annotations

from fastapi.testclient import TestClient

from server_support.app import create_app


class _Hooks:
    def __init__(self) -> None:
        self.events: list[str] = []

    def call(self, name: str, **kwargs):
        self.events.append(name)
        return None


class _Machine:
    def __init__(self) -> None:
        self.hooks = _Hooks()

    def list_categories(self) -> list[str]:
        return ["tool"]

    def list_category(self, category: str) -> dict:
        return {}


def test_server_lifecycle_and_request_hooks_fire():
    machine = _Machine()
    app = create_app(machine)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    events = machine.hooks.events
    assert "hooks/beforeServerStart" in events
    assert "hooks/afterServerStart" in events
    assert "hooks/beforeRequest" in events
    assert "hooks/afterRequest" in events
