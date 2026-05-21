"""Tests for MachineTracer."""

import pytest
import asyncio
from machine_core.plugins.observability_support.tracer import MachineTracer
from machine_core.plugins.observability_support.config import ObservabilityConfig
from machine_core.plugins.observability_support.spans import SpanKind, SpanAttributes
from tests.observability_support.helpers import InMemorySpanExporter


@pytest.fixture
def tracer_with_memory():
    exporter = InMemorySpanExporter()
    tracer = MachineTracer.from_config(
        ObservabilityConfig(exporter="console", service_name="test-service"),
        _test_exporter=exporter,
    )
    return tracer, exporter


def test_tracer_creates_span(tracer_with_memory):
    tracer, exporter = tracer_with_memory
    with tracer.span("test-operation", kind=SpanKind.AGENT_CALL, agent_name="my-agent"):
        pass
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test-operation"
    assert spans[0].attributes["machine.span.kind"] == "agent.call"
    assert spans[0].attributes[SpanAttributes.AGENT_NAME] == "my-agent"


def test_tracer_nested_spans(tracer_with_memory):
    tracer, exporter = tracer_with_memory
    with tracer.span("parent", kind=SpanKind.AGENT_CALL) as parent_span:
        with tracer.span(
            "child", kind=SpanKind.LLM_REQUEST, model_name="gpt-4o"
        ) as child_span:
            pass
    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    child, parent = spans  # finished order: child first
    assert child.parent is not None
    assert child.parent.span_id == parent.context.span_id


def test_tracer_records_exception(tracer_with_memory):
    tracer, exporter = tracer_with_memory
    with pytest.raises(ValueError):
        with tracer.span("failing-op", kind=SpanKind.TOOL_INVOKE, tool_name="bad_tool"):
            raise ValueError("something broke")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.is_ok is False
    events = span.events
    assert any(e.name == "exception" for e in events)


async def test_tracer_async_span(tracer_with_memory):
    tracer, exporter = tracer_with_memory
    async with tracer.async_span("async-op", kind=SpanKind.MEMORY_OP):
        await asyncio.sleep(0.01)
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "async-op"


def test_tracer_disabled_config():
    tracer = MachineTracer.from_config(ObservabilityConfig(enabled=False))
    with tracer.span("noop", kind=SpanKind.AGENT_CALL):
        pass


def test_tracer_adds_token_attributes(tracer_with_memory):
    tracer, exporter = tracer_with_memory
    with tracer.span(
        "llm-call",
        kind=SpanKind.LLM_REQUEST,
        model_name="claude-sonnet-4-20250514",
        token_input=1000,
        token_output=500,
        latency_ms=2500.0,
    ):
        pass
    spans = exporter.get_finished_spans()
    attrs = spans[0].attributes
    assert attrs[SpanAttributes.TOKEN_INPUT] == 1000
    assert attrs[SpanAttributes.TOKEN_OUTPUT] == 500
    assert attrs[SpanAttributes.LATENCY_MS] == 2500.0


def test_tracer_span_set_attribute_after_creation(tracer_with_memory):
    tracer, exporter = tracer_with_memory
    with tracer.span("llm-call", kind=SpanKind.LLM_REQUEST) as span:
        span.set_attribute(SpanAttributes.TOKEN_INPUT, 300)
        span.set_attribute(SpanAttributes.TOKEN_OUTPUT, 150)
    spans = exporter.get_finished_spans()
    assert spans[0].attributes[SpanAttributes.TOKEN_INPUT] == 300
