"""Integration tests for Batch 1: all 8 LLM providers."""

import pytest
from unittest.mock import patch

from machine_core import Machine
from machine_core.machine import MachineConfig


async def test_all_llm_providers_discoverable():
    """All 8 LLM provider manifests should be discovered."""
    from machine_core.plugins import builtin_manifests

    manifests = {m.name: m for m in builtin_manifests()}
    expected_providers = [
        "provider-ollama",
        "provider-azure-openai",
        "provider-grok",
        "provider-groq",
        "provider-google-gemini",
        "provider-vertex-gemini",
        "provider-vertex-claude",
        "provider-github-copilot",
    ]
    for name in expected_providers:
        assert name in manifests, f"Missing manifest: {name}"


async def test_machine_starts_with_missing_provider_deps():
    """Machine should start even if provider deps are missing."""
    m = Machine()
    await m.start()
    # At minimum, the 6 category plugins must load
    assert len(m.plugins.loaded_plugins) >= 6
    assert "tool-support" in m.plugins.loaded_plugins
    assert "model-provider-support" in m.plugins.loaded_plugins
    await m.shutdown()


async def test_disabled_provider_not_loaded():
    """Disabled providers should not load."""
    m = Machine(config=MachineConfig(disabled_plugins=["provider-ollama"]))
    await m.start()
    providers = m.list_category("model_provider")
    assert "ollama" not in providers
    await m.shutdown()
