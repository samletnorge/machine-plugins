"""provider_vertex_gemini: Vertex AI Gemini LLM provider via pydantic-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class VertexGeminiProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._project = config.get("project")
        self._location = config.get("location", "us-central1")
        self._model = config.get("model", "gemini-2.0-flash")

    async def setup(self, ctx: PluginContext):
        from pydantic_ai import Agent  # ImportError → lazy skip

        from .provider import VertexGeminiLLMProvider

        if not self._project:
            return

        provider = VertexGeminiLLMProvider(
            project=self._project, location=self._location, model=self._model
        )
        ctx.register("model_provider", "vertex-gemini", provider)

    async def shutdown(self, **kwargs):
        pass
