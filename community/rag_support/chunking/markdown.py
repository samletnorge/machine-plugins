"""Split text by markdown headers."""

from __future__ import annotations

import re
from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownChunker(Chunker):
    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        sections: list[tuple[str | None, int, str]] = []
        matches = list(_HEADER_RE.finditer(text))
        if not matches:
            return [Chunk(text=text.strip(), index=0)]
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.append((None, 0, preamble))
        for i, m in enumerate(matches):
            level = len(m.group(1))
            header = m.group(2).strip()
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections.append((header, level, content))
        return [
            Chunk(
                text=content,
                index=idx,
                metadata={"header": header, "header_level": level} if header else {},
            )
            for idx, (header, level, content) in enumerate(sections)
            if content
        ]
