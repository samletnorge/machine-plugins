"""Langfuse exporter — translates OTel spans to Langfuse traces/generations."""

from __future__ import annotations

from typing import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from observability_support.config import ObservabilityConfig
from observability_support.spans import SpanAttributes


def build_langfuse_exporter(config: ObservabilityConfig) -> SpanExporter:
    """Build a Langfuse exporter from config."""
    public_key = config.extra.get("public_key")
    secret_key = config.extra.get("secret_key")
    if not public_key or not secret_key:
        raise ValueError(
            "Langfuse exporter requires 'public_key' and 'secret_key' in extra config."
        )

    try:
        from langfuse import Langfuse
    except ImportError:
        raise ImportError(
            "Langfuse exporter requires the langfuse package. "
            "Install with: pip install langfuse"
        )

    host = config.extra.get("host", "https://cloud.langfuse.com")
    client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    return LangfuseSpanExporter(client=client)


class LangfuseSpanExporter(SpanExporter):
    """Translates OTel spans to Langfuse traces and generations."""

    def __init__(self, client: object) -> None:
        self._client = client

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            for span in spans:
                attrs = dict(span.attributes or {})
                kind = attrs.get("machine.span.kind", "")
                trace_id = (
                    format(span.context.trace_id, "032x") if span.context else None
                )

                if kind == "llm.request":
                    self._client.generation(  # type: ignore
                        trace_id=trace_id,
                        name=span.name,
                        model=attrs.get(SpanAttributes.MODEL_NAME),
                        usage={
                            "input": attrs.get(SpanAttributes.TOKEN_INPUT, 0),
                            "output": attrs.get(SpanAttributes.TOKEN_OUTPUT, 0),
                        },
                        metadata={
                            k: v
                            for k, v in attrs.items()
                            if not k.startswith("machine.token")
                        },
                    )
                else:
                    self._client.span(  # type: ignore
                        trace_id=trace_id,
                        name=span.name,
                        metadata=attrs,
                    )
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        if hasattr(self._client, "flush"):
            self._client.flush()  # type: ignore

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        if hasattr(self._client, "flush"):
            self._client.flush()  # type: ignore
        return True
