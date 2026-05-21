"""Schemas for the structured-output plugin."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class GenerateObjectRequest(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    model_ref: str
    output_schema: type[BaseModel] = Field(exclude=True)
    prompt: str
    system_instruction: str | None = None
    max_retries: int = 3
    parameters: dict[str, Any] = Field(default_factory=dict)


class GenerateObjectResponse(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    object: Any
    raw_output: str
    retries: int = 0
    model_ref: str
    duration_ms: float | None = None
