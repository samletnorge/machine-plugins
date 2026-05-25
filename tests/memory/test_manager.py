"""Tests for MemoryManager unified interface."""

import pytest

from memory_support.manager import MemoryManager
from memory_support.in_memory_storage import InMemoryStorage
from memory_support.windowing import LastNWindow
from memory_support.thread import MessageRole


@pytest.fixture
def manager():
    return MemoryManager(storage=InMemoryStorage())


@pytest.mark.asyncio
async def test_create_thread_returns_thread_with_id(manager):
    thread = await manager.create_thread(title="Test")
    assert thread.id.startswith("thread_")
    assert thread.title == "Test"


@pytest.mark.asyncio
async def test_get_thread_returns_created_thread(manager):
    thread = await manager.create_thread(title="Hello")
    fetched = await manager.get_thread(thread.id)
    assert fetched is not None
    assert fetched.id == thread.id
    assert fetched.title == "Hello"


@pytest.mark.asyncio
async def test_get_thread_nonexistent_returns_none(manager):
    assert await manager.get_thread("nonexistent") is None


@pytest.mark.asyncio
async def test_list_threads_returns_created_threads(manager):
    await manager.create_thread(title="A")
    await manager.create_thread(title="B")
    threads = await manager.list_threads()
    assert len(threads) == 2


@pytest.mark.asyncio
async def test_delete_thread_returns_true_then_false(manager):
    thread = await manager.create_thread()
    assert await manager.delete_thread(thread.id) is True
    assert await manager.delete_thread(thread.id) is False


@pytest.mark.asyncio
async def test_add_message_returns_message_with_correct_role_content(manager):
    thread = await manager.create_thread()
    msg = await manager.add_message(thread.id, role="user", content="hi")
    assert msg.role == MessageRole.USER
    assert msg.content == "hi"
    assert msg.id.startswith("msg_")


@pytest.mark.asyncio
async def test_get_messages_returns_in_order(manager):
    thread = await manager.create_thread()
    await manager.add_message(thread.id, role="user", content="first")
    await manager.add_message(thread.id, role="assistant", content="second")
    msgs = await manager.get_messages(thread.id)
    assert [m.content for m in msgs] == ["first", "second"]


@pytest.mark.asyncio
async def test_get_messages_with_window_applies_windowing(manager):
    thread = await manager.create_thread()
    for i in range(10):
        await manager.add_message(thread.id, role="user", content=f"msg{i}")
    window = LastNWindow(n=3)
    msgs = await manager.get_messages(thread.id, window=window)
    assert len(msgs) == 3
    assert msgs[-1].content == "msg9"


@pytest.mark.asyncio
async def test_working_memory_set_and_get(manager):
    thread = await manager.create_thread()
    wm = manager.working_memory(thread.id)
    await wm.set("name", "Alice")
    assert await wm.get("name") == "Alice"


@pytest.mark.asyncio
async def test_extract_facts_from_user_messages(manager):
    thread = await manager.create_thread()
    msg = await manager.add_message(thread.id, role="user", content="my name is Bob")
    facts = await manager.extract_facts([msg], thread_id=thread.id)
    assert len(facts) >= 1
    assert any("Bob" in f.content for f in facts)


@pytest.mark.asyncio
async def test_get_relevant_facts_retrieves_stored(manager):
    thread = await manager.create_thread()
    msg = await manager.add_message(thread.id, role="user", content="my name is Bob")
    await manager.extract_facts([msg], thread_id=thread.id)
    facts = await manager.get_relevant_facts(thread_id=thread.id)
    assert len(facts) >= 1


@pytest.mark.asyncio
async def test_build_context_returns_expected_keys(manager):
    thread = await manager.create_thread()
    await manager.add_message(thread.id, role="user", content="hello")
    ctx = await manager.build_context(thread.id)
    assert "messages" in ctx
    assert "working_memory_prompt" in ctx
    assert "facts" in ctx


@pytest.mark.asyncio
async def test_build_context_includes_working_memory_prompt(manager):
    thread = await manager.create_thread()
    await manager.add_message(thread.id, role="user", content="hello")
    wm = manager.working_memory(thread.id)
    await wm.set("task", "testing")
    ctx = await manager.build_context(thread.id)
    assert "task" in ctx["working_memory_prompt"]
    assert "testing" in ctx["working_memory_prompt"]


@pytest.mark.asyncio
async def test_build_context_includes_facts(manager):
    thread = await manager.create_thread()
    msg = await manager.add_message(thread.id, role="user", content="my name is Bob")
    await manager.extract_facts([msg], thread_id=thread.id)
    ctx = await manager.build_context(thread.id, include_facts=True)
    assert len(ctx["facts"]) >= 1
