"""PubSub support plugin — registers pubsub category with Machine.

Provides InMemoryPubSub implementation.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from collections import defaultdict


# --- Models ---


@dataclass
class Topic:
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PubSubSubscription:
    topic: str
    callback: Callable[[Any], Awaitable[None]]
    subscriber_id: str = ""


@dataclass
class PubSubEvent:
    topic: str
    data: Any
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# --- Base class ---


class PubSubProvider(ABC):
    @abstractmethod
    async def publish(
        self, topic: str, data: Any, source: str = "", metadata: dict | None = None
    ) -> PubSubEvent: ...

    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        callback: Callable[[PubSubEvent], Awaitable[None]],
        subscriber_id: str = "",
    ) -> PubSubSubscription: ...

    @abstractmethod
    async def unsubscribe(self, topic: str, subscriber_id: str) -> bool: ...

    @abstractmethod
    async def list_topics(self) -> list[Topic]: ...


# --- InMemoryPubSub ---


class InMemoryPubSub(PubSubProvider):
    def __init__(self):
        self._subscriptions: dict[str, list[PubSubSubscription]] = defaultdict(list)
        self._topics: dict[str, Topic] = {}
        self._history: list[PubSubEvent] = []

    async def publish(
        self, topic: str, data: Any, source: str = "", metadata: dict | None = None
    ) -> PubSubEvent:
        if topic not in self._topics:
            self._topics[topic] = Topic(name=topic)
        event = PubSubEvent(
            topic=topic, data=data, source=source, metadata=metadata or {}
        )
        self._history.append(event)
        for sub in self._subscriptions.get(topic, []):
            try:
                await sub.callback(event)
            except Exception:
                pass
        return event

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[PubSubEvent], Awaitable[None]],
        subscriber_id: str = "",
    ) -> PubSubSubscription:
        if topic not in self._topics:
            self._topics[topic] = Topic(name=topic)
        sub = PubSubSubscription(
            topic=topic, callback=callback, subscriber_id=subscriber_id
        )
        self._subscriptions[topic].append(sub)
        return sub

    async def unsubscribe(self, topic: str, subscriber_id: str) -> bool:
        subs = self._subscriptions.get(topic, [])
        before = len(subs)
        self._subscriptions[topic] = [
            s for s in subs if s.subscriber_id != subscriber_id
        ]
        return len(self._subscriptions[topic]) < before

    async def list_topics(self) -> list[Topic]:
        return list(self._topics.values())

    @property
    def history(self) -> list[PubSubEvent]:
        return list(self._history)


# --- Plugin ---


class PubSubSupportPlugin:
    """Plugin that registers the pubsub category and built-in implementations."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx):
        ctx.register_category(
            "pubsub",
            operations={
                "publish": {"method": "POST", "on": "item"},
                "subscribe": {"method": "POST", "on": "item"},
                "unsubscribe": {"method": "POST", "on": "item"},
                "list_topics": {"method": "GET", "on": "collection"},
            },
        )
        ctx.register("pubsub", "memory", InMemoryPubSub())

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
