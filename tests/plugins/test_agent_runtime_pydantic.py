"""Tests for agent-runtime-pydantic plugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_support.schemas import (
    AgentDefinition,
    AgentRunner,
    AgentRunResult,
)
from tool_support.schemas import ToolDefinition


def test_implements_agent_runner():
    """PydanticAgentRunner satisfies the AgentRunner protocol."""
    from agent_runtime_pydantic.runtime import PydanticAgentRunner

    runner = PydanticAgentRunner.__new__(PydanticAgentRunner)
    assert isinstance(runner, AgentRunner)


@pytest.mark.asyncio
async def test_run_calls_model_resolver():
    """Runner resolves model from definition.model_ref."""
    from agent_runtime_pydantic.runtime import PydanticAgentRunner

    mock_model = MagicMock()
    resolver = MagicMock(return_value=mock_model)
    runner = PydanticAgentRunner(model_resolver=resolver)

    defn = AgentDefinition(
        name="test-agent",
        description="test",
        model_ref="ollama/gemma4:latest",
        instruction="You are helpful.",
    )

    mock_result = MagicMock()
    mock_result.output = "42"
    mock_result.all_messages = MagicMock(return_value=[])

    with patch(
        "agent_runtime_pydantic.runtime.Agent"
    ) as MockAgent:
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        MockAgent.return_value = mock_agent_instance

        result = await runner.run(defn, "What is 6*7?", [])

    resolver.assert_called_once_with("ollama/gemma4:latest")
    assert result.agent_name == "test-agent"
    assert result.output == "42"
    assert result.duration_ms is not None


def test_tool_definition_to_pydantic():
    """Converter creates pydantic-ai Tool from ToolDefinition."""
    from agent_runtime_pydantic.converters import (
        tool_definition_to_pydantic,
    )

    td = ToolDefinition(
        name="get_weather",
        description="Get weather for a city",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}},
        handler=lambda city="Oslo": f"Sunny in {city}",
    )
    pt = tool_definition_to_pydantic(td)
    assert pt.name == "get_weather"
    assert pt.description == "Get weather for a city"


def test_pydantic_result_to_agent_run_result():
    """Converter creates AgentRunResult from pydantic-ai result."""
    from agent_runtime_pydantic.converters import (
        pydantic_result_to_agent_run_result,
    )

    mock_result = MagicMock()
    mock_result.output = "The answer is 42"
    mock_result.all_messages = MagicMock(return_value=[])

    run_result = pydantic_result_to_agent_run_result("test-agent", mock_result, 123.4)
    assert run_result.agent_name == "test-agent"
    assert run_result.output == "The answer is 42"
    assert run_result.duration_ms == 123.4
