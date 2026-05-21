"""Tests for local Whisper STT provider."""

import pytest
from unittest.mock import MagicMock, patch
from machine_core.plugins.voice_support.base import ListenOptions


class TestWhisperLocalProvider:
    def test_import(self):
        from machine_core.plugins.voice_support.providers.whisper_local import (
            WhisperLocalProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.whisper_local.whisper"
        ) as mock_whisper:
            mock_whisper.load_model.return_value = MagicMock()
            provider = WhisperLocalProvider(model_size="base")
            assert provider is not None

    @pytest.mark.asyncio
    async def test_listen_returns_text(self):
        from machine_core.plugins.voice_support.providers.whisper_local import (
            WhisperLocalProvider,
        )

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Hello world"}

        with patch(
            "machine_core.plugins.voice_support.providers.whisper_local.whisper"
        ) as mock_whisper:
            mock_whisper.load_model.return_value = mock_model
            provider = WhisperLocalProvider(model_size="base")

            async def audio_gen():
                yield b"\x00" * 1000

            result = await provider.listen(audio_gen())
            assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_listen_with_language(self):
        from machine_core.plugins.voice_support.providers.whisper_local import (
            WhisperLocalProvider,
        )

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Hei verden"}

        with patch(
            "machine_core.plugins.voice_support.providers.whisper_local.whisper"
        ) as mock_whisper:
            mock_whisper.load_model.return_value = mock_model
            provider = WhisperLocalProvider()

            async def audio_gen():
                yield b"\x00" * 100

            opts = ListenOptions(language="no")
            result = await provider.listen(audio_gen(), opts)
            assert result == "Hei verden"
            call_kwargs = mock_model.transcribe.call_args
            assert call_kwargs[1].get("language") == "no" or "no" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_speak_raises(self):
        from machine_core.plugins.voice_support.providers.whisper_local import (
            WhisperLocalProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.whisper_local.whisper"
        ) as mock_whisper:
            mock_whisper.load_model.return_value = MagicMock()
            provider = WhisperLocalProvider()
            with pytest.raises(NotImplementedError):
                await provider.speak("test")

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        from machine_core.plugins.voice_support.providers.whisper_local import (
            WhisperLocalProvider,
        )

        with patch(
            "machine_core.plugins.voice_support.providers.whisper_local.whisper"
        ) as mock_whisper:
            mock_whisper.load_model.return_value = MagicMock()
            provider = WhisperLocalProvider()
            with pytest.raises(NotImplementedError):
                await provider.connect()
