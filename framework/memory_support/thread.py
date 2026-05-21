"""Thread-based conversation models.

A Thread is a conversation container holding an ordered sequence of Messages.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional, Any

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """Roles a message sender can have."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in a conversation thread."""

    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": False}


class Thread(BaseModel):
    """A conversation thread — container for messages."""

    id: str = Field(default_factory=lambda: f"thread_{uuid.uuid4().hex[:12]}")
    title: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": False}


class Fact(BaseModel):
    """A single extracted fact or observation."""

    id: str = Field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:12]}")
    content: str
    confidence: float = 1.0
    source_message_id: str
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    model_config = {"frozen": False}
