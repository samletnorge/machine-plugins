"""Studio control-plane auth routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/auth", tags=["studio-auth"])


@router.get("/keys")
async def list_keys() -> dict[str, object]:
    return domain_payload("auth", ["auth_provider"])
