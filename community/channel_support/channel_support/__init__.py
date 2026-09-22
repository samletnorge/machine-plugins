"""Channel support plugin — registers channel category with Machine.

Provides InMemoryChannel and WebSocketChannel (stub).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from collections import defaultdict


# --- Models ---


@dataclass
class Message:
    channel: str
    content: Any
    sender: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    channel: str
    callback: Callable[[Message], Awaitable[None]]
    subscriber_id: str = ""


# --- Base class ---


class Channel(ABC):
    @abstractmethod
    async def send(
        self, channel: str, content: Any, sender: str = "", metadata: dict | None = None
    ) -> Message: ...

    @abstractmethod
    async def receive(self, channel: str, timeout: float = 0) -> Message | None: ...

    @abstractmethod
    async def subscribe(
        self,
        channel: str,
        callback: Callable[[Message], Awaitable[None]],
        subscriber_id: str = "",
    ) -> Subscription: ...

    @abstractmethod
    async def unsubscribe(self, channel: str, subscriber_id: str) -> bool: ...


# --- InMemoryChannel ---


class InMemoryChannel(Channel):
    def __init__(self, max_queue_size: int = 1000):
        self._queues: dict[str, asyncio.Queue] = {}
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._max_queue_size = max_queue_size

    def _queue(self, channel: str) -> asyncio.Queue:
        queue = self._queues.get(channel)
        if queue is None:
            queue = asyncio.Queue(maxsize=self._max_queue_size)
            self._queues[channel] = queue
        return queue

    async def send(
        self, channel: str, content: Any, sender: str = "", metadata: dict | None = None
    ) -> Message:
        msg = Message(
            channel=channel, content=content, sender=sender, metadata=metadata or {}
        )
        queue = self._queue(channel)
        if queue.full():
            # Drop the oldest message to bound memory for slow consumers.
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(msg)
        # Notify subscribers
        for sub in self._subscriptions.get(channel, []):
            try:
                await sub.callback(msg)
            except Exception:
                pass
        return msg

    async def receive(self, channel: str, timeout: float = 0) -> Message | None:
        q = self._queue(channel)
        try:
            if timeout > 0:
                return await asyncio.wait_for(q.get(), timeout=timeout)
            else:
                return q.get_nowait()
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[Message], Awaitable[None]],
        subscriber_id: str = "",
    ) -> Subscription:
        sub = Subscription(
            channel=channel, callback=callback, subscriber_id=subscriber_id
        )
        self._subscriptions[channel].append(sub)
        return sub

    async def unsubscribe(self, channel: str, subscriber_id: str) -> bool:
        subs = self._subscriptions.get(channel, [])
        before = len(subs)
        self._subscriptions[channel] = [
            s for s in subs if s.subscriber_id != subscriber_id
        ]
        return len(self._subscriptions[channel]) < before


# --- WebSocketChannel (stub) ---


class WebSocketChannel(Channel):
    """Stub WebSocket channel for future implementation."""

    def __init__(self, url: str = "ws://localhost:8080"):
        self._url = url

    async def send(
        self, channel: str, content: Any, sender: str = "", metadata: dict | None = None
    ) -> Message:
        raise NotImplementedError("WebSocketChannel is a stub")

    async def receive(self, channel: str, timeout: float = 0) -> Message | None:
        raise NotImplementedError("WebSocketChannel is a stub")

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[Message], Awaitable[None]],
        subscriber_id: str = "",
    ) -> Subscription:
        raise NotImplementedError("WebSocketChannel is a stub")

    async def unsubscribe(self, channel: str, subscriber_id: str) -> bool:
        raise NotImplementedError("WebSocketChannel is a stub")


# --- Plugin ---


class ChannelSupportPlugin:
    """Plugin that registers the channel category and built-in channel implementations."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx):
        ctx.register_category(
            "channel",
            operations={
                "send": {"method": "POST", "on": "item"},
                "receive": {"method": "GET", "on": "item"},
                "subscribe": {"method": "POST", "on": "item"},
                "unsubscribe": {"method": "POST", "on": "item"},
            },
        )
        ctx.register("channel", "memory", InMemoryChannel())
        ctx.register("channel", "websocket", WebSocketChannel())

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
