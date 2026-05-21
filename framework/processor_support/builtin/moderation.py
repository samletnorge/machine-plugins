"""Content moderation processor.

Calls a user-provided async moderation function (e.g., OpenAI moderation API)
to check if content is harmful. Returns TripWire if flagged.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ..base import Processor, ProcessorData, ProcessorResult, TripWire

# Type for the moderation callback
ModerateFn = Callable[[str], Awaitable[dict[str, Any]]]


class ModerationProcessor(Processor):
    """Check content against a moderation function.

    The moderate_fn must be an async callable that takes a string and returns
    a dict with at least:
        {"flagged": bool, "categories": list[str]}

    Args:
        moderate_fn: Async function to call for moderation.
    """

    name = "moderation"
    type = "both"

    def __init__(self, moderate_fn: ModerateFn) -> None:
        self._moderate_fn = moderate_fn

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Run moderation check."""
        result = await self._moderate_fn(data.text)
        new_meta = {**data.metadata, "moderation_result": result}

        if result.get("flagged", False):
            categories = result.get("categories", [])
            return TripWire(
                processor_name=self.name,
                reason=f"Content moderation flagged: {', '.join(categories)}",
            )

        return data.replace(metadata=new_meta)
