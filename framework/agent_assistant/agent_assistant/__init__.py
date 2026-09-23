"""agent_assistant: a general chat agent backed by a model provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class AgentAssistantPlugin:
    """Registers a chat-capable agent that delegates to a model provider."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, config: dict[str, Any] | None = None, **kwargs: Any) -> None:
        self._config = config or kwargs.get("config") or {}

    async def setup(self, ctx: "PluginContext") -> None:
        from .agent import DEFAULT_SYSTEM_PROMPT, AssistantAgent

        config = self._config or {}
        provider_name = config.get("provider", "deepseek")

        def resolver(name: str) -> Any:
            provider = ctx._machine.resolve("model_provider", name)
            if provider is None:
                available = list(ctx._machine.list_category("model_provider").keys())
                raise RuntimeError(
                    f"model provider '{name}' is not registered. "
                    f"Available: {', '.join(available) or 'none'}. "
                    f"Install a provider plugin (e.g. provider_deepseek) and set its API key."
                )
            return provider

        parameters = dict(config.get("parameters") or {})
        if "temperature" in config:
            parameters.setdefault("temperature", config["temperature"])

        agent = AssistantAgent(
            provider_name=provider_name,
            model=config.get("model", "") or "",
            system_prompt=config.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
            parameters=parameters,
            resolve_provider=resolver,
        )
        ctx.register("agent", "assistant", agent)

    async def shutdown(self, **kwargs: Any) -> None:
        pass
