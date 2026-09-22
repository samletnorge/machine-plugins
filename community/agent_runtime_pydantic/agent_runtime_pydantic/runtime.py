"""Pydantic-AI based agent runtime."""

from __future__ import annotations

import time
from typing import Any, Callable

from pydantic_ai import Agent, UsageLimits
from pydantic_ai.messages import (
    ModelRequest as PydanticModelRequest,
    ModelResponse as PydanticModelResponse,
    TextPart,
    UserPromptPart,
)

from agent_support.schemas import AgentDefinition, AgentRunResult
from tool_support.schemas import ToolDefinition

from .converters import pydantic_result_to_agent_run_result, tool_definition_to_pydantic


def _build_message_history(context: dict[str, Any] | None) -> list[Any]:
    """Convert prior {role, content} messages into pydantic-ai messages."""
    history: list[Any] = []
    for message in (context or {}).get("messages", []) or []:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            history.append(
                PydanticModelRequest(parts=[UserPromptPart(content=content)])
            )
        elif role == "assistant":
            history.append(PydanticModelResponse(parts=[TextPart(content=content)]))
    return history


class PydanticAgentRunner:
    """Agent runtime that wraps pydantic-ai Agent for the tool-calling loop."""

    description = "Pydantic-AI based agent runtime with structured output support"
    supports_streaming = False
    supports_tools = True

    def __init__(
        self,
        model_resolver: Callable[[str], Any],
        hook_caller: Callable[..., Any] | None = None,
    ) -> None:
        self._model_resolver = model_resolver
        self._hook_caller = hook_caller

    async def _emit(self, hook_name: str, **kwargs: Any) -> None:
        if self._hook_caller:
            result = self._hook_caller(hook_name, **kwargs)
            if hasattr(result, "__await__"):
                await result

    async def run(
        self,
        definition: AgentDefinition,
        input: str,
        tools: list[ToolDefinition],
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run the agent loop using pydantic-ai."""
        await self._emit("before_agent_run", definition=definition, input=input)

        try:
            model_ref = definition.model_ref or "ollama/gemma4:latest"
            pydantic_model = self._model_resolver(model_ref)

            pydantic_tools = [tool_definition_to_pydantic(td) for td in tools]

            agent = Agent(
                model=pydantic_model,
                system_prompt=definition.instruction or "",
                tools=pydantic_tools,
            )

            history = _build_message_history(context)
            usage_limits = (
                UsageLimits(request_limit=definition.max_steps)
                if definition.max_steps
                else None
            )

            start = time.monotonic()
            result = await agent.run(
                input,
                message_history=history or None,
                usage_limits=usage_limits,
            )
            duration_ms = (time.monotonic() - start) * 1000

            run_result = pydantic_result_to_agent_run_result(
                agent_name=definition.name,
                result=result,
                duration_ms=duration_ms,
            )

            for step in run_result.steps:
                await self._emit("on_agent_step", step=step)
            await self._emit("after_agent_run", result=run_result)
            return run_result

        except Exception as e:
            await self._emit("on_agent_error", definition=definition, error=e)
            raise
