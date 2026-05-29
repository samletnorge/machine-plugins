"""Dashboard and planned-section routes for Studio."""

from __future__ import annotations

from fastapi import APIRouter, Request

from studio_support.ui import SECTION_COPY, render_template

router = APIRouter(tags=["dashboard"])


@router.get("/")
async def dashboard(request: Request):
    return render_template(
        request,
        "dashboard.html",
        page_title="Mission Control",
        active_nav="dashboard",
    )


@router.get("/dashboard")
async def dashboard_alias(request: Request):
    return await dashboard(request)


@router.get("/account")
async def account_page(request: Request):
    return render_template(
        request,
        "section.html",
        page_title="Account",
        active_nav="account",
        section_title="Account",
        section_description="Personal preferences for Machine Studio live here, including theme selection.",
        account_page=True,
    )


@router.get("/sections/{section_key}")
async def planned_section(request: Request, section_key: str):
    title, description = SECTION_COPY.get(
        section_key,
        ("Section", "This Studio surface has been reserved but not wired yet."),
    )
    return render_template(
        request,
        "section.html",
        page_title=title,
        active_nav=section_key,
        section_title=title,
        section_description=description,
    )
