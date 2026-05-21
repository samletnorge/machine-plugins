"""Shared test fixtures for server tests."""

import pytest
from unittest.mock import AsyncMock


class MockToolAction:
    def __init__(
        self, name: str, description: str, input_schema: dict, output_schema: dict
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.execute = AsyncMock(return_value={"result": f"{name} executed"})


class MockAgentRunResult:
    def __init__(self, output: str):
        self.output = output
        self.data = output
        self.usage = {"input_tokens": 10, "output_tokens": 20}
        self.all_messages_json = lambda: [{"role": "assistant", "content": output}]


class MockAgent:
    def __init__(self, name: str, description: str, model: str = "openai/gpt-4o"):
        self.name = name
        self.description = description
        self.model = model
        self.tools = []

    async def run(self, prompt: str, **kwargs):
        return MockAgentRunResult(f"Response to: {prompt}")

    async def run_stream(self, prompt: str, **kwargs):
        async def _gen():
            yield {"type": "text_delta", "content": "Hello "}
            yield {"type": "text_delta", "content": "world"}
            yield {"type": "final", "content": "Hello world"}

        return _gen()

    async def generate(self, prompt: str, output_schema: type):
        return output_schema.model_validate({"summary": "test", "score": 0.9})


class MockWorkflowRun:
    def __init__(self, run_id: str, status: str = "completed"):
        self.run_id = run_id
        self.status = status
        self.result = {"output": "workflow done"}
        self.created_at = "2026-05-10T00:00:00Z"
        self.updated_at = "2026-05-10T00:00:01Z"


class MockWorkflow:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps = []

    async def start(self, **kwargs):
        return MockWorkflowRun("run-001")

    async def get_run(self, run_id: str):
        return MockWorkflowRun(run_id)

    async def resume(self, run_id: str, **kwargs):
        return MockWorkflowRun(run_id, status="completed")

    async def runs(self):
        return [MockWorkflowRun("run-001"), MockWorkflowRun("run-002")]


class MockThread:
    def __init__(self, id: str, messages=None, metadata=None):
        self.id = id
        self.messages = messages or []
        self.metadata = metadata or {}
        self.created_at = "2026-05-10T00:00:00Z"


class MockMessage:
    def __init__(self, id: str, role: str, content: str):
        self.id = id
        self.role = role
        self.content = content
        self.created_at = "2026-05-10T00:00:00Z"


class MockMemoryManager:
    def __init__(self):
        self._threads = {}

    async def create_thread(self, metadata=None):
        t = MockThread("thread-001", metadata=metadata or {})
        self._threads[t.id] = t
        return t

    async def get_thread(self, thread_id: str):
        return self._threads.get(thread_id, MockThread(thread_id))

    async def list_threads(self):
        return list(self._threads.values()) or [MockThread("thread-001")]

    async def delete_thread(self, thread_id: str):
        self._threads.pop(thread_id, None)

    async def add_message(self, thread_id: str, role: str, content: str):
        return MockMessage("msg-001", role, content)


class MockMachine:
    """Mock Machine using the ACTUAL generic registry API."""

    def __init__(self):
        self._operations = {
            "agent": {
                "run": {"method": "POST", "on": "item"},
                "stream": {"method": "POST", "on": "item"},
                "generate": {"method": "POST", "on": "item"},
            },
            "tool": {
                "execute": {"method": "POST", "on": "item"},
            },
            "workflow": {
                "start": {"method": "POST", "on": "item"},
                "runs": {"method": "GET", "on": "item"},
                "get_run": {"method": "GET", "on": "item", "path": "runs/{run_id}"},
                "resume": {
                    "method": "POST",
                    "on": "item",
                    "path": "runs/{run_id}/resume",
                },
            },
            "memory": {
                "create_thread": {"method": "POST", "on": "item", "path": "threads"},
                "list_threads": {"method": "GET", "on": "item", "path": "threads"},
                "get_thread": {
                    "method": "GET",
                    "on": "item",
                    "path": "threads/{thread_id}",
                },
                "add_message": {
                    "method": "POST",
                    "on": "item",
                    "path": "threads/{thread_id}/messages",
                },
                "delete_thread": {
                    "method": "DELETE",
                    "on": "item",
                    "path": "threads/{thread_id}",
                },
            },
        }
        self._registry = {
            "agent": {
                "chat": MockAgent("chat", "General chat agent"),
                "coder": MockAgent(
                    "coder", "Code generation agent", model="anthropic/claude-sonnet"
                ),
            },
            "tool": {
                "web_search": MockToolAction(
                    "web_search",
                    "Search the web",
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"results": {"type": "array"}},
                    },
                ),
                "calculator": MockToolAction(
                    "calculator",
                    "Do math",
                    input_schema={
                        "type": "object",
                        "properties": {"expression": {"type": "string"}},
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"result": {"type": "number"}},
                    },
                ),
            },
            "workflow": {
                "data_pipeline": MockWorkflow("data_pipeline", "ETL pipeline"),
            },
            "memory": {
                "manager": MockMemoryManager(),
            },
        }

    def get_operations(self, category: str) -> dict:
        return dict(self._operations.get(category, {}))

    def list_categories(self) -> list[str]:
        return list(self._registry.keys())

    def list_category(self, category: str) -> dict:
        return dict(self._registry.get(category, {}))

    def resolve(self, category: str, name: str):
        return self._registry.get(category, {}).get(name)


@pytest.fixture
def mock_machine():
    return MockMachine()


@pytest.fixture
def test_client(mock_machine):
    from fastapi.testclient import TestClient
    from machine_core.plugins.server_support.app import create_app

    app = create_app(mock_machine)
    return TestClient(app)
