"""OpenAPI spec -> ToolDefinition generator."""

from __future__ import annotations

import re
from typing import Any

import httpx

from tool_support.schemas import ToolDefinition


def generate_tools(
    spec: dict[str, Any],
    base_url: str | None = None,
    auth_headers: dict[str, str] | None = None,
    spec_url: str | None = None,
) -> list[ToolDefinition]:
    """Parse an OpenAPI 3.x spec and return a list of ToolDefinition objects.

    Args:
        spec: Parsed OpenAPI 3.x spec dict.
        base_url: Explicit base URL override for all endpoints.
        auth_headers: Headers to include in every request.
        spec_url: The URL the spec was fetched from. Used to resolve
            relative server URLs (e.g. ``"/"`` becomes the spec host).
    """
    tools: list[ToolDefinition] = []
    server_url = base_url or _get_server_url(spec, spec_url=spec_url)
    components = spec.get("components", {})

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue

            op_id = operation.get("operationId", f"{method}_{path}")
            name = _sanitize_name(op_id)
            description = operation.get("summary", operation.get("description", name))
            params_schema = _extract_params_schema(operation, components)

            handler = _make_handler(
                server_url=server_url,
                path=path,
                method=method.upper(),
                auth_headers=auth_headers or {},
            )

            tools.append(
                ToolDefinition(
                    name=name,
                    description=description,
                    parameters=simplify_schema(params_schema, components),
                    handler=handler,
                    metadata={
                        "source": "openapi",
                        "path": path,
                        "method": method,
                        "operation_id": op_id,
                        "operation_summary": operation.get("summary", ""),
                        "operation_description": operation.get("description", ""),
                        "parameter_details": _extract_parameter_details(
                            operation, components
                        ),
                    },
                )
            )

    return tools


def simplify_schema(
    schema: dict[str, Any],
    components: dict[str, Any],
    depth: int = 0,
    max_depth: int = 5,
) -> dict[str, Any]:
    """Resolve $ref pointers and strip non-essential fields from a JSON schema."""
    if depth > max_depth:
        return {"type": "object"}

    if "$ref" in schema:
        ref_path = schema["$ref"].split("/")
        # Build root context: refs like #/components/schemas/X need {"components": ...}
        root = (
            {"components": components} if "components" not in components else components
        )
        resolved: Any = root
        for part in ref_path[1:]:  # skip leading '#'
            resolved = resolved.get(part, {})
        if not resolved:
            return {"type": "object"}
        return simplify_schema(resolved, components, depth + 1, max_depth)

    result = dict(schema)

    if "properties" in result:
        result["properties"] = {
            k: simplify_schema(v, components, depth + 1, max_depth)
            for k, v in result["properties"].items()
        }

    if "items" in result:
        result["items"] = simplify_schema(
            result["items"], components, depth + 1, max_depth
        )

    for field in ["title", "default", "example", "examples", "nullable"]:
        result.pop(field, None)

    return result


def _get_server_url(spec: dict[str, Any], spec_url: str | None = None) -> str:
    """Extract server URL from spec, handling relative URLs.

    If the spec declares a relative server URL (e.g. "/") and a spec_url was
    provided (the URL the spec was fetched from), use the spec_url's origin
    as the base.
    """
    servers = spec.get("servers", [])
    url = servers[0]["url"] if servers else "http://localhost"

    # Handle relative server URLs like "/" or "/api/v1"
    if url.startswith("/") and spec_url:
        from urllib.parse import urlparse

        parsed = urlparse(spec_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        url = origin + url.rstrip("/")
    elif url.startswith("/"):
        url = "http://localhost" + url.rstrip("/")

    return url.rstrip("/")


def _sanitize_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:64]


def _extract_params_schema(
    operation: dict[str, Any], components: dict[str, Any]
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in operation.get("parameters", []):
        properties[param["name"]] = param.get("schema", {"type": "string"})
        if param.get("required"):
            required.append(param["name"])

    body = operation.get("requestBody", {})
    content = body.get("content", {})
    json_schema = content.get("application/json", {}).get("schema", {})

    if json_schema:
        resolved = simplify_schema(json_schema, components)
        if resolved.get("type") == "object" and "properties" in resolved:
            properties.update(resolved["properties"])
            required.extend(resolved.get("required", []))
        else:
            properties["body"] = resolved

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _extract_parameter_details(
    operation: dict[str, Any], components: dict[str, Any]
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for param in operation.get("parameters", []):
        schema = param.get("schema", {})
        details.append(
            {
                "name": param.get("name", ""),
                "in": param.get("in", "query"),
                "required": bool(param.get("required", False)),
                "description": param.get("description", ""),
                "schema": simplify_schema(schema, components),
            }
        )
    return details


def _make_handler(
    server_url: str, path: str, method: str, auth_headers: dict[str, str]
):
    """Create an async handler that makes the HTTP call for a given endpoint."""

    async def handler(**kwargs: Any) -> Any:
        url = f"{server_url}{path}"
        # Substitute path parameters
        for key, value in list(kwargs.items()):
            if f"{{{key}}}" in url:
                url = url.replace(f"{{{key}}}", str(value))
                del kwargs[key]

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method in ("GET", "DELETE"):
                resp = await client.request(
                    method, url, params=kwargs, headers=auth_headers
                )
            else:
                resp = await client.request(
                    method, url, json=kwargs, headers=auth_headers
                )
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return resp.text

    return handler
