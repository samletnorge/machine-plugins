"""Tests for WorkingMemory."""

import pytest

from machine_core.plugins.memory_support.working import WorkingMemory
from machine_core.plugins.memory_support.in_memory_storage import InMemoryStorage
from machine_core.plugins.memory_support.thread import Thread


@pytest.fixture
async def wm():
    storage = InMemoryStorage()
    thread = Thread(id="t1")
    await storage.create_thread(thread)
    return WorkingMemory(storage=storage, thread_id="t1")


@pytest.mark.asyncio
async def test_get_missing_returns_none(wm):
    assert await wm.get("nonexistent") is None


@pytest.mark.asyncio
async def test_get_missing_returns_default(wm):
    assert await wm.get("missing", default="fallback") == "fallback"


@pytest.mark.asyncio
async def test_set_then_get(wm):
    await wm.set("name", "Alice")
    assert await wm.get("name") == "Alice"


@pytest.mark.asyncio
async def test_delete_existing(wm):
    await wm.set("key", "val")
    assert await wm.delete("key") is True


@pytest.mark.asyncio
async def test_delete_missing(wm):
    assert await wm.delete("nope") is False


@pytest.mark.asyncio
async def test_get_all(wm):
    await wm.set("a", "1")
    await wm.set("b", "2")
    assert await wm.get_all() == {"a": "1", "b": "2"}


@pytest.mark.asyncio
async def test_to_system_prompt_empty(wm):
    assert await wm.to_system_prompt() == ""


@pytest.mark.asyncio
async def test_to_system_prompt_with_data(wm):
    await wm.set("name", "Alice")
    await wm.set("city", "Oslo")
    prompt = await wm.to_system_prompt()
    assert "<working_memory>" in prompt
    assert "</working_memory>" in prompt
    assert "- city: Oslo" in prompt
    assert "- name: Alice" in prompt
