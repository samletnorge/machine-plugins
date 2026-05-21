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
    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)

    async def send(
        self, channel: str, content: Any, sender: str = "", metadata: dict | None = None
    ) -> Message:
        msg = Message(
            channel=channel, content=content, sender=sender, metadata=metadata or {}
        )
        await self._queues[channel].put(msg)
        # Notify subscribers
        for sub in self._subscriptions.get(channel, []):
            try:
                await sub.callback(msg)
            except Exception:
                pass
        return msg

    async def receive(self, channel: str, timeout: float = 0) -> Message | None:
        q = self._queues[channel]
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
