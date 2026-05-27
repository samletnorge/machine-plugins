"""Studio control-plane evals routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/evals", tags=["studio-evals"])


@router.get("/runs")
async def list_runs() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "evals"}
