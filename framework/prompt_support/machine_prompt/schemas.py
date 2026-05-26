"""Schemas for the prompt_support plugin."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class PromptVariable(BaseModel):
    name: str
    description: str | None = None
    type: str = "string"
    required: bool = True
    default: Any = None


class PromptTemplate(BaseModel):
    name: str
    version: str = "1.0.0"
    template: str
    variables: list[PromptVariable] = Field(default_factory=list)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptBlock(BaseModel):
    role: str = "system"
    content: str
    name: str | None = None


class RenderedPrompt(BaseModel):
    text: str
    template_name: str
    template_version: str
    variables_used: dict[str, Any]
