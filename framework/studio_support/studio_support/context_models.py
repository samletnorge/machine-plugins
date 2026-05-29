from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AttachmentStatus = Literal["attached", "attaching", "failed", "detached"]


@dataclass(slots=True)
class StudioTenant:
    id: str
    slug: str
    name: str


@dataclass(slots=True)
class StudioProject:
    id: str
    tenant_id: str
    slug: str
    name: str
    entry: str
    capability_summary: dict[str, int]


@dataclass(slots=True)
class StudioEnvironment:
    id: str
    project_id: str
    name: str
    connection_kind: str
    connection_ref: str
    status: str


@dataclass(slots=True)
class StudioContext:
    tenant_id: str
    project_id: str
    environment_id: str


@dataclass(slots=True)
class RuntimeAttachment:
    context: StudioContext
    status: AttachmentStatus
    machine_name: str | None
    attached_at: str | None
    error: str | None
