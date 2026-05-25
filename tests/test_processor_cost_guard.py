"""Tests for cost guard processor."""

import pytest
from processor_support.base import ProcessorData, TripWire
from processor_support.builtin.cost_guard import CostGuardProcessor


@pytest.mark.asyncio
async def test_under_budget_passes():
    proc = CostGuardProcessor(max_cost_usd=1.0, cost_per_1k_tokens=0.01)
    data = ProcessorData(text="Hello", metadata={"token_count": 100})
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert "estimated_cost_usd" in result.metadata


@pytest.mark.asyncio
async def test_over_budget_blocks():
    proc = CostGuardProcessor(max_cost_usd=0.001, cost_per_1k_tokens=0.01)
    data = ProcessorData(text="x" * 10000, metadata={"token_count": 50000})
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "cost" in result.reason.lower()


@pytest.mark.asyncio
async def test_no_token_count_estimates():
    proc = CostGuardProcessor(max_cost_usd=1.0, cost_per_1k_tokens=0.01)
    data = ProcessorData(text="Hello world, this is a test")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert "estimated_cost_usd" in result.metadata


@pytest.mark.asyncio
async def test_exact_budget_passes():
    proc = CostGuardProcessor(max_cost_usd=0.01, cost_per_1k_tokens=0.01)
    data = ProcessorData(text="x", metadata={"token_count": 1000})
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
