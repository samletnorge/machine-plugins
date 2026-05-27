"""Studio control-plane auth routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["studio-auth"])


@router.get("/keys")
async def list_keys() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "auth"}
