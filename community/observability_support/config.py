"""Observability configuration for machine-core."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ObservabilityConfig(BaseModel):
    """Configuration for the observability-support plugin.

    The `exporter` field is a string name (e.g. "console", "langfuse", "otlp").
    Exporters register themselves via ctx.register("observability_exporter", name, impl).
    """

    enabled: bool = True
    exporter: str = "console"
    service_name: str = "machine-core"
    endpoint: str | None = None
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    extra: dict[str, Any] = Field(default_factory=dict)


class SpanConfig(BaseModel):
    """Configuration for individual span behavior."""

    record_exceptions: bool = True
    record_input: bool = False
    record_output: bool = False
    max_attribute_length: int = 1024
