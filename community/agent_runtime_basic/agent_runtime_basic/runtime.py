"""Basic agent runtime — custom loop with no pydantic-ai dependency."""

from __future__ import annotations

import inspect
import json
import time
from typing import Any, Callable

from loguru import logger

from agent_support.schemas import (
    AgentDefinition,
    AgentRunResult,
    AgentStep,
)
from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)
from tool_support.schemas import ToolDefinition

from .messages import (
    build_system_message,
    build_tool_result_message,
    build_user_message,
    tools_to_openai_schema,
)


class BasicAgentRunner:
    """Agent runtime using a manual loop: model -> tool calls -> execute -> repeat."""

    description = "Custom loop agent runtime — no external framework dependency"
    supports_streaming = False
    supports_tools = True

    def __init__(
        self,
        provider_resolver: Callable[[str], Any],
        hook_caller: Callable[..., Any] | None = None,
    ) -> None:
        self._provider_resolver = provider_resolver
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
        """Run the agent loop."""
        await self._emit("before_agent_run", definition=definition, input=input)
        start = time.monotonic()
        steps: list[AgentStep] = []

        try:
            model_ref = definition.model_ref or "ollama/gemma4:latest"
            if "/" in model_ref:
                provider_name, model_name = model_ref.split("/", 1)
            else:
                provider_name, model_name = model_ref, model_ref

            provider = self._provider_resolver(provider_name)
            if provider is None:
                raise ValueError(f"Provider '{provider_name}' not found")

            tool_map = {td.name: td for td in tools}
            openai_tools = tools_to_openai_schema(tools) if tools else None

            messages: list[dict[str, Any]] = []
            if definition.instruction:
                messages.append(build_system_message(definition.instruction))
            prior_messages = (context or {}).get("messages", [])
            if prior_messages:
                messages.extend(
                    {
                        "role": message.get("role", "user"),
                        "content": message.get("content", ""),
                    }
                    for message in prior_messages
                    if message.get("role") in {"user", "assistant"}
                )
            messages.append(build_user_message(input))

            max_steps = definition.max_steps or 10

            for step_num in range(max_steps):
                request = ModelRequest(
                    provider=provider_name,
                    model=model_name,
                    input=messages,
                    parameters={"tools": openai_tools} if openai_tools else {},
                    stream=False,
                )
                await self._emit("before_model_invoke", request=request)
                response: ModelResponse = await provider.generate(request)
                await self._emit(
                    "after_model_invoke", request=request, response=response
                )

                steps.append(
                    AgentStep(
                        step_type="model_call",
                        detail={"step": step_num, "model": model_name},
                        duration_ms=response.duration_ms,
                    )
                )
                await self._emit("on_agent_step", step=steps[-1])

                tool_calls = response.tool_calls or []
                if not tool_calls:
                    duration_ms = (time.monotonic() - start) * 1000
                    result = AgentRunResult(
                        agent_name=definition.name,
                        output=response.output,
                        steps=steps,
                        duration_ms=duration_ms,
                    )
                    await self._emit("after_agent_run", result=result)
                    return result

                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls,
                    }
                )

                for tc in tool_calls:
                    func_info = tc.get("function", {})
                    tool_name = func_info.get("name", "unknown")
                    args_str = func_info.get("arguments", "{}")
                    tc_id = tc.get("id", f"call_{step_num}_{tool_name}")

                    try:
                        args = (
                            json.loads(args_str)
                            if isinstance(args_str, str)
                            else args_str
                        )
                    except json.JSONDecodeError:
                        args = {}

                    td = tool_map.get(tool_name)
                    if not td:
                        tool_output = f"Error: tool '{tool_name}' not found"
                    else:
                        try:
                            t_start = time.monotonic()
                            await self._emit(
                                "before_tool_call", tool_name=tool_name, args=args
                            )
                            result = td.handler(**args)
                            if inspect.isawaitable(result):
                                result = await result
                            tool_output = str(result) if result is not None else ""
                            await self._emit(
                                "after_tool_call",
                                tool_name=tool_name,
                                result=tool_output,
                            )
                            t_dur = (time.monotonic() - t_start) * 1000
                            steps.append(
                                AgentStep(
                                    step_type="tool_call",
                                    detail={"tool_name": tool_name, "args": args},
                                    duration_ms=t_dur,
                                )
                            )
                        except Exception as e:
                            tool_output = f"Error executing {tool_name}: {e}"
                            steps.append(
                                AgentStep(
                                    step_type="tool_error",
                                    detail={"tool_name": tool_name, "error": str(e)},
                                )
                            )

                    await self._emit("on_agent_step", step=steps[-1])
                    messages.append(build_tool_result_message(tc_id, tool_output))

            duration_ms = (time.monotonic() - start) * 1000
            result = AgentRunResult(
                agent_name=definition.name,
                output=f"Agent reached max steps ({max_steps})",
                steps=steps,
                duration_ms=duration_ms,
            )
            await self._emit("after_agent_run", result=result)
            return result

        except Exception as e:
            await self._emit("on_agent_error", definition=definition, error=e)
            raise
