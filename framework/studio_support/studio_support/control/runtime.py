"""Studio runtime-facing JSON routes used by rich Studio surfaces."""

from __future__ import annotations

from collections import defaultdict
import inspect
from itertools import count
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from studio_support.dependencies import get_machine

router = APIRouter(prefix="/api", tags=["studio-runtime"])

_CHAT_THREADS: dict[str, list[dict[str, str]]] = defaultdict(list)
_CHAT_THREAD_AGENTS: dict[str, str] = {}
_CHAT_SESSION_IDS = count(1)


class ChatMessageRequest(BaseModel):
    agent: str
    message: str


def _machine_item(category: str, name: str) -> Any | None:
    machine = get_machine()
    if machine is None:
        return None
    if hasattr(machine, "resolve"):
        return machine.resolve(category, name)
    return getattr(machine, f"{category}s", {}).get(name)


def _item_owner(category: str, name: str) -> str | None:
    machine = get_machine()
    if machine is not None and hasattr(machine, "get_owner"):
        return machine.get_owner(category, name)
    return None


def _item_operations(category: str) -> list[str]:
    machine = get_machine()
    if machine is not None and hasattr(machine, "get_operations"):
        return sorted((machine.get_operations(category) or {}).keys())
    return []


def _chat_capable_agents() -> list[str]:
    machine = get_machine()
    if machine is None or not hasattr(machine, "list_category"):
        return []

    preferred: list[str] = []
    fallback: list[str] = []
    for name, agent in sorted(machine.list_category("agent").items()):
        run_method = getattr(agent, "run", None)
        if run_method is None:
            continue

        try:
            params = list(inspect.signature(run_method).parameters.values())
        except (TypeError, ValueError):
            fallback.append(name)
            continue

        required = [
            param
            for param in params
            if param.name != "self"
            and param.default is inspect._empty
            and param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        if len(required) <= 1:
            preferred.append(name)
        else:
            fallback.append(name)

    return preferred or fallback


def _chat_catalog() -> dict[str, list[str]]:
    machine = get_machine()
    if machine is None or not hasattr(machine, "list_category"):
        return {"agents": [], "runtimes": []}

    agents: list[str] = []
    runtimes: list[str] = []
    for name, agent in sorted(machine.list_category("agent").items()):
        run_method = getattr(agent, "run", None)
        if run_method is None:
            continue
        try:
            params = list(inspect.signature(run_method).parameters.values())
        except (TypeError, ValueError):
            runtimes.append(name)
            continue

        required = [
            param
            for param in params
            if param.name != "self"
            and param.default is inspect._empty
            and param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        if len(required) <= 1:
            agents.append(name)
        else:
            runtimes.append(name)

    return {"agents": agents, "runtimes": runtimes}


def _workflow_graph(workflow: Any) -> dict[str, list[dict[str, str]]]:
    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    previous: str | None = None

    for node in getattr(workflow, "nodes", []):
        names: list[str] = []
        if getattr(node, "step", None) is not None:
            names.append(getattr(node.step, "name", "step"))
        for step in getattr(node, "steps", []) or []:
            names.append(getattr(step, "name", "step"))

        for name in names:
            nodes.append(
                {
                    "id": name,
                    "label": name,
                    "kind": getattr(getattr(node, "node_type", None), "value", "step"),
                }
            )
            if previous is not None:
                edges.append({"source": previous, "target": name})
            previous = name

    return {"nodes": nodes, "edges": edges}


@router.get("/chat/threads")
async def list_chat_threads() -> dict[str, object]:
    catalog = _chat_catalog()
    agents = catalog["agents"]
    existing = {
        "default": list(_CHAT_THREADS.get("default", [])),
        **dict(_CHAT_THREADS),
    }

    threads = []
    for thread_id, messages in existing.items():
        threads.append(
            {
                "thread_id": thread_id,
                "agent": _CHAT_THREAD_AGENTS.get(
                    thread_id, agents[0] if agents else ""
                ),
                "messages": messages,
            }
        )
    return {"catalog": catalog, "threads": threads}


@router.post("/chat/sessions")
async def create_chat_session() -> dict[str, str]:
    thread_id = f"session-{next(_CHAT_SESSION_IDS)}"
    _CHAT_THREADS[thread_id] = []
    _CHAT_THREAD_AGENTS[thread_id] = ""
    return {"thread_id": thread_id}


@router.post("/chat/threads/{thread_id}/messages")
async def send_chat_message(
    thread_id: str, payload: ChatMessageRequest
) -> dict[str, object]:
    agent = _machine_item("agent", payload.agent)
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent '{payload.agent}' not found"
        )

    try:
        required = [
            param
            for param in inspect.signature(agent.run).parameters.values()
            if param.name != "self"
            and param.default is inspect._empty
            and param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
    except (TypeError, ValueError):
        required = []

    if len(required) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{payload.agent}' is not directly chat invokable in Studio",
        )

    _CHAT_THREAD_AGENTS.setdefault(thread_id, payload.agent)
    prior_messages = list(_CHAT_THREADS[thread_id])
    _CHAT_THREADS[thread_id].append({"role": "user", "content": payload.message})
    result = await agent.run(
        payload.message, context={"thread_id": thread_id, "messages": prior_messages}
    )
    response_text = getattr(result, "output", getattr(result, "data", str(result)))
    _CHAT_THREADS[thread_id].append({"role": "assistant", "content": response_text})

    return {"thread_id": thread_id, "messages": list(_CHAT_THREADS[thread_id])}


@router.get("/tools/{tool_name}")
async def get_tool_detail(tool_name: str) -> dict[str, object]:
    tool = _machine_item("tool", tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    input_model = getattr(tool, "input_model", None)
    input_schema = (
        input_model.model_json_schema()
        if input_model and hasattr(input_model, "model_json_schema")
        else {"type": "object", "properties": {}}
    )

    return {
        "name": tool_name,
        "description": getattr(tool, "description", None)
        or getattr(tool, "__doc__", None)
        or tool.__class__.__name__,
        "owner": _item_owner("tool", tool_name),
        "operations": _item_operations("tool"),
        "input_schema": input_schema,
    }


@router.get("/workflows/{workflow_name}")
async def get_workflow_detail(workflow_name: str) -> dict[str, object]:
    workflow = _machine_item("workflow", workflow_name)
    if workflow is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow_name}' not found"
        )
    return {"name": workflow_name, "graph": _workflow_graph(workflow)}


@router.get("/workflows/{workflow_name}/runs")
async def list_workflow_runs(workflow_name: str) -> dict[str, list[dict[str, object]]]:
    workflow = _machine_item("workflow", workflow_name)
    if workflow is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow_name}' not found"
        )

    runs = await workflow.runs() if hasattr(workflow, "runs") else []
    normalized = [run.to_dict() if hasattr(run, "to_dict") else run for run in runs]
    return {"runs": normalized}
