"""PII detection processor.

Detects emails, phone numbers, SSNs, and credit card numbers via regex.
Supports two modes: 'block' (return TripWire) or 'redact' (replace with placeholders).
"""

from __future__ import annotations

import re
from typing import Literal

from ..base import Processor, ProcessorData, ProcessorResult, TripWire


# Default PII patterns
_DEFAULT_PATTERNS: dict[str, tuple[str, str]] = {
    # pattern_name: (regex, replacement_placeholder)
    "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
    "phone": (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]"),
    "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    "credit_card": (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CREDIT_CARD]"),
}


class PIIProcessor(Processor):
    """Detect and optionally redact PII from text.

    Args:
        action: 'block' to return TripWire, 'redact' to replace PII with placeholders.
        extra_patterns: Additional regex patterns as {name: regex_string}.
    """

    name = "pii"
    type = "input"

    def __init__(
        self,
        action: Literal["block", "redact"] = "block",
        extra_patterns: dict[str, str] | None = None,
    ) -> None:
        self.action = action
        # Build compiled patterns: {name: (compiled_regex, placeholder)}
        self._patterns: dict[str, tuple[re.Pattern[str], str]] = {}
        for pname, (pattern, placeholder) in _DEFAULT_PATTERNS.items():
            self._patterns[pname] = (re.compile(pattern), placeholder)
        if extra_patterns:
            for pname, pattern in extra_patterns.items():
                self._patterns[pname] = (
                    re.compile(pattern),
                    f"[{pname.upper()}]",
                )

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Scan text for PII patterns."""
        for pname, (regex, placeholder) in self._patterns.items():
            if regex.search(data.text):
                if self.action == "block":
                    return TripWire(
                        processor_name=self.name,
                        reason=f"PII detected: {pname} found in text",
                    )
        if self.action == "redact":
            redacted = data.text
            for pname, (regex, placeholder) in self._patterns.items():
                redacted = regex.sub(placeholder, redacted)
            if redacted != data.text:
                return data.replace(text=redacted)
        return data
