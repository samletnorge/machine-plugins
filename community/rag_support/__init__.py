"""RAG support plugin.

Defines chunker, reranker, metadata_extractor, and rag_pipeline categories
and registers all built-in implementations.

Standalone chunkers (recursive, sentence, token, etc.) are always registered.
LLM/embedder-dependent components (semantic chunker, rerankers, extractors) are
only registered when their provider is configured via plugin config.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

from .models import Chunk, RankedResult, DocumentMetadata, IngestDocument

__all__ = [
    "Chunk",
    "RankedResult",
    "DocumentMetadata",
    "IngestDocument",
    "RagSupportPlugin",
]


class _LazyLLMAdapter:
    """Defers provider resolution until first generate() call.

    This avoids load-order issues where rag_support (a category definer)
    loads before model providers are registered.
    """

    def __init__(self, machine: Any, provider_name: str, model: str | None = None):
        self._machine = machine
        self._provider_name = provider_name
        self._model = model
        self._adapter: Any = None

    def _resolve(self) -> Any:
        if self._adapter is None:
            from .adapters import LLMAdapter

            provider = self._machine.resolve("model_provider", self._provider_name)
            if provider is None:
                raise ValueError(
                    f"Model provider '{self._provider_name}' not found. "
                    f"Available: {list(self._machine.list_category('model_provider').keys())}"
                )
            self._adapter = LLMAdapter(provider, model=self._model)
        return self._adapter

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self._resolve().generate(prompt, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)


class RagSupportPlugin:
    """Plugin that provides RAG pipeline components.

    Registers categories (chunker, reranker, metadata_extractor, rag_pipeline)
    and all built-in implementations. LLM/embedder-dependent components are
    only wired when config specifies which provider/model to use.
    """

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, **kwargs: Any) -> None:
        """Store config for use in setup()."""
        self._config = kwargs.get("config", {})

    async def setup(self, ctx: "PluginContext") -> None:
        """Register RAG categories and all built-in implementations."""
        from .chunking.recursive import RecursiveChunker
        from .chunking.sentence import SentenceChunker
        from .chunking.token import TokenChunker
        from .chunking.markdown import MarkdownChunker
        from .chunking.html import HTMLChunker
        from .chunking.json_chunker import JSONChunker
        from .chunking.code import CodeChunker

        # Define categories
        ctx.register_category(
            "chunker",
            operations={
                "chunk": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        ctx.register_category(
            "reranker",
            operations={
                "rerank": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        ctx.register_category(
            "metadata_extractor",
            operations={
                "extract": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        ctx.register_category(
            "rag_pipeline",
            operations={
                "ingest": {"method": "POST", "on": "item"},
                "retrieve": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )

        # --- Always-available chunkers (no deps) ---
        ctx.register("chunker", "recursive", RecursiveChunker())
        ctx.register("chunker", "sentence", SentenceChunker())
        ctx.register("chunker", "token", TokenChunker())
        ctx.register("chunker", "markdown", MarkdownChunker())
        ctx.register("chunker", "html", HTMLChunker())
        ctx.register("chunker", "json", JSONChunker())
        ctx.register("chunker", "code", CodeChunker())

        # --- Embedder-dependent: Semantic Chunker ---
        self._register_semantic_chunker(ctx)

        # --- LLM-dependent: Reranker + Extractors ---
        self._register_llm_components(ctx)

        # --- Cross-encoder reranker ---
        self._register_cross_encoder(ctx)

    def _register_semantic_chunker(self, ctx: "PluginContext") -> None:
        """Register semantic chunker if embedding provider is configured."""
        from .chunking.semantic import SemanticChunker

        cfg = self._config.get("semantic_chunker")
        if not cfg or not isinstance(cfg, dict):
            logger.debug(
                "rag_support: semantic chunker not registered "
                "(no semantic_chunker configured)"
            )
            return

        provider_name = cfg.get("provider")
        if not provider_name:
            return

        provider = ctx._machine.resolve("embedding", provider_name)
        if provider is None:
            logger.warning(
                "rag_support: semantic chunker not registered — "
                "embedding provider '{}' not found in registry",
                provider_name,
            )
            return

        from .adapters import EmbedderAdapter

        model = cfg.get("model")
        threshold = cfg.get("similarity_threshold", 0.5)
        embedder = EmbedderAdapter(provider, model=model)
        ctx.register(
            "chunker",
            "semantic",
            SemanticChunker(embedder=embedder, similarity_threshold=threshold),
        )
        logger.info(
            "rag_support: registered semantic chunker (provider={})", provider_name
        )

    def _register_llm_components(self, ctx: "PluginContext") -> None:
        """Register LLM-dependent reranker and extractors if LLM provider is configured.

        Uses lazy LLM resolution to avoid load-order dependency on model providers.
        """
        from .rerankers.llm import LLMReranker
        from .extractors.title import TitleExtractor
        from .extractors.summary import SummaryExtractor
        from .extractors.keywords import KeywordsExtractor
        from .extractors.questions import QuestionsExtractor

        # reranker_llm and extractor_llm can be separate configs
        # but often the same — check both
        reranker_cfg = self._config.get("reranker_llm")
        extractor_cfg = self._config.get("extractor_llm")

        if reranker_cfg and isinstance(reranker_cfg, dict):
            provider_name = reranker_cfg.get("provider")
            if provider_name:
                llm = _LazyLLMAdapter(
                    ctx._machine, provider_name, reranker_cfg.get("model")
                )
                ctx.register("reranker", "llm", LLMReranker(llm=llm))
                logger.info(
                    "rag_support: registered LLM reranker (provider={}, lazy)",
                    provider_name,
                )

        if extractor_cfg and isinstance(extractor_cfg, dict):
            provider_name = extractor_cfg.get("provider")
            if provider_name:
                llm = _LazyLLMAdapter(
                    ctx._machine, provider_name, extractor_cfg.get("model")
                )
                ctx.register("metadata_extractor", "title", TitleExtractor(llm=llm))
                ctx.register("metadata_extractor", "summary", SummaryExtractor(llm=llm))
                ctx.register(
                    "metadata_extractor", "keywords", KeywordsExtractor(llm=llm)
                )
                ctx.register(
                    "metadata_extractor", "questions", QuestionsExtractor(llm=llm)
                )
                logger.info(
                    "rag_support: registered 4 extractors (provider={}, lazy)",
                    provider_name,
                )

        if not reranker_cfg and not extractor_cfg:
            logger.debug(
                "rag_support: LLM components not registered "
                "(no reranker_llm or extractor_llm configured)"
            )

    def _register_cross_encoder(self, ctx: "PluginContext") -> None:
        """Register cross-encoder reranker if model is configured."""
        from .rerankers.cross_encoder import CrossEncoderReranker

        cfg = self._config.get("reranker_cross_encoder")
        if not cfg or not isinstance(cfg, dict):
            logger.debug(
                "rag_support: cross-encoder reranker not registered "
                "(no reranker_cross_encoder configured)"
            )
            return

        model_name = cfg.get("model")
        if not model_name:
            return

        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(model_name)
            ctx.register("reranker", "cross_encoder", CrossEncoderReranker(model=model))
            logger.info(
                "rag_support: registered cross-encoder reranker (model={})", model_name
            )
        except ImportError:
            logger.warning(
                "rag_support: cross-encoder reranker not registered — "
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

    async def shutdown(self, **kwargs: Any) -> None:
        """No-op — no resources to release."""
        pass
