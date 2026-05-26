"""Schemas for the tool_support plugin."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Schema for a registered tool."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    return_type: dict[str, Any] | None = None
    handler: Callable[..., Any] = Field(exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of a tool invocation."""

    tool_name: str
    output: Any = None
    error: str | None = None
    duration_ms: float | None = None
