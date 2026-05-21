"""Pydantic-AI based agent runtime."""

from __future__ import annotations

import time
from typing import Any, Callable

from pydantic_ai import Agent

from machine_core.plugins.agent_support.schemas import (
    AgentDefinition,
    AgentRunResult,
)
from machine_core.plugins.tool_support.schemas import ToolDefinition

from .converters import pydantic_result_to_agent_run_result, tool_definition_to_pydantic


class PydanticAgentRunner:
    """Agent runtime that wraps pydantic-ai Agent for the tool-calling loop."""

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

            start = time.monotonic()
            result = await agent.run(input)
            duration_ms = (time.monotonic() - start) * 1000

            run_result = pydantic_result_to_agent_run_result(
                agent_name=definition.name,
                result=result,
                duration_ms=duration_ms,
            )

            await self._emit("after_agent_run", result=run_result)
            return run_result

        except Exception as e:
            await self._emit("on_agent_error", definition=definition, error=e)
            raise
