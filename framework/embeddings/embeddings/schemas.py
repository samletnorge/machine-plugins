"""Schemas for the embeddings plugin."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model_ref: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class EmbeddingResult(BaseModel):
    vectors: list[list[float]]
    model_ref: str
    dimensions: int
    usage: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float | None = None
