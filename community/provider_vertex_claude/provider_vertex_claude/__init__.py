"""provider_vertex_claude: Vertex AI Claude LLM provider via pydantic-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class VertexClaudeProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._project = config.get("project")
        self._location = config.get("location", "us-east5")
        self._model = config.get("model", "claude-sonnet-4-20250514")

    async def setup(self, ctx: PluginContext):
        from pydantic_ai import Agent  # ImportError → lazy skip

        from .provider import VertexClaudeLLMProvider

        if not self._project:
            return

        provider = VertexClaudeLLMProvider(
            project=self._project, location=self._location, model=self._model
        )
        ctx.register("model_provider", "vertex-claude", provider)

    async def shutdown(self, **kwargs):
        pass
