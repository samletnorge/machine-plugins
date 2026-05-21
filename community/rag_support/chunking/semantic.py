"""Semantic chunker -- uses embeddings to find natural break points."""

from __future__ import annotations

import asyncio
import re
from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class SemanticChunker(Chunker):
    def __init__(
        self, embedder: object | None = None, similarity_threshold: float = 0.5
    ) -> None:
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        if self.embedder is None:
            return [Chunk(text=text.strip(), index=0)]
        sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
        if len(sentences) <= 1:
            return [Chunk(text=text.strip(), index=0)]

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                embeddings = pool.submit(
                    asyncio.run, self.embedder.embed_batch(sentences)
                ).result()
        else:
            embeddings = asyncio.run(self.embedder.embed_batch(sentences))

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
