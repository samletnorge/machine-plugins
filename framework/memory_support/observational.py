"""Observational memory — background fact extraction from conversations.

After each turn, facts/preferences/entities are extracted and stored.
In production the extraction uses an LLM call; the default extractor
uses simple keyword heuristics for development and testing.
"""

from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

from machine_core.plugins.memory_support.thread import Message, MessageRole, Fact

if TYPE_CHECKING:
    from machine_core.plugins.memory_support.storage import BaseStorage


class FactExtractor:
    """Extract facts from messages using keyword heuristics.

    This is the default development extractor. In production, replace with
    an LLM-based extractor that calls a model to identify facts, preferences,
    and entities.
    """

    _PATTERNS: list[re.Pattern] = [
        re.compile(r"(?:my name is|i'm called|call me)\s+(\w+)", re.IGNORECASE),
        re.compile(r"i (?:live|am) in\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
        re.compile(
            r"i (?:prefer|like|love|enjoy|use|drive|want)\s+(.+?)(?:\.|,|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"i (?:don't like|hate|dislike|avoid)\s+(.+?)(?:\.|,|$)", re.IGNORECASE
        ),
        re.compile(r"i (?:work at|work for|am a)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    ]

    def extract(
        self,
        messages: list[Message],
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[Fact]:
        """Extract facts from user messages using pattern matching."""
        facts: list[Fact] = []
        for msg in messages:
            if msg.role != MessageRole.USER:
                continue
            for pattern in self._PATTERNS:
                match = pattern.search(msg.content)
                if match:
                    fact_text = match.group(0).strip().rstrip(".,")
                    facts.append(
                        Fact(
                            content=fact_text,
                            source_message_id=msg.id,
                            thread_id=thread_id,
                            user_id=user_id,
                            confidence=0.8,
                        )
                    )
        return facts


class ObservationalMemory:
    """Manages background fact extraction and retrieval."""

    def __init__(
        self,
        storage: BaseStorage,
        extractor: Optional[FactExtractor] = None,
    ) -> None:
        self._storage = storage
        self._extractor = extractor or FactExtractor()

    async def extract_and_store(
        self,
        messages: list[Message],
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[Fact]:
        """Extract facts from messages and persist them."""
        facts = self._extractor.extract(messages, thread_id=thread_id, user_id=user_id)
        if facts:
            facts = await self._storage.store_facts(facts)
        return facts

    async def get_relevant_facts(
        self,
        *,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> list[Fact]:
        """Retrieve relevant facts, optionally filtered by query."""
        return await self._storage.get_facts(
            thread_id=thread_id,
            user_id=user_id,
            query=query,
            limit=limit,
        )


def facts_to_system_prompt(facts: list[Fact]) -> str:
    """Render a list of facts as a system prompt block."""
    if not facts:
        return ""
    lines = [f"- {f.content}" for f in facts]
    return (
        "<observed_facts>\n"
        "The following facts have been observed about the user:\n"
        + "\n".join(lines)
        + "\n</observed_facts>"
    )
