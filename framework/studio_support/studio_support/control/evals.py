"""Studio control-plane eval routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/evals", tags=["studio-evals"])


@router.get("/runs")
async def list_runs() -> dict[str, object]:
    return domain_payload("evals", ["scorer", "dataset"])
