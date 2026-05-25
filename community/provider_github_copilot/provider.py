"""GitHub Copilot LLM provider — pydantic-ai OpenAI with custom auth."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)

from .auth import CopilotAuth, COPILOT_CHAT_BASE_URL


class _PatchObjectField(httpx.AsyncBaseTransport):
    """Wraps an httpx transport to inject missing 'object' field in Copilot responses.

    GitHub Copilot's API is OpenAI-compatible but omits the 'object' field
    that the OpenAI SDK expects for validation.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport) -> None:
        self._transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._transport.handle_async_request(request)
        if b"/chat/completions" in request.url.raw_path:
            body = await response.aread()
            try:
                data = json.loads(body)
                patched = False
                if "object" not in data and "choices" in data:
                    data["object"] = "chat.completion"
                    patched = True
                # Fix missing/null index in choices (Copilot quirk)
                for i, choice in enumerate(data.get("choices", [])):
                    if choice.get("index") is None:
                        choice["index"] = i
                        patched = True
                if patched:
                    return httpx.Response(
                        status_code=response.status_code,
                        headers=response.headers,
                        content=json.dumps(data).encode(),
                    )
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        return response


class CopilotLLMProvider:
    """GitHub Copilot provider using pydantic-ai with custom auth."""

    def __init__(
        self,
        auth: CopilotAuth,
        model: str = "gpt-4o",
    ) -> None:
        self._provider_name = "github-copilot"
        self._model_name = model

        # Build httpx client with auth + response patching
        base_transport = httpx.AsyncHTTPTransport()
        patched_transport = _PatchObjectField(base_transport)
        http_client = httpx.AsyncClient(
            auth=auth,
            transport=patched_transport,
        )

        openai_client = AsyncOpenAI(
            api_key="copilot-placeholder",
            base_url=COPILOT_CHAT_BASE_URL,
            http_client=http_client,
        )

        provider = OpenAIProvider(openai_client=openai_client)
        self._model = OpenAIChatModel(model_name=model, provider=provider)
        self._agent = Agent(model=self._model)

    def get_pydantic_model(self, model_name: str | None = None) -> Any:
        """Return the pydantic-ai model used by this provider."""
        # TODO: if model_name differs from self._model_name, create a new OpenAIChatModel
        return self._model

    async def invoke(self, request: Any) -> Any:
        if isinstance(request, ModelRequest):
            return await self.generate(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        start = time.monotonic()
        prompt = request.input if isinstance(request.input, str) else str(request.input)
        result = await self._agent.run(prompt)
        duration = (time.monotonic() - start) * 1000

        usage_data = {}
        try:
            # pydantic-ai v1.97+: usage is a property, output is .output
            usage = result.usage
            usage_data = {
                "prompt_tokens": getattr(usage, "request_tokens", 0),
                "completion_tokens": getattr(usage, "response_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        except Exception:
            pass

        # pydantic-ai v1.97+: .output instead of .data
        output = getattr(result, "output", None) or getattr(result, "data", None)

        return ModelResponse(
            provider=self._provider_name,
            model=self._model_name,
            output=str(output) if output else "",
            usage=usage_data,
            duration_ms=duration,
        )
