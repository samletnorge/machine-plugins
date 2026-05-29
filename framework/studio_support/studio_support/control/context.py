"""Studio control-plane context routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from studio_support.dependencies import (
    get_studio_state,
    list_environments,
    list_projects,
    list_tenants,
    normalize_context_payload,
    switch_context,
)

router = APIRouter(prefix="/api", tags=["studio-control"])


class ContextSwitchRequest(BaseModel):
    tenant_slug: str
    project_slug: str
    environment_name: str


@router.get("/context")
async def get_context() -> dict[str, dict[str, object]]:
    return normalize_context_payload(get_studio_state())


@router.get("/tenants")
async def get_tenants() -> list[dict[str, object]]:
    return list_tenants()


@router.get("/tenants/{tenant_slug}/projects")
async def get_projects(tenant_slug: str) -> list[dict[str, object]]:
    return list_projects(tenant_slug)


@router.get("/projects/{project_slug}/environments")
async def get_environments(project_slug: str) -> list[dict[str, object]]:
    return list_environments(project_slug)


@router.put("/context")
async def put_context(
    payload: ContextSwitchRequest,
) -> dict[str, dict[str, object]]:
    return switch_context(
        tenant_slug=payload.tenant_slug,
        project_slug=payload.project_slug,
        environment_name=payload.environment_name,
    )
