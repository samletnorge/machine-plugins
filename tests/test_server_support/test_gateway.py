"""Tests for the model gateway proxy."""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server_support.gateway import (
    create_gateway_router,
    GatewayConfig,
    RequestCache,
    RateLimiter,
)


def test_gateway_config_defaults():
    config = GatewayConfig()
    assert config.cache_enabled is True
    assert config.rate_limit_rpm > 0
    assert config.providers == {}


def test_gateway_config_custom():
    config = GatewayConfig(
        providers={
            "openai": {"api_key": "sk-test", "base_url": "https://api.openai.com/v1"},
            "anthropic": {
                "api_key": "sk-ant-test",
                "base_url": "https://api.anthropic.com",
            },
        },
        rate_limit_rpm=100,
    )
    assert len(config.providers) == 2
    assert config.rate_limit_rpm == 100


def test_request_cache_hit():
    cache = RequestCache(max_size=100, ttl_seconds=60)
    cache.set("key1", {"response": "cached"})
    assert cache.get("key1") == {"response": "cached"}


def test_request_cache_miss():
    cache = RequestCache(max_size=100, ttl_seconds=60)
    assert cache.get("unknown") is None


def test_request_cache_expiry():
    cache = RequestCache(max_size=100, ttl_seconds=0)
    cache.set("key1", {"data": "test"})
    time.sleep(0.01)
    assert cache.get("key1") is None


def test_rate_limiter_allows():
    limiter = RateLimiter(rpm=60)
    assert limiter.allow("user1") is True


def test_rate_limiter_blocks():
    limiter = RateLimiter(rpm=2)
    limiter.allow("user1")
    limiter.allow("user1")
    assert limiter.allow("user1") is False


def test_gateway_route_exists():
    config = GatewayConfig()
    router = create_gateway_router(config)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post(
        "/gateway/chat/completions", json={"model": "gpt-4o", "messages": []}
    )
    assert resp.status_code != 404


@pytest.mark.asyncio
async def test_gateway_validates_api_key():
    config = GatewayConfig(api_keys=["valid-key"])
    router = create_gateway_router(config)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post(
        "/gateway/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer invalid-key"},
    )
    assert resp.status_code == 401


class _FakeProvider:
    async def generate(self, request):
        from model_provider_support.schemas import ModelResponse

        return ModelResponse(
            provider="fake",
            model=request.model,
            output="hello",
            usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        )


class _FakeMachine:
    def resolve(self, category, name):
        if category == "model_provider" and name == "fake":
            return _FakeProvider()
        return None

    def list_category(self, category):
        return {"fake": _FakeProvider()} if category == "model_provider" else {}


def _gateway_client(machine=None, **config_kwargs):
    router = create_gateway_router(
        GatewayConfig(cache_enabled=False, **config_kwargs), machine=machine
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_gateway_proxies_to_registered_provider():
    client = _gateway_client(_FakeMachine())
    resp = client.post(
        "/gateway/chat/completions",
        json={
            "provider": "fake",
            "model": "fake-model",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "hello"
    assert data["usage"]["total_tokens"] == 3


def test_gateway_returns_503_without_provider():
    client = _gateway_client(None)
    resp = client.post(
        "/gateway/chat/completions", json={"model": "ghost", "messages": []}
    )
    assert resp.status_code == 503
