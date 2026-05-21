"""Tests for FactExtractor, ObservationalMemory, and facts_to_system_prompt."""

import pytest

from machine_core.plugins.memory_support.observational import (
    FactExtractor,
    ObservationalMemory,
    facts_to_system_prompt,
)
from machine_core.plugins.memory_support.thread import Message, MessageRole, Fact
from machine_core.plugins.memory_support.in_memory_storage import InMemoryStorage


def _user(content: str) -> Message:
    return Message(role=MessageRole.USER, content=content)


def _assistant(content: str) -> Message:
    return Message(role=MessageRole.ASSISTANT, content=content)


# --- FactExtractor ---


class TestFactExtractor:
    def test_extracts_name(self):
        msgs = [_user("Hi, my name is Alice")]
        facts = FactExtractor().extract(msgs)
        assert len(facts) >= 1
        assert any("Alice" in f.content for f in facts)

    def test_extracts_location(self):
        msgs = [_user("I live in Oslo")]
        facts = FactExtractor().extract(msgs)
        assert len(facts) >= 1
        assert any("Oslo" in f.content for f in facts)

    def test_extracts_preference(self):
        msgs = [_user("I prefer electric cars")]
        facts = FactExtractor().extract(msgs)
        assert len(facts) >= 1
        assert any("electric" in f.content.lower() for f in facts)

    def test_ignores_assistant_messages(self):
        msgs = [_assistant("My name is Bot")]
        facts = FactExtractor().extract(msgs)
        assert facts == []

    def test_no_matches_returns_empty(self):
        msgs = [_user("Hello, how are you?")]
        facts = FactExtractor().extract(msgs)
        assert facts == []

    def test_thread_and_user_ids_propagated(self):
        msgs = [_user("My name is Bob")]
        facts = FactExtractor().extract(msgs, thread_id="t1", user_id="u1")
        assert facts[0].thread_id == "t1"
        assert facts[0].user_id == "u1"


# --- ObservationalMemory ---


class TestObservationalMemory:
    @pytest.mark.asyncio
    async def test_extract_and_store(self):
        storage = InMemoryStorage()
        om = ObservationalMemory(storage=storage)
        msgs = [_user("My name is Charlie"), _user("I live in Bergen")]
        facts = await om.extract_and_store(msgs, thread_id="t1", user_id="u1")
        assert len(facts) >= 2

    @pytest.mark.asyncio
    async def test_retrieve_by_thread(self):
        storage = InMemoryStorage()
        om = ObservationalMemory(storage=storage)
        await om.extract_and_store([_user("My name is Dan")], thread_id="t1")
        await om.extract_and_store([_user("My name is Eve")], thread_id="t2")
        facts = await om.get_relevant_facts(thread_id="t1")
        assert all(f.thread_id == "t1" for f in facts)

    @pytest.mark.asyncio
    async def test_retrieve_by_user(self):
        storage = InMemoryStorage()
        om = ObservationalMemory(storage=storage)
        await om.extract_and_store([_user("I live in Trondheim")], user_id="u1")
        await om.extract_and_store([_user("I live in Stavanger")], user_id="u2")
        facts = await om.get_relevant_facts(user_id="u1")
        assert all(f.user_id == "u1" for f in facts)

    @pytest.mark.asyncio
    async def test_retrieve_by_query(self):
        storage = InMemoryStorage()
        om = ObservationalMemory(storage=storage)
        await om.extract_and_store([_user("My name is Fiona"), _user("I live in Oslo")])
        facts = await om.get_relevant_facts(query="Oslo")
        assert len(facts) >= 1
        assert any("Oslo" in f.content for f in facts)


# --- facts_to_system_prompt ---


class TestFactsToSystemPrompt:
    def test_empty_returns_empty(self):
        assert facts_to_system_prompt([]) == ""

    def test_non_empty_returns_block(self):
        facts = [
            Fact(content="Name is Alice", source_message_id="m1"),
            Fact(content="Lives in Oslo", source_message_id="m2"),
        ]
        result = facts_to_system_prompt(facts)
        assert "<observed_facts>" in result
        assert "</observed_facts>" in result
        assert "- Name is Alice" in result
        assert "- Lives in Oslo" in result
