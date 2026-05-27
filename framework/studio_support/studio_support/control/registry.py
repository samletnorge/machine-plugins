"""Studio control-plane registry routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from studio_support.ui import machine_snapshot

router = APIRouter(prefix="/api/registry", tags=["studio-registry"])


@router.get("/plugins")
async def list_plugins() -> list[dict[str, object]]:
    return machine_snapshot()["manifests"]


@router.get("/plugins/{name}")
async def get_plugin(name: str) -> dict[str, object]:
    for manifest in machine_snapshot()["manifests"]:
        if manifest["name"] == name:
            return manifest
    raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")


@router.get("/search", response_class=HTMLResponse)
async def search_plugins(q: str = "") -> str:
    query = q.strip().lower()
    manifests = machine_snapshot()["manifests"]
    matches = [manifest for manifest in manifests if query in manifest["name"].lower()]
    if not matches:
        return '<p class="muted">No matching plugins found.</p>'
    return "".join(
        f'<article class="list-card"><div class="list-card-main"><strong>{manifest["name"]}</strong><p>{manifest.get("description") or "No manifest description available."}</p></div></article>'
        for manifest in matches
    )
