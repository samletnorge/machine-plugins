"""End-to-end integration tests for Machine + PluginManager."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from machine_core.machine import Machine
from machine_core.plugin.events import Event
from machine_core.plugin.manifest import PluginManifest, TransportConfig


# ---------------------------------------------------------------------------
# Fake plugin classes (in-process transport calls initialize/shutdown on these)
# ---------------------------------------------------------------------------


class FakeItemPlugin:
    """Plugin that registers items when initialized."""

    def __init__(self) -> None:
        self.initialized = False
        self.shut_down = False

    async def initialize(self, **kwargs: Any) -> None:
        self.initialized = True

    async def shutdown(self, **kwargs: Any) -> None:
        self.shut_down = True


class FakeCategoryPlugin:
    async def initialize(self, **kwargs: Any) -> None:
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass


class FakeHookProducer:
    async def initialize(self, **kwargs: Any) -> None:
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass


class FakeHookConsumer:
    async def initialize(self, **kwargs: Any) -> None:
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass


class FakeEventEmitter:
    async def initialize(self, **kwargs: Any) -> None:
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass


class FakeEventListener:
    async def initialize(self, **kwargs: Any) -> None:
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass


class FakeLifecyclePlugin:
    async def initialize(self, **kwargs: Any) -> None:
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manifest(
    name: str, cls: type, capabilities: list[str] | None = None
) -> PluginManifest:
    module = cls.__module__
    class_name = cls.__qualname__
    return PluginManifest(
        name=name,
        version="0.1.0",
        capabilities=capabilities or [],
        transport=TransportConfig(
            type="in-process", entry_point=f"{module}:{class_name}"
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def machine() -> Machine:
    return Machine()


@pytest.mark.asyncio
async def test_full_plugin_lifecycle(machine: Machine):
    """Load plugin → register items via context → verify → unload → verify cleanup."""
    manifest = _manifest("item_plugin", FakeItemPlugin, capabilities=["tools:register"])
    machine.plugins.register_manifest(manifest)

    await machine.plugins.load("item_plugin")
    assert machine.plugins.is_loaded("item_plugin")

    # Use the plugin's context to register an item
    host = machine.plugins.get_host("item_plugin")
    assert host is not None and host.context is not None
    machine.register_category("tools")
    host.context.register("tools", "wrench", {"size": 10})

    assert machine.resolve("tools", "wrench") == {"size": 10}
    assert machine.get_owner("tools", "wrench") == "item_plugin"

    # Unload → cleanup
    await machine.plugins.unload("item_plugin")
    assert not machine.plugins.is_loaded("item_plugin")
    assert machine.resolve("tools", "wrench") is None


@pytest.mark.asyncio
async def test_category_plugin_then_item_plugin(machine: Machine):
    """Category plugin defines category+validator, item plugin registers in it."""
    cat_manifest = _manifest(
        "cat_plugin", FakeCategoryPlugin, capabilities=["categories:define"]
    )
    item_manifest = _manifest(
        "item_plugin", FakeItemPlugin, capabilities=["numbers:register"]
    )

    machine.plugins.register_manifest(cat_manifest)
    machine.plugins.register_manifest(item_manifest)

    # Load category plugin and define category
    await machine.plugins.load("cat_plugin")
    cat_host = machine.plugins.get_host("cat_plugin")
    cat_host.context.register_category(
        "numbers", validator=lambda x: isinstance(x, int)
    )

    # Load item plugin and register valid item
    await machine.plugins.load("item_plugin")
    item_host = machine.plugins.get_host("item_plugin")
    item_host.context.register("numbers", "answer", 42)

    assert machine.resolve("numbers", "answer") == 42

    # Invalid item should raise
    from machine_core.plugin.errors import ValidationError

    with pytest.raises(ValidationError):
        item_host.context.register("numbers", "bad", "not_int")


@pytest.mark.asyncio
async def test_hook_round_trip(machine: Machine):
    """Plugin A defines hookspec, Plugin B subscribes, call returns results."""
    prod_manifest = _manifest(
        "hook_prod", FakeHookProducer, capabilities=["hooks:define"]
    )
    cons_manifest = _manifest(
        "hook_cons", FakeHookConsumer, capabilities=["hooks:subscribe"]
    )

    machine.plugins.register_manifest(prod_manifest)
    machine.plugins.register_manifest(cons_manifest)

    await machine.plugins.load("hook_prod")
    await machine.plugins.load("hook_cons")

    # Producer defines hookspec
    prod_host = machine.plugins.get_host("hook_prod")
    prod_host.context.register_hookspec("greet")

    # Consumer subscribes
    cons_host = machine.plugins.get_host("hook_cons")
    cons_host.context.subscribe_hook("greet", lambda name="World": f"Hello, {name}!")

    results = await machine.hooks.call("greet", name="Alice")
    assert results == ["Hello, Alice!"]


@pytest.mark.asyncio
async def test_event_round_trip(machine: Machine):
    """Plugin A emits event, Plugin B receives it."""

    class CustomEvent(Event):
        payload: str

    emitter_manifest = _manifest(
        "emitter", FakeEventEmitter, capabilities=["events:emit"]
    )
    listener_manifest = _manifest(
        "listener", FakeEventListener, capabilities=["events:subscribe"]
    )

    machine.plugins.register_manifest(emitter_manifest)
    machine.plugins.register_manifest(listener_manifest)

    await machine.plugins.load("emitter")
    await machine.plugins.load("listener")

    received: list[str] = []

    listener_host = machine.plugins.get_host("listener")
    listener_host.context.on(CustomEvent, lambda e: received.append(e.payload))

    emitter_host = machine.plugins.get_host("emitter")
    await emitter_host.context.emit(CustomEvent(source="emitter", payload="ping"))

    # Let the event bus task run
    await asyncio.sleep(0.05)

    assert received == ["ping"]


@pytest.mark.asyncio
async def test_machine_start_and_shutdown(machine: Machine):
    """machine.start() discovers, load a plugin, machine.shutdown() unloads all."""
    manifest = _manifest("lifecycle", FakeLifecyclePlugin, capabilities=[])
    machine.plugins.register_manifest(manifest)

    await machine.start()
    assert "lifecycle" in machine.plugins.discovered_plugins

    await machine.plugins.load("lifecycle")
    assert machine.plugins.is_loaded("lifecycle")

    await machine.shutdown()
    assert not machine.plugins.is_loaded("lifecycle")
    assert machine.plugins.loaded_plugins == []
