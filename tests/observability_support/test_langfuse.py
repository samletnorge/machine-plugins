"""Tests for the Langfuse exporter."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from observability_support.exporters.langfuse import (
    build_langfuse_exporter,
    LangfuseSpanExporter,
)
from observability_support.config import ObservabilityConfig
from opentelemetry.sdk.trace.export import SpanExportResult


def test_build_langfuse_requires_keys():
    config = ObservabilityConfig(exporter="langfuse", extra={})
    with pytest.raises(ValueError, match="public_key"):
        build_langfuse_exporter(config)


def test_build_langfuse_with_keys():
    config = ObservabilityConfig(
        exporter="langfuse",
        extra={"public_key": "pk-123", "secret_key": "sk-456"},
    )
    mock_langfuse_cls = MagicMock()
    mock_langfuse_module = MagicMock()
    mock_langfuse_module.Langfuse = mock_langfuse_cls
    with patch.dict(sys.modules, {"langfuse": mock_langfuse_module}):
        exporter = build_langfuse_exporter(config)
        assert isinstance(exporter, LangfuseSpanExporter)


def test_langfuse_exporter_export_translates_spans():
    mock_client = MagicMock()
    exporter = LangfuseSpanExporter(client=mock_client)

    mock_span = MagicMock()
    mock_span.name = "llm-call"
    mock_span.attributes = {
        "machine.model.name": "gpt-4o",
        "machine.token.input": 100,
        "machine.token.output": 50,
        "machine.span.kind": "llm.request",
        "machine.agent.name": "summarizer",
    }
    mock_span.start_time = 1000000000
    mock_span.end_time = 2000000000
    mock_span.context = MagicMock()
    mock_span.context.trace_id = 12345
    mock_span.context.span_id = 67890
    mock_span.parent = None
    mock_span.status = MagicMock()
    mock_span.status.is_ok = True

    result = exporter.export([mock_span])
    assert result == SpanExportResult.SUCCESS
    assert mock_client.generation.called or mock_client.span.called
