"""Utilities for converting JSON Schema to Pydantic models at runtime."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, create_model


def json_schema_to_model(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Convert a JSON Schema dict to a Pydantic model class.

    Handles basic types: string, number, integer, boolean, array, object.
    Falls back to Any for complex/unsupported schemas.
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields: dict[str, Any] = {}
    for field_name, field_schema in properties.items():
        field_type = _schema_type_to_python(field_schema)
        if field_name in required:
            fields[field_name] = (field_type, ...)
        else:
            fields[field_name] = (field_type | None, None)

    return create_model(name, **fields)


def _schema_type_to_python(schema: dict[str, Any]) -> type:
    """Map JSON Schema type to Python type."""
    type_map = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
    }
    schema_type = schema.get("type", "string")
    if schema_type == "array":
        return list
    if schema_type == "object":
        return dict
    return type_map.get(schema_type, str)
