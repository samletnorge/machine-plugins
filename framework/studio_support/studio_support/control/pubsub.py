"""Studio control-plane pub/sub routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/pubsub", tags=["studio-pubsub"])


@router.get("/events")
async def list_events() -> dict[str, object]:
    return domain_payload("pubsub", ["pubsub"])
