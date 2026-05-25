"""Dynamic OpenAPI-based Python client SDK for Machine Core API.

Auto-discovers endpoints from /openapi.json and builds namespaces dynamically.

Usage:
    from server_support.client import MachineClient

    client = MachineClient(base_url="http://localhost:8000")

    # Agents (auto-discovered)
    agents = client.agent.list()
    result = client.agent.run("chat", prompt="Hello!")

    # Tools
    tools = client.tool.list()
    result = client.tool.execute("web_search", query="python")

    # Workflows
    run = client.workflow.start("pipeline", data=[1, 2, 3])

    # Memory
    thread = client.memory.create_thread("manager", metadata={"user": "alice"})
    threads = client.memory.list_threads("manager")
"""

from __future__ import annotations

import re
from typing import Any, Optional


class _DynamicNamespace:
    """A namespace for a category (e.g., agent, tool) with list/get + operations."""

    def __init__(self, client: MachineClient, category: str, operations: dict):
        self._client = client
        self._category = category
        # operations: {op_name: {"method": "POST", "path_template": "/api/agent/{name}/run"}}
        self._operations = operations

    def list(self) -> list[dict]:
        """List all items in this category."""
        return self._client._get(f"/api/{self._category}")

    def get(self, name: str) -> dict:
        """Get a single item by name."""
        return self._client._get(f"/api/{self._category}/{name}")

    def __getattr__(self, op_name: str) -> Any:
        if op_name.startswith("_"):
            raise AttributeError(op_name)
        if op_name not in self._operations:
            raise AttributeError(
                f"'{self._category}' namespace has no operation '{op_name}'"
            )
        op = self._operations[op_name]

        def _call(name: str, **kwargs: Any) -> Any:
            method = op["method"]
            path_template = op["path_template"]
            # Fill {name}
            path = path_template.replace("{name}", name)
            # Fill remaining path params from kwargs
            path_params = re.findall(r"\{(\w+)\}", path)
            for param in path_params:
                if param in kwargs:
                    path = path.replace(f"{{{param}}}", str(kwargs.pop(param)))

            if method == "GET":
                return self._client._get(path)
            elif method == "DELETE":
                return self._client._delete(path)
            else:
                return self._client._post(path, kwargs)

        return _call


class MachineClient:
    """Dynamic Python client for Machine Core API.

    Auto-discovers categories and operations from /openapi.json on first access.

    Args:
        base_url: The base URL of the Machine Core API.
        api_key: Optional API key for authentication.
        http_client: Optional pre-configured httpx client or TestClient.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        api_key: Optional[str] = None,
        http_client: Any = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http_client = http_client
        self._namespaces: Optional[dict[str, _DynamicNamespace]] = None

    def _get_client(self) -> Any:
        if self._http_client is not None:
            return self._http_client
        import httpx

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return httpx.Client(base_url=self.base_url, headers=headers, timeout=60)

    def _get(self, path: str) -> Any:
        client = self._get_client()
        resp = client.get(path)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> Any:
        client = self._get_client()
        resp = client.post(path, json=body)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()

    def _delete(self, path: str) -> None:
        client = self._get_client()
        resp = client.delete(path)
        resp.raise_for_status()

    def _discover(self) -> None:
        """Fetch /openapi.json and build namespace map."""
        spec = self._get("/openapi.json")
        namespaces: dict[str, dict] = {}  # category -> {op_name -> op_info}

        for path, methods in spec.get("paths", {}).items():
            if not path.startswith("/api/"):
                continue

            for http_method, detail in methods.items():
                op_id = detail.get("operationId", "")
                # Our route_generator sets operationId as "{category}__{op_name}"
                if "__" not in op_id:
                    continue

                category, op_name = op_id.split("__", 1)

                if category not in namespaces:
                    namespaces[category] = {}

                # Skip list/get — those are built-in on _DynamicNamespace
                if op_name in ("list", "get"):
                    continue

                namespaces[category][op_name] = {
                    "method": http_method.upper(),
                    "path_template": path,
                }

        self._namespaces = {
            cat: _DynamicNamespace(self, cat, ops) for cat, ops in namespaces.items()
        }

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if self._namespaces is None:
            self._discover()
        assert self._namespaces is not None
        if name in self._namespaces:
            return self._namespaces[name]
        raise AttributeError(f"MachineClient has no namespace '{name}'")
