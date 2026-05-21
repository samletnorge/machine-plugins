"""Sentry exporter — initializes Sentry SDK with OTel integration."""

from __future__ import annotations

from opentelemetry.sdk.trace.export import SpanExporter

from machine_core.plugins.observability_support.config import ObservabilityConfig


def build_sentry_exporter(config: ObservabilityConfig) -> SpanExporter:
    """Build Sentry exporter by initializing the Sentry SDK with OTel tracing."""
    dsn = config.extra.get("dsn")
    if not dsn:
        raise ValueError("Sentry exporter requires 'dsn' in extra config.")

    try:
        import sentry_sdk
        from sentry_sdk.integrations.opentelemetry import SentrySpanProcessor
    except ImportError:
        raise ImportError(
            "Sentry exporter requires sentry-sdk[opentelemetry]. "
            "Install with: pip install sentry-sdk[opentelemetry]"
        )

    traces_sample_rate = config.extra.get("traces_sample_rate", config.sample_rate)
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=traces_sample_rate,
        instrumenter="otel",
    )

    return SentrySpanProcessor()
