"""Studio control-plane deploy routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/deploy", tags=["studio-deploy"])


@router.get("/targets")
async def list_targets() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "deploy"}
