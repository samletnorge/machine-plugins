"""Studio control-plane RAG routes."""

from __future__ import annotations

from fastapi import APIRouter

from ._common import domain_payload

router = APIRouter(prefix="/api/rag", tags=["studio-rag"])


@router.get("/pipelines")
async def list_pipelines() -> dict[str, object]:
    return domain_payload(
        "rag", ["rag_pipeline", "chunker", "reranker", "metadata_extractor"]
    )
