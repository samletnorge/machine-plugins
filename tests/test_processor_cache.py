"""Tests for response cache processor."""

import pytest
import time
from processor_support.base import ProcessorData
from processor_support.builtin.cache import CacheProcessor


@pytest.mark.asyncio
async def test_cache_miss_passes_through():
    proc = CacheProcessor(ttl_seconds=60)
    data = ProcessorData(text="Hello")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.text == "Hello"
    assert result.metadata.get("cache_hit") is not True


@pytest.mark.asyncio
async def test_cache_hit_returns_cached():
    proc = CacheProcessor(ttl_seconds=60)
    data = ProcessorData(text="Hello")

    await proc.process(data)
    proc.store("Hello", ProcessorData(text="Cached response"))

    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.text == "Cached response"
    assert result.metadata.get("cache_hit") is True


@pytest.mark.asyncio
async def test_cache_expired():
    proc = CacheProcessor(ttl_seconds=0)
    proc.store("Hello", ProcessorData(text="Old response"))
    time.sleep(0.01)

    data = ProcessorData(text="Hello")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.text == "Hello"
    assert result.metadata.get("cache_hit") is not True


@pytest.mark.asyncio
async def test_cache_different_keys():
    proc = CacheProcessor(ttl_seconds=60)
    proc.store("Hello", ProcessorData(text="Hello cached"))
    proc.store("World", ProcessorData(text="World cached"))

    result1 = await proc.process(ProcessorData(text="Hello"))
    result2 = await proc.process(ProcessorData(text="World"))
    assert result1.text == "Hello cached"
    assert result2.text == "World cached"


@pytest.mark.asyncio
async def test_cache_clear():
    proc = CacheProcessor(ttl_seconds=60)
    proc.store("Hello", ProcessorData(text="Cached"))
    proc.clear()

    result = await proc.process(ProcessorData(text="Hello"))
    assert result.text == "Hello"
    assert result.metadata.get("cache_hit") is not True
