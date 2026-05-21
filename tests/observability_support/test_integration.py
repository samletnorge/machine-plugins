"""Tests for plugin integration — auto-instrumentation of agents, tools, etc."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from machine_core.plugins.observability_support import ObservabilitySupportPlugin
from machine_core.plugins.observability_support.tracer import MachineTracer
from machine_core.plugins.observability_support.config import ObservabilityConfig
from machine_core.plugins.observability_support.spans import SpanAttributes, SpanKind
from tests.observability_support.helpers import InMemorySpanExporter


@pytest.fixture
def tracer_and_exporter():
    exporter = InMemorySpanExporter()
    tracer = MachineTracer.from_config(
        ObservabilityConfig(service_name="test"),
        _test_exporter=exporter,
    )
    return tracer, exporter


async def test_instrument_agent_wraps_run(tracer_and_exporter):
    from machine_core.plugins.observability_support import instrument_agent

    tracer, exporter = tracer_and_exporter

    agent = MagicMock()
    agent.name = "summarizer"
    original_run = AsyncMock(return_value="result")
    agent.run = original_run

    instrumented = instrument_agent(agent, tracer)
    result = await instrumented.run("hello")

    assert result == "result"
    spans = exporter.get_finished_spans()
    assert len(spans) >= 1
    agent_span = [s for s in spans if "summarizer" in s.name]
    assert len(agent_span) == 1
    assert agent_span[0].attributes[SpanAttributes.AGENT_NAME] == "summarizer"


async def test_instrument_tool_wraps_execute(tracer_and_exporter):
    from machine_core.plugins.observability_support import instrument_tool

    tracer, exporter = tracer_and_exporter

    tool = MagicMock()
    tool.name = "search_stations"
    original_execute = AsyncMock(return_value={"results": []})
    tool.execute = original_execute

    instrumented = instrument_tool(tool, tracer)
    result = await instrumented.execute(query="oslo")

    assert result == {"results": []}
    spans = exporter.get_finished_spans()
    tool_spans = [
        s
        for s in spans
        if s.attributes.get(SpanAttributes.TOOL_NAME) == "search_stations"
    ]
    assert len(tool_spans) == 1


async def test_instrument_agent_records_errors(tracer_and_exporter):
    from machine_core.plugins.observability_support import instrument_agent

    tracer, exporter = tracer_and_exporter

    agent = MagicMock()
    agent.name = "failing_agent"
    agent.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))

    instrumented = instrument_agent(agent, tracer)

    with pytest.raises(RuntimeError, match="LLM timeout"):
        await instrumented.run("hello")

    spans = exporter.get_finished_spans()
    assert len(spans) >= 1
    assert spans[0].status.is_ok is False


def test_setup_observability_returns_tracer_and_cost_tracker():
    from machine_core.plugins.observability_support import setup_observability

    config = ObservabilityConfig(exporter="console", service_name="my-app")
    tracer, cost_tracker = setup_observability(config)
    assert isinstance(tracer, MachineTracer)
    from machine_core.plugins.observability_support.cost import CostTracker

    assert isinstance(cost_tracker, CostTracker)


def test_setup_observability_disabled():
    from machine_core.plugins.observability_support import setup_observability

    config = ObservabilityConfig(enabled=False)
    tracer, cost_tracker = setup_observability(config)
    with tracer.span("test", kind=SpanKind.AGENT_CALL):
        pass
