"""Chat interface routes for Studio."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from studio_support.dependencies import get_machine
from studio_support.runtime_access import machine_item
from studio_support.ui import render_template

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
    return render_template(
        request,
        "chat.html",
        page_title="Chat",
        active_nav="chat",
        agents=agents,
        selected_agent=selected,
        messages=[],
    )


@router.post("/send")
async def chat_send(request: Request, agent: str = Form(...), message: str = Form(...)):
    agent_instance = machine_item("agent", agent)

    if agent_instance is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent}' not found")

    result = await agent_instance.run(message)
    response_text = getattr(result, "output", getattr(result, "data", str(result)))

    return HTMLResponse(
        f"""
        <article class=\"chat-bubble user\">
            <div class=\"chat-meta\">Operator</div>
            <div class=\"chat-body\">{message}</div>
        </article>
        <article class=\"chat-bubble assistant\">
            <div class=\"chat-meta\">{agent}</div>
            <div class=\"chat-body\">{response_text}</div>
        </article>
        """
    )
