"""Tests for ElevenLabs TTS provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from machine_core.plugins.voice_support.base import SpeakOptions


class TestElevenLabsProvider:
    def test_import(self):
        from machine_core.plugins.voice_support.providers.elevenlabs import (
            ElevenLabsProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.elevenlabs.AsyncElevenLabs",
            MagicMock(),
        ):
            provider = ElevenLabsProvider(api_key="test-key")
            assert provider is not None

    @pytest.mark.asyncio
    async def test_speak_streams(self):
        from machine_core.plugins.voice_support.providers.elevenlabs import (
            ElevenLabsProvider,
        )

        async def mock_stream():
            yield b"chunk1"
            yield b"chunk2"

        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value=mock_stream())

        with patch(
            "machine_core.plugins.voice_support.providers.elevenlabs.AsyncElevenLabs",
            return_value=mock_client,
        ):
            provider = ElevenLabsProvider(api_key="test-key")
            chunks = []
            async for chunk in await provider.speak("Hello"):
                chunks.append(chunk)
            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_listen_raises(self):
        from machine_core.plugins.voice_support.providers.elevenlabs import (
            ElevenLabsProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.elevenlabs.AsyncElevenLabs",
            MagicMock(),
        ):
            provider = ElevenLabsProvider(api_key="test-key")
            with pytest.raises(NotImplementedError):
                await provider.listen(None)

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        from machine_core.plugins.voice_support.providers.elevenlabs import (
            ElevenLabsProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.elevenlabs.AsyncElevenLabs",
            MagicMock(),
        ):
            provider = ElevenLabsProvider(api_key="test-key")
            with pytest.raises(NotImplementedError):
                await provider.connect()
