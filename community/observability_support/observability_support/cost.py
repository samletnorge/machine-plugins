"""Token counting and cost calculation for LLM usage."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class ModelPricing:
    """Pricing for a specific model (USD per 1,000 tokens)."""

    model: str
    input_cost_per_1k: float
    output_cost_per_1k: float


@dataclass
class UsageRecord:
    """Single LLM usage record."""

    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    workflow_name: str | None = None


# Prices as of May 2026 — update periodically
DEFAULT_PRICING: list[ModelPricing] = [
    ModelPricing("gpt-4o", 0.005, 0.015),
    ModelPricing("gpt-4o-mini", 0.00015, 0.0006),
    ModelPricing("gpt-4.1", 0.002, 0.008),
    ModelPricing("gpt-4.1-mini", 0.0004, 0.0016),
    ModelPricing("gpt-4.1-nano", 0.0001, 0.0004),
    ModelPricing("o3", 0.01, 0.04),
    ModelPricing("o3-mini", 0.0011, 0.0044),
    ModelPricing("o4-mini", 0.0011, 0.0044),
    ModelPricing("claude-sonnet-4-20250514", 0.003, 0.015),
    ModelPricing("claude-opus-4-20250514", 0.015, 0.075),
    ModelPricing("claude-haiku-35", 0.0008, 0.004),
    ModelPricing("gemini-2.5-pro", 0.00125, 0.01),
    ModelPricing("gemini-2.5-flash", 0.00015, 0.0006),
    ModelPricing("gemini-2.0-flash", 0.0001, 0.0004),
]


class CostTracker:
    """Tracks token usage and calculates costs across agents and workflows."""

    def __init__(self, pricing: Sequence[ModelPricing] | None = None) -> None:
        self._pricing: dict[str, ModelPricing] = {
            p.model: p for p in (pricing or DEFAULT_PRICING)
        }
        self._records: list[UsageRecord] = []

    def record(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        workflow_name: str | None = None,
    ) -> UsageRecord:
        """Record a single LLM call's token usage."""
        pricing = self._pricing.get(model)
        if pricing:
            cost = (input_tokens / 1000 * pricing.input_cost_per_1k) + (
                output_tokens / 1000 * pricing.output_cost_per_1k
            )
        else:
            cost = 0.0

        rec = UsageRecord(
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            workflow_name=workflow_name,
        )
        self._records.append(rec)
        return rec

    def get_records(self) -> list[UsageRecord]:
        return list(self._records)

    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self._records)

    def total_tokens(self) -> tuple[int, int]:
        """Return (total_input, total_output) tokens."""
        inp = sum(r.input_tokens for r in self._records)
        out = sum(r.output_tokens for r in self._records)
        return inp, out

    def cost_by_agent(self) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for r in self._records:
            result[r.agent_name] += r.cost_usd
        return dict(result)

    def cost_by_model(self) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for r in self._records:
            result[r.model] += r.cost_usd
        return dict(result)

    def reset(self) -> None:
        self._records.clear()
