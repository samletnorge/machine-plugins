"""Tests for configurable regex filter processor."""

import pytest
from processor_support.base import ProcessorData, TripWire
from processor_support.builtin.regex_filter import (
    RegexFilterProcessor,
)


@pytest.mark.asyncio
async def test_block_pattern_matches():
    proc = RegexFilterProcessor(block_patterns=[r"(?i)\bpassword\b"])
    data = ProcessorData(text="My password is hunter2")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "password" in result.reason.lower() or "blocked" in result.reason.lower()


@pytest.mark.asyncio
async def test_block_pattern_no_match_passes():
    proc = RegexFilterProcessor(block_patterns=[r"(?i)\bpassword\b"])
    data = ProcessorData(text="Tell me about the weather")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)


@pytest.mark.asyncio
async def test_allow_pattern_matches():
    proc = RegexFilterProcessor(allow_patterns=[r"(?i)^(hello|hi|hey)"])
    data = ProcessorData(text="Hello, how are you?")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)


@pytest.mark.asyncio
async def test_allow_pattern_no_match_blocks():
    proc = RegexFilterProcessor(allow_patterns=[r"(?i)^(hello|hi|hey)"])
    data = ProcessorData(text="Delete everything now")
    result = await proc.process(data)
    assert isinstance(result, TripWire)


@pytest.mark.asyncio
async def test_both_block_and_allow():
    proc = RegexFilterProcessor(
        block_patterns=[r"(?i)\bdelete\b"],
        allow_patterns=[r"(?i)^hello"],
    )
    data = ProcessorData(text="Hello, please delete my account")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
