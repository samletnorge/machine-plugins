"""Integration tests: all workspace plugins loaded together."""

import asyncio

from machine_core import Machine, Runnable, Streamable
from machine_core.stream import StreamResponse, StreamChunk  # noqa: F401

from tests.conftest import load_workspace_plugins


async def _machine_with_all_plugins() -> Machine:
    """Helper: create a Machine and load every workspace plugin."""
    machine = Machine()
    await load_workspace_plugins(machine)
    return machine


async def test_all_plugins_load():
    """Every category plugin should load and register its category."""
    m = await _machine_with_all_plugins()
    for category in (
        "tool",
        "model_provider",
        "agent",
        "prompt",
        "structured_output",
        "embedding",
        "vector_store",
    ):
        assert category in m.list_categories(), f"Missing category: {category}"
    await m.shutdown()


async def test_cross_category_registration():
    """Register items across categories via Machine API."""
    m = await _machine_with_all_plugins()

    from tool_support.schemas import ToolDefinition

    calc_tool = ToolDefinition(
        name="calculator",
        description="Math calculator",
        parameters={"type": "object"},
        handler=lambda **kw: 42,
    )
    m.register("tool", "calculator", calc_tool)

    from agent_support.schemas import AgentDefinition

    agent_def = AgentDefinition(
        name="math-agent",
        description="Does math",
        tool_refs=["calculator"],
    )
    m.register("agent", "math-agent", agent_def)

    resolved_tool = m.resolve("tool", "calculator")
    assert resolved_tool.name == "calculator"

    resolved_agent = m.resolve("agent", "math-agent")
    assert resolved_agent.tool_refs == ["calculator"]

    for tool_name in resolved_agent.tool_refs:
        t = m.resolve("tool", tool_name)
        assert t is not None

    await m.shutdown()


async def test_protocol_check_on_resolved():
    """Registered items can be checked against core protocols."""
    m = await _machine_with_all_plugins()

    class FakeAgent:
        async def run(self, input, **kwargs):
            return f"echo: {input}"

    m.register("agent", "echo", FakeAgent())
    agent = m.resolve("agent", "echo")
    assert isinstance(agent, Runnable)
    assert not isinstance(agent, Streamable)

    result = await agent.run("hello")
    assert result == "echo: hello"

    await m.shutdown()


async def test_hookspecs_from_all_plugins():
    """All hookspecs from all plugins should be registered."""
    m = await _machine_with_all_plugins()
    expected_hooks = [
        "before_tool_call",
        "after_tool_call",
        "on_tool_error",
        "before_model_invoke",
        "after_model_invoke",
        "on_model_error",
        "before_agent_run",
        "after_agent_run",
        "on_agent_handoff",
        "on_agent_step",
        "on_agent_error",
        "before_prompt_render",
        "after_prompt_render",
        "before_generate_object",
        "after_generate_object",
        "on_validation_retry",
        "before_embed",
        "after_embed",
        "before_search",
        "after_search",
        "before_upsert",
        "after_upsert",
    ]
    for hook in expected_hooks:
        assert hook in m.hooks._specs, f"Missing hookspec: {hook}"
    await m.shutdown()


async def test_event_observation_across_plugins():
    """Events from one plugin's category can be observed by anyone."""
    m = await _machine_with_all_plugins()

    from machine_core.plugin.events import ItemRegistered

    events_seen = []
    m.bus.on(ItemRegistered, lambda e: events_seen.append(e))

    await m.bus.emit(
        ItemRegistered(
            source="test", category="tool", name="calc", registered_by="test"
        )
    )

    await asyncio.sleep(0.05)

    assert len(events_seen) == 1
    assert events_seen[0].category == "tool"

    await m.shutdown()
