"""@tool decorator for creating ToolDefinition from typed functions."""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, get_type_hints

from .schemas import ToolDefinition


_PYTHON_TYPE_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _params_schema(func: Callable) -> dict[str, Any]:
    """Generate JSON Schema from function type hints."""
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls", "kwargs"):
            continue
        param_type = hints.get(param_name, Any)
        json_type = _PYTHON_TYPE_TO_JSON.get(param_type, "string")
        properties[param_name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def tool(
    name: str | None = None,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable:
    """Decorator that creates a ToolDefinition from a typed function."""

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip() or tool_name
        params = _params_schema(func)

        td = ToolDefinition(
            name=tool_name,
            description=tool_desc,
            parameters=params,
            handler=func,
            metadata=metadata or {},
        )

        @functools.wraps(func)
        async def wrapper(**kwargs: Any) -> Any:
            result = func(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result

        wrapper.__tool_definition__ = td
        return wrapper

    return decorator
