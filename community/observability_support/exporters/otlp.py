"""Generic OTLP HTTP exporter — works with any OTel-compatible backend."""

from __future__ import annotations

from opentelemetry.sdk.trace.export import SpanExporter

from machine_core.plugins.observability_support.config import ObservabilityConfig

_DEFAULT_ENDPOINT = "http://localhost:4318/v1/traces"


def build_otlp_exporter(config: ObservabilityConfig) -> SpanExporter:
    """Build an OTLP HTTP span exporter."""
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        raise ImportError(
            "OTLP HTTP exporter requires opentelemetry-exporter-otlp-proto-http. "
            "Install with: pip install opentelemetry-exporter-otlp-proto-http"
        )

    endpoint = config.endpoint or _DEFAULT_ENDPOINT
    headers = config.extra.get("headers")

    kwargs: dict = {"endpoint": endpoint}
    if headers:
        kwargs["headers"] = headers

    return OTLPSpanExporter(**kwargs)
