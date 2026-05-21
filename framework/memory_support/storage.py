"""Abstract base class for all storage backends.

Storage backends persist threads, messages, working memory, and observational facts.
The default InMemoryStorage is provided for development. Production backends
(PocketBase, Postgres, SQLite, Redis) are added in Phase 11.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugins.memory_support.thread import Thread, Message, Fact


class BaseStorage(ABC):
    """Abstract storage backend for the memory system."""

    # -- Thread CRUD ----------------------------------------------------------

    @abstractmethod
    async def create_thread(self, thread: Thread) -> Thread:
        """Persist a new thread. Returns the created thread."""
        ...

    @abstractmethod
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Return a thread by ID, or None."""
        ...

    @abstractmethod
    async def list_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        metadata_filter: Optional[dict] = None,
    ) -> list[Thread]:
        """Return threads, newest first."""
        ...

    @abstractmethod
    async def update_thread(self, thread_id: str, **kwargs) -> Thread:
        """Update thread fields (title, metadata). Returns updated thread."""
        ...

    @abstractmethod
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and all its messages. Returns True if found."""
        ...

    # -- Message CRUD ---------------------------------------------------------

    @abstractmethod
    async def add_message(self, thread_id: str, message: Message) -> Message:
        """Append a message to a thread. Returns the persisted message."""
        ...

    @abstractmethod
    async def get_messages(
        self,
        thread_id: str,
        *,
        limit: Optional[int] = None,
        before_id: Optional[str] = None,
    ) -> list[Message]:
        """Return messages in chronological order."""
        ...

    @abstractmethod
    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        """Delete a single message. Returns True if found."""
        ...

    # -- Working Memory -------------------------------------------------------

    @abstractmethod
    async def get_working_memory(self, thread_id: str, key: str) -> Optional[str]:
        """Get a single working memory value."""
        ...

    @abstractmethod
    async def set_working_memory(self, thread_id: str, key: str, value: str) -> None:
        """Set a working memory key-value pair."""
        ...

    @abstractmethod
    async def delete_working_memory_key(self, thread_id: str, key: str) -> bool:
        """Delete a working memory key. Returns True if found."""
        ...

    @abstractmethod
    async def get_all_working_memory(self, thread_id: str) -> dict[str, str]:
        """Get all working memory for a thread."""
        ...

    # -- Facts (Observational Memory) -----------------------------------------

    @abstractmethod
    async def store_facts(self, facts: list[Fact]) -> list[Fact]:
        """Persist a batch of extracted facts."""
        ...

    @abstractmethod
    async def get_facts(
        self,
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> list[Fact]:
        """Retrieve facts, optionally filtered."""
        ...

    @abstractmethod
    async def delete_fact(self, fact_id: str) -> bool:
        """Delete a single fact. Returns True if found."""
        ...
