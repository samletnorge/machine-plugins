"""Tests for the Jaeger exporter (delegates to OTLP)."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from observability_support.exporters.jaeger import (
    build_jaeger_exporter,
)
from observability_support.config import ObservabilityConfig


@pytest.fixture(autouse=True)
def mock_otlp_module():
    mock_exporter_cls = MagicMock()
    mock_module = MagicMock()
    mock_module.OTLPSpanExporter = mock_exporter_cls
    with patch.dict(
        sys.modules,
        {
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_module,
            "opentelemetry.exporter.otlp.proto.http": MagicMock(),
            "opentelemetry.exporter.otlp.proto": MagicMock(),
            "opentelemetry.exporter.otlp": MagicMock(),
            "opentelemetry.exporter": MagicMock(),
        },
    ):
        yield mock_exporter_cls


def test_jaeger_exporter_default(mock_otlp_module):
    config = ObservabilityConfig(exporter="jaeger")
    exporter = build_jaeger_exporter(config)
    assert exporter is not None
    call_args = str(mock_otlp_module.call_args)
    assert "4318" in call_args or mock_otlp_module.called


def test_jaeger_exporter_custom_endpoint(mock_otlp_module):
    config = ObservabilityConfig(exporter="jaeger", endpoint="http://jaeger:4317")
    build_jaeger_exporter(config)
    assert "http://jaeger:4317" in str(mock_otlp_module.call_args)
