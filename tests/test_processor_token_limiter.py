"""Tests for token limiter processor."""

import pytest
from processor_support.base import ProcessorData, TripWire
from processor_support.builtin.token_limiter import (
    TokenLimiterProcessor,
)


@pytest.mark.asyncio
async def test_short_text_passes():
    proc = TokenLimiterProcessor(max_tokens=100)
    data = ProcessorData(text="Hello world")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.text == "Hello world"


@pytest.mark.asyncio
async def test_long_text_truncated():
    proc = TokenLimiterProcessor(max_tokens=5, action="truncate")
    data = ProcessorData(text="This is a very long sentence with many tokens in it")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert len(result.text) < len(data.text)


@pytest.mark.asyncio
async def test_long_text_blocked():
    proc = TokenLimiterProcessor(max_tokens=5, action="block")
    data = ProcessorData(text="This is a very long sentence with many tokens in it")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "token" in result.reason.lower()


@pytest.mark.asyncio
async def test_token_count_in_metadata():
    proc = TokenLimiterProcessor(max_tokens=1000)
    data = ProcessorData(text="Hello world")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert "token_count" in result.metadata
    assert isinstance(result.metadata["token_count"], int)
    assert result.metadata["token_count"] > 0


@pytest.mark.asyncio
async def test_custom_model_encoding():
    proc = TokenLimiterProcessor(max_tokens=1000, model="gpt-4")
    data = ProcessorData(text="Hello world")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.metadata["token_count"] > 0
