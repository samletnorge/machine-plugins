"""agent-brreg-expert: Norwegian companies expert with RAG + live Brreg API tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class BrregExpertPlugin:
    """Plugin that registers a Brreg RAG pipeline and expert agent."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, **kwargs: Any) -> None:
        self._config = kwargs.get("config", {})

    async def setup(self, ctx: "PluginContext") -> None:
        # TODO: implement in Task 6
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass
