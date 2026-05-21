"""Convert between machine-core schemas and pydantic-ai types."""

from __future__ import annotations

import inspect
from typing import Any

from pydantic_ai import Tool as PydanticTool

from machine_core.plugins.agent_support.schemas import AgentRunResult, AgentStep
from machine_core.plugins.tool_support.schemas import ToolDefinition


def tool_definition_to_pydantic(td: ToolDefinition) -> PydanticTool:
    """Convert a machine-core ToolDefinition to a pydantic-ai Tool."""

    async def _wrapper(**kwargs: Any) -> Any:
        result = td.handler(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    return PydanticTool(
        function=_wrapper,
        name=td.name,
        description=td.description,
    )


def pydantic_result_to_agent_run_result(
    agent_name: str,
    result: Any,
    duration_ms: float,
) -> AgentRunResult:
    """Convert pydantic-ai run result to AgentRunResult."""
    output = getattr(result, "output", None) or getattr(result, "data", None)

    steps: list[AgentStep] = []
    all_messages = getattr(result, "all_messages", lambda: [])()
    for msg in all_messages:
        msg_kind = getattr(msg, "kind", None)
        if msg_kind == "request":
            steps.append(AgentStep(step_type="model_request", detail={}))
        elif msg_kind == "response":
            parts = getattr(msg, "parts", [])
            for part in parts:
                part_kind = getattr(part, "part_kind", None)
                if part_kind == "tool-call":
                    tool_name = getattr(part, "tool_name", "unknown")
                    steps.append(
                        AgentStep(
                            step_type="tool_call",
                            detail={"tool_name": tool_name},
                        )
                    )
                elif part_kind == "text":
                    steps.append(
                        AgentStep(
                            step_type="text_response",
                            detail={"text": getattr(part, "content", "")[:200]},
                        )
                    )
        elif msg_kind == "tool-return":
            tool_name = getattr(msg, "tool_name", "unknown")
            steps.append(
                AgentStep(
                    step_type="tool_result",
                    detail={"tool_name": tool_name},
                )
            )

    return AgentRunResult(
        agent_name=agent_name,
        output=str(output) if output else "",
        steps=steps,
        duration_ms=duration_ms,
    )
