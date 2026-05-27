"""Studio control-plane workspace routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/workspace", tags=["studio-workspace"])


@router.get("/files")
async def list_workspace_files() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "workspace"}
