"""Tests for BrregExpertPlugin.setup() wiring."""

from __future__ import annotations

import pytest

from agent_brreg_expert import BrregExpertPlugin


class FakeMachine:
    """Minimal machine mock for setup testing."""

    def __init__(self):
        self._registry: dict[tuple[str, str], object] = {}

    def register(self, category, name, impl, owner=None):
        self._registry[(category, name)] = impl

    def resolve(self, category, name):
        return self._registry.get((category, name))

    def list_category(self, category):
        return {k[1]: v for k, v in self._registry.items() if k[0] == category}


class FakeContext:
    """Minimal PluginContext mock."""

    def __init__(self, machine):
        self._machine = machine
        self._registrations = []

    def register(self, category, name, impl):
        self._machine.register(category, name, impl, owner="agent_brreg_expert")
        self._registrations.append((category, name))


@pytest.fixture
def machine():
    m = FakeMachine()
    # Pre-register the openapi generator with a simple mock
    m.register(
        "tool",
        "__openapi_generator__",
        {
            "generate_tools": lambda spec, **kw: [
                type("TD", (), {"name": "hentEnhet"})(),
                type("TD", (), {"name": "sokEnheter"})(),
            ]
        },
    )

    # Pre-register a no-op filter
    class FakeFilter:
        async def index_tools(self, tools):
            self.indexed = tools

    m.register("tool", "__filter_rag__", FakeFilter())
    return m


@pytest.mark.asyncio
async def test_setup_registers_pipeline_and_agent(machine, monkeypatch):
    """setup() should register rag_pipeline and agent."""
    # Mock httpx to avoid real network
    import httpx

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"openapi": "3.0.0", "info": {"title": "Brreg"}, "paths": {}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, **kw):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())

    plugin = BrregExpertPlugin()
    await plugin.initialize(config={"spec_url": "http://fake/spec.json"})

    ctx = FakeContext(machine)
    await plugin.setup(ctx)

    # Verify registrations
    assert machine.resolve("rag_pipeline", "brreg-companies") is not None
    assert machine.resolve("agent", "brreg-expert") is not None
    # Tools registered with brreg_ prefix
    assert machine.resolve("tool", "brreg_hentEnhet") is not None
    assert machine.resolve("tool", "brreg_sokEnheter") is not None


@pytest.mark.asyncio
async def test_setup_without_openapi_generator(machine, monkeypatch):
    """setup() should still register pipeline+agent even without tool_openapi."""
    # Remove the generator
    machine._registry.pop(("tool", "__openapi_generator__"), None)

    import httpx

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"openapi": "3.0.0", "info": {"title": "Brreg"}, "paths": {}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, **kw):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())

    plugin = BrregExpertPlugin()
    await plugin.initialize(config={})

    ctx = FakeContext(machine)
    await plugin.setup(ctx)

    # Pipeline and agent still registered
    assert machine.resolve("rag_pipeline", "brreg-companies") is not None
    assert machine.resolve("agent", "brreg-expert") is not None
