"""Registry and plugin inventory routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from studio_support.ui import render_template

router = APIRouter(tags=["registry"])


@router.get("/registry")
async def registry_page(request: Request):
    return render_template(
        request,
        "registry.html",
        page_title="Registry",
        active_nav="registry",
    )
