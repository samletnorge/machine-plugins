"""Tests for Edge TTS provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from machine_core.plugins.voice_support.base import (
    SpeakOptions,
    ListenOptions,
    AudioFormat,
)


class TestEdgeTTSProvider:
    def test_import(self):
        from machine_core.plugins.voice_support.providers.edge_tts import (
            EdgeTTSProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.edge_tts.edge_tts",
            MagicMock(),
        ):
            provider = EdgeTTSProvider()
            assert provider is not None

    def test_default_voice(self):
        from machine_core.plugins.voice_support.providers.edge_tts import (
            EdgeTTSProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.edge_tts.edge_tts",
            MagicMock(),
        ):
            provider = EdgeTTSProvider(voice="en-US-AriaNeural")
            assert provider.voice == "en-US-AriaNeural"

    @pytest.mark.asyncio
    async def test_speak_returns_async_iterator(self):
        from machine_core.plugins.voice_support.providers.edge_tts import (
            EdgeTTSProvider,
        )

        mock_communicate = MagicMock()

        async def mock_stream():
            yield {"type": "audio", "data": b"\x00\x01\x02\x03"}
            yield {"type": "audio", "data": b"\x04\x05\x06\x07"}

        mock_communicate.return_value.stream = mock_stream
        mock_edge = MagicMock()
        mock_edge.Communicate = mock_communicate

        with patch(
            "machine_core.plugins.voice_support.providers.edge_tts.edge_tts", mock_edge
        ):
            provider = EdgeTTSProvider()
            chunks = []
            async for chunk in await provider.speak("Hello world"):
                chunks.append(chunk)
            assert len(chunks) == 2
            assert chunks[0] == b"\x00\x01\x02\x03"

    @pytest.mark.asyncio
    async def test_speak_with_options(self):
        from machine_core.plugins.voice_support.providers.edge_tts import (
            EdgeTTSProvider,
        )

        mock_communicate = MagicMock()

        async def mock_stream():
            yield {"type": "audio", "data": b"audio_data"}

        mock_communicate.return_value.stream = mock_stream
        mock_edge = MagicMock()
        mock_edge.Communicate = mock_communicate

        with patch(
            "machine_core.plugins.voice_support.providers.edge_tts.edge_tts", mock_edge
        ):
            provider = EdgeTTSProvider()
            opts = SpeakOptions(voice="nb-NO-FinnNeural", speed=1.2)
            chunks = []
            async for chunk in await provider.speak("Hei", opts):
                chunks.append(chunk)
            mock_communicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_raises(self):
        from machine_core.plugins.voice_support.providers.edge_tts import (
            EdgeTTSProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.edge_tts.edge_tts",
            MagicMock(),
        ):
            provider = EdgeTTSProvider()
            with pytest.raises(NotImplementedError):
                await provider.listen(None)

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        from machine_core.plugins.voice_support.providers.edge_tts import (
            EdgeTTSProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.edge_tts.edge_tts",
            MagicMock(),
        ):
            provider = EdgeTTSProvider()
            with pytest.raises(NotImplementedError):
                await provider.connect()
