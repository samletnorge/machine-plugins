"""Span attribute constants and helpers for machine-core tracing."""

from __future__ import annotations

from enum import Enum
from typing import Any


class SpanKind(str, Enum):
    """Types of traced operations."""

    AGENT_CALL = "agent.call"
    TOOL_INVOKE = "tool.invoke"
    LLM_REQUEST = "llm.request"
    WORKFLOW_STEP = "workflow.step"
    MEMORY_OP = "memory.operation"
    PROCESSOR_RUN = "processor.run"


class SpanAttributes:
    """Standard attribute keys for machine-core spans."""

    MODEL_NAME = "machine.model.name"
    TOKEN_INPUT = "machine.token.input"
    TOKEN_OUTPUT = "machine.token.output"
    LATENCY_MS = "machine.latency_ms"
    COST_USD = "machine.cost_usd"
    AGENT_NAME = "machine.agent.name"
    TOOL_NAME = "machine.tool.name"
    WORKFLOW_NAME = "machine.workflow.name"
    STEP_NAME = "machine.step.name"
    ERROR_TYPE = "machine.error.type"
    ERROR_MESSAGE = "machine.error.message"


def create_span_attributes(
    kind: SpanKind,
    *,
    agent_name: str | None = None,
    tool_name: str | None = None,
    model_name: str | None = None,
    workflow_name: str | None = None,
    step_name: str | None = None,
    token_input: int | None = None,
    token_output: int | None = None,
    latency_ms: float | None = None,
    cost_usd: float | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Build a span attribute dict, omitting None values."""
    mapping: list[tuple[str, Any]] = [
        ("machine.span.kind", kind.value),
        (SpanAttributes.AGENT_NAME, agent_name),
        (SpanAttributes.TOOL_NAME, tool_name),
        (SpanAttributes.MODEL_NAME, model_name),
        (SpanAttributes.WORKFLOW_NAME, workflow_name),
        (SpanAttributes.STEP_NAME, step_name),
        (SpanAttributes.TOKEN_INPUT, token_input),
        (SpanAttributes.TOKEN_OUTPUT, token_output),
        (SpanAttributes.LATENCY_MS, latency_ms),
        (SpanAttributes.COST_USD, cost_usd),
        (SpanAttributes.ERROR_TYPE, error_type),
        (SpanAttributes.ERROR_MESSAGE, error_message),
    ]
    return {k: v for k, v in mapping if v is not None}
