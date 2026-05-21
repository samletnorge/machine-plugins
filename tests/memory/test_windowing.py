"""Tests for windowing strategies."""

import pytest

from machine_core.plugins.memory_support.windowing import (
    LastNWindow,
    TokenLimitedWindow,
    SummarizedWindow,
)
from machine_core.plugins.memory_support.thread import Message, MessageRole


def _msg(role: MessageRole, content: str) -> Message:
    return Message(role=role, content=content)


def _user(content: str) -> Message:
    return _msg(MessageRole.USER, content)


def _assistant(content: str) -> Message:
    return _msg(MessageRole.ASSISTANT, content)


def _system(content: str) -> Message:
    return _msg(MessageRole.SYSTEM, content)


# --- LastNWindow ---


class TestLastNWindow:
    def test_empty_returns_empty(self):
        assert LastNWindow(n=5).apply([]) == []

    def test_keeps_last_n(self):
        msgs = [_user(f"msg{i}") for i in range(10)]
        result = LastNWindow(n=3, preserve_system=False).apply(msgs)
        assert len(result) == 3
        assert [m.content for m in result] == ["msg7", "msg8", "msg9"]

    def test_preserves_leading_system_messages(self):
        msgs = [_system("sys1"), _system("sys2"), _user("u1"), _user("u2"), _user("u3")]
        result = LastNWindow(n=2, preserve_system=True).apply(msgs)
        assert result[0].content == "sys1"
        assert result[1].content == "sys2"
        assert result[2].content == "u2"
        assert result[3].content == "u3"
        assert len(result) == 4

    def test_no_preserve_system(self):
        msgs = [_system("sys"), _user("u1"), _user("u2"), _user("u3")]
        result = LastNWindow(n=2, preserve_system=False).apply(msgs)
        assert len(result) == 2
        assert result[0].content == "u2"
        assert result[1].content == "u3"

    def test_fewer_than_n(self):
        msgs = [_user("only")]
        result = LastNWindow(n=5).apply(msgs)
        assert len(result) == 1


# --- TokenLimitedWindow ---


class TestTokenLimitedWindow:
    def test_empty_returns_empty(self):
        assert TokenLimitedWindow(max_tokens=100).apply([]) == []

    def test_keeps_within_budget(self):
        # Each message is ~1 word = ~1 token
        msgs = [_user(f"word{i}") for i in range(20)]
        result = TokenLimitedWindow(max_tokens=5, preserve_system=False).apply(msgs)
        assert len(result) <= 6  # at most ~5 tokens worth

    def test_preserves_system_messages(self):
        msgs = [_system("sys"), _user("a"), _user("b"), _user("c")]
        result = TokenLimitedWindow(max_tokens=100, preserve_system=True).apply(msgs)
        assert result[0].role == MessageRole.SYSTEM
        assert result[0].content == "sys"

    def test_single_huge_message(self):
        big = _user(" ".join(["word"] * 10000))
        result = TokenLimitedWindow(max_tokens=5, preserve_system=False).apply([big])
        # Should still include at least the one message
        assert len(result) == 1


# --- SummarizedWindow ---


class TestSummarizedWindow:
    def test_under_threshold_returns_all(self):
        msgs = [_user(f"m{i}") for i in range(5)]
        result = SummarizedWindow(keep_recent=3, summarize_after=10).apply(msgs)
        assert len(result) == 5

    def test_over_threshold_collapses(self):
        msgs = [_user(f"message {i}") for i in range(25)]
        result = SummarizedWindow(keep_recent=5, summarize_after=20).apply(msgs)
        # 1 summary + 5 recent
        assert len(result) == 6
        assert result[0].role == MessageRole.SYSTEM
        assert "[Summary of" in result[0].content

    def test_summary_message_is_system(self):
        msgs = [_user(f"msg{i}") for i in range(30)]
        result = SummarizedWindow(keep_recent=5, summarize_after=10).apply(msgs)
        assert result[0].role == MessageRole.SYSTEM
