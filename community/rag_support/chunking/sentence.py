"""Sentence-boundary chunker."""

from __future__ import annotations

import re
from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class SentenceChunker(Chunker):
    def __init__(self, max_sentences: int = 5) -> None:
        self.max_sentences = max_sentences

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
        chunks: list[Chunk] = []
        for i in range(0, len(sentences), self.max_sentences):
            batch = sentences[i : i + self.max_sentences]
            chunks.append(Chunk(text=" ".join(batch), index=len(chunks)))
        return chunks
