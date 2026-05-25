"""Tests for InMemoryStorage."""

import pytest

from memory_support.thread import (
    Fact,
    Message,
    MessageRole,
    Thread,
)


# -- Threads -------------------------------------------------------------------


class TestThreadCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get(self, storage):
        t = Thread(title="Chat")
        created = await storage.create_thread(t)
        assert created.id == t.id
        fetched = await storage.get_thread(t.id)
        assert fetched is not None
        assert fetched.title == "Chat"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, storage):
        assert await storage.get_thread("no_such_id") is None

    @pytest.mark.asyncio
    async def test_list_threads_pagination(self, storage):
        for i in range(5):
            await storage.create_thread(Thread(title=f"t{i}"))
        page = await storage.list_threads(limit=2, offset=0)
        assert len(page) == 2
        page2 = await storage.list_threads(limit=2, offset=2)
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_list_threads_metadata_filter(self, storage):
        await storage.create_thread(Thread(metadata={"env": "prod"}))
        await storage.create_thread(Thread(metadata={"env": "dev"}))
        results = await storage.list_threads(metadata_filter={"env": "prod"})
        assert len(results) == 1
        assert results[0].metadata["env"] == "prod"

    @pytest.mark.asyncio
    async def test_update_thread(self, storage):
        t = Thread(title="Old")
        await storage.create_thread(t)
        updated = await storage.update_thread(t.id, title="New")
        assert updated.title == "New"

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self, storage):
        with pytest.raises(KeyError):
            await storage.update_thread("bad_id", title="x")

    @pytest.mark.asyncio
    async def test_delete_thread(self, storage):
        t = Thread()
        await storage.create_thread(t)
        assert await storage.delete_thread(t.id) is True
        assert await storage.get_thread(t.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, storage):
        assert await storage.delete_thread("nope") is False


# -- Messages ------------------------------------------------------------------


class TestMessageCRUD:
    @pytest.mark.asyncio
    async def test_add_and_get(self, storage):
        t = Thread()
        await storage.create_thread(t)
        msg = Message(role=MessageRole.USER, content="hello")
        await storage.add_message(t.id, msg)
        msgs = await storage.get_messages(t.id)
        assert len(msgs) == 1
        assert msgs[0].content == "hello"

    @pytest.mark.asyncio
    async def test_chronological_order(self, storage):
        t = Thread()
        await storage.create_thread(t)
        for i in range(3):
            await storage.add_message(
                t.id, Message(role=MessageRole.USER, content=str(i))
            )
        msgs = await storage.get_messages(t.id)
        assert [m.content for m in msgs] == ["0", "1", "2"]

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, storage):
        t = Thread()
        await storage.create_thread(t)
        for i in range(5):
            await storage.add_message(
                t.id, Message(role=MessageRole.USER, content=str(i))
            )
        msgs = await storage.get_messages(t.id, limit=2)
        assert len(msgs) == 2
        # limit returns the last N messages
        assert msgs[0].content == "3"
        assert msgs[1].content == "4"

    @pytest.mark.asyncio
    async def test_get_messages_with_before_id(self, storage):
        t = Thread()
        await storage.create_thread(t)
        ids = []
        for i in range(4):
            m = Message(role=MessageRole.USER, content=str(i))
            await storage.add_message(t.id, m)
            ids.append(m.id)
        msgs = await storage.get_messages(t.id, before_id=ids[2])
        assert len(msgs) == 2
        assert msgs[-1].content == "1"

    @pytest.mark.asyncio
    async def test_delete_message(self, storage):
        t = Thread()
        await storage.create_thread(t)
        msg = Message(role=MessageRole.USER, content="bye")
        await storage.add_message(t.id, msg)
        assert await storage.delete_message(t.id, msg.id) is True
        assert await storage.get_messages(t.id) == []

    @pytest.mark.asyncio
    async def test_delete_message_nonexistent(self, storage):
        t = Thread()
        await storage.create_thread(t)
        assert await storage.delete_message(t.id, "no_msg") is False


# -- Working Memory ------------------------------------------------------------


class TestWorkingMemory:
    @pytest.mark.asyncio
    async def test_set_and_get(self, storage):
        t = Thread()
        await storage.create_thread(t)
        await storage.set_working_memory(t.id, "mood", "happy")
        assert await storage.get_working_memory(t.id, "mood") == "happy"

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, storage):
        t = Thread()
        await storage.create_thread(t)
        assert await storage.get_working_memory(t.id, "nope") is None

    @pytest.mark.asyncio
    async def test_delete_key(self, storage):
        t = Thread()
        await storage.create_thread(t)
        await storage.set_working_memory(t.id, "k", "v")
        assert await storage.delete_working_memory_key(t.id, "k") is True
        assert await storage.get_working_memory(t.id, "k") is None

    @pytest.mark.asyncio
    async def test_delete_missing_key_returns_false(self, storage):
        t = Thread()
        await storage.create_thread(t)
        assert await storage.delete_working_memory_key(t.id, "x") is False

    @pytest.mark.asyncio
    async def test_get_all(self, storage):
        t = Thread()
        await storage.create_thread(t)
        await storage.set_working_memory(t.id, "a", "1")
        await storage.set_working_memory(t.id, "b", "2")
        all_wm = await storage.get_all_working_memory(t.id)
        assert all_wm == {"a": "1", "b": "2"}


# -- Facts ---------------------------------------------------------------------


class TestFacts:
    @pytest.mark.asyncio
    async def test_store_and_get(self, storage):
        f = Fact(content="sky is blue", source_message_id="m1", thread_id="t1")
        stored = await storage.store_facts([f])
        assert len(stored) == 1
        results = await storage.get_facts(thread_id="t1")
        assert len(results) == 1
        assert results[0].content == "sky is blue"

    @pytest.mark.asyncio
    async def test_filter_by_user_id(self, storage):
        await storage.store_facts(
            [
                Fact(content="a", source_message_id="m1", user_id="u1"),
                Fact(content="b", source_message_id="m2", user_id="u2"),
            ]
        )
        results = await storage.get_facts(user_id="u1")
        assert len(results) == 1
        assert results[0].content == "a"

    @pytest.mark.asyncio
    async def test_filter_by_query(self, storage):
        await storage.store_facts(
            [
                Fact(content="Python is great", source_message_id="m1"),
                Fact(content="Rust is fast", source_message_id="m2"),
            ]
        )
        results = await storage.get_facts(query="python")
        assert len(results) == 1
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_delete_fact(self, storage):
        f = Fact(content="x", source_message_id="m1")
        await storage.store_facts([f])
        assert await storage.delete_fact(f.id) is True
        assert await storage.delete_fact(f.id) is False

    @pytest.mark.asyncio
    async def test_delete_fact_nonexistent(self, storage):
        assert await storage.delete_fact("no_fact") is False


# -- Cascade -------------------------------------------------------------------


class TestDeleteThreadCascade:
    @pytest.mark.asyncio
    async def test_deleting_thread_removes_messages_wm_facts(self, storage):
        t = Thread()
        await storage.create_thread(t)
        await storage.add_message(t.id, Message(role=MessageRole.USER, content="hi"))
        await storage.set_working_memory(t.id, "k", "v")
        await storage.store_facts(
            [
                Fact(content="fact", source_message_id="m1", thread_id=t.id),
            ]
        )

        await storage.delete_thread(t.id)

        assert await storage.get_messages(t.id) == []
        assert await storage.get_all_working_memory(t.id) == {}
        assert await storage.get_facts(thread_id=t.id) == []
