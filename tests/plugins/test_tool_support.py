"""Tests for tool-support builtin plugin."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from tool_support.schemas import ToolDefinition, ToolResult
from tool_support.decorator import tool


# --- Schema tests ---


def test_tool_definition_valid():
    td = ToolDefinition(
        name="calc",
        description="Calculator",
        parameters={"type": "object", "properties": {"expr": {"type": "string"}}},
        handler=lambda **kw: None,
    )
    assert td.name == "calc"
    assert td.description == "Calculator"


def test_tool_definition_requires_name():
    with pytest.raises(PydanticValidationError):
        ToolDefinition(description="x", parameters={}, handler=lambda: None)


def test_tool_result():
    r = ToolResult(tool_name="calc", output=42, duration_ms=1.5)
    assert r.output == 42
    assert r.error is None


def test_tool_result_with_error():
    r = ToolResult(tool_name="calc", output=None, error="division by zero")
    assert r.error == "division by zero"


# --- Decorator tests ---


def test_tool_decorator_basic():
    @tool()
    async def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    td = add.__tool_definition__
    assert td.name == "add"
    assert td.description == "Add two numbers."
    assert "a" in td.parameters.get("properties", {})
    assert "b" in td.parameters.get("properties", {})


def test_tool_decorator_custom_name():
    @tool(name="my_adder", description="Custom adder")
    async def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    td = add.__tool_definition__
    assert td.name == "my_adder"
    assert td.description == "Custom adder"


def test_tool_decorator_preserves_callable():
    @tool()
    async def echo(text: str) -> str:
        """Echo text."""
        return text

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(echo(text="hi"))
    assert result == "hi"


# --- Plugin setup tests ---


@pytest.mark.asyncio
async def test_plugin_setup_registers_category():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="tool-support",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "tool:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="tool_support:ToolSupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("tool-support")

    assert "tool" in m._registry


@pytest.mark.asyncio
async def test_plugin_hookspecs_registered():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="tool-support",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "tool:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="tool_support:ToolSupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("tool-support")

    assert "before_tool_call" in m.hooks._specs
    assert "after_tool_call" in m.hooks._specs
    assert "on_tool_error" in m.hooks._specs
