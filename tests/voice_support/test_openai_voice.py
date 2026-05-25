"""Tests for OpenAI voice provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from voice_support.base import (
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    AudioFormat,
)


class TestOpenAIVoiceProvider:
    def test_import(self):
        from voice_support.providers.openai_voice import (
            OpenAIVoiceProvider,
        )

        with patch(
            "voice_support.providers.openai_voice.AsyncOpenAI",
            MagicMock(),
        ):
            provider = OpenAIVoiceProvider(api_key="test-key")
            assert provider is not None

    @pytest.mark.asyncio
    async def test_speak_streams_audio(self):
        from voice_support.providers.openai_voice import (
            OpenAIVoiceProvider,
        )

        mock_response = MagicMock()
        mock_response.iter_bytes = MagicMock(return_value=iter([b"chunk1", b"chunk2"]))

        mock_client = MagicMock()
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)

        with patch(
            "voice_support.providers.openai_voice.AsyncOpenAI",
            return_value=mock_client,
        ):
            provider = OpenAIVoiceProvider(api_key="test-key")
            chunks = []
            async for chunk in await provider.speak("Hello"):
                chunks.append(chunk)
            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_speak_with_voice_option(self):
        from voice_support.providers.openai_voice import (
            OpenAIVoiceProvider,
        )

        mock_response = MagicMock()
        mock_response.iter_bytes = MagicMock(return_value=iter([b"audio"]))

        mock_client = MagicMock()
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)

        with patch(
            "voice_support.providers.openai_voice.AsyncOpenAI",
            return_value=mock_client,
        ):
            provider = OpenAIVoiceProvider(api_key="test-key")
            opts = SpeakOptions(voice="nova", speed=1.5)
            async for _ in await provider.speak("Test", opts):
                pass
            call_kwargs = mock_client.audio.speech.create.call_args.kwargs
            assert call_kwargs["voice"] == "nova"
            assert call_kwargs["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_listen_returns_text(self):
        from voice_support.providers.openai_voice import (
            OpenAIVoiceProvider,
        )

        mock_transcription = MagicMock()
        mock_transcription.text = "Hello world"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=mock_transcription
        )

        with patch(
            "voice_support.providers.openai_voice.AsyncOpenAI",
            return_value=mock_client,
        ):
            provider = OpenAIVoiceProvider(api_key="test-key")

            async def audio_gen():
                yield b"\x00\x01" * 100

            result = await provider.listen(audio_gen())
            assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_listen_with_language(self):
        from voice_support.providers.openai_voice import (
            OpenAIVoiceProvider,
        )

        mock_transcription = MagicMock()
        mock_transcription.text = "Hei verden"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=mock_transcription
        )

        with patch(
            "voice_support.providers.openai_voice.AsyncOpenAI",
            return_value=mock_client,
        ):
            provider = OpenAIVoiceProvider(api_key="test-key")

            async def audio_gen():
                yield b"\x00" * 100

            opts = ListenOptions(language="no")
            result = await provider.listen(audio_gen(), opts)
            assert result == "Hei verden"

    @pytest.mark.asyncio
    async def test_connect_returns_session(self):
        from voice_support.providers.openai_voice import (
            OpenAIVoiceProvider,
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=b"response_audio")
        mock_ws.close = AsyncMock()

        with patch(
            "voice_support.providers.openai_voice.AsyncOpenAI",
            MagicMock(),
        ):
            with patch(
                "voice_support.providers.openai_voice.websockets"
            ) as mock_websockets:
                mock_websockets.connect = AsyncMock(return_value=mock_ws)
                provider = OpenAIVoiceProvider(api_key="test-key")
                session = await provider.connect(ConnectOptions(voice="alloy"))
                assert session is not None
                await session.send(b"audio")
                response = await session.receive()
                assert response is not None
                await session.close()
