"""AST-aware code chunker for Python source files."""

from __future__ import annotations

import ast
from rag_support.chunking.base import Chunker
from rag_support.models import Chunk


class CodeChunker(Chunker):
    def __init__(self, language: str = "python") -> None:
        self.language = language

    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        if not text.strip():
            return []
        if self.language == "python":
            return self._chunk_python(text)
        return self._chunk_fallback(text)

    def _chunk_python(self, text: str) -> list[Chunk]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return self._chunk_fallback(text)
        lines = text.splitlines(keepends=True)
        chunks: list[Chunk] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = node.end_lineno if node.end_lineno else start + 1
                source = "".join(lines[start:end]).rstrip()
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                chunks.append(
                    Chunk(
                        text=source,
                        index=len(chunks),
                        metadata={"name": node.name, "type": kind, "line": node.lineno},
                    )
                )
        if not chunks:
            return [Chunk(text=text.strip(), index=0)]
        return chunks

    def _chunk_fallback(self, text: str) -> list[Chunk]:
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        return [Chunk(text=b, index=i) for i, b in enumerate(blocks)]
