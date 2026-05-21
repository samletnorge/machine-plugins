"""Recursive character text splitter.

Splits text by trying separators in order: paragraphs -> sentences -> words -> characters.
Each level is attempted when the previous produces chunks still too large.
"""

from __future__ import annotations

from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk

_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class RecursiveChunker(Chunker):
    """Recursive character text splitter.

    Args:
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between consecutive chunks.
        separators: Ordered list of separators to try.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        separators: list[str] | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or list(_DEFAULT_SEPARATORS)

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []

        raw_chunks = self._split(text, self.separators)
        merged = self._merge(raw_chunks)

        return [Chunk(text=t, index=i) for i, t in enumerate(merged) if t.strip()]

    def _split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy."""
        if len(text) <= self.chunk_size:
            return [text]

        sep = ""
        for s in separators:
            if s == "":
                sep = s
                break
            if s in text:
                sep = s
                break

        if sep == "":
            parts = [
                text[i : i + self.chunk_size]
                for i in range(0, len(text), self.chunk_size)
            ]
        else:
            parts = text.split(sep)

        remaining_seps = (
            separators[separators.index(sep) + 1 :] if sep in separators else [""]
        )
        result: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= self.chunk_size:
                result.append(part)
            else:
                result.extend(self._split(part, remaining_seps))

        return result

    def _merge(self, parts: list[str]) -> list[str]:
        """Merge small parts into chunks respecting chunk_size and overlap."""
        merged: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current} {part}".strip() if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    merged.append(current)
                current = part

        if current:
            merged.append(current)

        if self.chunk_overlap <= 0 or len(merged) <= 1:
            return merged

        overlapped: list[str] = [merged[0]]
        for i in range(1, len(merged)):
            prev = merged[i - 1]
            overlap_text = (
                prev[-self.chunk_overlap :] if len(prev) > self.chunk_overlap else prev
            )
            overlapped.append(f"{overlap_text} {merged[i]}".strip())

        return overlapped
