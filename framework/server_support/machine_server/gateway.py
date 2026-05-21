"""Model gateway — proxy, caching, rate limiting for LLM providers."""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


class GatewayConfig(BaseModel):
    """Configuration for the model gateway."""

    providers: dict[str, dict[str, str]] = Field(default_factory=dict)
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
            # Evict oldest
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
        # Remove entries older than 60s
        self._requests[key] = [t for t in window if now - t < 60]
        if len(self._requests[key]) >= self._rpm:
            return False
        self._requests[key].append(now)
        return True


def _cache_key(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def create_gateway_router(config: GatewayConfig) -> APIRouter:
    """Create the gateway API router."""
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

        if config.cache_enabled:
            key = _cache_key(body)
            cached = cache.get(key)
            if cached is not None:
                return cached

        # In a real implementation, this would proxy to the provider.
        # For now, return a stub indicating no provider configured.
        model = body.get("model", "unknown")
        result = {
            "error": "no_provider",
            "message": f"No provider configured for model '{model}'",
        }

        if config.cache_enabled:
            cache.set(_cache_key(body), result)

        return result

    return router
