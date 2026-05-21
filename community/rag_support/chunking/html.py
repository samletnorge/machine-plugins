"""Split HTML by structural elements."""

from __future__ import annotations

from html.parser import HTMLParser
from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk

_BLOCK_TAGS = {
    "div",
    "section",
    "article",
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "tr",
    "blockquote",
}


class HTMLChunker(Chunker):
    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        parts: list[str] = []
        current: list[str] = []

        class _Parser(HTMLParser):
            def handle_starttag(self, tag: str, attrs: list) -> None:
                if tag in _BLOCK_TAGS and current:
                    joined = " ".join(current).strip()
                    if joined:
                        parts.append(joined)
                    current.clear()

            def handle_data(self, data: str) -> None:
                stripped = data.strip()
                if stripped:
                    current.append(stripped)

            def handle_endtag(self, tag: str) -> None:
                if tag in _BLOCK_TAGS and current:
                    joined = " ".join(current).strip()
                    if joined:
                        parts.append(joined)
                    current.clear()

        parser = _Parser()
        parser.feed(text)
        if current:
            joined = " ".join(current).strip()
            if joined:
                parts.append(joined)
        return [Chunk(text=p, index=i) for i, p in enumerate(parts) if p]
