"""Tests for observability configuration."""

import pytest
from observability_support.config import ObservabilityConfig, SpanConfig


def test_default_config():
    cfg = ObservabilityConfig()
    assert cfg.exporter == "console"
    assert cfg.enabled is True
    assert cfg.service_name == "machine-core"
    assert cfg.extra == {}


def test_config_with_exporter_string():
    cfg = ObservabilityConfig(exporter="langfuse")
    assert cfg.exporter == "langfuse"


def test_config_disabled():
    cfg = ObservabilityConfig(enabled=False)
    assert cfg.enabled is False


def test_config_custom_service_name():
    cfg = ObservabilityConfig(service_name="drivstoffapp-backend")
    assert cfg.service_name == "drivstoffapp-backend"


def test_config_extra_options():
    cfg = ObservabilityConfig(
        exporter="langfuse",
        extra={
            "public_key": "pk-123",
            "secret_key": "sk-456",
            "host": "https://cloud.langfuse.com",
        },
    )
    assert cfg.extra["public_key"] == "pk-123"


def test_config_endpoint_override():
    cfg = ObservabilityConfig(exporter="otlp", endpoint="http://localhost:4318")
    assert cfg.endpoint == "http://localhost:4318"


def test_config_sample_rate():
    cfg = ObservabilityConfig(sample_rate=0.5)
    assert cfg.sample_rate == 0.5


def test_config_sample_rate_bounds():
    with pytest.raises(ValueError):
        ObservabilityConfig(sample_rate=1.5)
    with pytest.raises(ValueError):
        ObservabilityConfig(sample_rate=-0.1)


def test_config_has_default_span_config():
    cfg = ObservabilityConfig()
    assert isinstance(cfg.span, SpanConfig)
    assert cfg.span.record_exceptions is True
    assert cfg.span.record_input is False
    assert cfg.span.record_output is False
    assert cfg.span.max_attribute_length == 1024


def test_config_accepts_custom_span_config():
    cfg = ObservabilityConfig(
        span=SpanConfig(
            record_exceptions=False,
            record_input=True,
            record_output=True,
            max_attribute_length=10,
        )
    )
    assert cfg.span.record_exceptions is False
    assert cfg.span.record_input is True
    assert cfg.span.record_output is True
    assert cfg.span.max_attribute_length == 10
