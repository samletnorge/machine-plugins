"""Token-count based chunker.

Splits text using a real BPE tokenizer (``tiktoken``) so that ``max_tokens``
reflects actual model tokens rather than whitespace-separated words. The
tokenizer is imported lazily and the chunker falls back to whitespace
tokenization when ``tiktoken`` (or the requested encoding) is unavailable, so
the plugin keeps working in minimal environments. All produced ``Chunk``
objects keep the standard semantics (``text`` plus a sequential ``index``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from rag_support.chunking.base import Chunker
from rag_support.models import Chunk

_DEFAULT_ENCODING = "cl100k_base"


@lru_cache(maxsize=8)
def _load_encoding(encoding_name: str) -> Any | None:
    """Return a cached tiktoken encoding, or ``None`` if unavailable."""
    try:
        import tiktoken
    except Exception:  # noqa: BLE001 - optional dependency
        return None
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception:  # noqa: BLE001 - network/unknown encoding
        return None


class TokenChunker(Chunker):
    def __init__(
        self,
        max_tokens: int = 256,
        token_overlap: int = 0,
        encoding_name: str = _DEFAULT_ENCODING,
    ) -> None:
        self.max_tokens = max_tokens
        self.token_overlap = token_overlap
        self.encoding_name = encoding_name

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []

        encoding = _load_encoding(self.encoding_name)
        if encoding is not None:
            tokens = encoding.encode(text)
            decode = encoding.decode
        else:
            tokens = text.split()
            decode = " ".join

        chunks: list[Chunk] = []
        step = max(1, self.max_tokens - self.token_overlap)
        for i in range(0, len(tokens), step):
            batch = tokens[i : i + self.max_tokens]
            chunks.append(Chunk(text=decode(batch), index=len(chunks)))
        return chunks
