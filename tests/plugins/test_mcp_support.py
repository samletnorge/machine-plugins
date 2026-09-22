"""Tests for the MCP client plugin (mocked MCP session)."""

from __future__ import annotations

from machine_core import Machine
from machine_core.plugin.context import PluginContext

from mcp_support import MCPSupportPlugin


class _FakeTool:
    name = "ping"
    description = "Ping the server"
    inputSchema = {"type": "object", "properties": {}}


class _FakeListResult:
    tools = [_FakeTool()]


class _FakeContent:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeCallResult:
    content = [_FakeContent("pong")]


class _FakeSession:
    def __init__(self, read, write) -> None:
        self.calls: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def initialize(self):
        return None

    async def list_tools(self):
        return _FakeListResult()

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return _FakeCallResult()


class _FakeStdio:
    async def __aenter__(self):
        return (object(), object())

    async def __aexit__(self, *args):
        return False


def _fake_stdio_client(params):
    return _FakeStdio()


async def test_mcp_support_registers_tools_from_server(monkeypatch):
    import mcp
    import mcp.client.stdio as stdio_mod

    monkeypatch.setattr(mcp, "ClientSession", _FakeSession)
    monkeypatch.setattr(stdio_mod, "stdio_client", _fake_stdio_client)

    machine = Machine()
    machine.register_category("tool")

    plugin = MCPSupportPlugin()
    await plugin.initialize({"servers": [{"name": "demo", "command": "echo"}]})
    ctx = PluginContext("mcp_support", {"tool:register"}, machine)
    await plugin.setup(ctx)

    tool = machine.resolve("tool", "demo__ping")
    assert tool is not None
    assert tool.description == "Ping the server"
    assert await tool.handler() == "pong"

    await plugin.shutdown()


async def test_mcp_support_is_noop_without_servers(monkeypatch):
    machine = Machine()
    machine.register_category("tool")

    plugin = MCPSupportPlugin()
    await plugin.initialize({})
    ctx = PluginContext("mcp_support", {"tool:register"}, machine)
    await plugin.setup(ctx)

    assert machine.list_category("tool") == {}
    await plugin.shutdown()


def test_mcp_support_manifest_entry_point():
    import json
    from pathlib import Path

    import mcp_support

    package_dir = Path(mcp_support.__file__).parent
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        manifest_path = package_dir.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    assert manifest["transport"]["entry_point"] == "mcp_support:MCPSupportPlugin"
    assert "tool:register" in manifest["capabilities"]
