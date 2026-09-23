"""Tests for the general chat assistant agent."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_assistant.agent import AssistantAgent


class FakeProvider:
    def __init__(self, output: str = "the answer") -> None:
        self.requests: list = []
        self._output = output

    async def generate(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            output=self._output,
            model=request.model or "deepseek-chat",
            usage={"prompt_tokens": 1, "completion_tokens": 2},
        )


@pytest.mark.anyio
async def test_assistant_includes_system_and_history():
    provider = FakeProvider("42")
    agent = AssistantAgent(system_prompt="sys", resolve_provider=lambda name: provider)

    reply = await agent.run(
        "follow-up",
        context={
            "messages": [
                {"role": "user", "content": "q1"},
                {"role": "assistant", "content": "a1"},
            ]
        },
    )

    assert reply.output == "42"
    sent = provider.requests[0].input
    assert sent[0] == {"role": "system", "content": "sys"}
    assert sent[1] == {"role": "user", "content": "q1"}
    assert sent[2] == {"role": "assistant", "content": "a1"}
    assert sent[3] == {"role": "user", "content": "follow-up"}


@pytest.mark.anyio
async def test_assistant_without_resolver_raises():
    agent = AssistantAgent()

    with pytest.raises(RuntimeError):
        await agent.run("hi")
