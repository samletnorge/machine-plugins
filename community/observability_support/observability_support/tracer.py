"""MachineTracer — OpenTelemetry wrapper for machine-core."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import Any, Generator, AsyncGenerator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import StatusCode, Span

from observability_support.config import ObservabilityConfig, SpanConfig
from observability_support.spans import (
    SpanAttributes,
    SpanKind,
    create_span_attributes,
    truncate_attribute_value,
    truncate_attributes,
)

_EXPORTER_BUILDERS = {
    "otlp": ("observability_support.exporters.otlp", "build_otlp_exporter"),
    "datadog": ("observability_support.exporters.datadog", "build_datadog_exporter"),
    "jaeger": ("observability_support.exporters.jaeger", "build_jaeger_exporter"),
    "langfuse": (
        "observability_support.exporters.langfuse",
        "build_langfuse_exporter",
    ),
    "langsmith": (
        "observability_support.exporters.langsmith",
        "build_langsmith_exporter",
    ),
    "sentry": ("observability_support.exporters.sentry", "build_sentry_exporter"),
}


def resolve_exporter(config: ObservabilityConfig) -> SpanExporter | None:
    """Resolve an exporter instance from ``config.exporter`` by name."""
    name = (config.exporter or "").lower()
    if not name:
        return None
    try:
        if name == "console":
            from observability_support.exporters.console import ConsoleSpanExporter

            return ConsoleSpanExporter()
        if name in _EXPORTER_BUILDERS:
            import importlib

            module_name, func_name = _EXPORTER_BUILDERS[name]
            builder = getattr(importlib.import_module(module_name), func_name)
            return builder(config)
    except Exception:  # noqa: BLE001 - a missing backend must not break startup
        return None
    return None


class _NoOpSpanContext:
    """Context manager that does nothing when observability is disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _SpanProxy:
    """Wraps a real span to apply SpanConfig rules on attribute writes.

    Values set both at span creation and later via ``set_attribute`` are
    truncated to ``max_attribute_length``, and input/output attributes are
    dropped entirely unless the corresponding recording flag is enabled.
    All other attribute access is delegated to the wrapped span.
    """

    def __init__(self, span: Span, config: SpanConfig) -> None:
        object.__setattr__(self, "_span", span)
        object.__setattr__(self, "_config", config)

    def set_attribute(self, key: str, value: Any) -> None:
        if key == SpanAttributes.INPUT and not self._config.record_input:
            return
        if key == SpanAttributes.OUTPUT and not self._config.record_output:
            return
        value = truncate_attribute_value(value, self._config.max_attribute_length)
        self._span.set_attribute(key, value)

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_span"), name)


class MachineTracer:
    """Wraps OpenTelemetry TracerProvider with machine-core conventions."""

    def __init__(
        self,
        provider: TracerProvider | None,
        enabled: bool = True,
        span_config: SpanConfig | None = None,
    ) -> None:
        self._provider = provider
        self._enabled = enabled
        self._span_config = span_config or SpanConfig()
        self._tracer = provider.get_tracer("machine-core") if provider else None

    @classmethod
    def from_config(
        cls,
        config: ObservabilityConfig,
        _test_exporter: SpanExporter | None = None,
    ) -> MachineTracer:
        """Create tracer from config. _test_exporter overrides for testing."""
        if not config.enabled:
            return cls(provider=None, enabled=False, span_config=config.span)

        resource = Resource.create({"service.name": config.service_name})
        provider_kwargs: dict[str, Any] = {"resource": resource}
        if config.sample_rate < 1.0:
            provider_kwargs["sampler"] = TraceIdRatioBased(config.sample_rate)
        provider = TracerProvider(**provider_kwargs)

        exporter = _test_exporter or resolve_exporter(config)
        if exporter is not None:
            provider.add_span_processor(SimpleSpanProcessor(exporter))

        return cls(provider=provider, enabled=True, span_config=config.span)

    def _prepare_attributes(
        self, kind: SpanKind, attr_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        kwargs = dict(attr_kwargs)
        if not self._span_config.record_input:
            kwargs.pop("input", None)
        if not self._span_config.record_output:
            kwargs.pop("output", None)
        attributes = create_span_attributes(kind=kind, **kwargs)
        return truncate_attributes(
            attributes, self._span_config.max_attribute_length
        )

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

        attributes = self._prepare_attributes(kind, attr_kwargs)
        with self._tracer.start_as_current_span(
            name,
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield _SpanProxy(span, self._span_config)
            except Exception as exc:
                if self._span_config.record_exceptions:
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

        attributes = self._prepare_attributes(kind, attr_kwargs)
        with self._tracer.start_as_current_span(
            name,
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield _SpanProxy(span, self._span_config)
            except Exception as exc:
                if self._span_config.record_exceptions:
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
