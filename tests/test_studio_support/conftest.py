"""Shared fixtures for studio tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from studio_support.app import create_studio_app


class FakeAgent:
    name = "greeter"

    async def run(self, msg):
        return SimpleNamespace(output=f"Hello, {msg}")


class FakeTool:
    name = "echo"
    description = "Echoes input"

    async def execute(self, data):
        return {"echo": data}


class FakeMachine:
    name = "TestMachine"

    def __init__(self):
        self._agents = {"greeter": FakeAgent()}
        self._tools = {"echo": FakeTool()}

    def list_category(self, cat):
        if cat == "agent":
            return self._agents
        if cat == "tool":
            return self._tools
        return {}

    def list_categories(self):
        return ["agent", "tool"]

    def resolve(self, cat, name):
        return self.list_category(cat).get(name)


@pytest.fixture
def fake_machine():
    return FakeMachine()


@pytest.fixture
def studio_client(fake_machine):
    app = create_studio_app(fake_machine)
    return TestClient(app)
