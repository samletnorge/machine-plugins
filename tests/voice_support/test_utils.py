"""Tests for audio utilities."""

import pytest
from voice_support.utils import (
    create_wav_header,
    pcm_to_wav,
    chunk_audio,
    detect_audio_format,
)


class TestWavHeader:
    def test_header_length(self):
        header = create_wav_header(
            data_size=1000, sample_rate=16000, channels=1, bits_per_sample=16
        )
        assert len(header) == 44

    def test_header_riff_magic(self):
        header = create_wav_header(data_size=100)
        assert header[:4] == b"RIFF"
        assert header[8:12] == b"WAVE"

    def test_default_params(self):
        header = create_wav_header(data_size=0)
        assert len(header) == 44


class TestPcmToWav:
    def test_wraps_pcm_data(self):
        pcm = b"\x00\x01" * 100
        wav = pcm_to_wav(pcm)
        assert wav[:4] == b"RIFF"
        assert wav[44:] == pcm

    def test_empty_pcm(self):
        wav = pcm_to_wav(b"")
        assert len(wav) == 44


class TestChunkAudio:
    def test_even_chunks(self):
        data = b"\x00" * 1000
        chunks = list(chunk_audio(data, chunk_size=250))
        assert len(chunks) == 4
        assert all(len(c) == 250 for c in chunks)

    def test_uneven_last_chunk(self):
        data = b"\x00" * 1000
        chunks = list(chunk_audio(data, chunk_size=300))
        assert len(chunks) == 4
        assert len(chunks[-1]) == 100

    def test_empty_data(self):
        chunks = list(chunk_audio(b"", chunk_size=100))
        assert chunks == []


class TestDetectFormat:
    def test_wav(self):
        header = b"RIFF" + b"\x00" * 4 + b"WAVE"
        assert detect_audio_format(header) == "wav"

    def test_mp3_id3(self):
        assert detect_audio_format(b"ID3" + b"\x00" * 10) == "mp3"

    def test_mp3_sync(self):
        assert detect_audio_format(b"\xff\xfb" + b"\x00" * 10) == "mp3"

    def test_ogg(self):
        assert detect_audio_format(b"OggS" + b"\x00" * 10) == "ogg"

    def test_flac(self):
        assert detect_audio_format(b"fLaC" + b"\x00" * 10) == "flac"

    def test_unknown(self):
        assert detect_audio_format(b"\x00\x00\x00\x00") == "unknown"
