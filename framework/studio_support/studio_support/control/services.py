"""Studio control-plane service routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["studio-control"])


@router.get("/health")
async def studio_health() -> dict[str, str]:
    return {"status": "ok", "service": "studio-control"}


@router.get("/services/status")
async def service_status() -> dict[str, object]:
    return {
        "studio_mount": "/_studio",
        "runtime_api": "/api/*",
        "health_endpoint": "/health",
        "docs_endpoint": "/docs",
        "notes": [
            "Studio is mounted from the CLI capability and attached to one active project runtime.",
            "Runtime API docs remain at the server root while control-plane pages live under /_studio.",
            "Log streaming, deploy control, and service actions are reserved for the next control-plane pass.",
        ],
    }


@router.post("/services/{action}")
async def service_action(action: str) -> dict[str, object]:
    if action not in {"start", "stop", "restart"}:
        raise HTTPException(status_code=404, detail=f"Unknown action '{action}'")
    return {"status": "accepted", "action": action, "implemented": False}
