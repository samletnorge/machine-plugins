"""Shared test utilities for observability tests."""

from typing import Sequence
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class InMemorySpanExporter(SpanExporter):
    """Simple in-memory exporter for testing."""

    def __init__(self):
        self._spans: list[ReadableSpan] = []
        self._stopped = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._stopped:
            return SpanExportResult.FAILURE
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self) -> list[ReadableSpan]:
        return list(self._spans)

    def clear(self):
        self._spans.clear()

    def shutdown(self) -> None:
        self._stopped = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
