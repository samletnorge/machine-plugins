"""MemoryManager — unified interface for all memory operations.

Coordinates threads, messages, working memory, observational memory,
and context building for agent consumption.
"""

from __future__ import annotations

from typing import Optional, Any

from memory_support.thread import (
    Thread,
    Message,
    MessageRole,
    Fact,
)
from memory_support.working import WorkingMemory
from memory_support.observational import (
    FactExtractor,
    ObservationalMemory,
)
from memory_support.windowing import WindowStrategy, LastNWindow
from memory_support.storage import BaseStorage


class MemoryManager:
    """Central coordinator for all memory subsystems.

    Usage:
        storage = InMemoryStorage()
        mm = MemoryManager(storage=storage)
        thread = await mm.create_thread(title="New chat")
        await mm.add_message(thread.id, role="user", content="Hello")
        context = await mm.build_context(thread.id)
    """

    def __init__(
        self,
        storage: BaseStorage,
        default_window: Optional[WindowStrategy] = None,
        fact_extractor: Optional[FactExtractor] = None,
    ) -> None:
        self._storage = storage
        self._default_window = default_window or LastNWindow(n=50)
        self._observational = ObservationalMemory(
            storage=storage, extractor=fact_extractor
        )

    @property
    def storage(self) -> BaseStorage:
        return self._storage

    # -- Thread operations ----------------------------------------------------

    async def create_thread(
        self,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Thread:
        """Create a new conversation thread."""
        thread = Thread(title=title, metadata=metadata or {})
        return await self._storage.create_thread(thread)

    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        return await self._storage.get_thread(thread_id)

    async def list_threads(self, **kwargs) -> list[Thread]:
        return await self._storage.list_threads(**kwargs)

    async def delete_thread(self, thread_id: str) -> bool:
        return await self._storage.delete_thread(thread_id)

    # -- Message operations ---------------------------------------------------

    async def add_message(
        self,
        thread_id: str,
        *,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """Add a message to a thread."""
        msg = Message(
            role=MessageRole(role),
            content=content,
            metadata=metadata or {},
        )
        return await self._storage.add_message(thread_id, msg)

    async def get_messages(
        self,
        thread_id: str,
        *,
        window: Optional[WindowStrategy] = None,
        limit: Optional[int] = None,
    ) -> list[Message]:
        """Get messages, optionally applying a windowing strategy."""
        msgs = await self._storage.get_messages(thread_id, limit=limit)
        if window:
            msgs = window.apply(msgs)
        return msgs

    # -- Working memory -------------------------------------------------------

    def working_memory(self, thread_id: str) -> WorkingMemory:
        """Get a WorkingMemory instance for a thread."""
        return WorkingMemory(storage=self._storage, thread_id=thread_id)

    # -- Observational memory -------------------------------------------------

    async def extract_facts(
        self,
        messages: list[Message],
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[Fact]:
        """Extract and store facts from messages."""
        return await self._observational.extract_and_store(
            messages, thread_id=thread_id, user_id=user_id
        )

    async def get_relevant_facts(
        self,
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> list[Fact]:
        return await self._observational.get_relevant_facts(
            thread_id=thread_id, user_id=user_id, query=query, limit=limit
        )

    # -- Context building (for agent integration) -----------------------------

    async def build_context(
        self,
        thread_id: str,
        *,
        window: Optional[WindowStrategy] = None,
        include_facts: bool = True,
        fact_limit: int = 10,
    ) -> dict[str, Any]:
        """Build a complete context dict for agent consumption.

        Returns:
            {
                "messages": list[Message],
                "working_memory_prompt": str,
                "facts": list[Fact],
            }
        """
        msgs = await self.get_messages(thread_id, window=window or self._default_window)

        wm = self.working_memory(thread_id)
        wm_prompt = await wm.to_system_prompt()

        facts: list[Fact] = []
        if include_facts:
            facts = await self.get_relevant_facts(thread_id=thread_id, limit=fact_limit)

        return {
            "messages": msgs,
            "working_memory_prompt": wm_prompt,
            "facts": facts,
        }
