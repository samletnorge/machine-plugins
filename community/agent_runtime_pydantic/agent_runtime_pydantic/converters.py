"""Convert between machine-core schemas and pydantic-ai types."""

from __future__ import annotations

import inspect
from typing import Any

from pydantic_ai import Tool as PydanticTool

from agent_support.schemas import AgentRunResult, AgentStep
from tool_support.schemas import ToolDefinition

_EMPTY_SCHEMA = {"type": "object", "properties": {}}


def tool_definition_to_pydantic(td: ToolDefinition) -> PydanticTool:
    """Convert a machine-core ToolDefinition to a pydantic-ai Tool.

    The declared JSON schema is passed through so the model sees the real
    parameters instead of one inferred from an opaque ``**kwargs`` wrapper.
    """

    async def _wrapper(**kwargs: Any) -> Any:
        result = td.handler(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    return PydanticTool.from_schema(
        function=_wrapper,
        name=td.name,
        description=td.description,
        json_schema=td.parameters or _EMPTY_SCHEMA,
    )


def _all_messages(result: Any) -> list[Any]:
    raw = getattr(result, "all_messages", None)
    if callable(raw):
        raw = raw()
    return list(raw or [])


def pydantic_result_to_agent_run_result(
    agent_name: str,
    result: Any,
    duration_ms: float,
) -> AgentRunResult:
    """Convert a pydantic-ai run result to AgentRunResult."""
    output = getattr(result, "output", None)

    steps: list[AgentStep] = []
    for message in _all_messages(result):
        message_kind = getattr(message, "kind", None)
        parts = getattr(message, "parts", []) or []

        if message_kind == "request":
            steps.append(AgentStep(step_type="model_request", detail={}))

        for part in parts:
            part_kind = getattr(part, "part_kind", None)
            if part_kind == "tool-call":
                steps.append(
                    AgentStep(
                        step_type="tool_call",
                        detail={"tool_name": getattr(part, "tool_name", "unknown")},
                    )
                )
            elif part_kind == "tool-return":
                steps.append(
                    AgentStep(
                        step_type="tool_result",
                        detail={"tool_name": getattr(part, "tool_name", "unknown")},
                    )
                )
            elif part_kind == "text":
                text = getattr(part, "content", "") or ""
                steps.append(
                    AgentStep(
                        step_type="text_response",
                        detail={"text": text[:200]},
                    )
                )

    return AgentRunResult(
        agent_name=agent_name,
        output=str(output) if output else "",
        steps=steps,
        duration_ms=duration_ms,
    )
