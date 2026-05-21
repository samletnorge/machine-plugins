"""Tests for channel_support plugin."""

import pytest
from machine_core.plugins.channel_support import (
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


# --- WebSocketChannel (stub) tests ---


@pytest.mark.asyncio
async def test_websocket_stub_raises():
    ws = WebSocketChannel()
    with pytest.raises(NotImplementedError):
        await ws.send("ch", "data")


# --- Plugin test ---


def test_plugin_instantiation():
    plugin = ChannelSupportPlugin()
    assert hasattr(plugin, "setup")
