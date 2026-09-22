"""Prompt injection defense processor.

Detects common prompt injection patterns via regex. Returns TripWire
if suspicious patterns are found.
"""

from __future__ import annotations

import re

from ..base import Processor, ProcessorData, ProcessorResult, TripWire


# Common injection patterns (case-insensitive)
_DEFAULT_PATTERNS: list[str] = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)ignore\s+(all\s+)?prior\s+instructions",
    r"(?i)disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(?i)your\s+new\s+(system\s+)?prompt\s+is",
    r"(?i)you\s+are\s+now\s+a\s+different",
    r"(?i)pretend\s+you\s+are\s+\w+\s+who\s+can",
    r"(?i)act\s+as\s+if\s+you\s+have\s+no\s+(restrictions|filters|rules)",
    r"(?i)SYSTEM:\s*you\s+are",
    r"(?i)---\s*\n\s*SYSTEM:",
    r"(?i)\bDAN\b.*\b(do\s+anything|no\s+restrictions)",
    r"(?i)jailbreak",
    r"(?i)bypass\s+(your\s+)?(safety|content|moderation)\s+(filters?|rules?|guidelines?)",
]


class PromptInjectionProcessor(Processor):
    """Detect prompt injection attempts via pattern matching.

    Args:
        extra_patterns: Additional regex patterns to check.
    """

    name = "prompt_injection"
    type = "input"

    def __init__(self, extra_patterns: list[str] | None = None) -> None:
        patterns = _DEFAULT_PATTERNS.copy()
        if extra_patterns:
            patterns.extend(extra_patterns)
        self._compiled = [re.compile(p) for p in patterns]

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Scan for injection patterns."""
        for regex in self._compiled:
            if regex.search(data.text):
                return TripWire(
                    processor_name=self.name,
                    reason=f"Prompt injection detected: matched pattern '{regex.pattern}'",
                )
        return data
