"""Agent network — supervisor routing and delegation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class NetworkAgent:
    """An agent registered in a network."""

    agent: Any
    description: str
    capabilities: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.agent.name


@dataclass
class DelegationConfig:
    """Configuration for delegation behavior in an agent network."""

    max_delegations: int = -1  # -1 = unlimited
    on_delegation_start: Callable | None = None  # async (agent_name, task) -> bool
    on_delegation_complete: Callable | None = None  # async (agent_name, result) -> None


class AgentNetwork:
    """A supervisor agent network that routes tasks to sub-agents.

    Sub-agents are registered with descriptions and capabilities.
    The supervisor can delegate tasks based on routing logic.
    Agents can be exposed as tools for LLM-based routing.
    """

    def __init__(
        self,
        name: str,
        delegation_config: DelegationConfig | None = None,
    ) -> None:
        self.name = name
        self.agents: dict[str, NetworkAgent] = {}
        self.delegation_config = delegation_config or DelegationConfig()
        self._delegation_count = 0

    def register(self, network_agent: NetworkAgent) -> None:
        """Register a sub-agent in the network."""
        self.agents[network_agent.name] = network_agent

    def build_routing_prompt(self, task: str) -> str:
        """Build a prompt that lists available agents for routing decisions."""
        lines = [f"Task: {task}", "", "Available agents:"]
        for na in self.agents.values():
            caps = ", ".join(na.capabilities) if na.capabilities else "general"
            lines.append(f"- **{na.name}**: {na.description} (capabilities: {caps})")
        lines.append("")
        lines.append("Choose the best agent to handle this task.")
        return "\n".join(lines)

    async def delegate(self, agent_name: str, input_data: Any) -> Any:
        """Delegate a task to a specific sub-agent by name."""
        if agent_name not in self.agents:
            raise KeyError(
                f"Agent '{agent_name}' not found in network. "
                f"Available: {list(self.agents.keys())}"
            )

        na = self.agents[agent_name]

        # Check delegation start hook
        if self.delegation_config.on_delegation_start:
            task_str = str(input_data)
            allowed = await self.delegation_config.on_delegation_start(
                agent_name, task_str
            )
            if not allowed:
                raise PermissionError(
                    f"Delegation to '{agent_name}' was rejected by hook"
                )

        # Enforce max_delegations if configured (-1 = unlimited)
        if (
            self.delegation_config.max_delegations >= 0
            and self._delegation_count >= self.delegation_config.max_delegations
        ):
            raise RuntimeError(
                f"Max delegations ({self.delegation_config.max_delegations}) "
                f"reached in network '{self.name}'"
            )

        self._delegation_count += 1

        # Simple protocol: agent.run(input_data) -> output
        result = await na.agent.run(input_data)

        # Complete hook
        if self.delegation_config.on_delegation_complete:
            await self.delegation_config.on_delegation_complete(agent_name, result)

        return result

    def as_tools(self) -> list[dict[str, Any]]:
        """Export each agent as a tool definition (for LLM function calling)."""
        tools = []
        for na in self.agents.values():
            tools.append(
                {
                    "name": f"delegate_to_{na.name}",
                    "description": f"Delegate task to {na.name}: {na.description}",
                    "capabilities": na.capabilities,
                    "agent_name": na.name,
                }
            )
        return tools
