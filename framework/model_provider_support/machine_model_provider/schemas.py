"""Schemas for the model-provider-support plugin."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class ModelProviderConfig(BaseModel):
    provider: str
    model: str
    model_type: str
    credentials_ref: str | None = None
    base_url: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ModelRequest(BaseModel):
    provider: str
    model: str
    input: Any
    parameters: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class ModelResponse(BaseModel):
    provider: str
    model: str
    output: Any
    usage: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float | None = None
    tool_calls: list[dict[str, Any]] | None = None
