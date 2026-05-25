"""Integration test: full memory lifecycle through Machine plugin system."""

import pytest

from machine_core import Machine
from machine_core.plugin.manifest import PluginManifest, TransportConfig
from memory_support.manager import MemoryManager
from memory_support.in_memory_storage import InMemoryStorage
from memory_support.windowing import LastNWindow
from memory_support.observational import facts_to_system_prompt


@pytest.mark.asyncio
async def test_plugin_loads_and_registers_categories():
    """Memory-support plugin registers 'memory' and 'storage-backend' categories."""
    m = Machine()
    manifest = PluginManifest(
        name="memory-support",
        version="0.10.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "memory:register",
            "storage-backend:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="memory_support:MemorySupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("memory-support")

    assert "memory" in m._registry
    assert "storage-backend" in m._registry


@pytest.mark.asyncio
async def test_plugin_hookspecs_registered():
    """Memory-support plugin registers memory lifecycle hooks."""
    m = Machine()
    manifest = PluginManifest(
        name="memory-support",
        version="0.10.0",
        capabilities=["categories:define", "hooks:define"],
        transport=TransportConfig(
            type="in-process",
            entry_point="memory_support:MemorySupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("memory-support")

    assert "hooks/beforeMemoryStore" in m.hooks._specs
    assert "hooks/afterMemoryStore" in m.hooks._specs
    assert "hooks/beforeFactExtraction" in m.hooks._specs
    assert "hooks/afterFactExtraction" in m.hooks._specs


@pytest.mark.asyncio
async def test_full_memory_lifecycle():
    """End-to-end: create thread, add messages, extract facts, build context."""
    storage = InMemoryStorage()
    mm = MemoryManager(storage=storage, default_window=LastNWindow(n=10))

    # Create thread
    thread = await mm.create_thread(title="Integration test")
    assert thread.id.startswith("thread_")

    # Add messages
    await mm.add_message(
        thread.id, role="system", content="You are a helpful assistant."
    )
    await mm.add_message(
        thread.id, role="user", content="Hi! My name is Alice and I live in Oslo."
    )
    await mm.add_message(
        thread.id, role="assistant", content="Nice to meet you, Alice!"
    )
    await mm.add_message(thread.id, role="user", content="I prefer electric cars.")

    # Get windowed messages
    msgs = await mm.get_messages(thread.id, window=LastNWindow(n=3))
    assert len(msgs) == 4  # system preserved + last 3 non-system = 4

    # Extract facts
    all_msgs = await mm.get_messages(thread.id)
    facts = await mm.extract_facts(all_msgs, thread_id=thread.id, user_id="alice")
    assert len(facts) >= 2  # name + location at minimum

    # Working memory
    wm = mm.working_memory(thread.id)
    await wm.set("user_name", "Alice")
    await wm.set("city", "Oslo")
    prompt = await wm.to_system_prompt()
    assert "Alice" in prompt
    assert "working_memory" in prompt

    # Facts to system prompt
    retrieved_facts = await mm.get_relevant_facts(thread_id=thread.id)
    fact_prompt = facts_to_system_prompt(retrieved_facts)
    assert "observed_facts" in fact_prompt

    # Build full context
    ctx = await mm.build_context(thread.id, include_facts=True)
    assert "messages" in ctx
    assert "working_memory_prompt" in ctx
    assert "facts" in ctx
    assert len(ctx["messages"]) > 0
    assert len(ctx["working_memory_prompt"]) > 0
    assert len(ctx["facts"]) > 0

    # Delete thread cascades
    deleted = await mm.delete_thread(thread.id)
    assert deleted is True
    assert await mm.get_thread(thread.id) is None


@pytest.mark.asyncio
async def test_memory_tools_lifecycle():
    """End-to-end: use tool functions with manager."""
    from memory_support.tools import (
        remember,
        recall,
        forget,
        list_memories,
    )

    storage = InMemoryStorage()
    mm = MemoryManager(storage=storage)
    thread = await mm.create_thread(title="Tools test")

    result = await remember(mm, thread.id, key="color", value="blue")
    assert "blue" in result

    result = await recall(mm, thread.id, key="color")
    assert "blue" in result

    result = await list_memories(mm, thread.id)
    assert "color" in result and "blue" in result

    result = await forget(mm, thread.id, key="color")
    assert "Forgot" in result

    result = await list_memories(mm, thread.id)
    assert "No memories" in result
