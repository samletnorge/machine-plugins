"""Task 10: Agent-as-step adapter tests."""

import pytest
from unittest.mock import AsyncMock
from pydantic import BaseModel

from workflow_support.agent_step import agent_as_step
from workflow_support.step import Step, StepContext


class AgentInput(BaseModel):
    prompt: str


class AgentOutput(BaseModel):
    response: str


class TestAgentAsStep:
    def test_creates_step_from_agent(self):
        mock_agent = AsyncMock()
        mock_agent.name = "helper-agent"
        s = agent_as_step(
            agent=mock_agent,
            name="helper",
            input_schema=AgentInput,
            output_schema=AgentOutput,
        )
        assert isinstance(s, Step)
        assert s.name == "helper"

    @pytest.mark.asyncio
    async def test_executes_agent_run(self):
        mock_agent = AsyncMock()
        mock_agent.name = "helper-agent"
        mock_agent.run = AsyncMock(return_value=AgentOutput(response="Hello!"))

        s = agent_as_step(
            agent=mock_agent,
            name="helper",
            input_schema=AgentInput,
            output_schema=AgentOutput,
        )
        ctx = StepContext(
            input_data=AgentInput(prompt="Hi"),
            state={},
            previous_output=None,
        )
        result = await s.execute(ctx)
        assert result.response == "Hello!"
        mock_agent.run.assert_called_once()

    def test_defaults_name_from_agent(self):
        mock_agent = AsyncMock()
        mock_agent.name = "my-agent"
        s = agent_as_step(
            agent=mock_agent,
            input_schema=AgentInput,
            output_schema=AgentOutput,
        )
        assert s.name == "my-agent"
