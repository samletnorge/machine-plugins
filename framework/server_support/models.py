"""Shared request/response models for the server."""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class AgentRunRequest(BaseModel):
    """Request to run an agent."""

    prompt: str = Field(
        ..., min_length=1, description="The prompt to send to the agent"
    )
    thread_id: Optional[str] = Field(
        None, description="Optional thread ID for conversation continuity"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class AgentGenerateRequest(BaseModel):
    """Request for structured agent output."""

    prompt: str = Field(..., min_length=1)
    output_schema: dict[str, Any] = Field(
        ..., description="JSON Schema for the expected output"
    )
    thread_id: Optional[str] = None


class AgentRunResponse(BaseModel):
    """Response from running an agent."""

    output: str
    usage: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)


class AgentInfoResponse(BaseModel):
    """Metadata about a registered agent."""

    name: str
    description: str
    model: str
    tools: list[str] = Field(default_factory=list)


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""

    input: dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    """Response from executing a tool."""

    result: Any
    tool_name: str


class ToolInfoResponse(BaseModel):
    """Metadata about a registered tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class WorkflowStartRequest(BaseModel):
    """Request to start a workflow."""

    input: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunResponse(BaseModel):
    """Response representing a workflow run."""

    run_id: str
    status: str
    result: Any = None
    created_at: str
    updated_at: str


class WorkflowResumeRequest(BaseModel):
    """Request to resume a suspended workflow."""

    data: dict[str, Any] = Field(default_factory=dict)


class WorkflowInfoResponse(BaseModel):
    """Metadata about a registered workflow."""

    name: str
    description: str


class ThreadCreateRequest(BaseModel):
    """Request to create a memory thread."""

    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadResponse(BaseModel):
    """Response representing a thread."""

    id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class MessageCreateRequest(BaseModel):
    """Request to add a message to a thread."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., min_length=1)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant", "system"):
            raise ValueError(
                f"Invalid role '{v}'. Must be 'user', 'assistant', or 'system'."
            )
        return v


class MessageResponse(BaseModel):
    """Response representing a message."""

    id: str
    role: str
    content: str
    created_at: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    status_code: int
