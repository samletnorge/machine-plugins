"""Studio control-plane voice routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/voice", tags=["studio-voice"])


@router.get("/voices")
async def list_voices() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "voice"}
