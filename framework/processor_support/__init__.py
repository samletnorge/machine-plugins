"""Processor-support plugin.

Defines the "processor" category and registers built-in processors
for input/output middleware pipelines on agent calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

from .base import Processor, ProcessorData, TripWire
from .runner import ProcessorRunner

__all__ = [
    "Processor",
    "ProcessorData",
    "TripWire",
    "ProcessorRunner",
    "ProcessorSupportPlugin",
]


class ProcessorSupportPlugin:
    """Plugin that provides the processor middleware pipeline.

    Registers the "processor" category and all built-in processors.
    Built-in processors use sensible defaults; override by unregistering
    and re-registering with custom config.
    """

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: "PluginContext"):
        """Register the processor category and all built-in processors."""
        from .builtin.pii import PIIProcessor
        from .builtin.prompt_injection import PromptInjectionProcessor
        from .builtin.token_limiter import TokenLimiterProcessor
        from .builtin.cost_guard import CostGuardProcessor
        from .builtin.regex_filter import RegexFilterProcessor
        from .builtin.cache import CacheProcessor

        # Define the processor category with operations
        ctx.register_category(
            "processor",
            operations={
                "run_pipeline": {"method": "POST", "on": "collection"},
                "list": {"method": "GET", "on": "collection"},
            },
        )

        # Register built-in processors with default configs
        ctx.register("processor", "pii", PIIProcessor())
        ctx.register("processor", "prompt_injection", PromptInjectionProcessor())
        ctx.register(
            "processor", "token_limiter", TokenLimiterProcessor(max_tokens=100_000)
        )
        ctx.register(
            "processor",
            "cost_guard",
            CostGuardProcessor(max_cost_usd=10.0, cost_per_1k_tokens=0.01),
        )
        ctx.register("processor", "regex_filter", RegexFilterProcessor())
        ctx.register("processor", "cache", CacheProcessor(ttl_seconds=300))

        # Note: ModerationProcessor and ToolSearchProcessor require callbacks,
        # so they are NOT registered by default.

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
