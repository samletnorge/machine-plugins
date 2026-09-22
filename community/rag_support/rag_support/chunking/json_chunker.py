"""Split JSON by keys or array items."""

from __future__ import annotations

import json as json_lib
from rag_support.chunking.base import Chunker
from rag_support.models import Chunk


class JSONChunker(Chunker):
    def __init__(self, max_items: int = 5) -> None:
        self.max_items = max_items

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        try:
            data = json_lib.loads(text)
        except (json_lib.JSONDecodeError, ValueError):
            return [Chunk(text=text.strip(), index=0)]
        chunks: list[Chunk] = []
        if isinstance(data, dict):
            for key, value in data.items():
                chunks.append(
                    Chunk(
                        text=json_lib.dumps({key: value}, indent=2),
                        index=len(chunks),
                        metadata={"json_key": key},
                    )
                )
        elif isinstance(data, list):
            for i in range(0, len(data), self.max_items):
                batch = data[i : i + self.max_items]
                chunks.append(
                    Chunk(
                        text=json_lib.dumps(batch, indent=2),
                        index=len(chunks),
                        metadata={"json_range": f"{i}-{i + len(batch)}"},
                    )
                )
        else:
            chunks.append(Chunk(text=str(data), index=0))
        return chunks
