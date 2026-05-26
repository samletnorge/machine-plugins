"""Tests for model_provider_support builtin plugin."""

import pytest
from pydantic import ValidationError as PydanticValidationError
from model_provider_support.schemas import (
    ModelProviderConfig,
    ModelRequest,
    ModelResponse,
)


def test_model_provider_config_valid():
    cfg = ModelProviderConfig(provider="openai", model="gpt-4o", model_type="llm")
    assert cfg.provider == "openai"
    assert cfg.base_url is None


def test_model_provider_config_full():
    cfg = ModelProviderConfig(
        provider="elevenlabs",
        model="eleven_multilingual_v2",
        model_type="tts",
        credentials_ref="infisical:ELEVENLABS_KEY",
        base_url="https://api.elevenlabs.io",
        parameters={"stability": 0.5},
    )
    assert cfg.model_type == "tts"
    assert cfg.parameters["stability"] == 0.5


def test_model_request():
    req = ModelRequest(provider="openai", model="gpt-4o", input="Hello")
    assert req.stream is False
    assert req.parameters == {}


def test_model_response():
    resp = ModelResponse(
        provider="openai",
        model="gpt-4o",
        output="Hi there!",
        usage={"prompt_tokens": 5, "completion_tokens": 3},
        duration_ms=120.5,
    )
    assert resp.output == "Hi there!"
    assert resp.usage["prompt_tokens"] == 5


def test_model_request_requires_provider():
    with pytest.raises(PydanticValidationError):
        ModelRequest(model="gpt-4o", input="hello")


async def test_plugin_setup_registers_category():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="model_provider_support",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "model_provider:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="model_provider_support:ModelProviderSupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("model_provider_support")
    assert "model_provider" in m._registry


async def test_plugin_hookspecs_registered():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="model_provider_support",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "model_provider:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="model_provider_support:ModelProviderSupportPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("model_provider_support")
    assert "before_model_invoke" in m.hooks._specs
    assert "after_model_invoke" in m.hooks._specs
    assert "on_model_error" in m.hooks._specs
