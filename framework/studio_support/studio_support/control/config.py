"""Studio control-plane config routes."""

from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from studio_support.ui import machine_snapshot

router = APIRouter(prefix="/api/config", tags=["studio-config"])


@router.get("")
async def get_config() -> dict[str, object]:
    snapshot = machine_snapshot()
    env_names = sorted(
        name
        for name in os.environ
        if name.startswith(
            ("LLM_", "EMBEDDING_", "MACHINE_", "GCP_", "AZURE_", "OLLAMA_")
        )
    )
    return {
        "project_config": snapshot["project_config"],
        "env_names": env_names,
        "project_root": snapshot["project_root"],
        "entry": snapshot["entry"],
        "environment": snapshot["environment"],
        "plugins_declared": snapshot["plugins_declared"],
        "plugin_configs": snapshot["plugin_configs"],
    }


@router.get("/env", response_class=HTMLResponse)
async def get_env_names_fragment() -> str:
    payload = await get_config()
    env_names = payload["env_names"]
    if not env_names:
        return (
            '<li class="muted">No Studio-relevant environment variables detected.</li>'
        )
    return "".join(f"<li>{name}</li>" for name in env_names)
