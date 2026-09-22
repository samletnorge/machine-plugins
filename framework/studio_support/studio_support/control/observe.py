"""Studio control-plane observability routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/observe", tags=["studio-observe"])


@router.get("/traces")
async def list_traces() -> dict[str, object]:
    return domain_payload("observe", ["observability_exporter"])
