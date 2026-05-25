"""Tests for the console span exporter."""

import pytest
from io import StringIO
from observability_support.exporters.console import (
    ConsoleSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult


@pytest.fixture
def console_setup():
    output = StringIO()
    exporter = ConsoleSpanExporter(output=output)
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    return tracer, output


def test_console_exports_span_name(console_setup):
    tracer, output = console_setup
    with tracer.start_as_current_span(
        "my-operation", attributes={"machine.agent.name": "test"}
    ):
        pass
    text = output.getvalue()
    assert "my-operation" in text


def test_console_exports_attributes(console_setup):
    tracer, output = console_setup
    with tracer.start_as_current_span(
        "op", attributes={"machine.model.name": "gpt-4o", "machine.token.input": 500}
    ):
        pass
    text = output.getvalue()
    assert "gpt-4o" in text
    assert "500" in text


def test_console_exports_duration(console_setup):
    tracer, output = console_setup
    with tracer.start_as_current_span("op"):
        pass
    text = output.getvalue()
    assert "duration" in text.lower()


def test_console_export_returns_success():
    exporter = ConsoleSpanExporter(output=StringIO())
    result = exporter.export([])
    assert result == SpanExportResult.SUCCESS
