"""Tests for the @traced decorator."""

import pytest
import asyncio
from observability_support.decorator import traced
from observability_support.tracer import MachineTracer
from observability_support.config import ObservabilityConfig
from observability_support.spans import SpanKind, SpanAttributes
from tests.observability_support.helpers import InMemorySpanExporter


@pytest.fixture
def setup_tracer():
    exporter = InMemorySpanExporter()
    tracer = MachineTracer.from_config(
        ObservabilityConfig(service_name="test"),
        _test_exporter=exporter,
    )
    return tracer, exporter


def test_traced_sync_function(setup_tracer):
    tracer, exporter = setup_tracer

    @traced(tracer=tracer, kind=SpanKind.TOOL_INVOKE, tool_name="my_tool")
    def my_function(x: int) -> int:
        return x * 2

    result = my_function(5)
    assert result == 10
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "my_function"
    assert spans[0].attributes[SpanAttributes.TOOL_NAME] == "my_tool"


async def test_traced_async_function(setup_tracer):
    tracer, exporter = setup_tracer

    @traced(tracer=tracer, kind=SpanKind.PROCESSOR_RUN)
    async def my_async_fn(x: int) -> int:
        await asyncio.sleep(0.01)
        return x + 1

    result = await my_async_fn(10)
    assert result == 11
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "my_async_fn"


def test_traced_records_exception(setup_tracer):
    tracer, exporter = setup_tracer

    @traced(tracer=tracer, kind=SpanKind.AGENT_CALL)
    def failing():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        failing()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.is_ok is False


def test_traced_custom_name(setup_tracer):
    tracer, exporter = setup_tracer

    @traced(tracer=tracer, kind=SpanKind.AGENT_CALL, name="custom-span-name")
    def another_fn():
        return 42

    another_fn()
    spans = exporter.get_finished_spans()
    assert spans[0].name == "custom-span-name"


def test_traced_preserves_function_metadata(setup_tracer):
    tracer, exporter = setup_tracer

    @traced(tracer=tracer, kind=SpanKind.AGENT_CALL)
    def documented_fn():
        """This is my docstring."""
        pass

    assert documented_fn.__name__ == "documented_fn"
    assert documented_fn.__doc__ == "This is my docstring."
