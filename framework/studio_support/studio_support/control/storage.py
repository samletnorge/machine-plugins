"""Studio control-plane storage routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/storage", tags=["studio-storage"])


@router.get("/files")
async def list_files() -> dict[str, object]:
    return domain_payload("storage", ["storage-backend"])
