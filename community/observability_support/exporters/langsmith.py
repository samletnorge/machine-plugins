"""LangSmith exporter — translates OTel spans to LangSmith runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from observability_support.config import ObservabilityConfig
from observability_support.spans import SpanAttributes


def build_langsmith_exporter(config: ObservabilityConfig) -> SpanExporter:
    """Build a LangSmith exporter from config."""
    api_key = config.extra.get("api_key")
    if not api_key:
        raise ValueError("LangSmith exporter requires 'api_key' in extra config.")

    try:
        from langsmith import Client
    except ImportError:
        raise ImportError(
            "LangSmith exporter requires the langsmith package. "
            "Install with: pip install langsmith"
        )

    project = config.extra.get("project", "default")
    endpoint = config.extra.get("endpoint", "https://api.smith.langchain.com")
    client = Client(api_url=endpoint, api_key=api_key)
    return LangSmithSpanExporter(client=client, project=project)


class LangSmithSpanExporter(SpanExporter):
    """Translates OTel spans to LangSmith runs."""

    def __init__(self, client: object, project: str = "default") -> None:
        self._client = client
        self._project = project

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            for span in spans:
                attrs = dict(span.attributes or {})
                kind = attrs.get("machine.span.kind", "chain")
                run_type = "llm" if kind == "llm.request" else "chain"

                self._client.create_run(  # type: ignore
                    name=span.name,
                    run_type=run_type,
                    project_name=self._project,
                    inputs={"attributes": attrs},
                    start_time=datetime.fromtimestamp(
                        (span.start_time or 0) / 1e9, tz=timezone.utc
                    ),
                    end_time=datetime.fromtimestamp(
                        (span.end_time or 0) / 1e9, tz=timezone.utc
                    ),
                    extra={"metadata": attrs},
                )
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
