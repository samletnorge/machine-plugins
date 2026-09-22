"""Console span exporter — prints spans to stdout for development."""

from __future__ import annotations

import sys
from typing import IO, Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class ConsoleSpanExporter(SpanExporter):
    """Exports spans as human-readable text to a stream."""

    def __init__(self, output: IO[str] | None = None) -> None:
        self._output = output or sys.stdout

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            duration_ns = (span.end_time or 0) - (span.start_time or 0)
            duration_ms = duration_ns / 1_000_000

            attrs = dict(span.attributes or {})
            attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items())

            line = f"[TRACE] {span.name} | duration={duration_ms:.1f}ms | {attr_str}\n"
            self._output.write(line)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
