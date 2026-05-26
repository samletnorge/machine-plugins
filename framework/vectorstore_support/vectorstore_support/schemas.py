"""Schemas for the vectorstore_support plugin."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VectorStoreConfig(BaseModel):
    name: str
    dimensions: int
    distance_metric: str = "cosine"  # cosine | l2 | dot
    parameters: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query_vector: list[float]
    top_k: int = 10
    filter: dict[str, Any] | None = None
    table: str | None = None


class SearchResult(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    text: str | None = None


class UpsertRequest(BaseModel):
    id: str
    vector: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)
    text: str | None = None
    table: str | None = None
