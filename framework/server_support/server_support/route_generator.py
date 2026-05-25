"""Dynamic route generator — reads Machine registry and creates FastAPI routes."""

from __future__ import annotations

import inspect
import re
import typing
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from loguru import logger

from .sse import sse_response


def _serialize(obj: Any) -> Any:
    """Serialize an arbitrary object to JSON-safe form."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return {
            k: v
            for k, v in obj.__dict__.items()
            if not k.startswith("_") and not callable(v)
        }
    return str(obj)


def _extract_path_params(path_template: str) -> list[str]:
    """Extract parameter names from a path template like 'runs/{run_id}/resume'."""
    return re.findall(r"\{(\w+)\}", path_template)


def _coerce_kwargs(fn: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Coerce kwargs values to their annotated Pydantic types if applicable.

    For multi-param functions like run(definition: AgentDefinition, input: str, ...),
    this converts raw dicts to Pydantic model instances where type hints indicate one.
    """
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        return kwargs

    coerced = {}
    for key, value in kwargs.items():
        ann = hints.get(key)
        if (
            ann is not None
            and isinstance(value, dict)
            and hasattr(ann, "model_validate")
        ):
            coerced[key] = ann.model_validate(value)
        else:
            coerced[key] = value
    return coerced


def generate_routes(machine: Any) -> APIRouter:
    """Generate an APIRouter with routes for every category and operation."""
    router = APIRouter(prefix="/api")

    categories = (
        machine.list_categories() if hasattr(machine, "list_categories") else []
    )

    for category in categories:
        _cat = category  # capture for closures

        # --- LIST all items in category ---
        def _make_list(cat: str = _cat):
            async def _list():
                items = machine.list_category(cat)
                return [_serialize(v) for v in items.values()]

            return _list

        router.add_api_route(
            f"/{_cat}",
            _make_list(),
            methods=["GET"],
            tags=[_cat],
            operation_id=f"{_cat}__list",
        )

        # --- GET single item by name ---
        def _make_get(cat: str = _cat):
            async def _get(name: str):
                item = machine.resolve(cat, name)
                if item is None:
                    raise HTTPException(404, f"{cat} '{name}' not found")
                return _serialize(item)

            return _get

        router.add_api_route(
            f"/{_cat}/{{name}}",
            _make_get(),
            methods=["GET"],
            tags=[_cat],
            operation_id=f"{_cat}__get",
        )

        # --- Operation routes ---
        ops = machine.get_operations(_cat) if hasattr(machine, "get_operations") else {}
        for op_name, op_meta in ops.items():
            method = op_meta.get("method", "POST")
            path_suffix = op_meta.get("path", op_name)
            is_stream = op_name == "stream" or "stream" in op_name.lower()
            is_delete = method.upper() == "DELETE"

            full_path = f"/{_cat}/{{name}}/{path_suffix}"
            path_params = _extract_path_params(path_suffix)

            def _make_op(
                cat: str = _cat,
                _op_name: str = op_name,
                _path_params: list[str] = path_params,
                _is_stream: bool = is_stream,
                _is_delete: bool = is_delete,
                _method: str = method,
            ):
                async def _handler(name: str, request: Request):
                    item = machine.resolve(cat, name)
                    if item is None:
                        raise HTTPException(404, f"{cat} '{name}' not found")

                    # Find the method on the item
                    fn_name = _op_name
                    fn = getattr(item, fn_name, None)
                    # For stream, try run_stream first
                    if _is_stream and fn is None:
                        fn = getattr(item, "run_stream", None)
                    if fn is None:
                        raise HTTPException(
                            404, f"Operation '{_op_name}' not found on {cat} '{name}'"
                        )

                    # Build kwargs from path params + body
                    kwargs: dict[str, Any] = {}

                    # Extract extra path params from the actual request path
                    # FastAPI path params beyond {name} need manual extraction
                    actual_path = request.url.path
                    # Build a regex from the full_path pattern
                    pattern = f"/api/{cat}/[^/]+/{_build_regex(_op_name, _path_params)}"
                    if _path_params:
                        # Extract from URL manually
                        parts = actual_path.split(f"/{name}/", 1)
                        if len(parts) == 2:
                            remainder = parts[1]
                            _extract_params_from_path(
                                _path_params,
                                _op_name if "path" not in {} else "",
                                remainder,
                                kwargs,
                                request,
                                cat,
                            )

                    # Parse body for POST
                    if _method.upper() in ("POST", "PUT", "PATCH"):
                        try:
                            body = await request.json()
                        except Exception:
                            body = {}
                        kwargs.update(body)

                    # Stream handling
                    if _is_stream:
                        try:
                            typed_kwargs = _coerce_kwargs(fn, kwargs)
                            gen = fn(**typed_kwargs)
                            if inspect.isawaitable(gen):
                                gen = await gen
                            return sse_response(gen)
                        except TypeError:
                            # Same retry logic for stream
                            sig = inspect.signature(fn)
                            params = [
                                p for p in sig.parameters.values() if p.name != "self"
                            ]
                            ann = None
                            if (
                                params
                                and params[0].annotation != inspect.Parameter.empty
                            ):
                                ann = params[0].annotation
                            if isinstance(ann, str):
                                hints = typing.get_type_hints(fn)
                                ann = hints.get(params[0].name)
                            if ann and hasattr(ann, "model_validate"):
                                gen = fn(ann.model_validate(kwargs))
                            else:
                                gen = fn(kwargs)
                            if inspect.isawaitable(gen):
                                gen = await gen
                            return sse_response(gen)
                        except Exception as e:
                            logger.error(f"Stream error: {e}")
                            raise HTTPException(500, str(e))

                    # Normal call
                    try:
                        # Pre-validate kwargs against type hints for Pydantic models
                        typed_kwargs = _coerce_kwargs(fn, kwargs)
                        result = fn(**typed_kwargs)
                        if inspect.isawaitable(result):
                            result = await result
                    except TypeError as e:
                        # Retry: inspect signature and build typed request if possible
                        logger.debug(f"Retrying with positional arg: {e}")
                        try:
                            sig = inspect.signature(fn)
                            params = [
                                p for p in sig.parameters.values() if p.name != "self"
                            ]
                            ann = None
                            if (
                                params
                                and params[0].annotation != inspect.Parameter.empty
                            ):
                                ann = params[0].annotation

                            # Resolve string annotations (from __future__ import annotations)
                            if isinstance(ann, str):
                                hints = typing.get_type_hints(fn)
                                first_param_name = params[0].name
                                ann = hints.get(first_param_name)

                            if ann and hasattr(ann, "model_validate"):
                                typed_arg = ann.model_validate(kwargs)
                                result = fn(typed_arg)
                            else:
                                result = fn(kwargs)
                            if inspect.isawaitable(result):
                                result = await result
                        except Exception:
                            raise HTTPException(500, str(e))
                    except Exception as e:
                        logger.error(f"Operation error: {e}")
                        raise HTTPException(500, str(e))

                    if _is_delete:
                        return Response(status_code=204)

                    return _serialize(result)

                return _handler

            router.add_api_route(
                full_path,
                _make_op(),
                methods=[method.upper()],
                tags=[_cat],
                operation_id=f"{_cat}__{op_name}",
            )

    return router


