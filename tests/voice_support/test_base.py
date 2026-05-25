"""Tests for voice base types and ABC."""

import pytest
from pydantic import ValidationError
from voice_support.base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    RealtimeSession,
    AudioFormat,
    VoiceConfig,
)


class TestSpeakOptions:
    def test_defaults(self):
        opts = SpeakOptions()
        assert opts.voice is None
        assert opts.speed == 1.0
        assert opts.format == AudioFormat.PCM

    def test_custom(self):
        opts = SpeakOptions(voice="en-US-AriaNeural", speed=1.5, format=AudioFormat.MP3)
        assert opts.voice == "en-US-AriaNeural"
        assert opts.speed == 1.5
        assert opts.format == AudioFormat.MP3

    def test_speed_validation(self):
        with pytest.raises(ValidationError):
            SpeakOptions(speed=-1.0)
        with pytest.raises(ValidationError):
            SpeakOptions(speed=5.0)


class TestListenOptions:
    def test_defaults(self):
        opts = ListenOptions()
        assert opts.language is None
        assert opts.format == AudioFormat.PCM

    def test_custom(self):
        opts = ListenOptions(language="no", format=AudioFormat.WAV)
        assert opts.language == "no"


class TestConnectOptions:
    def test_defaults(self):
        opts = ConnectOptions()
        assert opts.voice is None
        assert opts.language is None
        assert opts.model is None

    def test_custom(self):
        opts = ConnectOptions(voice="alloy", language="en", model="gpt-4o-realtime")
        assert opts.model == "gpt-4o-realtime"


class TestVoiceConfig:
    def test_defaults(self):
        cfg = VoiceConfig()
        assert cfg.default_speak_voice is None
        assert cfg.default_listen_language is None

    def test_custom(self):
        cfg = VoiceConfig(default_speak_voice="alloy", default_listen_language="no")
        assert cfg.default_speak_voice == "alloy"


class TestAudioFormat:
    def test_values(self):
        assert AudioFormat.PCM == "pcm"
        assert AudioFormat.MP3 == "mp3"
        assert AudioFormat.WAV == "wav"
        assert AudioFormat.OGG == "ogg"
        assert AudioFormat.FLAC == "flac"


class TestVoiceProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            VoiceProvider()

    def test_concrete_subclass_must_implement_speak(self):
        class Incomplete(VoiceProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_works(self):
        class Minimal(VoiceProvider):
            async def speak(self, text, options=None):
                async def _gen():
                    yield b"audio"

                return _gen()

            async def listen(self, audio, options=None):
                return "transcribed"

            async def connect(self, options=None):
                raise NotImplementedError

        provider = Minimal()
        assert provider is not None


class TestRealtimeSession:
    def test_protocol_shape(self):
        """RealtimeSession must define send, receive, close."""
        assert hasattr(RealtimeSession, "send")
        assert hasattr(RealtimeSession, "receive")
        assert hasattr(RealtimeSession, "close")
