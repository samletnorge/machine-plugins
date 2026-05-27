"""Studio control-plane RAG routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/rag", tags=["studio-rag"])


@router.get("/pipelines")
async def list_pipelines() -> dict[str, object]:
    return {"items": [], "implemented": False, "domain": "rag"}
