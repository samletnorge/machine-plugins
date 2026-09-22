"""Semantic chunker -- uses embeddings to find natural break points."""

from __future__ import annotations

import asyncio
import re
from rag_support.chunking.base import Chunker
from rag_support.models import Chunk

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class SemanticChunker(Chunker):
    def __init__(
        self, embedder: object | None = None, similarity_threshold: float = 0.5
    ) -> None:
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

    async def chunk_async(self, text: str, **kwargs: object) -> list[Chunk]:
        """Chunk text from within a running event loop.

        This is the preferred entry point when an event loop is already
        running: the embedding call is awaited on the caller's loop, so
        provider clients bound to that loop keep working.
        """
        if not text.strip():
            return []
        if self.embedder is None:
            return [Chunk(text=text.strip(), index=0)]

        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [Chunk(text=text.strip(), index=0)]

        embeddings = await self.embedder.embed_batch(sentences)
        return self._build_chunks(sentences, embeddings)

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        """Synchronously chunk text.

        When no event loop is running this uses ``asyncio.run`` directly. When
        a loop *is* running, ``asyncio.run`` cannot be used, so the embedding
        coroutine is created and awaited inside a fresh loop in a worker
        thread. The coroutine is never created on one loop and executed on
        another. Prefer :meth:`chunk_async` from async code.
        """
        if not text.strip():
            return []
        if self.embedder is None:
            return [Chunk(text=text.strip(), index=0)]

        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [Chunk(text=text.strip(), index=0)]

        embeddings = self._run_embed_batch(sentences)
        return self._build_chunks(sentences, embeddings)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]

    def _run_embed_batch(self, sentences: list[str]) -> list[list[float]]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: safe to drive the coroutine with asyncio.run.
            return asyncio.run(self.embedder.embed_batch(sentences))

        import concurrent.futures

        def _embed_in_new_loop() -> list[list[float]]:
            # Build *and* run the coroutine inside the worker thread so the
            # coroutine is never shared across event loops.
            return asyncio.run(self.embedder.embed_batch(sentences))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_embed_in_new_loop).result()

    def _build_chunks(
        self, sentences: list[str], embeddings: list[list[float]]
    ) -> list[Chunk]:
        breaks = [0]
        for i in range(1, len(embeddings)):
            sim = self._cosine_sim(embeddings[i - 1], embeddings[i])
            if sim < self.similarity_threshold:
                breaks.append(i)
        breaks.append(len(sentences))

        chunks: list[Chunk] = []
        for i in range(len(breaks) - 1):
            group = sentences[breaks[i] : breaks[i + 1]]
            chunks.append(Chunk(text=" ".join(group), index=len(chunks)))
        return chunks

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
