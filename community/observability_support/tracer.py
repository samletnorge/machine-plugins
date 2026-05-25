"""MachineTracer — OpenTelemetry wrapper for machine-core."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import Any, Generator, AsyncGenerator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.trace import StatusCode, Span

from observability_support.config import ObservabilityConfig
from observability_support.spans import (
    SpanKind,
    create_span_attributes,
)


class _NoOpSpanContext:
    """Context manager that does nothing when observability is disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MachineTracer:
    """Wraps OpenTelemetry TracerProvider with machine-core conventions."""

    def __init__(self, provider: TracerProvider | None, enabled: bool = True) -> None:
        self._provider = provider
        self._enabled = enabled
        self._tracer = provider.get_tracer("machine-core") if provider else None

    @classmethod
    def from_config(
        cls,
        config: ObservabilityConfig,
        _test_exporter: SpanExporter | None = None,
    ) -> MachineTracer:
        """Create tracer from config. _test_exporter overrides for testing."""
        if not config.enabled:
            return cls(provider=None, enabled=False)

        provider = TracerProvider()

        if _test_exporter:
            provider.add_span_processor(SimpleSpanProcessor(_test_exporter))

        return cls(provider=provider, enabled=True)

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind,
        **attr_kwargs: Any,
    ) -> Generator[Span | _NoOpSpanContext, None, None]:
        """Create a traced span as a sync context manager."""
        if not self._enabled or not self._tracer:
            yield _NoOpSpanContext()
            return

        attributes = create_span_attributes(kind=kind, **attr_kwargs)
        with self._tracer.start_as_current_span(name, attributes=attributes) as span:
            try:
                yield span
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        kind: SpanKind,
        **attr_kwargs: Any,
    ) -> AsyncGenerator[Span | _NoOpSpanContext, None]:
        """Create a traced span as an async context manager."""
        if not self._enabled or not self._tracer:
            yield _NoOpSpanContext()
            return

        attributes = create_span_attributes(kind=kind, **attr_kwargs)
        with self._tracer.start_as_current_span(name, attributes=attributes) as span:
            try:
                yield span
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    def add_exporter(self, exporter: SpanExporter) -> None:
        """Add an exporter to the tracer provider. Used by plugin setup."""
        if self._provider:
            self._provider.add_span_processor(SimpleSpanProcessor(exporter))

    def shutdown(self) -> None:
        """Flush and shut down the tracer provider."""
        if self._provider:
            self._provider.shutdown()
