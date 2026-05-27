"""Shared fixtures for studio tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from tool_support.schemas import ToolDefinition

from studio_support.app import create_studio_app
from studio_support.control import runtime


class FakeAgent:
    name = "greeter"

    def __init__(self):
        self.calls = []

    async def run(self, msg, context=None):
        self.calls.append({"msg": msg, "context": context})
        return SimpleNamespace(output=f"Hello, {msg}")


class FakeRuntimeRunner:
    name = "basic"

    async def run(self, definition, input, tools, context=None):
        return SimpleNamespace(output=f"Runtime hello, {input}")


class FakeTool:
    name = "echo"
    description = "Echoes input"
    input_model = None

    async def execute(self, data):
        return {"echo": data}


class EchoInput(BaseModel):
    text: str


class WorkflowRunRecord:
    def __init__(self, run_id: str, status: str):
        self.run_id = run_id
        self.status = status

    def to_dict(self):
        return {"run_id": self.run_id, "status": self.status}


class FakeWorkflow:
    name = "sequence"

    def __init__(self):
        self.nodes = [
            SimpleNamespace(
                node_type=SimpleNamespace(value="sequential"),
                step=SimpleNamespace(name="collect"),
                steps=[],
            ),
            SimpleNamespace(
                node_type=SimpleNamespace(value="parallel"),
                step=None,
                steps=[SimpleNamespace(name="rank"), SimpleNamespace(name="respond")],
            ),
        ]
        self._runs = [WorkflowRunRecord("run-1", "completed")]

    async def start(self, **kwargs):
        return {"accepted": True, "input": kwargs}

    async def runs(self):
        return self._runs

    async def get_run(self, run_id: str):
        for run in self._runs:
            if run.run_id == run_id:
                return run
        return None


class FakeMachine:
    name = "TestMachine"

    def __init__(self):
        self._agents = {"basic": FakeRuntimeRunner(), "greeter": FakeAgent()}
        self._tools = {"echo": FakeTool()}
        self._tools["echo"].input_model = EchoInput
        self._tools["handler-tool"] = ToolDefinition(
            name="handler-tool",
            description="Executes via handler",
            parameters={
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            handler=lambda input: {"handled": input},
        )
        self._workflows = {"sequence": FakeWorkflow()}

    def list_category(self, cat):
        if cat == "agent":
            return self._agents
        if cat == "tool":
            return self._tools
        if cat == "workflow":
            return self._workflows
        return {}

    def list_categories(self):
        return ["agent", "tool", "workflow"]

    def resolve(self, cat, name):
        return self.list_category(cat).get(name)

    def get_owner(self, cat, name):
        return "test-plugin"

    def get_operations(self, cat):
        if cat == "agent":
            return {"run": {"method": "POST"}, "stream": {"method": "POST"}}
        if cat == "tool":
            return {"execute": {"method": "POST"}}
        if cat == "workflow":
            return {
                "start": {"method": "POST"},
                "runs": {"method": "GET"},
                "get_run": {"method": "GET", "path": "runs/{run_id}"},
            }
        return {}

    @property
    def greeter(self):
        return self._agents["greeter"]


@pytest.fixture
def fake_machine():
    return FakeMachine()


@pytest.fixture
def studio_client(fake_machine):
    runtime._CHAT_THREADS.clear()
    runtime._CHAT_SESSION_IDS = iter(range(1, 10_000))
    app = create_studio_app(fake_machine)
    return TestClient(app)
