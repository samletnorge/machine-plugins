"""Tests for observability configuration."""

import pytest
from machine_core.plugins.observability_support.config import ObservabilityConfig


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
