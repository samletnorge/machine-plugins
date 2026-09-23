"""Schemas for the tool_support plugin."""

from __future__ import annotations

import inspect
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

    async def execute(self, payload: Any = None, **kwargs: Any) -> Any:
        """Invoke the tool handler.

        Accepts either keyword arguments (the generic operation route) or a
        single positional mapping (the Studio tool tester).
        """
        if payload is not None:
            if isinstance(payload, dict):
                kwargs = {**payload, **kwargs}
            else:
                kwargs.setdefault("input", payload)
        result = self.handler(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


class ToolResult(BaseModel):
    """Result of a tool invocation."""

    tool_name: str
    output: Any = None
    error: str | None = None
    duration_ms: float | None = None
