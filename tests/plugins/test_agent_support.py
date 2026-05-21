"""Tests for agent-support builtin plugin."""

import pytest
from machine_core.plugins.agent_support.schemas import (
    AgentDefinition,
    AgentRunner,
    AgentRunResult,
    AgentStep,
    HandoffRequest,
)


def test_agent_definition_minimal():
    ad = AgentDefinition(name="greeter", description="Greets users")
    assert ad.name == "greeter"
    assert ad.tool_refs == []
    assert ad.max_steps == 10


def test_agent_definition_full():
    ad = AgentDefinition(
        name="research-agent",
        description="Does research",
        model_ref="openai/gpt-4o",
        tool_refs=["web_search", "calculator"],
        instruction="You are a research assistant.",
        max_steps=25,
        metadata={"team": "backend"},
    )
    assert len(ad.tool_refs) == 2
    assert ad.model_ref == "openai/gpt-4o"


def test_agent_step():
    step = AgentStep(
        step_type="tool_call",
        detail={"tool": "calculator", "args": {"expr": "2+2"}},
        duration_ms=15.0,
    )
    assert step.step_type == "tool_call"


def test_agent_run_result():
    result = AgentRunResult(
        agent_name="greeter",
        output="Hello!",
        steps=[AgentStep(step_type="output", detail={"text": "Hello!"})],
        duration_ms=100.0,
    )
    assert len(result.steps) == 1


def test_handoff_request():
    hr = HandoffRequest(
        from_agent="router",
        to_agent="specialist",
        message="Handle this query",
        context={"topic": "billing"},
    )
    assert hr.from_agent == "router"
    assert hr.context["topic"] == "billing"


async def test_plugin_setup_registers_category():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="agent-support",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "agent:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="machine_core.plugins.agent_support:AgentSupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("agent-support")
    assert "agent" in m._registry
    assert "before_agent_run" in m.hooks._specs
    assert "after_agent_run" in m.hooks._specs
    assert "on_agent_handoff" in m.hooks._specs
    assert "on_agent_step" in m.hooks._specs
    assert "on_agent_error" in m.hooks._specs


class _MockRunner:
    async def run(self, definition, input, tools, context=None):
        return AgentRunResult(
            agent_name=definition.name, output="hello", steps=[], duration_ms=10.0
        )


def test_agent_runner_protocol():
    runner = _MockRunner()
    assert isinstance(runner, AgentRunner)


@pytest.mark.asyncio
async def test_agent_runner_run():
    runner = _MockRunner()
    defn = AgentDefinition(name="test", description="test agent")
    result = await runner.run(defn, "hi", [])
    assert result.agent_name == "test"
    assert result.output == "hello"
