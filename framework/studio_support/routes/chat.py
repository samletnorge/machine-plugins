"""Chat interface routes for Studio."""

from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from machine_core.plugins.studio_support.dependencies import get_machine

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("")
async def chat_page(request: Request, agent: str = ""):
    m = get_machine()
    agents = (
        list(m.list_category("agent").keys())
        if hasattr(m, "list_category")
        else list(getattr(m, "agents", {}).keys())
    )
    selected = agent if agent in agents else (agents[0] if agents else "")
    return templates.TemplateResponse(
        request,
        "chat.html",
        context={
            "agents": agents,
            "selected_agent": selected,
            "messages": [],
        },
    )


@router.post("/send")
async def chat_send(request: Request, agent: str = Form(...), message: str = Form(...)):
    m = get_machine()
    agent_instance = (
        m.resolve("agent", agent)
        if hasattr(m, "resolve")
        else getattr(m, "agents", {}).get(agent)
    )

    if agent_instance is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent}' not found")

    result = await agent_instance.run(message)
    response_text = getattr(result, "output", getattr(result, "data", str(result)))

    return HTMLResponse(f"""
    <div class="chat-message bg-gray-800 p-3 rounded mb-2">
        <p class="text-gray-400 text-sm">You</p>
        <p>{message}</p>
    </div>
    <div class="chat-message bg-gray-900 p-3 rounded mb-2">
        <p class="text-gray-400 text-sm">{agent}</p>
        <p>{response_text}</p>
    </div>
    """)
