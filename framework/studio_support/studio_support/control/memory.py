"""Studio control-plane memory routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/memory", tags=["studio-memory"])


@router.get("/threads")
async def list_threads() -> dict[str, object]:
    return domain_payload("memory", ["memory"])
