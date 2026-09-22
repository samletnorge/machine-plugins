"""Studio control-plane workspace routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/workspace", tags=["studio-workspace"])


@router.get("/files")
async def list_files() -> dict[str, object]:
    return domain_payload("workspace", ["sandbox", "filesystem"])
