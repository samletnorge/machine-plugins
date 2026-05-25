"""Tests for the Sentry exporter."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from observability_support.exporters.sentry import (
    build_sentry_exporter,
)
from observability_support.config import ObservabilityConfig


def test_build_sentry_requires_dsn():
    config = ObservabilityConfig(exporter="sentry", extra={})
    with pytest.raises(ValueError, match="dsn"):
        build_sentry_exporter(config)


def test_build_sentry_with_dsn():
    config = ObservabilityConfig(
        exporter="sentry",
        extra={"dsn": "https://key@sentry.io/123"},
    )
    mock_sentry = MagicMock()
    mock_integrations = MagicMock()
    mock_processor = MagicMock()
    mock_integrations.SentrySpanProcessor = mock_processor
    with patch.dict(
        sys.modules,
        {
            "sentry_sdk": mock_sentry,
            "sentry_sdk.integrations": MagicMock(),
            "sentry_sdk.integrations.opentelemetry": mock_integrations,
        },
    ):
        exporter = build_sentry_exporter(config)
        mock_sentry.init.assert_called_once()
        assert exporter is not None
