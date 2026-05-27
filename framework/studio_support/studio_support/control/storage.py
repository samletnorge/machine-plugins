"""Studio control-plane storage routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/storage", tags=["studio-storage"])


@router.get("/files")
async def list_files() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "storage"}