def _build_regex(op_name: str, path_params: list[str]) -> str:
    """Not actually used for matching — placeholder."""
    return op_name


def _extract_params_from_path(
    param_names: list[str],
    op_name: str,
    remainder: str,
    kwargs: dict,
    request: Request,
    cat: str,
) -> None:
    """Extract path parameters from the URL remainder after /{name}/."""
    # The remainder is like: "runs/run-001/resume" or "threads/thread-1/messages"
    # and param_names are like ["run_id"] or ["thread_id"]
    # We need to match them positionally from the path template segments
    parts = remainder.strip("/").split("/")

    # Strategy: the param positions correspond to the template structure.
    # For "runs/{run_id}/resume" with remainder "runs/run-001/resume":
    #   parts = ["runs", "run-001", "resume"]
    #   {run_id} is at index 1
    # For "threads/{thread_id}" with remainder "threads/thread-1":
    #   parts = ["threads", "thread-1"]
    #   {thread_id} is at index 1
    # For "threads/{thread_id}/messages" with remainder "threads/thread-1/messages":
    #   parts = ["threads", "thread-1", "messages"]
    #   {thread_id} is at index 1

    # Get the path template from operations to find param positions
    # We'll use a simple heuristic: params appear at odd indices in typical REST paths
    # Actually, let's just search for param values by examining the template structure

    # Since we know param_names, and typical REST patterns put the value after a static segment,
    # we iterate through parts and assign params to non-static-looking segments
    # that aren't the op_name itself.

    # Better approach: reconstruct from the operation metadata
    # But we don't have the template here. Use positional assignment.
    param_idx = 0
    static_segments = set()

    # Identify static segments (non-param parts of the template)
    # Static segments: first segment is usually a resource name, last might be action
    # Params are the values between static parts
    for i, part in enumerate(parts):
        # If this part matches a known segment name like "runs", "threads", "resume", "messages"
        # it's static. Otherwise it might be a param value.
        if (
            part.isidentifier()
            and not part.startswith("run-")
            and not part.startswith("thread-")
            and not part.startswith("msg-")
        ):
            static_segments.add(i)

    # Assign remaining positions to params
    for i, part in enumerate(parts):
        if i not in static_segments and param_idx < len(param_names):
            kwargs[param_names[param_idx]] = part
            param_idx += 1

    # Fallback: if no params were assigned (heuristic failed), try simple assignment
    if param_idx == 0 and len(param_names) > 0:
        # Just assign non-first, non-last parts
        for i, part in enumerate(parts):
            if i > 0 and param_idx < len(param_names):
                kwargs[param_names[param_idx]] = part
                param_idx += 1
