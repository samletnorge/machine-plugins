"""Tests for the generic OTLP HTTP exporter."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from observability_support.exporters.otlp import (
    build_otlp_exporter,
)
from observability_support.config import ObservabilityConfig


@pytest.fixture(autouse=True)
def mock_otlp_module():
    """Mock the OTLP exporter module since it's an optional dependency."""
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


def test_build_otlp_exporter_default_endpoint(mock_otlp_module):
    config = ObservabilityConfig(exporter="otlp")
    exporter = build_otlp_exporter(config)
    mock_otlp_module.assert_called_once()
    assert exporter is not None


def test_build_otlp_exporter_custom_endpoint(mock_otlp_module):
    config = ObservabilityConfig(exporter="otlp", endpoint="http://my-collector:4318")
    build_otlp_exporter(config)
    call_kwargs = mock_otlp_module.call_args
    assert "http://my-collector:4318" in str(call_kwargs)


def test_build_otlp_exporter_with_headers(mock_otlp_module):
    config = ObservabilityConfig(
        exporter="otlp",
        extra={"headers": {"Authorization": "Bearer tok123"}},
    )
    build_otlp_exporter(config)
    assert mock_otlp_module.called
