"""Tests for prompt_support builtin plugin."""

import pytest
from prompt_support.schemas import (
    PromptTemplate,
    PromptBlock,
    PromptVariable,
    RenderedPrompt,
)
from prompt_support.registry import PromptRegistry


def test_prompt_variable():
    v = PromptVariable(name="user_name", description="The user's name")
    assert v.required is True
    assert v.default is None


def test_prompt_template():
    t = PromptTemplate(
        name="greeting",
        template="Hello, {user_name}! You are a {role}.",
        variables=[
            PromptVariable(name="user_name"),
            PromptVariable(name="role", default="assistant"),
        ],
    )
    assert t.version == "1.0.0"
    assert len(t.variables) == 2


def test_prompt_block():
    b = PromptBlock(role="system", content="You are helpful.", name="sys_intro")
    assert b.role == "system"


def test_rendered_prompt():
    r = RenderedPrompt(
        text="Hello, Alice!",
        template_name="greeting",
        template_version="1.0.0",
        variables_used={"user_name": "Alice"},
    )
    assert "Alice" in r.text


def test_registry_register_and_get():
    reg = PromptRegistry()
    t = PromptTemplate(name="test", template="Hello {name}")
    reg.register(t)
    got = reg.get("test")
    assert got.name == "test"


def test_registry_get_missing_raises():
    reg = PromptRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")


def test_registry_render():
    reg = PromptRegistry()
    t = PromptTemplate(
        name="greet",
        template="Hello, {user_name}!",
        variables=[PromptVariable(name="user_name")],
    )
    reg.register(t)
    result = reg.render("greet", {"user_name": "Bob"})
    assert result.text == "Hello, Bob!"
    assert result.variables_used == {"user_name": "Bob"}


def test_registry_render_with_default():
    reg = PromptRegistry()
    t = PromptTemplate(
        name="greet",
        template="Hello, {user_name}! Role: {role}.",
        variables=[
            PromptVariable(name="user_name"),
            PromptVariable(name="role", required=False, default="user"),
        ],
    )
    reg.register(t)
    result = reg.render("greet", {"user_name": "Bob"})
    assert result.text == "Hello, Bob! Role: user."


def test_registry_compose():
    reg = PromptRegistry()
    blocks = [
        PromptBlock(role="system", content="You are helpful."),
        PromptBlock(role="user", content="What is 2+2?"),
    ]
    result = reg.compose(blocks)
    assert "You are helpful." in result
    assert "What is 2+2?" in result


def test_registry_list_templates():
    reg = PromptRegistry()
    reg.register(PromptTemplate(name="a", template="A"))
    reg.register(PromptTemplate(name="b", template="B"))
    names = reg.list_templates()
    assert sorted(names) == ["a", "b"]


def test_registry_versioned():
    reg = PromptRegistry()
    reg.register(PromptTemplate(name="greet", version="1.0.0", template="Hi {name}"))
    reg.register(
        PromptTemplate(name="greet", version="2.0.0", template="Hello {name}!")
    )
    v1 = reg.get("greet", version="1.0.0")
    v2 = reg.get("greet", version="2.0.0")
    assert v1.template == "Hi {name}"
    assert v2.template == "Hello {name}!"
    latest = reg.get("greet")
    assert latest.version == "2.0.0"


async def test_plugin_setup_registers_category():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="prompt_support",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "prompt:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="prompt_support:PromptSupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("prompt_support")
    assert "prompt" in m._registry
    assert "before_prompt_render" in m.hooks._specs
    assert "after_prompt_render" in m.hooks._specs
