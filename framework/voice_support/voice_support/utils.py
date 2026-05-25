"""Audio format utilities for voice providers."""

from __future__ import annotations

import struct
from typing import Iterator


def create_wav_header(
    data_size: int,
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header


def pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 16000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    header = create_wav_header(len(pcm_data), sample_rate, channels, bits_per_sample)
    return header + pcm_data


def chunk_audio(data: bytes, chunk_size: int = 4096) -> Iterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def detect_audio_format(data: bytes) -> str:
    if len(data) < 4:
        return "unknown"
    if data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WAVE":
        return "wav"
    if data[:3] == b"ID3" or (
        len(data) >= 2 and data[0] == 0xFF and data[1] in (0xFB, 0xFA, 0xF3, 0xF2)
    ):
        return "mp3"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"fLaC":
        return "flac"
    return "unknown"
