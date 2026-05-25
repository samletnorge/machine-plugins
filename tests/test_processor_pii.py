"""Tests for PII detection processor."""

import pytest
from processor_support.base import ProcessorData, TripWire
from processor_support.builtin.pii import PIIProcessor


@pytest.mark.asyncio
async def test_pii_detects_email():
    proc = PIIProcessor()
    data = ProcessorData(text="Contact me at john@example.com please")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "email" in result.reason.lower()


@pytest.mark.asyncio
async def test_pii_detects_phone_us():
    proc = PIIProcessor()
    data = ProcessorData(text="Call me at 555-123-4567")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "phone" in result.reason.lower()


@pytest.mark.asyncio
async def test_pii_detects_ssn():
    proc = PIIProcessor()
    data = ProcessorData(text="My SSN is 123-45-6789")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "ssn" in result.reason.lower()


@pytest.mark.asyncio
async def test_pii_detects_credit_card():
    proc = PIIProcessor()
    data = ProcessorData(text="Card number: 4111 1111 1111 1111")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "credit_card" in result.reason.lower()


@pytest.mark.asyncio
async def test_pii_clean_text_passes():
    proc = PIIProcessor()
    data = ProcessorData(text="Tell me about the weather today")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.text == "Tell me about the weather today"


@pytest.mark.asyncio
async def test_pii_redact_mode():
    proc = PIIProcessor(action="redact")
    data = ProcessorData(text="Email: john@example.com and SSN: 123-45-6789")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert "john@example.com" not in result.text
    assert "123-45-6789" not in result.text
    assert "[EMAIL]" in result.text
    assert "[SSN]" in result.text


@pytest.mark.asyncio
async def test_pii_custom_patterns():
    proc = PIIProcessor(extra_patterns={"norwegian_id": r"\b\d{11}\b"})
    data = ProcessorData(text="My ID is 12345678901")
    result = await proc.process(data)
    assert isinstance(result, TripWire)
    assert "norwegian_id" in result.reason.lower()
