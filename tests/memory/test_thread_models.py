"""Tests for Thread, Message, MessageRole, and Fact models."""

from datetime import datetime, timezone

import pytest

from machine_core.plugins.memory_support.thread import (
    Fact,
    Message,
    MessageRole,
    Thread,
)


class TestMessageRole:
    def test_enum_values(self):
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL == "tool"

    def test_all_members(self):
        assert set(MessageRole) == {
            MessageRole.USER,
            MessageRole.ASSISTANT,
            MessageRole.SYSTEM,
            MessageRole.TOOL,
        }


class TestMessage:
    def test_default_id_prefix(self):
        msg = Message(role=MessageRole.USER, content="hi")
        assert msg.id.startswith("msg_")

    def test_unique_ids(self):
        a = Message(role=MessageRole.USER, content="a")
        b = Message(role=MessageRole.USER, content="b")
        assert a.id != b.id

    def test_required_fields(self):
        with pytest.raises(Exception):
            Message()  # missing role and content

    def test_created_at_auto(self):
        before = datetime.now(timezone.utc)
        msg = Message(role=MessageRole.USER, content="x")
        assert msg.created_at >= before

    def test_metadata_default_empty(self):
        msg = Message(role=MessageRole.USER, content="x")
        assert msg.metadata == {}

    def test_metadata_provided(self):
        msg = Message(role=MessageRole.USER, content="x", metadata={"k": "v"})
        assert msg.metadata == {"k": "v"}

    def test_all_roles_accepted(self):
        for role in MessageRole:
            msg = Message(role=role, content="test")
            assert msg.role == role


class TestThread:
    def test_default_id_prefix(self):
        t = Thread()
        assert t.id.startswith("thread_")

    def test_unique_ids(self):
        assert Thread().id != Thread().id

    def test_title_optional(self):
        t = Thread()
        assert t.title is None

    def test_title_provided(self):
        t = Thread(title="My Chat")
        assert t.title == "My Chat"

    def test_metadata_default_empty(self):
        assert Thread().metadata == {}

    def test_metadata_provided(self):
        t = Thread(metadata={"user_id": "u1"})
        assert t.metadata["user_id"] == "u1"

    def test_created_at_auto(self):
        before = datetime.now(timezone.utc)
        t = Thread()
        assert t.created_at >= before

    def test_updated_at_auto(self):
        t = Thread()
        assert t.updated_at is not None


class TestFact:
    def test_default_id_prefix(self):
        f = Fact(content="sky is blue", source_message_id="msg_abc")
        assert f.id.startswith("fact_")

    def test_unique_ids(self):
        a = Fact(content="a", source_message_id="m1")
        b = Fact(content="b", source_message_id="m2")
        assert a.id != b.id

    def test_required_fields(self):
        with pytest.raises(Exception):
            Fact()  # missing content and source_message_id

    def test_confidence_default(self):
        f = Fact(content="x", source_message_id="m")
        assert f.confidence == 1.0

    def test_confidence_custom(self):
        f = Fact(content="x", source_message_id="m", confidence=0.5)
        assert f.confidence == 0.5

    def test_expires_at_optional(self):
        f = Fact(content="x", source_message_id="m")
        assert f.expires_at is None

    def test_expires_at_provided(self):
        exp = datetime(2030, 1, 1, tzinfo=timezone.utc)
        f = Fact(content="x", source_message_id="m", expires_at=exp)
        assert f.expires_at == exp

    def test_thread_id_optional(self):
        f = Fact(content="x", source_message_id="m")
        assert f.thread_id is None

    def test_user_id_optional(self):
        f = Fact(content="x", source_message_id="m")
        assert f.user_id is None

    def test_created_at_auto(self):
        before = datetime.now(timezone.utc)
        f = Fact(content="x", source_message_id="m")
        assert f.created_at >= before
