"""Channel support plugin — registers channel category with Machine.

Provides InMemoryChannel and a real WebSocketChannel client.
"""

from __future__ import annotations

import asyncio
import json
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


# --- WebSocketChannel ---


class WebSocketChannel(Channel):
    """WebSocket client channel backed by the ``websockets`` library.

    Messages are JSON frames shaped like :class:`Message`. Incoming frames are
    fanned out by a background receiver task (started by :meth:`connect`) to
    per-channel queues and to registered subscriptions.

    ``websockets`` is imported lazily so merely constructing the channel (as the
    plugin does at registration time) never requires the dependency.
    """

    def __init__(self, url: str = "ws://localhost:8080"):
        self._url = url
        self._ws: Any = None
        self._receiver_task: asyncio.Task | None = None
        self._queues: dict[str, asyncio.Queue] = {}
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)

    async def connect(self) -> None:
        """Open the WebSocket connection and start the receiver loop."""
        if self._ws is not None:
            return
        try:
            import websockets
        except ImportError as e:
            raise ImportError(
                "WebSocketChannel requires the 'websockets' package. Install it "
                "with: pip install websockets."
            ) from e
        self._ws = await websockets.connect(self._url)
        self._receiver_task = asyncio.create_task(self._receiver_loop())

    def _ensure_connected(self) -> None:
        if self._ws is not None:
            return
        try:
            import websockets  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "WebSocketChannel requires the 'websockets' package. Install it "
                "with: pip install websockets."
            ) from e
        raise RuntimeError(
            "WebSocketChannel is not connected; call 'await connect()' first."
        )

    def _queue(self, channel: str) -> asyncio.Queue:
        queue = self._queues.get(channel)
        if queue is None:
            queue = asyncio.Queue()
            self._queues[channel] = queue
        return queue

    @staticmethod
    def _decode(raw: Any) -> Message | None:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        channel = payload.get("channel")
        if not isinstance(channel, str):
            return None
        return Message(
            channel=channel,
            content=payload.get("content"),
            sender=payload.get("sender", ""),
            metadata=payload.get("metadata") or {},
        )

    async def _receiver_loop(self) -> None:
        ws = self._ws
        if ws is None:
            return
        try:
            async for raw in ws:
                message = self._decode(raw)
                if message is None:
                    continue
                self._queue(message.channel).put_nowait(message)
                for sub in list(self._subscriptions.get(message.channel, [])):
                    try:
                        await sub.callback(message)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            raise
        except Exception:
            # Connection dropped or closed; receive() will simply time out.
            pass

    async def send(
        self, channel: str, content: Any, sender: str = "", metadata: dict | None = None
    ) -> Message:
        self._ensure_connected()
        message = Message(
            channel=channel, content=content, sender=sender, metadata=metadata or {}
        )
        await self._ws.send(
            json.dumps(
                {
                    "channel": message.channel,
                    "content": message.content,
                    "sender": message.sender,
                    "metadata": message.metadata,
                }
            )
        )
        return message

    async def receive(self, channel: str, timeout: float = 0) -> Message | None:
        self._ensure_connected()
        queue = self._queue(channel)
        try:
            if timeout > 0:
                return await asyncio.wait_for(queue.get(), timeout=timeout)
            return queue.get_nowait()
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

    async def close(self) -> None:
        """Close the connection and stop the receiver loop."""
        if self._receiver_task is not None:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except (asyncio.CancelledError, Exception):
                pass
            self._receiver_task = None
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None


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
