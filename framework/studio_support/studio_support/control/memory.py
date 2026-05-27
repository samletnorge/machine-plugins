"""Studio control-plane memory routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/memory", tags=["studio-memory"])


@router.get("/threads")
async def list_threads() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "memory"}
