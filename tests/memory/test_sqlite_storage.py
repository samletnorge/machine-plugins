"""Tests for the SQLite memory storage backend."""

from __future__ import annotations

import pytest

from memory_support.sqlite_storage import SqliteStorage
from memory_support.thread import Fact, Message, MessageRole, Thread


@pytest.fixture
def storage(tmp_path):
    return SqliteStorage(str(tmp_path / "memory.db"))


async def test_thread_and_message_roundtrip(storage):
    thread = await storage.create_thread(Thread(title="chat"))
    await storage.add_message(thread.id, Message(role=MessageRole.USER, content="hi"))
    await storage.add_message(
        thread.id, Message(role=MessageRole.ASSISTANT, content="hello")
    )

    fetched = await storage.get_thread(thread.id)
    assert fetched.title == "chat"
    messages = await storage.get_messages(thread.id)
    assert [m.content for m in messages] == ["hi", "hello"]
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.ASSISTANT]


async def test_messages_limit_and_before_id(storage):
    thread = await storage.create_thread(Thread())
    ids = []
    for i in range(5):
        msg = await storage.add_message(
            thread.id, Message(role=MessageRole.USER, content=str(i))
        )
        ids.append(msg.id)

    limited = await storage.get_messages(thread.id, limit=2)
    assert [m.content for m in limited] == ["3", "4"]

    before = await storage.get_messages(thread.id, before_id=ids[3])
    assert [m.content for m in before] == ["0", "1", "2"]


async def test_delete_thread_cascades(storage):
    thread = await storage.create_thread(Thread())
    await storage.add_message(thread.id, Message(role=MessageRole.USER, content="x"))
    await storage.set_working_memory(thread.id, "k", "v")

    assert await storage.delete_thread(thread.id) is True
    assert await storage.get_thread(thread.id) is None
    assert await storage.get_messages(thread.id) == []
    assert await storage.get_all_working_memory(thread.id) == {}


async def test_working_memory_crud(storage):
    thread = await storage.create_thread(Thread())
    await storage.set_working_memory(thread.id, "name", "Ada")
    assert await storage.get_working_memory(thread.id, "name") == "Ada"
    assert await storage.get_all_working_memory(thread.id) == {"name": "Ada"}
    assert await storage.delete_working_memory_key(thread.id, "name") is True
    assert await storage.get_working_memory(thread.id, "name") is None


async def test_facts_roundtrip_and_filter(storage):
    await storage.store_facts(
        [
            Fact(content="likes coffee", source_message_id="m1", thread_id="t1"),
            Fact(content="lives in Oslo", source_message_id="m2", thread_id="t2"),
        ]
    )
    assert len(await storage.get_facts()) == 2
    assert len(await storage.get_facts(thread_id="t1")) == 1
    assert [f.content for f in await storage.get_facts(query="oslo")] == [
        "lives in Oslo"
    ]


async def test_list_threads_newest_first(storage):
    first = await storage.create_thread(Thread(title="first"))
    second = await storage.create_thread(Thread(title="second"))

    threads = await storage.list_threads()
    assert [t.id for t in threads] == [second.id, first.id]


async def test_data_persists_across_instances(tmp_path):
    path = str(tmp_path / "shared.db")
    storage = SqliteStorage(path)
    thread = await storage.create_thread(Thread(title="persisted"))
    await storage.add_message(thread.id, Message(role=MessageRole.USER, content="kept"))

    reopened = SqliteStorage(path)
    assert (await reopened.get_thread(thread.id)).title == "persisted"
    assert [m.content for m in await reopened.get_messages(thread.id)] == ["kept"]
