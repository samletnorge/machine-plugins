"""tool_filter_rag: Semantic tool filtering via embeddings + vector store."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class _LazyToolFilterManager:
    """Lazy wrapper that resolves embedding + vectorstore on first use.

    During Machine startup, implementation plugins load in undefined order
    within the same tier.  The RAG filter needs both an embedder AND a
    vector store, but they may not be registered yet when *this* plugin's
    ``setup()`` runs.  By deferring resolution to first call we sidestep
    the ordering problem entirely.
    """

    def __init__(self, machine: Any, config: dict[str, Any] | None = None) -> None:
        self._machine = machine
        self._config = config or {}
        self._inner: Any = None

    def _resolve(self) -> Any | None:
        if self._inner is not None:
            return self._inner

        vector_stores = self._machine.list_category("vector_store")

        embedding_provider_name = self._config.get("embedding_provider")
        if not embedding_provider_name:
            raise ValueError(
                "tool_filter_rag requires plugin config 'embedding_provider'"
            )

        embedder = self._machine.resolve("embedding", embedding_provider_name)
        if embedder is None:
            available = list(self._machine.list_category("embedding").keys())
            raise ValueError(
                "tool_filter_rag embedding provider "
                f"'{embedding_provider_name}' not found. Available: {available}"
            )

        if not vector_stores:
            return None

        vector_store_name = self._config.get("vector_store")
        if vector_store_name:
            store = self._machine.resolve("vector_store", vector_store_name)
            if store is None:
                available = list(vector_stores.keys())
                raise ValueError(
                    "tool_filter_rag vector store "
                    f"'{vector_store_name}' not found. Available: {available}"
                )
        else:
            store = next(iter(vector_stores.values()))

        from .filter import ToolFilterManager

        self._inner = ToolFilterManager(embedder=embedder, store=store)
        return self._inner

    async def index_tools(self, tools: list) -> None:
        mgr = self._resolve()
        if mgr is None:
            from loguru import logger

            logger.debug(
                "tool_filter_rag: cannot index — no embedding provider or vector store available"
            )
            return
        return await mgr.index_tools(tools)

    async def filter(self, prompt: str, top_k: int = 10) -> list:
        mgr = self._resolve()
        if mgr is None:
            return []
        return await mgr.filter(prompt, top_k=top_k)


class ToolFilterRAGPlugin:
    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, **kwargs):
        self._config = kwargs.get("config", {}) or {}

    async def setup(self, ctx: PluginContext):
        # Register a lazy wrapper — actual embedder/store resolution happens
        # on first use, not at startup.
        manager = _LazyToolFilterManager(machine=ctx._machine, config=self._config)
        ctx.register("tool", "__filter_rag__", manager)

    async def shutdown(self, **kwargs):
        pass
