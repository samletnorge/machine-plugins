"""Tests for Deepgram STT provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from machine_core.plugins.voice_support.base import ListenOptions


class TestDeepgramProvider:
    def test_import(self):
        from machine_core.plugins.voice_support.providers.deepgram import (
            DeepgramProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.deepgram.DeepgramClient",
            MagicMock(),
        ):
            provider = DeepgramProvider(api_key="test-key")
            assert provider is not None

    @pytest.mark.asyncio
    async def test_listen_returns_text(self):
        from machine_core.plugins.voice_support.providers.deepgram import (
            DeepgramProvider,
        )

        mock_response = MagicMock()
        mock_response.results.channels[0].alternatives[0].transcript = "Hello world"

        mock_client = MagicMock()
        mock_client.listen.asyncrest.v1.transcribe_file = AsyncMock(
            return_value=mock_response
        )

        with patch(
            "machine_core.plugins.voice_support.providers.deepgram.DeepgramClient",
            return_value=mock_client,
        ):
            with patch(
                "machine_core.plugins.voice_support.providers.deepgram.PrerecordedOptions",
                MagicMock(),
            ):
                provider = DeepgramProvider(api_key="test-key")

                async def audio_gen():
                    yield b"\x00" * 100

                result = await provider.listen(audio_gen())
                assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_speak_raises(self):
        from machine_core.plugins.voice_support.providers.deepgram import (
            DeepgramProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.deepgram.DeepgramClient",
            MagicMock(),
        ):
            provider = DeepgramProvider(api_key="test-key")
            with pytest.raises(NotImplementedError):
                await provider.speak("test")

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        from machine_core.plugins.voice_support.providers.deepgram import (
            DeepgramProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.deepgram.DeepgramClient",
            MagicMock(),
        ):
            provider = DeepgramProvider(api_key="test-key")
            with pytest.raises(NotImplementedError):
                await provider.connect()
