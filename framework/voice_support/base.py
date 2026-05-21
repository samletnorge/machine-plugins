"""Voice provider abstract base class and shared types."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import AsyncIterator, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AudioFormat(str, enum.Enum):
    PCM = "pcm"
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    FLAC = "flac"


class SpeakOptions(BaseModel):
    voice: str | None = None
    speed: float = Field(default=1.0, ge=0.1, le=4.0)
    format: AudioFormat = AudioFormat.PCM


class ListenOptions(BaseModel):
    language: str | None = None
    format: AudioFormat = AudioFormat.PCM


class ConnectOptions(BaseModel):
    voice: str | None = None
    language: str | None = None
    model: str | None = None


class VoiceConfig(BaseModel):
    default_speak_voice: str | None = None
    default_listen_language: str | None = None


@runtime_checkable
class RealtimeSession(Protocol):
    async def send(self, audio: bytes) -> None: ...
    async def receive(self) -> bytes | str: ...
    async def close(self) -> None: ...


class VoiceProvider(ABC):
    @abstractmethod
    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str: ...

    @abstractmethod
    async def connect(
        self, options: ConnectOptions | None = None
    ) -> RealtimeSession: ...
