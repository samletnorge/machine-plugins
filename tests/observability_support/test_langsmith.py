"""Tests for the LangSmith exporter."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from machine_core.plugins.observability_support.exporters.langsmith import (
    build_langsmith_exporter,
    LangSmithSpanExporter,
)
from machine_core.plugins.observability_support.config import ObservabilityConfig
from opentelemetry.sdk.trace.export import SpanExportResult


def test_build_langsmith_requires_api_key():
    config = ObservabilityConfig(exporter="langsmith", extra={})
    with pytest.raises(ValueError, match="api_key"):
        build_langsmith_exporter(config)


def test_build_langsmith_with_key():
    config = ObservabilityConfig(
        exporter="langsmith",
        extra={"api_key": "ls-123", "project": "my-project"},
    )
    mock_client_cls = MagicMock()
    mock_langsmith_module = MagicMock()
    mock_langsmith_module.Client = mock_client_cls
    with patch.dict(sys.modules, {"langsmith": mock_langsmith_module}):
        exporter = build_langsmith_exporter(config)
        assert isinstance(exporter, LangSmithSpanExporter)


def test_langsmith_export_success():
    mock_client = MagicMock()
    exporter = LangSmithSpanExporter(client=mock_client, project="test")

    mock_span = MagicMock()
    mock_span.name = "agent-call"
    mock_span.attributes = {
        "machine.agent.name": "writer",
        "machine.span.kind": "agent.call",
    }
    mock_span.start_time = 1000000000
    mock_span.end_time = 1500000000
    mock_span.context = MagicMock()
    mock_span.context.trace_id = 111
    mock_span.context.span_id = 222
    mock_span.parent = None
    mock_span.status = MagicMock()
    mock_span.status.is_ok = True

    result = exporter.export([mock_span])
    assert result == SpanExportResult.SUCCESS
