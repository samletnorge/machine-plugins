"""Studio control-plane deploy routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/deploy", tags=["studio-deploy"])


@router.get("/targets")
async def list_targets() -> dict[str, object]:
    return domain_payload("deploy", ["deployer"])
