"""Tests for Fish Audio TTS provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from voice_support.base import SpeakOptions


class TestFishAudioProvider:
    def test_import(self):
        from voice_support.providers.fish_audio import (
            FishAudioProvider,
        )

        provider = FishAudioProvider(api_key="test-key")
        assert provider is not None

    @pytest.mark.asyncio
    async def test_speak_streams(self):
        from voice_support.providers.fish_audio import (
            FishAudioProvider,
        )

        async def mock_aiter(**kwargs):
            yield b"chunk1"
            yield b"chunk2"

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = mock_aiter
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "voice_support.providers.fish_audio.httpx.AsyncClient",
            return_value=mock_client,
        ):
            provider = FishAudioProvider(api_key="test-key")
            chunks = []
            async for chunk in await provider.speak("Hello"):
                chunks.append(chunk)
            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_listen_raises(self):
        from voice_support.providers.fish_audio import (
            FishAudioProvider,
        )

        provider = FishAudioProvider(api_key="test-key")
        with pytest.raises(NotImplementedError):
            await provider.listen(None)

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        from voice_support.providers.fish_audio import (
            FishAudioProvider,
        )

        provider = FishAudioProvider(api_key="test-key")
        with pytest.raises(NotImplementedError):
            await provider.connect()
