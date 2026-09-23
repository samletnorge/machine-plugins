"""Studio control-plane overview route (JSON snapshot for the SPA)."""

from __future__ import annotations

from fastapi import APIRouter

from studio_support.ui import machine_snapshot

router = APIRouter(prefix="/api", tags=["studio-overview"])


@router.get("/overview")
async def get_overview() -> dict[str, object]:
    """Return the full machine/context snapshot used by the Studio dashboard."""
    return machine_snapshot()
