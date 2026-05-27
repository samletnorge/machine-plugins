"""Studio control-plane pubsub routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/pubsub", tags=["studio-pubsub"])


@router.get("/events")
async def list_events() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "pubsub"}
