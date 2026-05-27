"""Runtime catalog routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from studio_support.ui import machine_snapshot, render_template

router = APIRouter(tags=["resources"])


@router.get("/agents")
async def agents_page(request: Request):
    snapshot = machine_snapshot()
    return render_template(
        request,
        "resources.html",
        page_title="Agents",
        active_nav="agents",
        resource_title="Agents",
        resource_category="agent",
        resources=snapshot["runtime_agents"],
        empty_copy="No agents are currently registered in this runtime.",
    )


@router.get("/tools")
async def tools_page(request: Request):
    snapshot = machine_snapshot()
    return render_template(
        request,
        "resources.html",
        page_title="Tools",
        active_nav="tools",
        resource_title="Tools",
        resource_category="tool",
        resources=snapshot["runtime_tools"],
        empty_copy="No tools are currently registered in this runtime.",
    )


@router.get("/workflows")
async def workflows_page(request: Request):
    snapshot = machine_snapshot()
    return render_template(
        request,
        "resources.html",
        page_title="Workflows",
        active_nav="workflows",
        resource_title="Workflows",
        resource_category="workflow",
        resources=snapshot["runtime_workflows"],
        empty_copy="No workflows are currently registered in this runtime.",
    )
