"""Cost guard processor.

Estimates the cost of a request based on token count and aborts
if it exceeds a budget threshold.
"""

from __future__ import annotations

from ..base import Processor, ProcessorData, ProcessorResult, TripWire


class CostGuardProcessor(Processor):
    """Block requests that would exceed a cost budget.

    Args:
        max_cost_usd: Maximum allowed estimated cost in USD.
        cost_per_1k_tokens: Cost per 1,000 tokens (input pricing).
    """

    name = "cost_guard"
    type = "input"

    def __init__(self, max_cost_usd: float, cost_per_1k_tokens: float) -> None:
        self.max_cost_usd = max_cost_usd
        self.cost_per_1k_tokens = cost_per_1k_tokens

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Estimate cost and block if over budget."""
        token_count = data.metadata.get("token_count")
        if token_count is None:
            # Rough estimate: ~4 chars per token
            token_count = max(1, len(data.text) // 4)

        estimated_cost = (token_count / 1000) * self.cost_per_1k_tokens
        new_meta = {**data.metadata, "estimated_cost_usd": estimated_cost}

        if estimated_cost > self.max_cost_usd:
            return TripWire(
                processor_name=self.name,
                reason=(
                    f"Cost limit exceeded: estimated ${estimated_cost:.4f} "
                    f"> budget ${self.max_cost_usd:.4f}"
                ),
            )

        return data.replace(metadata=new_meta)
