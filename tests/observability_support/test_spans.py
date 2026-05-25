"""Tests for span attribute constants and helpers."""

from observability_support.spans import (
    SpanKind,
    SpanAttributes,
    create_span_attributes,
)


def test_span_kind_values():
    assert SpanKind.AGENT_CALL.value == "agent.call"
    assert SpanKind.TOOL_INVOKE.value == "tool.invoke"
    assert SpanKind.LLM_REQUEST.value == "llm.request"
    assert SpanKind.WORKFLOW_STEP.value == "workflow.step"
    assert SpanKind.MEMORY_OP.value == "memory.operation"
    assert SpanKind.PROCESSOR_RUN.value == "processor.run"


def test_span_attributes_constants():
    assert SpanAttributes.MODEL_NAME == "machine.model.name"
    assert SpanAttributes.TOKEN_INPUT == "machine.token.input"
    assert SpanAttributes.TOKEN_OUTPUT == "machine.token.output"
    assert SpanAttributes.LATENCY_MS == "machine.latency_ms"
    assert SpanAttributes.COST_USD == "machine.cost_usd"
    assert SpanAttributes.AGENT_NAME == "machine.agent.name"
    assert SpanAttributes.TOOL_NAME == "machine.tool.name"
    assert SpanAttributes.WORKFLOW_NAME == "machine.workflow.name"
    assert SpanAttributes.STEP_NAME == "machine.step.name"
    assert SpanAttributes.ERROR_TYPE == "machine.error.type"
    assert SpanAttributes.ERROR_MESSAGE == "machine.error.message"


def test_create_span_attributes_agent():
    attrs = create_span_attributes(
        kind=SpanKind.AGENT_CALL,
        agent_name="summarizer",
        model_name="gpt-4o",
    )
    assert attrs[SpanAttributes.AGENT_NAME] == "summarizer"
    assert attrs[SpanAttributes.MODEL_NAME] == "gpt-4o"
    assert "machine.span.kind" in attrs
    assert attrs["machine.span.kind"] == "agent.call"


def test_create_span_attributes_tool():
    attrs = create_span_attributes(
        kind=SpanKind.TOOL_INVOKE,
        tool_name="search_stations",
    )
    assert attrs[SpanAttributes.TOOL_NAME] == "search_stations"


def test_create_span_attributes_llm_with_tokens():
    attrs = create_span_attributes(
        kind=SpanKind.LLM_REQUEST,
        model_name="claude-sonnet-4-20250514",
        token_input=500,
        token_output=200,
        latency_ms=1200.5,
    )
    assert attrs[SpanAttributes.TOKEN_INPUT] == 500
    assert attrs[SpanAttributes.TOKEN_OUTPUT] == 200
    assert attrs[SpanAttributes.LATENCY_MS] == 1200.5


def test_create_span_attributes_omits_none_values():
    attrs = create_span_attributes(kind=SpanKind.AGENT_CALL)
    assert SpanAttributes.MODEL_NAME not in attrs
    assert SpanAttributes.AGENT_NAME not in attrs
