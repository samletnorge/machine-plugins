"""@tool decorator for creating ToolDefinition from typed functions."""

from __future__ import annotations

import functools
import inspect
import typing
from enum import Enum as _Enum
from typing import Any, Callable, get_type_hints

from .schemas import ToolDefinition


def _json_schema_for_type(tp: Any) -> dict[str, Any]:
    """Best-effort JSON Schema for a Python annotation."""
    if tp in (inspect.Parameter.empty, Any, typing.Any):
        return {}
    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is bytes:
        return {"type": "string", "format": "binary"}

    origin = typing.get_origin(tp)
    args = typing.get_args(tp)

    if origin in (list, set, frozenset, tuple):
        return {"type": "array", "items": _json_schema_for_type(args[0]) if args else {}}
    if origin is dict:
        return {"type": "object"}
    if origin is typing.Literal:
        values = list(args)
        if values and all(isinstance(v, str) for v in values):
            return {"type": "string", "enum": values}
        return {"enum": values}
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _json_schema_for_type(non_none[0])
        return {"anyOf": [_json_schema_for_type(a) for a in non_none]}

    if isinstance(tp, type) and issubclass(tp, _Enum):
        return {"type": "string", "enum": [member.value for member in tp]}
    if hasattr(tp, "model_json_schema"):
        return tp.model_json_schema()

    return {"type": "string"}


def _is_optional(tp: Any) -> bool:
    if typing.get_origin(tp) is typing.Union:
        return type(None) in typing.get_args(tp)
    return False


def _params_schema(func: Callable) -> dict[str, Any]:
    """Generate JSON Schema from function type hints."""
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls", "kwargs", "args"):
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        param_type = hints.get(param_name, Any)
        properties[param_name] = _json_schema_for_type(param_type)
        if param.default is inspect.Parameter.empty and not _is_optional(param_type):
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
