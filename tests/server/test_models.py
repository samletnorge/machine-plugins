"""Tests for shared server models."""

import pytest
from pydantic import ValidationError


def test_agent_run_request_valid():
    from machine_core.plugins.server_support.models import AgentRunRequest

    req = AgentRunRequest(prompt="Hello")
    assert req.prompt == "Hello"
    assert req.thread_id is None


def test_agent_run_request_with_thread():
    from machine_core.plugins.server_support.models import AgentRunRequest

    req = AgentRunRequest(prompt="Hello", thread_id="t-123")
    assert req.thread_id == "t-123"


def test_agent_run_request_empty_prompt_fails():
    from machine_core.plugins.server_support.models import AgentRunRequest

    with pytest.raises(ValidationError):
        AgentRunRequest(prompt="")


def test_agent_generate_request_with_schema():
    from machine_core.plugins.server_support.models import AgentGenerateRequest

    req = AgentGenerateRequest(
        prompt="Summarize",
        output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
    )
    assert req.output_schema["type"] == "object"


def test_tool_execute_request():
    from machine_core.plugins.server_support.models import ToolExecuteRequest

    req = ToolExecuteRequest(input={"query": "test"})
    assert req.input["query"] == "test"


def test_workflow_start_request():
    from machine_core.plugins.server_support.models import WorkflowStartRequest

    req = WorkflowStartRequest(input={"data": [1, 2, 3]})
    assert req.input["data"] == [1, 2, 3]


def test_workflow_start_request_empty():
    from machine_core.plugins.server_support.models import WorkflowStartRequest

    req = WorkflowStartRequest()
    assert req.input == {}


def test_thread_create_request():
    from machine_core.plugins.server_support.models import ThreadCreateRequest

    req = ThreadCreateRequest(metadata={"user": "alice"})
    assert req.metadata["user"] == "alice"


def test_message_create_request():
    from machine_core.plugins.server_support.models import MessageCreateRequest

    req = MessageCreateRequest(role="user", content="Hello")
    assert req.role == "user"


def test_message_create_request_invalid_role():
    from machine_core.plugins.server_support.models import MessageCreateRequest

    with pytest.raises(ValidationError):
        MessageCreateRequest(role="invalid", content="Hello")


def test_agent_info_response():
    from machine_core.plugins.server_support.models import AgentInfoResponse

    resp = AgentInfoResponse(
        name="chat",
        description="Chat agent",
        model="openai/gpt-4o",
        tools=["web_search"],
    )
    assert resp.name == "chat"


def test_error_response():
    from machine_core.plugins.server_support.models import ErrorResponse

    resp = ErrorResponse(detail="Not found", status_code=404)
    assert resp.status_code == 404
