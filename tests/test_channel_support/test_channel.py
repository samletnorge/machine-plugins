"""Tests for channel_support plugin."""

import pytest
from channel_support import (
    ChannelSupportPlugin,
    InMemoryChannel,
    WebSocketChannel,
    Message,
    Subscription,
)


@pytest.fixture
def channel():
    return InMemoryChannel()


# --- InMemoryChannel tests ---


@pytest.mark.asyncio
async def test_send_and_receive(channel):
    await channel.send("ch1", "hello", sender="alice")
    msg = await channel.receive("ch1")
    assert msg is not None
    assert msg.content == "hello"
    assert msg.sender == "alice"


@pytest.mark.asyncio
async def test_receive_empty(channel):
    msg = await channel.receive("empty")
    assert msg is None


@pytest.mark.asyncio
async def test_subscribe_receives_messages(channel):
    received = []

    async def handler(msg):
        received.append(msg)

    await channel.subscribe("ch1", handler, subscriber_id="sub1")
    await channel.send("ch1", "data")
    assert len(received) == 1
    assert received[0].content == "data"


@pytest.mark.asyncio
async def test_unsubscribe(channel):
    received = []

    async def handler(msg):
        received.append(msg)

    await channel.subscribe("ch1", handler, subscriber_id="sub1")
    result = await channel.unsubscribe("ch1", "sub1")
    assert result is True
    await channel.send("ch1", "data")
    assert len(received) == 0


@pytest.mark.asyncio
async def test_unsubscribe_nonexistent(channel):
    result = await channel.unsubscribe("ch1", "nope")
    assert result is False


@pytest.mark.asyncio
async def test_multiple_subscribers(channel):
    r1, r2 = [], []

    async def h1(msg):
        r1.append(msg)

    async def h2(msg):
        r2.append(msg)

    await channel.subscribe("ch", h1, subscriber_id="s1")
    await channel.subscribe("ch", h2, subscriber_id="s2")
    await channel.send("ch", "hi")
    assert len(r1) == 1
    assert len(r2) == 1


@pytest.mark.asyncio
async def test_send_returns_message(channel):
    msg = await channel.send("ch", "content", sender="bob")
    assert isinstance(msg, Message)
    assert msg.channel == "ch"


@pytest.mark.asyncio
async def test_subscribe_returns_subscription(channel):
    async def noop(msg):
        pass

    sub = await channel.subscribe("ch", noop, subscriber_id="x")
    assert isinstance(sub, Subscription)
    assert sub.subscriber_id == "x"


# --- WebSocketChannel tests ---


@pytest.mark.asyncio
async def test_websocket_unconnected_send_raises():
    ws = WebSocketChannel("ws://127.0.0.1:1")
    with pytest.raises((RuntimeError, ImportError)):
        await ws.send("ch", "data")


@pytest.mark.asyncio
async def test_websocket_unconnected_receive_raises():
    ws = WebSocketChannel("ws://127.0.0.1:1")
    with pytest.raises((RuntimeError, ImportError)):
        await ws.receive("ch")


@pytest.mark.asyncio
async def test_websocket_subscribe_unsubscribe():
    ws = WebSocketChannel("ws://127.0.0.1:1")

    async def noop(msg):
        pass

    sub = await ws.subscribe("ch", noop, subscriber_id="s1")
    assert isinstance(sub, Subscription)
    assert sub.subscriber_id == "s1"
    assert await ws.unsubscribe("ch", "s1") is True
    assert await ws.unsubscribe("ch", "s1") is False


@pytest.mark.asyncio
async def test_websocket_send_receive_over_local_server():
    websockets = pytest.importorskip("websockets")

    async def echo(websocket):
        async for raw in websocket:
            await websocket.send(raw)

    async with websockets.serve(echo, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        ws = WebSocketChannel(f"ws://127.0.0.1:{port}")
        await ws.connect()
        try:
            received = []

            async def handler(msg):
                received.append(msg)

            await ws.subscribe("ch", handler, subscriber_id="s1")
            sent = await ws.send("ch", {"hello": "world"}, sender="alice")
            assert sent.channel == "ch"

            msg = await ws.receive("ch", timeout=2.0)
            assert msg is not None
            assert msg.channel == "ch"
            assert msg.content == {"hello": "world"}
            assert msg.sender == "alice"

            assert len(received) == 1
            assert received[0].content == {"hello": "world"}
        finally:
            await ws.close()


# --- Plugin test ---


def test_plugin_instantiation():
    plugin = ChannelSupportPlugin()
    assert hasattr(plugin, "setup")


@pytest.mark.asyncio
async def test_queue_is_bounded():
    from channel_support import InMemoryChannel

    channel = InMemoryChannel(max_queue_size=2)
    for i in range(4):
        await channel.send("c", i)

    first = await channel.receive("c")
    second = await channel.receive("c")
    assert [first.content, second.content] == [2, 3]
    assert await channel.receive("c") is None
