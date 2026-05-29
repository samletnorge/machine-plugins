"""Shared fixtures for studio tests."""

from pathlib import Path
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

    def __init__(
        self,
        *,
        name: str = "TestMachine",
        chat_agent_name: str = "greeter",
        tool_name: str = "echo",
        workflow_name: str = "sequence",
    ):
        self.name = name
        self._agents = {"basic": FakeRuntimeRunner(), chat_agent_name: FakeAgent()}
        self._tools = {tool_name: FakeTool()}
        self._tools[tool_name].input_model = EchoInput
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
        self._workflows = {workflow_name: FakeWorkflow()}

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
        return self._agents.get("greeter")


class FakeMachineRegistry:
    def __init__(self, machines_by_environment: dict[str, FakeMachine]):
        self._machines_by_environment = machines_by_environment

    def resolve_for_context(self, context):
        return self._machines_by_environment[context.environment_id]


def _write_studio_pyproject(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        """
[tool.machine-core.studio]
active_tenant = "tenant-northwind"
active_project = "project-fuel-ops"
active_environment = "env-dev"

[[tool.machine-core.studio.tenants]]
id = "tenant-northwind"
slug = "northwind"
name = "Northwind"

[[tool.machine-core.studio.tenants]]
id = "tenant-samletnorge"
slug = "samletnorge"
name = "Samletnorge"

[[tool.machine-core.studio.tenants]]
id = "tenant-mythrantic"
slug = "mythrantic"
name = "Mythrantic"

[[tool.machine-core.studio.projects]]
id = "project-fuel-ops"
tenant_id = "tenant-northwind"
slug = "fuel-ops"
name = "Fuel Ops"
entry = "test.main:machine"

[tool.machine-core.studio.projects.capability_summary]
agents = 2
tools = 2

[[tool.machine-core.studio.projects]]
id = "project-car-expert"
tenant_id = "tenant-samletnorge"
slug = "car-expert"
name = "Car Expert"
entry = "test.car:machine"

[tool.machine-core.studio.projects.capability_summary]
agents = 2
tools = 2

[[tool.machine-core.studio.projects]]
id = "project-news-finder"
tenant_id = "tenant-samletnorge"
slug = "news-finder"
name = "News Finder"
entry = "test.news:machine"

[tool.machine-core.studio.projects.capability_summary]
agents = 2
tools = 2

[[tool.machine-core.studio.projects]]
id = "project-ai-playground"
tenant_id = "tenant-mythrantic"
slug = "ai-playground"
name = "AI Playground"
entry = "test.playground:machine"

[tool.machine-core.studio.projects.capability_summary]
agents = 1
tools = 2

[[tool.machine-core.studio.environments]]
id = "env-dev"
project_id = "project-fuel-ops"
name = "dev"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-staging"
project_id = "project-fuel-ops"
name = "staging"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-prod"
project_id = "project-fuel-ops"
name = "prod"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-car-dev"
project_id = "project-car-expert"
name = "dev"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-car-staging"
project_id = "project-car-expert"
name = "staging"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-news-dev"
project_id = "project-news-finder"
name = "dev"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-news-prod"
project_id = "project-news-finder"
name = "prod"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-playground-dev"
project_id = "project-ai-playground"
name = "dev"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-playground-prod"
project_id = "project-ai-playground"
name = "prod"
connection_kind = "local"
connection_ref = "fake-machine"
status = "healthy"
""".strip()
    )


@pytest.fixture
def fake_machine():
    return FakeMachine()


@pytest.fixture
def context_aware_fake_machine():
    return FakeMachineRegistry(
        {
            "env-dev": FakeMachine(
                name="DevMachine",
                chat_agent_name="greeter",
                tool_name="echo",
                workflow_name="sequence",
            ),
            "env-staging": FakeMachine(
                name="StagingMachine",
                chat_agent_name="designer-agent",
                tool_name="staging-echo",
                workflow_name="staging-sequence",
            ),
            "env-prod": FakeMachine(
                name="ProdMachine",
                chat_agent_name="prod-agent",
                tool_name="prod-echo",
                workflow_name="prod-sequence",
            ),
            "env-car-dev": FakeMachine(
                name="CarExpertDevMachine",
                chat_agent_name="car-expert",
                tool_name="lookup-vehicle",
                workflow_name="car-diagnose",
            ),
            "env-car-staging": FakeMachine(
                name="CarExpertStagingMachine",
                chat_agent_name="price-advisor",
                tool_name="estimate-repair",
                workflow_name="car-pricing",
            ),
            "env-news-dev": FakeMachine(
                name="NewsFinderDevMachine",
                chat_agent_name="news-finder",
                tool_name="search-news",
                workflow_name="news-briefing",
            ),
            "env-news-prod": FakeMachine(
                name="NewsFinderProdMachine",
                chat_agent_name="topic-summarizer",
                tool_name="extract-article",
                workflow_name="news-digest",
            ),
            "env-playground-dev": FakeMachine(
                name="PlaygroundDevMachine",
                chat_agent_name="playground-assistant",
                tool_name="run-prompt",
                workflow_name="prompt-lab",
            ),
            "env-playground-prod": FakeMachine(
                name="PlaygroundProdMachine",
                chat_agent_name="model-judge",
                tool_name="compare-models",
                workflow_name="model-bakeoff",
            ),
        }
    )


@pytest.fixture(autouse=True)
def studio_root(tmp_path, monkeypatch):
    _write_studio_pyproject(tmp_path)
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def studio_client(fake_machine, studio_root):
    runtime._CHAT_THREADS.clear()
    runtime._CHAT_THREAD_AGENTS.clear()
    runtime._CHAT_SESSION_IDS = iter(range(1, 10_000))
    app = create_studio_app(fake_machine)
    return TestClient(app)


@pytest.fixture
def context_aware_studio_client(context_aware_fake_machine, studio_root):
    runtime._CHAT_THREADS.clear()
    runtime._CHAT_THREAD_AGENTS.clear()
    runtime._CHAT_SESSION_IDS = iter(range(1, 10_000))
    app = create_studio_app(context_aware_fake_machine)
    return TestClient(app)
