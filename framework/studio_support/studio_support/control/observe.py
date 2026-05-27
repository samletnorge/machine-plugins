"""Studio control-plane observability routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/observe", tags=["studio-observe"])


@router.get("/traces")
async def list_traces() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "observe"}
