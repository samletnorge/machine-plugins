"""Tests for content moderation processor."""

import pytest
from machine_core.plugins.processor_support.base import ProcessorData, TripWire
from machine_core.plugins.processor_support.builtin.moderation import (
    ModerationProcessor,
)


async def _mock_moderate_safe(text: str) -> dict:
    return {"flagged": False, "categories": []}


async def _mock_moderate_harmful(text: str) -> dict:
    if "harmful" in text.lower():
        return {"flagged": True, "categories": ["violence"]}
    return {"flagged": False, "categories": []}


@pytest.mark.asyncio
async def test_safe_content_passes():
    proc = ModerationProcessor(moderate_fn=_mock_moderate_safe)
    data = ProcessorData(text="Tell me about cats")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)


@pytest.mark.asyncio
async def test_harmful_content_blocked():
    proc = ModerationProcessor(moderate_fn=_mock_moderate_harmful)
    data = ProcessorData(text="This is harmful content")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "moderation" in result.reason.lower() or "violence" in result.reason.lower()


@pytest.mark.asyncio
async def test_moderation_metadata_added():
    proc = ModerationProcessor(moderate_fn=_mock_moderate_safe)
    data = ProcessorData(text="Hello")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert "moderation_result" in result.metadata


@pytest.mark.asyncio
async def test_moderation_callback_receives_text():
    received = []

    async def capture_fn(text: str) -> dict:
        received.append(text)
        return {"flagged": False, "categories": []}

    proc = ModerationProcessor(moderate_fn=capture_fn)
    data = ProcessorData(text="Check this text")
    await proc.process(data)
    assert received == ["Check this text"]
