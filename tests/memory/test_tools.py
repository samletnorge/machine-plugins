"""Tests for memory tool functions."""

import pytest

from memory_support.tools import (
    remember,
    recall,
    forget,
    list_memories,
)
from memory_support.manager import MemoryManager
from memory_support.in_memory_storage import InMemoryStorage


@pytest.fixture
async def setup():
    """Create a manager and thread for tool tests."""
    mgr = MemoryManager(storage=InMemoryStorage())
    thread = await mgr.create_thread(title="tool-test")
    return mgr, thread.id


@pytest.mark.asyncio
async def test_remember_returns_confirmation(setup):
    mgr, tid = setup
    result = await remember(mgr, tid, key="color", value="blue")
    assert "Remembered" in result
    assert "color" in result
    assert "blue" in result


@pytest.mark.asyncio
async def test_recall_after_remember_returns_value(setup):
    mgr, tid = setup
    await remember(mgr, tid, key="color", value="blue")
    result = await recall(mgr, tid, key="color")
    assert "blue" in result


@pytest.mark.asyncio
async def test_recall_missing_key_returns_no_memory(setup):
    mgr, tid = setup
    result = await recall(mgr, tid, key="missing")
    assert "No memory found" in result


@pytest.mark.asyncio
async def test_forget_existing_key(setup):
    mgr, tid = setup
    await remember(mgr, tid, key="color", value="blue")
    result = await forget(mgr, tid, key="color")
    assert "Forgot" in result


@pytest.mark.asyncio
async def test_forget_missing_key(setup):
    mgr, tid = setup
    result = await forget(mgr, tid, key="nope")
    assert "not found" in result


@pytest.mark.asyncio
async def test_list_memories_empty(setup):
    mgr, tid = setup
    result = await list_memories(mgr, tid)
    assert "No memories" in result


@pytest.mark.asyncio
async def test_list_memories_after_remember(setup):
    mgr, tid = setup
    await remember(mgr, tid, key="name", value="Alice")
    await remember(mgr, tid, key="color", value="red")
    result = await list_memories(mgr, tid)
    assert "name" in result
    assert "Alice" in result
    assert "color" in result
    assert "red" in result
