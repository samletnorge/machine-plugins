"""In-memory storage backend for development and testing."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from memory_support.thread import Thread, Message, Fact
from .storage import BaseStorage


class InMemoryStorage(BaseStorage):
    """Dict-backed storage. Data is lost on process exit."""

    def __init__(self) -> None:
        self._threads: dict[str, Thread] = {}
        self._messages: dict[str, list[Message]] = {}  # thread_id -> messages
        self._working: dict[str, dict[str, str]] = {}  # thread_id -> {k: v}
        self._facts: dict[str, Fact] = {}  # fact_id -> Fact
        self._thread_order: list[str] = []  # newest first

    # -- Threads --------------------------------------------------------------

    async def create_thread(self, thread: Thread) -> Thread:
        self._threads[thread.id] = deepcopy(thread)
        self._messages[thread.id] = []
        self._working[thread.id] = {}
        self._thread_order.insert(0, thread.id)
        return deepcopy(thread)

    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        t = self._threads.get(thread_id)
        return deepcopy(t) if t else None

    async def list_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        metadata_filter: Optional[dict] = None,
    ) -> list[Thread]:
        ids = self._thread_order[offset : offset + limit]
        threads = [deepcopy(self._threads[tid]) for tid in ids if tid in self._threads]
        if metadata_filter:
            threads = [
                t
                for t in threads
                if all(t.metadata.get(k) == v for k, v in metadata_filter.items())
            ]
        return threads

    async def update_thread(self, thread_id: str, **kwargs) -> Thread:
        t = self._threads.get(thread_id)
        if not t:
            raise KeyError(f"Thread {thread_id} not found")
        for k, v in kwargs.items():
            if hasattr(t, k):
                setattr(t, k, v)
        t.updated_at = datetime.now(timezone.utc)
        return deepcopy(t)

    async def delete_thread(self, thread_id: str) -> bool:
        if thread_id not in self._threads:
            return False
        del self._threads[thread_id]
        self._messages.pop(thread_id, None)
        self._working.pop(thread_id, None)
        self._thread_order = [tid for tid in self._thread_order if tid != thread_id]
        # Remove facts associated with this thread
        self._facts = {
            fid: f for fid, f in self._facts.items() if f.thread_id != thread_id
        }
        return True

    # -- Messages -------------------------------------------------------------

    async def add_message(self, thread_id: str, message: Message) -> Message:
        if thread_id not in self._messages:
            self._messages[thread_id] = []
        self._messages[thread_id].append(deepcopy(message))
        # Update thread's updated_at
        if thread_id in self._threads:
            self._threads[thread_id].updated_at = datetime.now(timezone.utc)
        return deepcopy(message)

    async def get_messages(
        self,
        thread_id: str,
        *,
        limit: Optional[int] = None,
        before_id: Optional[str] = None,
    ) -> list[Message]:
        msgs = self._messages.get(thread_id, [])
        if before_id:
            idx = next((i for i, m in enumerate(msgs) if m.id == before_id), len(msgs))
            msgs = msgs[:idx]
        if limit is not None:
            msgs = msgs[-limit:]
        return [deepcopy(m) for m in msgs]

    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        msgs = self._messages.get(thread_id, [])
        before = len(msgs)
        self._messages[thread_id] = [m for m in msgs if m.id != message_id]
        return len(self._messages[thread_id]) < before

    # -- Working Memory -------------------------------------------------------

    async def get_working_memory(self, thread_id: str, key: str) -> Optional[str]:
        return self._working.get(thread_id, {}).get(key)

    async def set_working_memory(self, thread_id: str, key: str, value: str) -> None:
        if thread_id not in self._working:
            self._working[thread_id] = {}
        self._working[thread_id][key] = value

    async def delete_working_memory_key(self, thread_id: str, key: str) -> bool:
        wm = self._working.get(thread_id, {})
        if key in wm:
            del wm[key]
            return True
        return False

    async def get_all_working_memory(self, thread_id: str) -> dict[str, str]:
        return dict(self._working.get(thread_id, {}))

    # -- Facts ----------------------------------------------------------------

    async def store_facts(self, facts: list[Fact]) -> list[Fact]:
        stored = []
        for f in facts:
            copy = deepcopy(f)
            self._facts[copy.id] = copy
            stored.append(deepcopy(copy))
        return stored

    async def get_facts(
        self,
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> list[Fact]:
        results = list(self._facts.values())
        if thread_id:
            results = [f for f in results if f.thread_id == thread_id]
        if user_id:
            results = [f for f in results if f.user_id == user_id]
        if query:
            q = query.lower()
            results = [f for f in results if q in f.content.lower()]
        results.sort(key=lambda f: f.created_at, reverse=True)
        return [deepcopy(f) for f in results[:limit]]

    async def delete_fact(self, fact_id: str) -> bool:
        if fact_id in self._facts:
            del self._facts[fact_id]
            return True
        return False
