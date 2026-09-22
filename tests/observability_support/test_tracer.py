"""Tests for MachineTracer."""

import pytest
import asyncio
from observability_support.tracer import MachineTracer
from observability_support.config import ObservabilityConfig, SpanConfig
from observability_support.spans import SpanKind, SpanAttributes
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


def test_resolve_exporter_by_name():
    from observability_support.tracer import resolve_exporter
    from observability_support.exporters.console import ConsoleSpanExporter

    assert isinstance(
        resolve_exporter(ObservabilityConfig(exporter="console")),
        ConsoleSpanExporter,
    )
    assert resolve_exporter(ObservabilityConfig(exporter="does-not-exist")) is None
    assert resolve_exporter(ObservabilityConfig(exporter="")) is None


def test_from_config_attaches_a_span_processor():
    tracer = MachineTracer.from_config(ObservabilityConfig(exporter="console"))

    processors = getattr(
        tracer._provider._active_span_processor, "_span_processors", []
    )
    assert processors, "an exporter should be attached by default"


def test_from_config_sets_service_name_resource():
    tracer = MachineTracer.from_config(
        ObservabilityConfig(exporter="console", service_name="svc-x")
    )
    assert tracer._provider.resource.attributes["service.name"] == "svc-x"


def _tracer_with_span_config(exporter, **span_kwargs):
    return MachineTracer.from_config(
        ObservabilityConfig(
            exporter="console",
            service_name="test-service",
            span=SpanConfig(**span_kwargs),
        ),
        _test_exporter=exporter,
    )


def test_span_config_truncates_initial_string_attributes():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(exporter, max_attribute_length=5)
    with tracer.span(
        "op",
        kind=SpanKind.AGENT_CALL,
        agent_name="a-very-long-agent-name",
    ):
        pass
    spans = exporter.get_finished_spans()
    assert spans[0].attributes[SpanAttributes.AGENT_NAME] == "a-ver"


def test_span_config_truncates_attributes_set_after_creation():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(exporter, max_attribute_length=3)
    with tracer.span("op", kind=SpanKind.AGENT_CALL) as span:
        span.set_attribute(SpanAttributes.AGENT_NAME, "abcdefgh")
    spans = exporter.get_finished_spans()
    assert spans[0].attributes[SpanAttributes.AGENT_NAME] == "abc"


def test_span_config_does_not_truncate_non_string_attributes():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(exporter, max_attribute_length=2)
    with tracer.span(
        "op", kind=SpanKind.LLM_REQUEST, token_input=12345, latency_ms=99.5
    ):
        pass
    attrs = exporter.get_finished_spans()[0].attributes
    assert attrs[SpanAttributes.TOKEN_INPUT] == 12345
    assert attrs[SpanAttributes.LATENCY_MS] == 99.5


def test_span_config_record_exceptions_disabled():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(exporter, record_exceptions=False)
    with pytest.raises(ValueError):
        with tracer.span("failing-op", kind=SpanKind.TOOL_INVOKE):
            raise ValueError("boom")
    span = exporter.get_finished_spans()[0]
    assert span.status.is_ok is True
    assert not any(e.name == "exception" for e in span.events)


def test_span_config_record_exceptions_enabled_by_default():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(exporter)
    with pytest.raises(ValueError):
        with tracer.span("failing-op", kind=SpanKind.TOOL_INVOKE):
            raise ValueError("boom")
    span = exporter.get_finished_spans()[0]
    assert span.status.is_ok is False
    assert any(e.name == "exception" for e in span.events)


def test_span_config_records_input_output_only_when_enabled():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(exporter)
    with tracer.span("op", kind=SpanKind.LLM_REQUEST, input="prompt", output="reply"):
        pass
    attrs = exporter.get_finished_spans()[0].attributes
    assert SpanAttributes.INPUT not in attrs
    assert SpanAttributes.OUTPUT not in attrs


def test_span_config_captures_input_output_when_enabled():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(
        exporter, record_input=True, record_output=True
    )
    with tracer.span("op", kind=SpanKind.LLM_REQUEST, input="prompt", output="reply"):
        pass
    attrs = exporter.get_finished_spans()[0].attributes
    assert attrs[SpanAttributes.INPUT] == "prompt"
    assert attrs[SpanAttributes.OUTPUT] == "reply"


def test_span_config_input_output_truncated_when_enabled():
    exporter = InMemorySpanExporter()
    tracer = _tracer_with_span_config(
        exporter, record_input=True, record_output=True, max_attribute_length=4
    )
    with tracer.span(
        "op", kind=SpanKind.LLM_REQUEST, input="prompt-text", output="reply-text"
    ):
        pass
    attrs = exporter.get_finished_spans()[0].attributes
    assert attrs[SpanAttributes.INPUT] == "prom"
    assert attrs[SpanAttributes.OUTPUT] == "repl"


def test_from_config_forwards_span_config_to_proxy():
    exporter = InMemorySpanExporter()
    tracer = MachineTracer.from_config(
        ObservabilityConfig(
            exporter="console",
            span=SpanConfig(record_exceptions=False, max_attribute_length=1),
        ),
        _test_exporter=exporter,
    )
    with tracer.span("op", kind=SpanKind.AGENT_CALL, agent_name="abc") as span:
        span.set_attribute(SpanAttributes.TOOL_NAME, "tool")
    span = exporter.get_finished_spans()[0]
    assert span.attributes[SpanAttributes.AGENT_NAME] == "a"
    assert span.attributes[SpanAttributes.TOOL_NAME] == "t"

