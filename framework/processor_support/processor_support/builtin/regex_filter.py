"""Configurable regex filter processor.

Block text matching specific patterns, or only allow text matching
specific patterns. Block patterns take precedence over allow patterns.
"""

from __future__ import annotations

import re

from ..base import Processor, ProcessorData, ProcessorResult, TripWire


class RegexFilterProcessor(Processor):
    """Block or allow text based on regex patterns.

    Args:
        block_patterns: Regexes that cause TripWire if matched.
        allow_patterns: If set, only text matching at least one is allowed.
    """

    name = "regex_filter"
    type = "both"

    def __init__(
        self,
        block_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
    ) -> None:
        self._block = [re.compile(p) for p in (block_patterns or [])]
        self._allow = [re.compile(p) for p in (allow_patterns or [])]

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Apply block/allow regex filters."""
        # Block patterns checked first
        for regex in self._block:
            if regex.search(data.text):
                return TripWire(
                    processor_name=self.name,
                    reason=f"Blocked by pattern: {regex.pattern}",
                )

        # Allow patterns: if any are defined, at least one must match
        if self._allow:
            if not any(regex.search(data.text) for regex in self._allow):
                return TripWire(
                    processor_name=self.name,
                    reason="Text did not match any allow pattern",
                )

        return data
