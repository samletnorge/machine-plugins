"""Task 12: Agent network — supervisor routing tests."""

import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel

from workflow_support.network import (
    AgentNetwork,
    DelegationConfig,
    NetworkAgent,
)


class TaskInput(BaseModel):
    task: str


class TaskOutput(BaseModel):
    result: str


class TestNetworkAgent:
    def test_create_network_agent(self):
        agent = AsyncMock()
        agent.name = "researcher"
        na = NetworkAgent(
            agent=agent,
            description="Researches topics",
            capabilities=["search", "summarize"],
        )
        assert na.agent is agent
        assert na.description == "Researches topics"
        assert "search" in na.capabilities


class TestDelegationConfig:
    def test_default_config(self):
        config = DelegationConfig()
        assert config.max_delegations == -1
        assert config.on_delegation_start is None
        assert config.on_delegation_complete is None

    @pytest.mark.asyncio
    async def test_on_delegation_start_hook_can_reject(self):
        async def reject_hook(agent_name: str, task: str) -> bool:
            return agent_name != "forbidden"

        config = DelegationConfig(on_delegation_start=reject_hook)
        assert await config.on_delegation_start("allowed", "do stuff") is True
        assert await config.on_delegation_start("forbidden", "do stuff") is False


class TestAgentNetwork:
    def test_register_agents(self):
        network = AgentNetwork(name="my-network")
        agent1 = AsyncMock()
        agent1.name = "agent1"
        agent2 = AsyncMock()
        agent2.name = "agent2"

        network.register(NetworkAgent(agent=agent1, description="First agent"))
        network.register(NetworkAgent(agent=agent2, description="Second agent"))
        assert len(network.agents) == 2

    def test_routing_prompt_lists_agents(self):
        network = AgentNetwork(name="my-network")
        agent1 = AsyncMock()
        agent1.name = "researcher"
        network.register(
            NetworkAgent(
                agent=agent1,
                description="Researches topics and finds information",
                capabilities=["search", "summarize"],
            )
        )
        prompt = network.build_routing_prompt("Find fuel prices")
        assert "researcher" in prompt
        assert "Researches topics" in prompt
        assert "search" in prompt

    @pytest.mark.asyncio
    async def test_delegate_to_agent(self):
        network = AgentNetwork(name="net")
        agent = AsyncMock()
        agent.name = "worker"
        agent.run = AsyncMock(return_value=TaskOutput(result="done"))
        network.register(NetworkAgent(agent=agent, description="Does work"))

        result = await network.delegate("worker", TaskInput(task="do it"))
        assert result.result == "done"
        agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegate_unknown_agent_raises(self):
        network = AgentNetwork(name="net")
        with pytest.raises(KeyError, match="unknown"):
            await network.delegate("unknown", TaskInput(task="x"))

    @pytest.mark.asyncio
    async def test_delegation_hooks_called(self):
        start_calls: list[str] = []
        complete_calls: list[str] = []

        async def on_start(agent_name: str, task: str) -> bool:
            start_calls.append(agent_name)
            return True

        async def on_complete(agent_name: str, result: Any) -> None:
            complete_calls.append(agent_name)

        config = DelegationConfig(
            on_delegation_start=on_start,
            on_delegation_complete=on_complete,
        )
        network = AgentNetwork(name="net", delegation_config=config)
        agent = AsyncMock()
        agent.name = "worker"
        agent.run = AsyncMock(return_value=TaskOutput(result="ok"))
        network.register(NetworkAgent(agent=agent, description="worker"))

        await network.delegate("worker", TaskInput(task="go"))
        assert "worker" in start_calls
        assert "worker" in complete_calls

    @pytest.mark.asyncio
    async def test_delegation_rejected_by_hook(self):
        async def reject_all(agent_name: str, task: str) -> bool:
            return False

        config = DelegationConfig(on_delegation_start=reject_all)
        network = AgentNetwork(name="net", delegation_config=config)
        agent = AsyncMock()
        agent.name = "worker"
        agent.run = AsyncMock()
        network.register(NetworkAgent(agent=agent, description="worker"))

        with pytest.raises(PermissionError, match="rejected"):
            await network.delegate("worker", TaskInput(task="nope"))
        agent.run.assert_not_called()

    def test_agents_as_tools_list(self):
        network = AgentNetwork(name="net")
        a1 = AsyncMock()
        a1.name = "researcher"
        a2 = AsyncMock()
        a2.name = "writer"
        network.register(NetworkAgent(agent=a1, description="Researches"))
        network.register(NetworkAgent(agent=a2, description="Writes"))

        tools = network.as_tools()
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "delegate_to_researcher" in tool_names
        assert "delegate_to_writer" in tool_names
