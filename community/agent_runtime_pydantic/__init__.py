"""agent-runtime-pydantic: Pydantic-AI based agent runtime plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


def _make_model_resolver(ctx: "PluginContext"):
    """Create a model_resolver that looks up providers from Machine registry."""

    def resolver(model_ref: str) -> Any:
        if "/" in model_ref:
            provider_name, model_name = model_ref.split("/", 1)
        else:
            provider_name, model_name = model_ref, model_ref

        provider = ctx._machine.resolve("model_provider", provider_name)
        if provider is None:
            raise ValueError(
                f"Model provider '{provider_name}' not found. "
                f"Available: {list(ctx._machine.list_category('model_provider').keys())}"
            )

        if hasattr(provider, "get_pydantic_model"):
            return provider.get_pydantic_model(model_name=model_name)

        raise ValueError(
            f"Provider '{provider_name}' does not support get_pydantic_model(). "
            f"Use agent-runtime-basic instead, or add get_pydantic_model() to the provider."
        )

    return resolver


class AgentRuntimePydanticPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        from pydantic_ai import Agent  # noqa: F401 — ImportError → lazy skip

        from .runtime import PydanticAgentRunner

        resolver = _make_model_resolver(ctx)
        runner = PydanticAgentRunner(
            model_resolver=resolver,
            hook_caller=ctx._machine.hooks.call,
        )
        ctx.register("agent", "pydantic-ai", runner)

    async def shutdown(self, **kwargs):
        pass
