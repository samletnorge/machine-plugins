"""The generic tool execute route must work for @tool-produced ToolDefinitions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from server_support.app import create_app
from tool_support import tool


@tool(name="echo", description="Echo text back.")
async def echo(text: str) -> str:
    return f"echo:{text}"


class _Machine:
    def __init__(self) -> None:
        self._tools = {"echo": echo.__tool_definition__}
        self._ops = {"tool": {"execute": {"method": "POST", "on": "item"}}}

    def list_categories(self) -> list[str]:
        return ["tool"]

    def list_category(self, category: str) -> dict:
        return self._tools if category == "tool" else {}

    def resolve(self, category: str, name: str):
        return self._tools.get(name) if category == "tool" else None

    def get_operations(self, category: str) -> dict:
        return self._ops.get(category, {})

    def get_owner(self, category: str, name: str):
        return "test"


def test_tool_execute_route_invokes_handler():
    client = TestClient(create_app(_Machine()))

    response = client.post("/api/tool/echo/execute", json={"text": "hi"})

    assert response.status_code == 200
    assert response.json() == "echo:hi"


def test_tool_definition_execute_delegates_to_handler():
    import asyncio

    assert asyncio.run(echo.__tool_definition__.execute(text="x")) == "echo:x"
