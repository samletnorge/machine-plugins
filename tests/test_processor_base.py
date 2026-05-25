"""Tests for processor base types."""

import pytest
from processor_support.base import (
    ProcessorData,
    TripWire,
    Processor,
)


def test_processor_data_creation():
    """ProcessorData holds input text and arbitrary metadata."""
    data = ProcessorData(text="Hello world", metadata={"user_id": "abc"})
    assert data.text == "Hello world"
    assert data.metadata == {"user_id": "abc"}


def test_processor_data_defaults():
    """ProcessorData metadata defaults to empty dict."""
    data = ProcessorData(text="hi")
    assert data.metadata == {}


def test_processor_data_immutable_copy():
    """ProcessorData.replace() returns a new instance with overrides."""
    original = ProcessorData(text="hello", metadata={"a": 1})
    replaced = original.replace(text="bye")
    assert replaced.text == "bye"
    assert replaced.metadata == {"a": 1}
    assert original.text == "hello"  # original unchanged


def test_tripwire_creation():
    """TripWire carries a reason string and the processor name."""
    tw = TripWire(processor_name="pii", reason="SSN detected")
    assert tw.processor_name == "pii"
    assert tw.reason == "SSN detected"


def test_tripwire_is_not_processor_data():
    """TripWire is a distinct type from ProcessorData."""
    tw = TripWire(processor_name="test", reason="blocked")
    assert not isinstance(tw, ProcessorData)


def test_processor_abc_requires_process():
    """Processor subclass must implement process()."""
    with pytest.raises(TypeError):
        Processor()  # type: ignore


def test_processor_subclass_with_name_and_type():
    """Processor subclass must set name and type."""

    class MyProcessor(Processor):
        name = "my_proc"
        type = "input"

        async def process(self, data: ProcessorData) -> ProcessorData:
            return data

    proc = MyProcessor()
    assert proc.name == "my_proc"
    assert proc.type == "input"
