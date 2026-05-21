"""Tests for ProcessorRunner — sequential processor chain."""

import pytest
from machine_core.plugins.processor_support.base import (
    Processor,
    ProcessorData,
    TripWire,
    ProcessorResult,
)
from machine_core.plugins.processor_support.runner import ProcessorRunner


class UpperProcessor(Processor):
    name = "upper"
    type = "input"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        return data.replace(text=data.text.upper())


class ExclamationProcessor(Processor):
    name = "exclaim"
    type = "input"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        return data.replace(text=data.text + "!")


class BlockBadWordsProcessor(Processor):
    name = "blocker"
    type = "input"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        if "bad" in data.text.lower():
            return TripWire(processor_name=self.name, reason="Bad word detected")
        return data


class MetadataProcessor(Processor):
    name = "meta"
    type = "both"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        new_meta = {**data.metadata, "processed_by_meta": True}
        return data.replace(metadata=new_meta)


class OutputOnlyProcessor(Processor):
    name = "output_only"
    type = "output"

    async def process(self, data: ProcessorData) -> ProcessorResult:
        return data.replace(text=data.text + " [reviewed]")


@pytest.mark.asyncio
async def test_runner_empty_chain():
    runner = ProcessorRunner(processors=[])
    data = ProcessorData(text="hello")
    result = await runner.run(data, phase="input")
    assert isinstance(result, ProcessorData)
    assert result.text == "hello"


@pytest.mark.asyncio
async def test_runner_single_processor():
    runner = ProcessorRunner(processors=[UpperProcessor()])
    data = ProcessorData(text="hello")
    result = await runner.run(data, phase="input")
    assert isinstance(result, ProcessorData)
    assert result.text == "HELLO"


@pytest.mark.asyncio
async def test_runner_chain_order():
    runner = ProcessorRunner(processors=[UpperProcessor(), ExclamationProcessor()])
    data = ProcessorData(text="hello")
    result = await runner.run(data, phase="input")
    assert isinstance(result, ProcessorData)
    assert result.text == "HELLO!"


@pytest.mark.asyncio
async def test_runner_tripwire_stops_chain():
    runner = ProcessorRunner(
        processors=[UpperProcessor(), BlockBadWordsProcessor(), ExclamationProcessor()]
    )
    data = ProcessorData(text="this is bad")
    result = await runner.run(data, phase="input")
    assert isinstance(result, TripWire)
    assert result.processor_name == "blocker"
    assert "Bad word" in result.reason


@pytest.mark.asyncio
async def test_runner_tripwire_first_processor():
    runner = ProcessorRunner(processors=[BlockBadWordsProcessor(), UpperProcessor()])
    data = ProcessorData(text="bad input")
    result = await runner.run(data, phase="input")
    assert isinstance(result, TripWire)


@pytest.mark.asyncio
async def test_runner_filters_by_phase_input():
    runner = ProcessorRunner(
        processors=[UpperProcessor(), OutputOnlyProcessor(), MetadataProcessor()]
    )
    data = ProcessorData(text="hello")
    result = await runner.run(data, phase="input")
    assert isinstance(result, ProcessorData)
    assert result.text == "HELLO"
    assert "[reviewed]" not in result.text
    assert result.metadata.get("processed_by_meta") is True


@pytest.mark.asyncio
async def test_runner_filters_by_phase_output():
    runner = ProcessorRunner(
        processors=[UpperProcessor(), OutputOnlyProcessor(), MetadataProcessor()]
    )
    data = ProcessorData(text="hello")
    result = await runner.run(data, phase="output")
    assert isinstance(result, ProcessorData)
    assert result.text == "hello [reviewed]"
    assert result.metadata.get("processed_by_meta") is True


@pytest.mark.asyncio
async def test_runner_preserves_metadata_through_chain():
    runner = ProcessorRunner(processors=[MetadataProcessor(), UpperProcessor()])
    data = ProcessorData(text="hello", metadata={"original": True})
    result = await runner.run(data, phase="input")
    assert isinstance(result, ProcessorData)
    assert result.metadata["original"] is True
    assert result.metadata["processed_by_meta"] is True
