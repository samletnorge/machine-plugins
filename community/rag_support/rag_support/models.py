"""Core data models for the RAG pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A chunk of text produced by a chunker."""

    text: str
    index: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    start_char: int | None = None
    end_char: int | None = None


class DocumentMetadata(BaseModel):
    """Extracted metadata for a document."""

    title: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    source: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RankedResult(BaseModel):
    """A result after reranking."""

    id: str
    text: str
    original_score: float
    rerank_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestDocument(BaseModel):
    """A document to be ingested into the RAG pipeline."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
