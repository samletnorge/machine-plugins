"""Tests for ingestor.py — bulk download + parse logic."""

import asyncio
import json
from unittest.mock import AsyncMock, patch
import pytest

from agent_brreg_expert.ingestor import (
    parse_json_stream,
    parse_csv_bytes,
    download_entities,
)


def test_parse_json_stream():
    """JSON array bytes are parsed into list of dicts."""
    data = json.dumps(
        [
            {"organisasjonsnummer": "123", "navn": "A"},
            {"organisasjonsnummer": "456", "navn": "B"},
        ]
    ).encode()
    result = parse_json_stream(data)
    assert len(result) == 2
    assert result[0]["navn"] == "A"


def test_parse_json_stream_empty():
    """Empty JSON array returns empty list."""
    assert parse_json_stream(b"[]") == []


def test_parse_json_stream_embedded():
    """Handles Brreg _embedded wrapper format."""
    data = json.dumps(
        {"_embedded": {"enheter": [{"organisasjonsnummer": "789"}]}}
    ).encode()
    result = parse_json_stream(data)
    assert len(result) == 1
    assert result[0]["organisasjonsnummer"] == "789"


def test_parse_csv_bytes():
    """CSV bytes are parsed into list of dicts."""
    csv_data = b"orgnr;kategori;navn\n111;Idrett;Forening\n222;Kultur;Lag\n"
    result = parse_csv_bytes(csv_data, delimiter=";")
    assert len(result) == 2
    assert result[0]["orgnr"] == "111"
    assert result[1]["kategori"] == "Kultur"


def test_parse_csv_bytes_empty():
    """Empty CSV (header only) returns empty list."""
    assert parse_csv_bytes(b"col1;col2\n", delimiter=";") == []


def test_download_entities_success():
    """download_entities fetches and parses JSON."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps([{"organisasjonsnummer": "999"}]).encode()
    mock_response.raise_for_status = lambda: None

    with patch("agent_brreg_expert.ingestor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(download_entities())
        assert len(result) == 1
        assert result[0]["organisasjonsnummer"] == "999"
