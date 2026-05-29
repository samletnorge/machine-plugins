from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


class RemoteRuntimeError(RuntimeError):
    pass


def _join_url(base_url: str, path: str) -> str:
    return parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _http_json(method: str, url: str, body: Any | None = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with request.urlopen(req, timeout=15) as response:
            payload = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RemoteRuntimeError(f"{exc.code} {exc.reason}: {detail}") from exc
    except error.URLError as exc:
        raise RemoteRuntimeError(str(exc.reason)) from exc

    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


@dataclass(slots=True)
class RemoteResourceProxy:
    client: "RemoteMachineClient"
    category: str
    payload: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.payload.get("name", ""))

    @property
    def description(self) -> str | None:
        value = self.payload.get("description")
        return str(value) if value is not None else None

    def __getattr__(self, name: str) -> Any:
        if name in self.payload:
            return self.payload[name]
        raise AttributeError(name)


class RemoteAgentProxy(RemoteResourceProxy):
    async def run(self, message: str, context: dict[str, Any] | None = None) -> Any:
        del context
        return await asyncio.to_thread(
            self.client.invoke_operation,
            self.category,
            self.name,
            "run",
            message,
        )


class RemoteToolProxy(RemoteResourceProxy):
    async def execute(self, data: dict[str, Any]) -> Any:
        return await asyncio.to_thread(
            self.client.invoke_operation,
            self.category,
            self.name,
            "execute",
            data,
        )


class RemoteWorkflowProxy(RemoteResourceProxy):
    async def runs(self) -> list[dict[str, Any]]:
        result = await asyncio.to_thread(
            self.client.invoke_operation,
            self.category,
            self.name,
            "runs",
            None,
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "runs" in result:
            runs = result["runs"]
            return runs if isinstance(runs, list) else []
        return []


class RemoteMachineClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.name = self.base_url
        self._operations: dict[str, dict[str, dict[str, str]]] | None = None
        self._category_counts: dict[str, int] | None = None

    def _discover(self) -> None:
        if self._operations is not None:
            return
        spec = _http_json("GET", _join_url(self.base_url, "/openapi.json"))
        operations: dict[str, dict[str, dict[str, str]]] = {}
        for path, methods in spec.get("paths", {}).items():
            if not path.startswith("/api/"):
                continue
            for http_method, detail in methods.items():
                operation_id = detail.get("operationId", "")
                if "__" not in operation_id:
                    continue
                category, op_name = operation_id.split("__", 1)
                operations.setdefault(category, {})[op_name] = {
                    "method": http_method.upper(),
                    "path": path,
                }
        self._operations = operations

    def _health(self) -> dict[str, Any]:
        return _http_json("GET", _join_url(self.base_url, "/health"))

    def list_categories(self) -> list[str]:
        if self._category_counts is None:
            health = self._health()
            categories = health.get("categories", {})
            self._category_counts = categories if isinstance(categories, dict) else {}
        if self._category_counts:
            return sorted(self._category_counts.keys())
        self._discover()
        return sorted((self._operations or {}).keys())

    def get_operations(self, category: str) -> dict[str, dict[str, str]]:
        self._discover()
        return dict((self._operations or {}).get(category, {}))

    def get_owner(self, category: str, name: str) -> None:
        del category, name
        return None

    def list_category(self, category: str) -> dict[str, RemoteResourceProxy]:
        try:
            items = _http_json("GET", _join_url(self.base_url, f"/api/{category}"))
        except RemoteRuntimeError as exc:
            if str(exc).startswith("404 "):
                return {}
            raise
        if not isinstance(items, list):
            return {}
        return {
            item.get("name", ""): self._proxy_for(category, item)
            for item in items
            if isinstance(item, dict) and item.get("name")
        }

    def resolve(self, category: str, name: str) -> RemoteResourceProxy | None:
        try:
            item = _http_json(
                "GET", _join_url(self.base_url, f"/api/{category}/{name}")
            )
        except RemoteRuntimeError as exc:
            if str(exc).startswith("404 "):
                return None
            raise
        if not isinstance(item, dict):
            return None
        return self._proxy_for(category, item)

    def invoke_operation(
        self,
        category: str,
        name: str,
        operation: str,
        payload: Any | None,
    ) -> Any:
        operations = self.get_operations(category)
        if operation not in operations:
            raise RemoteRuntimeError(
                f"Runtime category '{category}' has no operation '{operation}'"
            )
        operation_meta = operations[operation]
        path = operation_meta["path"].replace("{name}", name)
        method = operation_meta["method"]
        return _http_json(method, _join_url(self.base_url, path), payload)

    def _proxy_for(self, category: str, payload: dict[str, Any]) -> RemoteResourceProxy:
        if category == "agent":
            return RemoteAgentProxy(client=self, category=category, payload=payload)
        if category == "tool":
            return RemoteToolProxy(client=self, category=category, payload=payload)
        if category == "workflow":
            return RemoteWorkflowProxy(client=self, category=category, payload=payload)
        return RemoteResourceProxy(client=self, category=category, payload=payload)
