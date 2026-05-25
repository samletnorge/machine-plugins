"""Tests for the Datadog exporter."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from observability_support.exporters.datadog import (
    build_datadog_exporter,
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


def test_build_datadog_default(mock_otlp_module):
    config = ObservabilityConfig(exporter="datadog")
    exporter = build_datadog_exporter(config)
    assert exporter is not None


def test_build_datadog_custom_endpoint(mock_otlp_module):
    config = ObservabilityConfig(
        exporter="datadog",
        endpoint="https://trace.agent.datadoghq.com/v1/traces",
        extra={"dd_api_key": "abc123"},
    )
    build_datadog_exporter(config)
    assert mock_otlp_module.called
