"""Schemas for the agent_support plugin."""

from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    name: str
    description: str
    model_ref: str | None = None
    tool_refs: list[str] = Field(default_factory=list)
    instruction: str | None = None
    max_steps: int = 10
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentStep(BaseModel):
    step_type: str
    detail: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float | None = None


class AgentRunResult(BaseModel):
    agent_name: str
    output: Any = None
    steps: list[AgentStep] = Field(default_factory=list)
    duration_ms: float | None = None


@runtime_checkable
class AgentRunner(Protocol):
    """Protocol for agent runtime implementations."""

    async def run(
        self,
        definition: AgentDefinition,
        input: str,
        tools: list[Any],
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult: ...


class HandoffRequest(BaseModel):
    from_agent: str
    to_agent: str
    message: Any = None
    context: dict[str, Any] = Field(default_factory=dict)
