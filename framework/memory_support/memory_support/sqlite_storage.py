"""SQLite storage backend for the memory system.

Persists threads, messages, working memory, and facts to a local SQLite
database. Blocking sqlite3 calls run on a worker thread so the storage is safe
to use from async code. Uses WAL mode for concurrent readers.

Note: use a file path (not ``:memory:``) — each operation opens its own
connection, so an in-memory database would not persist between calls.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Callable, Optional

from memory_support.thread import Fact, Message, MessageRole, Thread

from .storage import BaseStorage


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


class SqliteStorage(BaseStorage):
    """SQLite-backed memory storage."""

    def __init__(self, path: str = "./data/memory.db") -> None:
        self._path = path
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS threads(
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages(
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_thread
                    ON messages(thread_id, seq);
                CREATE TABLE IF NOT EXISTS working_memory(
                    thread_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY(thread_id, key),
                    FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS facts(
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source_message_id TEXT NOT NULL,
                    thread_id TEXT,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                );
                """
            )

    async def _run(self, fn: Callable[..., Any], *args: Any) -> Any:
        return await asyncio.to_thread(fn, *args)

    # -- Threads --------------------------------------------------------------

    def _row_to_thread(self, row: sqlite3.Row) -> Thread:
        return Thread(
            id=row["id"],
            title=row["title"],
            metadata=json.loads(row["metadata"]),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    async def create_thread(self, thread: Thread) -> Thread:
        def op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO threads(id,title,metadata,created_at,updated_at)"
                    " VALUES(?,?,?,?,?)",
                    (
                        thread.id,
                        thread.title,
                        json.dumps(thread.metadata),
                        _dt(thread.created_at),
                        _dt(thread.updated_at),
                    ),
                )

        await self._run(op)
        return thread

    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        def op() -> Optional[Thread]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM threads WHERE id=?", (thread_id,)
                ).fetchone()
            return self._row_to_thread(row) if row else None

        return await self._run(op)

    async def list_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        metadata_filter: Optional[dict] = None,
    ) -> list[Thread]:
        def op() -> list[Thread]:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM threads ORDER BY created_at DESC, rowid DESC"
                ).fetchall()
            threads = [self._row_to_thread(row) for row in rows]
            if metadata_filter:
                threads = [
                    t
                    for t in threads
                    if all(t.metadata.get(k) == v for k, v in metadata_filter.items())
                ]
            return threads[offset : offset + limit]

        return await self._run(op)

    async def update_thread(self, thread_id: str, **kwargs: Any) -> Thread:
        def op() -> Thread:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM threads WHERE id=?", (thread_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"Thread {thread_id} not found")
                thread = self._row_to_thread(row)
                for key, value in kwargs.items():
                    if hasattr(thread, key):
                        setattr(thread, key, value)
                thread.updated_at = datetime.now().astimezone()
                conn.execute(
                    "UPDATE threads SET title=?, metadata=?, updated_at=? WHERE id=?",
                    (
                        thread.title,
                        json.dumps(thread.metadata),
                        _dt(thread.updated_at),
                        thread_id,
                    ),
                )
            return thread

        return await self._run(op)

    async def delete_thread(self, thread_id: str) -> bool:
        def op() -> bool:
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM threads WHERE id=?", (thread_id,))
                conn.execute("DELETE FROM facts WHERE thread_id=?", (thread_id,))
            return cur.rowcount > 0

        return await self._run(op)

    # -- Messages -------------------------------------------------------------

    async def add_message(self, thread_id: str, message: Message) -> Message:
        def op() -> None:
            with self._connect() as conn:
                seq = conn.execute(
                    "SELECT COALESCE(MAX(seq), -1) + 1 FROM messages WHERE thread_id=?",
                    (thread_id,),
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO messages(id,thread_id,seq,role,content,metadata,created_at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (
                        message.id,
                        thread_id,
                        seq,
                        str(message.role),
                        message.content,
                        json.dumps(message.metadata),
                        _dt(message.created_at),
                    ),
                )
                conn.execute(
                    "UPDATE threads SET updated_at=? WHERE id=?",
                    (_dt(datetime.now().astimezone()), thread_id),
                )

        await self._run(op)
        return message

    async def get_messages(
        self,
        thread_id: str,
        *,
        limit: Optional[int] = None,
        before_id: Optional[str] = None,
    ) -> list[Message]:
        def op() -> list[Message]:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE thread_id=? ORDER BY seq ASC",
                    (thread_id,),
                ).fetchall()
            messages = [
                Message(
                    id=row["id"],
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    metadata=json.loads(row["metadata"]),
                    created_at=_parse_dt(row["created_at"]),
                )
                for row in rows
            ]
            if before_id:
                idx = next(
                    (i for i, m in enumerate(messages) if m.id == before_id),
                    len(messages),
                )
                messages = messages[:idx]
            if limit is not None:
                messages = messages[-limit:]
            return messages

        return await self._run(op)

    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        def op() -> bool:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM messages WHERE thread_id=? AND id=?",
                    (thread_id, message_id),
                )
            return cur.rowcount > 0

        return await self._run(op)

    # -- Working Memory -------------------------------------------------------

    async def get_working_memory(self, thread_id: str, key: str) -> Optional[str]:
        def op() -> Optional[str]:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT value FROM working_memory WHERE thread_id=? AND key=?",
                    (thread_id, key),
                ).fetchone()
            return row["value"] if row else None

        return await self._run(op)

    async def set_working_memory(self, thread_id: str, key: str, value: str) -> None:
        def op() -> None:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO working_memory(thread_id,key,value) VALUES(?,?,?)"
                    " ON CONFLICT(thread_id,key) DO UPDATE SET value=excluded.value",
                    (thread_id, key, value),
                )

        await self._run(op)

    async def delete_working_memory_key(self, thread_id: str, key: str) -> bool:
        def op() -> bool:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM working_memory WHERE thread_id=? AND key=?",
                    (thread_id, key),
                )
            return cur.rowcount > 0

        return await self._run(op)

    async def get_all_working_memory(self, thread_id: str) -> dict[str, str]:
        def op() -> dict[str, str]:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT key, value FROM working_memory WHERE thread_id=?",
                    (thread_id,),
                ).fetchall()
            return {row["key"]: row["value"] for row in rows}

        return await self._run(op)

    # -- Facts ----------------------------------------------------------------

    async def store_facts(self, facts: list[Fact]) -> list[Fact]:
        def op() -> None:
            with self._connect() as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO facts(id,content,confidence,source_message_id,"
                    "thread_id,user_id,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)",
                    [
                        (
                            fact.id,
                            fact.content,
                            fact.confidence,
                            fact.source_message_id,
                            fact.thread_id,
                            fact.user_id,
                            _dt(fact.created_at),
                            _dt(fact.expires_at),
                        )
                        for fact in facts
                    ],
                )

        await self._run(op)
        return facts

    async def get_facts(
        self,
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> list[Fact]:
        def op() -> list[Fact]:
            clauses = []
            params: list[Any] = []
            if thread_id:
                clauses.append("thread_id=?")
                params.append(thread_id)
            if user_id:
                clauses.append("user_id=?")
                params.append(user_id)
            sql = "SELECT * FROM facts"
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY created_at DESC"
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            facts = [
                Fact(
                    id=row["id"],
                    content=row["content"],
                    confidence=row["confidence"],
                    source_message_id=row["source_message_id"],
                    thread_id=row["thread_id"],
                    user_id=row["user_id"],
                    created_at=_parse_dt(row["created_at"]),
                    expires_at=_parse_dt(row["expires_at"]),
                )
                for row in rows
            ]
            if query:
                needle = query.lower()
                facts = [f for f in facts if needle in f.content.lower()]
            return facts[:limit]

        return await self._run(op)

    async def delete_fact(self, fact_id: str) -> bool:
        def op() -> bool:
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM facts WHERE id=?", (fact_id,))
            return cur.rowcount > 0

        return await self._run(op)
