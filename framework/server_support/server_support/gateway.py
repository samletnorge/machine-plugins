"""Model gateway — OpenAI-compatible proxy over the Machine's model providers.

Adds auth, caching, and rate limiting in front of the registered
``model_provider`` implementations. Requests are translated to a
``ModelRequest`` and the provider's ``ModelResponse`` is returned in OpenAI
chat-completions shape.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

_FORWARDED_PARAMS = (
    "temperature",
    "top_p",
    "max_tokens",
    "presence_penalty",
    "frequency_penalty",
    "stop",
    "tools",
    "tool_choice",
    "response_format",
    "seed",
)


class GatewayConfig(BaseModel):
    """Configuration for the model gateway."""

    providers: dict[str, Any] = Field(default_factory=dict)
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1000
    rate_limit_rpm: int = 60
    api_keys: list[str] = Field(default_factory=list)


class RequestCache:
    """Simple TTL cache for gateway responses."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._store: dict[str, tuple[float, Any]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest]
        self._store[key] = (time.monotonic(), value)


class RateLimiter:
    """Token-bucket style per-key rate limiter."""

    def __init__(self, rpm: int = 60):
        self._rpm = rpm
        self._requests: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._requests[key]
        self._requests[key] = [t for t in window if now - t < 60]
        if len(self._requests[key]) >= self._rpm:
            return False
        self._requests[key].append(now)
        return True


def _cache_key(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _select_provider(machine: Any, config: GatewayConfig, body: dict) -> tuple[str | None, str]:
    """Choose (provider_name, model_name) for a request."""
    explicit = body.get("provider")
    if explicit:
        return explicit, body.get("model") or explicit

    model = body.get("model") or ""
    if "/" in model:
        provider_name, model_name = model.split("/", 1)
        return provider_name, model_name

    entry = config.providers.get(model)
    if isinstance(entry, str):
        return entry, model
    if isinstance(entry, dict) and entry.get("provider"):
        return entry["provider"], entry.get("model", model)

    if machine is not None and hasattr(machine, "list_category"):
        providers = machine.list_category("model_provider")
        if providers:
            name = next(iter(sorted(providers)))
            return name, model or ""

    return None, model


def _forwarded_parameters(body: dict) -> dict[str, Any]:
    return {k: body[k] for k in _FORWARDED_PARAMS if k in body}


def _to_openai_response(response: Any, provider_name: str) -> dict[str, Any]:
    usage = getattr(response, "usage", {}) or {}
    message: dict[str, Any] = {
        "role": "assistant",
        "content": getattr(response, "output", None),
    }
    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": getattr(response, "model", ""),
        "provider": provider_name,
        "choices": [
            {"index": 0, "message": message, "finish_reason": "stop"}
        ],
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


def create_gateway_router(config: GatewayConfig, machine: Any = None) -> APIRouter:
    """Create the gateway API router.

    ``machine`` is used to resolve ``model_provider`` implementations at
    request time so the gateway reflects whatever is registered.
    """
    router = APIRouter(prefix="/gateway", tags=["gateway"])
    cache = RequestCache(
        max_size=config.cache_max_size, ttl_seconds=config.cache_ttl_seconds
    )
    limiter = RateLimiter(rpm=config.rate_limit_rpm)

    def _check_auth(request: Request) -> None:
        if not config.api_keys:
            return
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
        if token not in config.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @router.post("/chat/completions")
    async def chat_completions(request: Request):
        _check_auth(request)
        body = await request.json()

        client_id = request.client.host if request.client else "unknown"
        if not limiter.allow(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        key = _cache_key(body) if config.cache_enabled else ""
        if config.cache_enabled:
            cached = cache.get(key)
            if cached is not None:
                return cached

        provider_name, model_name = _select_provider(machine, config, body)
        provider = (
            machine.resolve("model_provider", provider_name)
            if machine is not None
            and provider_name
            and hasattr(machine, "resolve")
            else None
        )
        if provider is None or not hasattr(provider, "generate"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "No model provider available"
                    + (f" for '{provider_name}'" if provider_name else "")
                ),
            )

        from model_provider_support.schemas import ModelRequest

        model_request = ModelRequest(
            provider=provider_name,
            model=model_name,
            input=body.get("messages") or body.get("prompt", ""),
            parameters=_forwarded_parameters(body),
        )

        response = await provider.generate(model_request)
        result = _to_openai_response(response, provider_name)

        if config.cache_enabled:
            cache.set(key, result)
        return result

    return router
