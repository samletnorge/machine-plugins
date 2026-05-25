"""Tests for gTTS provider."""

import pytest
import io
from unittest.mock import MagicMock, patch
from voice_support.base import SpeakOptions


class TestGTTSProvider:
    def test_import(self):
        from voice_support.providers.gtts import GTTSProvider

        with patch(
            "voice_support.providers.gtts.gTTS", MagicMock()
        ):
            provider = GTTSProvider()
            assert provider is not None

    @pytest.mark.asyncio
    async def test_speak_returns_chunks(self):
        from voice_support.providers.gtts import GTTSProvider

        fake_audio = b"\x00" * 1000
        mock_gtts = MagicMock()
        mock_gtts.return_value.write_to_fp = lambda fp: fp.write(fake_audio)

        with patch("voice_support.providers.gtts.gTTS", mock_gtts):
            provider = GTTSProvider()
            chunks = []
            async for chunk in await provider.speak("Hello"):
                chunks.append(chunk)
            assert b"".join(chunks) == fake_audio

    @pytest.mark.asyncio
    async def test_speak_with_language(self):
        from voice_support.providers.gtts import GTTSProvider

        mock_gtts = MagicMock()
        mock_gtts.return_value.write_to_fp = lambda fp: fp.write(b"audio")

        with patch("voice_support.providers.gtts.gTTS", mock_gtts):
            provider = GTTSProvider(language="no")
            await provider.speak("Hei")

    @pytest.mark.asyncio
    async def test_listen_raises(self):
        from voice_support.providers.gtts import GTTSProvider

        with patch(
            "voice_support.providers.gtts.gTTS", MagicMock()
        ):
            provider = GTTSProvider()
            with pytest.raises(NotImplementedError):
                await provider.listen(None)

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        from voice_support.providers.gtts import GTTSProvider

        with patch(
            "voice_support.providers.gtts.gTTS", MagicMock()
        ):
            provider = GTTSProvider()
            with pytest.raises(NotImplementedError):
                await provider.connect()
