"""tool-openapi: Generate tools from OpenAPI specs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class ToolOpenAPIPlugin:
    """In-process plugin class for tool-openapi."""

    async def initialize(self, **kwargs):
        """Called by transport on load."""
        pass

    async def setup(self, ctx: PluginContext):
        """Register OpenAPI generator utilities into the tool category."""
        from .generator import generate_tools, simplify_schema

        ctx.register(
            "tool",
            "__openapi_generator__",
            {
                "generate_tools": generate_tools,
                "simplify_schema": simplify_schema,
            },
        )

    async def shutdown(self, **kwargs):
        """Called on unload."""
        pass
