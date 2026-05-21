"""Tests for processor integration with Machine via the plugin system."""

import pytest
from machine_core.plugins.processor_support.base import (
    Processor,
    ProcessorData,
    ProcessorResult,
    TripWire,
)
from machine_core.plugins.processor_support.runner import ProcessorRunner
from machine_core.plugins.processor_support.builtin.pii import PIIProcessor
from machine_core.plugins.processor_support.builtin.prompt_injection import (
    PromptInjectionProcessor,
)
from machine_core.plugins.processor_support.builtin.token_limiter import (
    TokenLimiterProcessor,
)
from machine_core.plugins.processor_support.builtin.cost_guard import CostGuardProcessor
from machine_core.plugins.processor_support.builtin.regex_filter import (
    RegexFilterProcessor,
)
from machine_core.plugins.processor_support.builtin.cache import CacheProcessor
from machine_core.plugins.processor_support.builtin.tool_search import (
    ToolSearchProcessor,
)


class UpperInputProcessor(Processor):
    name = "upper_input"
    type = "input"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        return data.replace(text=data.text.upper())


class ReviewOutputProcessor(Processor):
    name = "review_output"
    type = "output"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        return data.replace(text=data.text + " [reviewed]")


class BlockBadProcessor(Processor):
    name = "block_bad"
    type = "input"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        if "bad" in data.text.lower():
            return TripWire(processor_name=self.name, reason="Bad content")
        return data


@pytest.mark.asyncio
async def test_runner_as_plugin_pipeline():
    runner = ProcessorRunner(
        processors=[UpperInputProcessor(), ReviewOutputProcessor()]
    )
    data = ProcessorData(text="hello")

    input_result = await runner.run(data, phase="input")
    assert isinstance(input_result, ProcessorData)
    assert input_result.text == "HELLO"

    output_result = await runner.run(ProcessorData(text="HELLO"), phase="output")
    assert isinstance(output_result, ProcessorData)
    assert output_result.text == "HELLO [reviewed]"


@pytest.mark.asyncio
async def test_tripwire_blocks_pipeline():
    runner = ProcessorRunner(processors=[BlockBadProcessor(), UpperInputProcessor()])
    data = ProcessorData(text="this is bad")
    result = await runner.run(data, phase="input")
    assert isinstance(result, TripWire)
    assert result.reason == "Bad content"


@pytest.mark.asyncio
async def test_full_pipeline_input_then_output():
    runner = ProcessorRunner(
        processors=[UpperInputProcessor(), ReviewOutputProcessor()]
    )

    input_data = ProcessorData(text="hello")
    input_result = await runner.run(input_data, phase="input")
    assert input_result.text == "HELLO"

    agent_output = input_result.text
    output_data = ProcessorData(text=agent_output, metadata=input_result.metadata)
    output_result = await runner.run(output_data, phase="output")
    assert output_result.text == "HELLO [reviewed]"


@pytest.mark.asyncio
async def test_builtin_processors_instantiate():
    processors = {
        "pii": PIIProcessor(),
        "prompt_injection": PromptInjectionProcessor(),
        "token_limiter": TokenLimiterProcessor(max_tokens=1000),
        "cost_guard": CostGuardProcessor(max_cost_usd=1.0, cost_per_1k_tokens=0.01),
        "regex_filter": RegexFilterProcessor(block_patterns=[r"test"]),
        "cache": CacheProcessor(ttl_seconds=60),
    }
    for name, proc in processors.items():
        assert proc.name == name or proc.name
        assert proc.type in ("input", "output", "both")


@pytest.mark.asyncio
async def test_runner_with_real_builtins():
    runner = ProcessorRunner(
        processors=[
            PIIProcessor(),
            PromptInjectionProcessor(),
            TokenLimiterProcessor(max_tokens=1000),
        ]
    )
    data = ProcessorData(text="What is the capital of France?")
    result = await runner.run(data, phase="input")
    assert isinstance(result, ProcessorData)
    assert result.text == "What is the capital of France?"
    assert "token_count" in result.metadata


@pytest.mark.asyncio
async def test_runner_with_real_builtins_pii_blocks():
    runner = ProcessorRunner(
        processors=[
            PIIProcessor(),
            PromptInjectionProcessor(),
            TokenLimiterProcessor(max_tokens=1000),
        ]
    )
    data = ProcessorData(text="My email is john@example.com")
    result = await runner.run(data, phase="input")
    assert isinstance(result, TripWire)
    assert result.processor_name == "pii"
