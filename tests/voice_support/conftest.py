"""Shared test fixtures for voice_support tests."""

import pytest
from typing import AsyncIterator


async def audio_chunks(
    data: bytes = b"\x00\x01\x02\x03" * 256, chunk_size: int = 256
) -> AsyncIterator[bytes]:
    """Generate fake audio chunks for testing."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """1KB of fake PCM audio data."""
    return b"\x00\x01\x02\x03" * 256


@pytest.fixture
def sample_text() -> str:
    return "Hello, this is a test of the voice system."
