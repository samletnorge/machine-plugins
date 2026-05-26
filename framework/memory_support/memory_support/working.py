"""Working memory — a persistent scratchpad injected into system prompts.

Agents use working memory to remember facts across turns within a thread:
user name, preferences, current task state, etc.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from memory_support.storage import BaseStorage


class WorkingMemoryData(BaseModel):
    """Serializable container for working memory key-value pairs."""

    data: dict[str, str] = Field(default_factory=dict)


class WorkingMemory:
    """Persistent key-value scratchpad scoped to a thread.

    Values are stored through the storage backend and survive across turns.
    The `to_system_prompt()` method renders all current memory as a text
    block suitable for injection into the system prompt.
    """

    def __init__(self, storage: BaseStorage, thread_id: str) -> None:
        self._storage = storage
        self._thread_id = thread_id

    async def get(self, key: str, *, default: Optional[str] = None) -> Optional[str]:
        """Get a value by key, or return default."""
        val = await self._storage.get_working_memory(self._thread_id, key)
        return val if val is not None else default

    async def set(self, key: str, value: str) -> None:
        """Set a key-value pair."""
        await self._storage.set_working_memory(self._thread_id, key, value)

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if it existed."""
        return await self._storage.delete_working_memory_key(self._thread_id, key)

    async def get_all(self) -> dict[str, str]:
        """Get all working memory as a dict."""
        return await self._storage.get_all_working_memory(self._thread_id)

    async def to_system_prompt(self) -> str:
        """Render working memory as a system prompt block.

        Returns empty string if no memory is stored.
        """
        data = await self.get_all()
        if not data:
            return ""
        lines = [f"- {k}: {v}" for k, v in sorted(data.items())]
        return (
            "<working_memory>\n"
            "The following information has been remembered from this conversation:\n"
            + "\n".join(lines)
            + "\n</working_memory>"
        )
