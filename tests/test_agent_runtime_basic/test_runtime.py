from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_runtime_basic.runtime import BasicAgentRunner
from agent_support.schemas import AgentDefinition


class FakeProvider:
    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return SimpleNamespace(output="ok", tool_calls=[], duration_ms=1)


@pytest.mark.anyio
async def test_basic_runtime_includes_prior_context_messages_in_model_input():
    provider = FakeProvider()
    runner = BasicAgentRunner(lambda _name: provider)

    await runner.run(
        definition=AgentDefinition(
            name="chat", description="chat", instruction="system"
        ),
        input="follow-up",
        tools=[],
        context={
            "thread_id": "default",
            "messages": [
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
            ],
        },
    )

    sent_messages = provider.requests[0].input
    assert sent_messages[0] == {"role": "system", "content": "system"}
    assert sent_messages[1] == {"role": "user", "content": "first question"}
    assert sent_messages[2] == {"role": "assistant", "content": "first answer"}
    assert sent_messages[3] == {"role": "user", "content": "follow-up"}
