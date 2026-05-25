"""Tool tester routes for Studio."""

from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from studio_support.dependencies import get_machine

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/{tool_name}")
async def tool_page(request: Request, tool_name: str):
    m = get_machine()
    tool = (
        m.resolve("tool", tool_name)
        if hasattr(m, "resolve")
        else getattr(m, "tools", {}).get(tool_name)
    )
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return templates.TemplateResponse(
        request,
        "tool_tester.html",
        context={
            "tool": tool,
        },
    )


@router.post("/{tool_name}/execute")
async def tool_execute(request: Request, tool_name: str):
    m = get_machine()
    tool = (
        m.resolve("tool", tool_name)
        if hasattr(m, "resolve")
        else getattr(m, "tools", {}).get(tool_name)
    )
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    body = await request.json()
    result = await tool.execute(body)
    return {"result": result}
