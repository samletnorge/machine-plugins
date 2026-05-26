"""History windowing strategies for conversation memory.

These strategies control which messages are sent to the model,
keeping context within token limits while preserving relevance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from memory_support.thread import Message, MessageRole


class WindowStrategy(ABC):
    """Base class for windowing strategies."""

    @abstractmethod
    def apply(self, messages: list[Message]) -> list[Message]:
        """Apply the windowing strategy, returning the messages to send."""
        ...


class LastNWindow(WindowStrategy):
    """Keep the last N messages, optionally preserving leading system messages."""

    def __init__(self, n: int = 20, preserve_system: bool = True) -> None:
        self.n = n
        self.preserve_system = preserve_system

    def apply(self, messages: list[Message]) -> list[Message]:
        if not messages:
            return []

        system_msgs: list[Message] = []
        other_msgs: list[Message] = []

        if self.preserve_system:
            for m in messages:
                if m.role == MessageRole.SYSTEM and not other_msgs:
                    system_msgs.append(m)
                else:
                    other_msgs.append(m)
        else:
            other_msgs = list(messages)

        recent = other_msgs[-self.n :] if other_msgs else []
        return system_msgs + recent


class TokenLimitedWindow(WindowStrategy):
    """Keep messages from the end until a token budget is exceeded.

    Uses a simple word-count heuristic (words ~ tokens).
    """

    def __init__(self, max_tokens: int = 4000, preserve_system: bool = True) -> None:
        self.max_tokens = max_tokens
        self.preserve_system = preserve_system

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: ~1 token per word for English."""
        return len(text.split())

    def apply(self, messages: list[Message]) -> list[Message]:
        if not messages:
            return []

        system_msgs: list[Message] = []
        other_msgs: list[Message] = []

        if self.preserve_system:
            for m in messages:
                if m.role == MessageRole.SYSTEM and not other_msgs:
                    system_msgs.append(m)
                else:
                    other_msgs.append(m)
        else:
            other_msgs = list(messages)

        budget = self.max_tokens
        for sm in system_msgs:
            budget -= self._estimate_tokens(sm.content)

        selected: list[Message] = []
        for m in reversed(other_msgs):
            cost = self._estimate_tokens(m.content)
            if budget - cost < 0 and selected:
                break
            budget -= cost
            selected.insert(0, m)

        return system_msgs + selected


class SummarizedWindow(WindowStrategy):
    """When history exceeds a threshold, collapse older messages into a summary.

    The summary is a simple concatenation placeholder. In production, an LLM
    call would generate the summary (injected via MemoryManager).
    """

    def __init__(self, keep_recent: int = 10, summarize_after: int = 20) -> None:
        self.keep_recent = keep_recent
        self.summarize_after = summarize_after

    def apply(self, messages: list[Message]) -> list[Message]:
        if not messages or len(messages) <= self.summarize_after:
            return list(messages)

        older = messages[: -self.keep_recent]
        recent = messages[-self.keep_recent :]

        summary_text = f"[Summary of {len(older)} earlier messages] " + "; ".join(
            m.content[:60] for m in older[-5:]
        )
        summary_msg = Message(role=MessageRole.SYSTEM, content=summary_text)

        return [summary_msg] + recent
