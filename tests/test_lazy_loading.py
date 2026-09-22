"""Tests for lazy loading of implementation plugins."""

import json

from machine_core import Machine
from machine_core.machine import MachineConfig
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


async def test_declared_plugin_with_broken_entry_point_is_skipped(tmp_path):
    """A declared plugin whose entry point cannot be imported is skipped."""
    plugin_dir = tmp_path / "plugins" / "broken-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "broken-plugin",
                "version": "0.1.0",
                "capabilities": [],
                "transport": {
                    "type": "in-process",
                    "entry_point": "nonexistent_module:BrokenPlugin",
                },
            }
        )
    )

    machine = Machine(MachineConfig(plugins=["broken-plugin"], data_dir=tmp_path))
    await machine.start()

    assert not machine.plugins.is_loaded("broken-plugin")
    await machine.shutdown()
