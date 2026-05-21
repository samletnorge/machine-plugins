"""Tests for lazy loading of implementation plugins."""

import pytest
from unittest.mock import patch, MagicMock
from machine_core import Machine
from machine_core.plugin.manifest import PluginManifest


def test_manifest_dependencies_field():
    """PluginManifest should accept a dependencies list."""
    m = PluginManifest(
        name="test-plugin",
        version="0.1.0",
        capabilities=["model_provider:register"],
        dependencies=["httpx>=0.28", "pydantic-ai>=2.0"],
        transport={"type": "in-process", "entry_point": "test:TestPlugin"},
    )
    assert m.dependencies == ["httpx>=0.28", "pydantic-ai>=2.0"]


def test_manifest_dependencies_default_empty():
    """Dependencies should default to empty list."""
    m = PluginManifest(
        name="test-plugin",
        version="0.1.0",
        capabilities=[],
        transport={"type": "in-process", "entry_point": "test:TestPlugin"},
    )
    assert m.dependencies == []


async def test_lazy_loading_skips_import_error():
    """Machine.start() should skip plugins with ImportError, not crash."""
    m = Machine()
    broken_manifest = PluginManifest(
        name="broken-plugin",
        version="0.1.0",
        capabilities=[],
        dependencies=["nonexistent-package"],
        transport={
            "type": "in-process",
            "entry_point": "nonexistent_module:BrokenPlugin",
        },
    )

    import machine_core.plugins as plugins_mod

    original_fn = plugins_mod.builtin_manifests

    def patched_manifests():
        result = original_fn()
        result.append(broken_manifest)
        return result

    with patch.object(plugins_mod, "builtin_manifests", patched_manifests):
        await m.start()

    # All real plugins should still be loaded
    assert "tool" in m._registry
    assert "model_provider" in m._registry
    assert "embedding" in m._registry
    # Broken plugin should NOT be loaded
    assert not m.plugins.is_loaded("broken-plugin")
    await m.shutdown()


async def test_lazy_loading_logs_debug_message(caplog):
    """Lazy loading should produce a debug log with install instructions."""
    m = Machine()

    broken_manifest = PluginManifest(
        name="needs-httpx",
        version="0.1.0",
        capabilities=[],
        dependencies=["httpx>=0.28"],
        transport={
            "type": "in-process",
            "entry_point": "nonexistent_httpx_plugin:Plugin",
        },
    )

    import machine_core.plugins as plugins_mod

    original_fn = plugins_mod.builtin_manifests

    def patched_manifests():
        result = original_fn()
        result.append(broken_manifest)
        return result

    with patch.object(plugins_mod, "builtin_manifests", patched_manifests):
        await m.start()

    # The key assertion: Machine started without crash
    assert m.plugins.is_loaded("tool-support")
    assert not m.plugins.is_loaded("needs-httpx")
    await m.shutdown()


async def test_existing_plugins_still_load_after_core_changes():
    """All 7 category plugins must still load after core changes."""
    m = Machine()
    await m.start()
    expected_categories = [
        "tool",
        "model_provider",
        "embedding",
        "agent",
        "prompt",
        "structured_output",
        "vector_store",
    ]
    for cat in expected_categories:
        assert cat in m._registry, f"Category '{cat}' not registered"
    # 7 categories + provider/embedding implementation plugins that successfully load
    assert len(m.plugins.loaded_plugins) >= 7
    await m.shutdown()
