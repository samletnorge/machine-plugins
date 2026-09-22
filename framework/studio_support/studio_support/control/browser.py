"""Studio control-plane browser routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/browser", tags=["studio-browser"])


@router.get("/sessions")
async def list_sessions() -> dict[str, object]:
    return domain_payload("browser", ["browser"])
