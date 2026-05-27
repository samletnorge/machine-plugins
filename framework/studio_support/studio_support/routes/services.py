"""Service, API surface, and docs routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from studio_support.ui import render_template

router = APIRouter(tags=["services"])


@router.get("/services")
async def services_page(request: Request):
    return render_template(
        request,
        "services.html",
        page_title="Services",
        active_nav="services",
    )


@router.get("/api")
async def api_page(request: Request):
    return render_template(
        request,
        "api.html",
        page_title="API Surface",
        active_nav="api",
    )


@router.get("/docs")
async def docs_page(request: Request):
    return render_template(
        request,
        "docs.html",
        page_title="Docs",
        active_nav="docs",
    )
