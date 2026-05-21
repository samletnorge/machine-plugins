"""Tests for agent-runtime-basic plugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from machine_core.plugins.agent_support.schemas import (
    AgentDefinition,
    AgentRunner,
    AgentRunResult,
)
from machine_core.plugins.tool_support.schemas import ToolDefinition
from machine_core.plugins.model_provider_support.schemas import ModelResponse


def test_implements_agent_runner():
    """BasicAgentRunner satisfies the AgentRunner protocol."""
    from machine_core.plugins.agent_runtime_basic.runtime import BasicAgentRunner

    runner = BasicAgentRunner.__new__(BasicAgentRunner)
    assert isinstance(runner, AgentRunner)


@pytest.mark.asyncio
async def test_run_no_tools_returns_text():
    """Without tool calls in response, agent returns text directly."""
    from machine_core.plugins.agent_runtime_basic.runtime import BasicAgentRunner

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(
        return_value=ModelResponse(
            provider="test",
            model="test-model",
            output="The answer is 42",
            usage={},
            duration_ms=100.0,
            tool_calls=None,
        )
    )

    resolver = MagicMock(return_value=mock_provider)
    runner = BasicAgentRunner(provider_resolver=resolver)

    defn = AgentDefinition(
        name="test-agent",
        description="test",
        model_ref="test/test-model",
        instruction="Be helpful.",
    )

    result = await runner.run(defn, "What is 6*7?", [])
    assert result.output == "The answer is 42"
    assert result.agent_name == "test-agent"
    assert len(result.steps) == 1
    resolver.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_run_with_tool_calls():
    """Agent executes tool calls and feeds results back."""
    from machine_core.plugins.agent_runtime_basic.runtime import BasicAgentRunner

    resp1 = ModelResponse(
        provider="test",
        model="test-model",
        output=None,
        usage={},
        duration_ms=50.0,
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "add", "arguments": '{"a": 6, "b": 7}'},
            }
        ],
    )
    resp2 = ModelResponse(
        provider="test",
        model="test-model",
        output="The answer is 13",
        usage={},
        duration_ms=50.0,
        tool_calls=None,
    )

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(side_effect=[resp1, resp2])
    resolver = MagicMock(return_value=mock_provider)
    runner = BasicAgentRunner(provider_resolver=resolver)

    add_tool = ToolDefinition(
        name="add",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        },
        handler=lambda a=0, b=0: a + b,
    )

    defn = AgentDefinition(
        name="calc",
        description="calculator",
        model_ref="test/test-model",
    )
    result = await runner.run(defn, "What is 6+7?", [add_tool])
    assert result.output == "The answer is 13"
    assert any(s.step_type == "tool_call" for s in result.steps)


def test_tools_to_openai_schema():
    """tools_to_openai_schema converts ToolDefinitions correctly."""
    from machine_core.plugins.agent_runtime_basic.messages import tools_to_openai_schema

    tools = [
        ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            handler=lambda: None,
        )
    ]
    schema = tools_to_openai_schema(tools)
    assert len(schema) == 1
    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_max_steps_reached():
    """Agent stops after max_steps with appropriate message."""
    from machine_core.plugins.agent_runtime_basic.runtime import BasicAgentRunner

    # Always return tool calls — force hitting max_steps
    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(
        return_value=ModelResponse(
            provider="test",
            model="test-model",
            output=None,
            usage={},
            duration_ms=10.0,
            tool_calls=[
                {
                    "id": "call_x",
                    "type": "function",
                    "function": {"name": "noop", "arguments": "{}"},
                }
            ],
        )
    )

    resolver = MagicMock(return_value=mock_provider)
    runner = BasicAgentRunner(provider_resolver=resolver)

    noop_tool = ToolDefinition(
        name="noop",
        description="Does nothing",
        parameters={},
        handler=lambda: "ok",
    )

    defn = AgentDefinition(
        name="looper",
        description="test",
        model_ref="test/m",
        max_steps=3,
    )
    result = await runner.run(defn, "loop forever", [noop_tool])
    assert "max steps" in result.output.lower()
