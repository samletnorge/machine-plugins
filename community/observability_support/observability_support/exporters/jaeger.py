"""Jaeger exporter — modern Jaeger accepts OTLP natively."""

from __future__ import annotations

from opentelemetry.sdk.trace.export import SpanExporter

from observability_support.config import ObservabilityConfig

_DEFAULT_JAEGER_ENDPOINT = "http://localhost:4318/v1/traces"


def build_jaeger_exporter(config: ObservabilityConfig) -> SpanExporter:
    """Build exporter for Jaeger (via OTLP, since Jaeger 1.35+ supports OTLP natively)."""
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        raise ImportError(
            "Jaeger exporter requires opentelemetry-exporter-otlp-proto-http. "
            "Install with: pip install opentelemetry-exporter-otlp-proto-http"
        )

    endpoint = config.endpoint or _DEFAULT_JAEGER_ENDPOINT
    return OTLPSpanExporter(endpoint=endpoint)
