"""Tests for token counting and cost calculation."""

import pytest
from machine_core.plugins.observability_support.cost import (
    CostTracker,
    ModelPricing,
    UsageRecord,
    DEFAULT_PRICING,
)


def test_model_pricing():
    p = ModelPricing(model="gpt-4o", input_cost_per_1k=0.005, output_cost_per_1k=0.015)
    assert p.model == "gpt-4o"


def test_default_pricing_includes_common_models():
    models = {p.model for p in DEFAULT_PRICING}
    assert "gpt-4o" in models
    assert "gpt-4o-mini" in models
    assert "claude-sonnet-4-20250514" in models
    assert "claude-haiku-35" in models


def test_cost_tracker_record_usage():
    tracker = CostTracker()
    tracker.record(
        agent_name="summarizer", model="gpt-4o", input_tokens=1000, output_tokens=500
    )
    records = tracker.get_records()
    assert len(records) == 1
    assert records[0].agent_name == "summarizer"
    assert records[0].input_tokens == 1000
    assert records[0].output_tokens == 500


def test_cost_tracker_calculates_cost():
    tracker = CostTracker()
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=1000, output_tokens=500)
    records = tracker.get_records()
    assert abs(records[0].cost_usd - 0.0125) < 1e-6


def test_cost_tracker_unknown_model_zero_cost():
    tracker = CostTracker()
    tracker.record(
        agent_name="a", model="unknown-model", input_tokens=100, output_tokens=50
    )
    assert tracker.get_records()[0].cost_usd == 0.0


def test_cost_tracker_custom_pricing():
    custom = [
        ModelPricing(model="my-model", input_cost_per_1k=0.01, output_cost_per_1k=0.02)
    ]
    tracker = CostTracker(pricing=custom)
    tracker.record(
        agent_name="a", model="my-model", input_tokens=2000, output_tokens=1000
    )
    assert abs(tracker.get_records()[0].cost_usd - 0.04) < 1e-6


def test_cost_tracker_total_cost():
    tracker = CostTracker()
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=1000, output_tokens=500)
    tracker.record(
        agent_name="b", model="gpt-4o", input_tokens=2000, output_tokens=1000
    )
    total = tracker.total_cost()
    expected = 0.0125 + 0.025
    assert abs(total - expected) < 1e-6


def test_cost_tracker_cost_by_agent():
    tracker = CostTracker()
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=1000, output_tokens=500)
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=1000, output_tokens=500)
    tracker.record(
        agent_name="b", model="gpt-4o", input_tokens=2000, output_tokens=1000
    )
    by_agent = tracker.cost_by_agent()
    assert abs(by_agent["a"] - 0.025) < 1e-6
    assert abs(by_agent["b"] - 0.025) < 1e-6


def test_cost_tracker_cost_by_model():
    tracker = CostTracker()
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=1000, output_tokens=500)
    tracker.record(
        agent_name="a", model="gpt-4o-mini", input_tokens=1000, output_tokens=500
    )
    by_model = tracker.cost_by_model()
    assert "gpt-4o" in by_model
    assert "gpt-4o-mini" in by_model


def test_cost_tracker_total_tokens():
    tracker = CostTracker()
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=100, output_tokens=50)
    tracker.record(agent_name="b", model="gpt-4o", input_tokens=200, output_tokens=100)
    assert tracker.total_tokens() == (300, 150)


def test_cost_tracker_reset():
    tracker = CostTracker()
    tracker.record(agent_name="a", model="gpt-4o", input_tokens=100, output_tokens=50)
    tracker.reset()
    assert len(tracker.get_records()) == 0
    assert tracker.total_cost() == 0.0
