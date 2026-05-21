"""agent-runtime-basic: Custom loop agent runtime, no pydantic-ai dependency."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


def _make_provider_resolver(ctx: "PluginContext"):
    def resolver(provider_name: str) -> Any:
        provider = ctx._machine.resolve("model_provider", provider_name)
        if provider is None:
            raise ValueError(
                f"Model provider '{provider_name}' not found. "
                f"Available: {list(ctx._machine.list_category('model_provider').keys())}"
            )
        return provider

    return resolver


class AgentRuntimeBasicPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        from .runtime import BasicAgentRunner

        resolver = _make_provider_resolver(ctx)
        runner = BasicAgentRunner(
            provider_resolver=resolver,
            hook_caller=ctx._machine.hooks.call,
        )
        ctx.register("agent", "basic", runner)

    async def shutdown(self, **kwargs):
        pass
