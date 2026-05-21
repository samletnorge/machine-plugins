"""Native tools that agents can invoke to interact with working memory.

These functions are designed to be registered as agent tools so the LLM
can explicitly remember, recall, and forget information during a conversation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugins.memory_support.manager import MemoryManager


async def remember(
    manager: MemoryManager,
    thread_id: str,
    *,
    key: str,
    value: str,
) -> str:
    """Store a key-value pair in working memory."""
    wm = manager.working_memory(thread_id)
    await wm.set(key, value)
    return f"Remembered: {key} = {value}"


async def recall(
    manager: MemoryManager,
    thread_id: str,
    *,
    key: str,
) -> str:
    """Retrieve a value from working memory by key."""
    wm = manager.working_memory(thread_id)
    val = await wm.get(key)
    if val is None:
        return f"No memory found for key '{key}'"
    return f"{key}: {val}"


async def forget(
    manager: MemoryManager,
    thread_id: str,
    *,
    key: str,
) -> str:
    """Remove a key from working memory."""
    wm = manager.working_memory(thread_id)
    deleted = await wm.delete(key)
    if deleted:
        return f"Forgot '{key}'"
    return f"Key '{key}' not found in memory"


async def list_memories(
    manager: MemoryManager,
    thread_id: str,
) -> str:
    """List all key-value pairs in working memory for this thread."""
    wm = manager.working_memory(thread_id)
    data = await wm.get_all()
    if not data:
        return "No memories stored for this thread."
    lines = [f"- {k}: {v}" for k, v in sorted(data.items())]
    return "Current working memory:\n" + "\n".join(lines)
