"""Studio control-plane voice routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/voice", tags=["studio-voice"])


@router.get("/voices")
async def list_voices() -> dict[str, object]:
    return domain_payload("voice", ["voice_provider"])
