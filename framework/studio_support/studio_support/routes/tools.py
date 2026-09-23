"""Tool execution route (JSON API used by the Studio SPA)."""

from __future__ import annotations

import inspect

from fastapi import APIRouter, HTTPException, Request

from studio_support.runtime_access import machine_item

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/{tool_name}/execute")
async def tool_execute(request: Request, tool_name: str):
    tool = machine_item("tool", tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    body = await request.json()

    execute = getattr(tool, "execute", None)
    if callable(execute):
        result = execute(body)
        if inspect.isawaitable(result):
            result = await result
        return {"result": result}

    handler = getattr(tool, "handler", None)
    if callable(handler):
        result = handler(**body)
        if inspect.isawaitable(result):
            result = await result
        return {"result": result}

    filter_method = getattr(tool, "filter", None)
    if callable(filter_method):
        prompt = body.get("prompt") or body.get("input") or body.get("query") or ""
        top_k = body.get("top_k", 10)
        result = filter_method(prompt, top_k=top_k)
        if inspect.isawaitable(result):
            result = await result
        return {"result": result}

    raise HTTPException(
        status_code=400,
        detail=f"Tool '{tool_name}' is not executable from Studio",
    )
