"""Tests for pubsub_support plugin."""

import pytest
from pubsub_support import (
    PubSubSupportPlugin,
    InMemoryPubSub,
    Topic,
    PubSubEvent,
    PubSubSubscription,
)


@pytest.fixture
def pubsub():
    return InMemoryPubSub()


# --- InMemoryPubSub tests ---


@pytest.mark.asyncio
async def test_publish_creates_topic(pubsub):
    await pubsub.publish("events.user", {"action": "login"})
    topics = await pubsub.list_topics()
    assert any(t.name == "events.user" for t in topics)


@pytest.mark.asyncio
async def test_publish_returns_event(pubsub):
    event = await pubsub.publish("t", "data", source="src")
    assert isinstance(event, PubSubEvent)
    assert event.topic == "t"
    assert event.data == "data"
    assert event.source == "src"


@pytest.mark.asyncio
async def test_subscribe_and_publish(pubsub):
    received = []

    async def handler(event):
        received.append(event)

    await pubsub.subscribe("t", handler, subscriber_id="s1")
    await pubsub.publish("t", "hello")
    assert len(received) == 1
    assert received[0].data == "hello"


@pytest.mark.asyncio
async def test_unsubscribe(pubsub):
    received = []

    async def handler(event):
        received.append(event)

    await pubsub.subscribe("t", handler, subscriber_id="s1")
    result = await pubsub.unsubscribe("t", "s1")
    assert result is True
    await pubsub.publish("t", "data")
    assert len(received) == 0


@pytest.mark.asyncio
async def test_unsubscribe_nonexistent(pubsub):
    result = await pubsub.unsubscribe("t", "nope")
    assert result is False


@pytest.mark.asyncio
async def test_multiple_subscribers(pubsub):
    r1, r2 = [], []

    async def h1(e):
        r1.append(e)

    async def h2(e):
        r2.append(e)

    await pubsub.subscribe("t", h1, subscriber_id="s1")
    await pubsub.subscribe("t", h2, subscriber_id="s2")
    await pubsub.publish("t", "x")
    assert len(r1) == 1
    assert len(r2) == 1


@pytest.mark.asyncio
async def test_list_topics_empty(pubsub):
    topics = await pubsub.list_topics()
    assert topics == []


@pytest.mark.asyncio
async def test_history(pubsub):
    await pubsub.publish("t1", "a")
    await pubsub.publish("t2", "b")
    assert len(pubsub.history) == 2


@pytest.mark.asyncio
async def test_subscribe_returns_subscription(pubsub):
    async def noop(e):
        pass

    sub = await pubsub.subscribe("t", noop, subscriber_id="x")
    assert isinstance(sub, PubSubSubscription)
    assert sub.topic == "t"


# --- Plugin test ---


def test_plugin_instantiation():
    plugin = PubSubSupportPlugin()
    assert hasattr(plugin, "setup")
