"""Config and project metadata routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from studio_support.ui import render_template

router = APIRouter(tags=["config"])


@router.get("/config")
async def config_page(request: Request):
    env_names = sorted(
        name
        for name in os.environ
        if name.startswith(
            ("LLM_", "EMBEDDING_", "MACHINE_", "GCP_", "AZURE_", "OLLAMA_")
        )
    )
    return render_template(
        request,
        "config.html",
        page_title="Config",
        active_nav="config",
        env_names=env_names,
    )
