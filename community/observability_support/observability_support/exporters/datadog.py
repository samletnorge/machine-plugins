"""Datadog exporter — sends spans via OTLP to Datadog Agent."""

from __future__ import annotations

from opentelemetry.sdk.trace.export import SpanExporter

from observability_support.config import ObservabilityConfig

# Datadog Agent accepts OTLP on port 4318 by default
_DEFAULT_DD_ENDPOINT = "http://localhost:4318/v1/traces"


def build_datadog_exporter(config: ObservabilityConfig) -> SpanExporter:
    """Build exporter for Datadog (via OTLP to the Datadog Agent)."""
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        raise ImportError(
            "Datadog exporter requires opentelemetry-exporter-otlp-proto-http. "
            "Install with: pip install opentelemetry-exporter-otlp-proto-http"
        )

    endpoint = config.endpoint or _DEFAULT_DD_ENDPOINT
    headers: dict[str, str] = {}

    dd_api_key = config.extra.get("dd_api_key")
    if dd_api_key:
        headers["DD-API-KEY"] = dd_api_key

    return OTLPSpanExporter(endpoint=endpoint, headers=headers or None)
