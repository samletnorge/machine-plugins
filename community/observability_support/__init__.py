"""observability_support: OpenTelemetry tracing, cost tracking, and exporter backends."""

from __future__ import annotations

import functools
from typing import Any, TYPE_CHECKING

from observability_support.config import (
    ObservabilityConfig,
    SpanConfig,
)
from observability_support.tracer import MachineTracer
from observability_support.decorator import traced
from observability_support.cost import CostTracker, ModelPricing
from observability_support.spans import SpanKind, SpanAttributes

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class ObservabilitySupportPlugin:
    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category(
            "observability_exporter",
            operations={
                "export": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass


def setup_observability(
    config: ObservabilityConfig,
) -> tuple[MachineTracer, CostTracker]:
    """Create a MachineTracer and CostTracker from config.

    Returns (tracer, cost_tracker) for use across the application.
    """
    tracer = MachineTracer.from_config(config)
    cost_tracker = CostTracker()
    return tracer, cost_tracker


def instrument_agent(agent: Any, tracer: MachineTracer) -> Any:
    """Wrap agent.run() and agent.run_stream() with tracing spans.

    Modifies the agent in-place and returns it for convenience.
    """
    original_run = agent.run

    @functools.wraps(original_run)
    async def traced_run(*args: Any, **kwargs: Any) -> Any:
        async with tracer.async_span(
            f"agent:{agent.name}",
            kind=SpanKind.AGENT_CALL,
            agent_name=agent.name,
        ):
            return await original_run(*args, **kwargs)

    agent.run = traced_run

    # Wrap run_stream if it exists
    if hasattr(agent, "run_stream"):
        original_stream = agent.run_stream

        @functools.wraps(original_stream)
        async def traced_stream(*args: Any, **kwargs: Any) -> Any:
            async with tracer.async_span(
                f"agent_stream:{agent.name}",
                kind=SpanKind.AGENT_CALL,
                agent_name=agent.name,
            ):
                return await original_stream(*args, **kwargs)

        agent.run_stream = traced_stream

    return agent


def instrument_tool(tool: Any, tracer: MachineTracer) -> Any:
    """Wrap tool.execute() with tracing spans.

    Modifies the tool in-place and returns it for convenience.
    """
    original_execute = tool.execute

    @functools.wraps(original_execute)
    async def traced_execute(*args: Any, **kwargs: Any) -> Any:
        async with tracer.async_span(
            f"tool:{tool.name}",
            kind=SpanKind.TOOL_INVOKE,
            tool_name=tool.name,
        ):
            return await original_execute(*args, **kwargs)

    tool.execute = traced_execute
    return tool


__all__ = [
    "ObservabilitySupportPlugin",
    "ObservabilityConfig",
    "SpanConfig",
    "MachineTracer",
    "traced",
    "CostTracker",
    "ModelPricing",
    "SpanKind",
    "SpanAttributes",
    "setup_observability",
    "instrument_agent",
    "instrument_tool",
]
