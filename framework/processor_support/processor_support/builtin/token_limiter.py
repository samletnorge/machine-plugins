"""Token limiter processor.

Counts tokens using tiktoken. Can truncate or block inputs exceeding the limit.
"""

from __future__ import annotations

from typing import Literal

import tiktoken

from ..base import Processor, ProcessorData, ProcessorResult, TripWire


class TokenLimiterProcessor(Processor):
    """Count tokens and optionally truncate or block.

    Args:
        max_tokens: Maximum allowed token count.
        action: 'truncate' to trim text, 'block' to return TripWire.
        model: Model name for tiktoken encoding (default: gpt-4o).
    """

    name = "token_limiter"
    type = "input"

    def __init__(
        self,
        max_tokens: int,
        action: Literal["truncate", "block"] = "truncate",
        model: str = "gpt-4o",
    ) -> None:
        self.max_tokens = max_tokens
        self.action = action
        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Count tokens and enforce limit."""
        tokens = self._encoding.encode(data.text)
        token_count = len(tokens)
        new_meta = {**data.metadata, "token_count": token_count}

        if token_count <= self.max_tokens:
            return data.replace(metadata=new_meta)

        if self.action == "block":
            return TripWire(
                processor_name=self.name,
                reason=f"Token limit exceeded: {token_count} > {self.max_tokens}",
            )

        # Truncate
        truncated_tokens = tokens[: self.max_tokens]
        truncated_text = self._encoding.decode(truncated_tokens)
        new_meta["token_count"] = self.max_tokens
        new_meta["truncated"] = True
        return data.replace(text=truncated_text, metadata=new_meta)
