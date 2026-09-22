"""Shared fixtures and helpers for the machine-plugins test suite.

Plugins no longer auto-load as "builtins"; the runtime loads only the plugins a
project declares. Tests therefore discover the manifests that live in this
workspace and load them explicitly through the plugin manager.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from machine_core import Machine
from machine_core.plugin.manifest import PluginManifest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def discover_manifests() -> list[PluginManifest]:
    """Return the manifests for every framework, community, and satellite plugin."""
    paths: list[Path] = []
    for group in ("framework", "community"):
        paths.extend(sorted((WORKSPACE_ROOT / group).glob("*/manifest.json")))
    paths.extend(sorted(WORKSPACE_ROOT.parent.glob("machine-plugin-*/manifest.json")))
    return [PluginManifest.from_file(path) for path in paths]


async def load_workspace_plugins(machine: Machine) -> Machine:
    """Load every workspace plugin into ``machine`` (category definers first).

    Plugins whose dependencies are unavailable are skipped, matching the
    runtime's lazy-loading behaviour.
    """
    manifests = discover_manifests()
    manifests.sort(key=lambda m: 0 if "categories:define" in m.capabilities else 1)
    for manifest in manifests:
        machine.plugins.register_manifest(manifest)
        try:
            await machine.plugins.load(manifest.name)
        except Exception:  # noqa: BLE001 - optional plugin dependency missing
            continue
    return machine


@pytest.fixture
async def machine_with_all_plugins():
    """A Machine with every workspace plugin that can load."""
    machine = Machine()
    await load_workspace_plugins(machine)
    yield machine
    await machine.shutdown()
