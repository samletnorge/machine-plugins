"""Shared fixtures for observability tests."""

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from tests.observability_support.helpers import InMemorySpanExporter


@pytest.fixture
def memory_exporter():
    return InMemorySpanExporter()


@pytest.fixture
def tracer_provider(memory_exporter):
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
    return provider
