"""CLI-support plugin.

Provides the `machine` CLI command for project scaffolding,
development, building, deployment, and studio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

__all__ = ["CLISupportPlugin"]


class CLISupportPlugin:
    """Plugin that provides the machine CLI."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: "PluginContext"):
        pass

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
