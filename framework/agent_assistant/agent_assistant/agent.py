"""General chat agent backed by a model provider (DeepSeek by default)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

DEFAULT_SYSTEM_PROMPT = (
    "You are Machine Assistant, a capable general-purpose AI assistant embedded in "
    "Machine Studio. Answer complex questions thoughtfully and concisely. Prefer clear "
    "structure and markdown when it helps."
)

_ROLES = {"system", "user", "assistant"}


@dataclass
class AssistantReply:
    """Minimal reply object the Studio chat route understands (``.output``)."""

    output: str
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantAgent:
    """A single-turn chat agent that delegates to a registered model provider."""

    name: str = "assistant"
    description: str = "General chat agent backed by the configured model provider."
    provider_name: str = "deepseek"
    model: str = ""
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    parameters: dict[str, Any] = field(default_factory=dict)
    resolve_provider: Callable[[str], Any] | None = None

    def _messages(self, message: str, context: dict[str, Any] | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for item in (context or {}).get("messages", []):
            role = item.get("role")
            content = item.get("content")
            if role in _ROLES and content is not None:
                messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": message})
        return messages

    async def run(self, message: str, context: dict[str, Any] | None = None) -> AssistantReply:
        from model_provider_support.schemas import ModelRequest

        if self.resolve_provider is None:
            raise RuntimeError("AssistantAgent has no model provider resolver")

        provider = self.resolve_provider(self.provider_name)
        request = ModelRequest(
            provider=self.provider_name,
            model=self.model,
            input=self._messages(message, context),
            parameters=dict(self.parameters),
            stream=False,
        )
        response = await provider.generate(request)
        return AssistantReply(
            output=str(getattr(response, "output", "") or ""),
            provider=self.provider_name,
            model=str(getattr(response, "model", self.model) or self.model),
            usage=dict(getattr(response, "usage", {}) or {}),
        )
