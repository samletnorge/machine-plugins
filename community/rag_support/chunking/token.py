"""Token-count based chunker."""

from __future__ import annotations

from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk


class TokenChunker(Chunker):
    def __init__(self, max_tokens: int = 256, token_overlap: int = 0) -> None:
        self.max_tokens = max_tokens
        self.token_overlap = token_overlap

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        tokens = text.split()
        chunks: list[Chunk] = []
        step = max(1, self.max_tokens - self.token_overlap)
        for i in range(0, len(tokens), step):
            batch = tokens[i : i + self.max_tokens]
            chunks.append(Chunk(text=" ".join(batch), index=len(chunks)))
        return chunks
