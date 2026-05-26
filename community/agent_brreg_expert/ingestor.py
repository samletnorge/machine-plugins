"""Bulk download logic for Brønnøysundregistrene data."""

from __future__ import annotations

import csv
import gzip
import io
import json
import zipfile
from typing import Any

import httpx
from loguru import logger

# Brreg bulk download URLs
ENHETER_URL = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned"
UNDERENHETER_URL = "https://data.brreg.no/enhetsregisteret/api/underenheter/lastned"
ROLLER_URL = "https://data.brreg.no/enhetsregisteret/api/roller/totalbestand"
FRIVILLIG_URL = "https://data.brreg.no/frivillighetsregisteret/api/totalbestand/csv"
PARTI_URL = "https://data.brreg.no/partiregisteret/api/lastned/csv"

# Timeout for large downloads (30 min)
DOWNLOAD_TIMEOUT = 1800.0


def parse_json_stream(data: bytes) -> list[dict[str, Any]]:
    """Parse JSON bytes (expected to be a JSON array) into list of dicts.

    Handles gzip-compressed data transparently.
    """
    if not data or data.strip() == b"":
        return []
    # Detect gzip (magic bytes 1f 8b)
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    parsed = json.loads(data)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        # Some endpoints wrap in {"_embedded": {"enheter": [...]}}
        embedded = parsed.get("_embedded", {})
        for key in ("enheter", "underenheter", "roller"):
            if key in embedded:
                return embedded[key]
        return [parsed]
    return []


def parse_csv_bytes(data: bytes, delimiter: str = ";") -> list[dict[str, Any]]:
    """Parse CSV bytes into list of dicts."""
    if not data:
        return []
    text = data.decode("utf-8-sig")  # BOM-safe
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [dict(row) for row in reader]


MAX_RETRIES = 3


async def _stream_download(url: str, label: str, retries: int = MAX_RETRIES) -> bytes:
    """Stream-download a large file with progress logging and retries."""
    import asyncio

    for attempt in range(1, retries + 1):
        logger.info("Streaming download (attempt {}): {} from {}", attempt, label, url)
        chunks: list[bytes] = []
        total = 0
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(DOWNLOAD_TIMEOUT, connect=30.0)
            ) as client:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    expected = resp.headers.get("content-length", "?")
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                        chunks.append(chunk)
                        total += len(chunk)
                        if total % (50 * 1024 * 1024) < len(chunk):
                            logger.info(
                                "{}: downloaded {} MB / {} bytes expected",
                                label,
                                total // (1024 * 1024),
                                expected,
                            )
            logger.info("{}: download complete ({} MB)", label, total // (1024 * 1024))
            return b"".join(chunks)
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ReadError) as e:
            if attempt < retries:
                wait = 5 * attempt
                logger.warning(
                    "{}: download failed at {} MB ({}), retrying in {}s...",
                    label,
                    total // (1024 * 1024),
                    e,
                    wait,
                )
                await asyncio.sleep(wait)
            else:
                raise


async def download_entities() -> list[dict[str, Any]]:
    """Download all entities from Enhetsregisteret."""
    data = await _stream_download(ENHETER_URL, "entities")
    result = parse_json_stream(data)
    logger.info("Downloaded {} entities", len(result))
    return result


async def download_sub_entities() -> list[dict[str, Any]]:
    """Download all sub-entities from Enhetsregisteret."""
    data = await _stream_download(UNDERENHETER_URL, "sub-entities")
    result = parse_json_stream(data)
    logger.info("Downloaded {} sub-entities", len(result))
    return result


async def download_roles() -> list[dict[str, Any]]:
    """Download all roles (zipped JSON)."""
    logger.info("Downloading roles from {}", ROLLER_URL)
    data = await _stream_download(ROLLER_URL, "roles")

    # Roles come as a zip file containing JSON
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        if not names:
            return []
        inner = zf.read(names[0])
        result = parse_json_stream(inner)
        logger.info("Downloaded {} role records", len(result))
        return result
    except zipfile.BadZipFile:
        # Maybe it's raw JSON or gzip
        result = parse_json_stream(data)
        logger.info("Downloaded {} role records (unzipped)", len(result))
        return result


async def download_frivillig() -> list[dict[str, Any]]:
    """Download voluntary organisations (CSV)."""
    logger.info("Downloading frivillig from {}", FRIVILLIG_URL)
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(FRIVILLIG_URL)
        resp.raise_for_status()
        result = parse_csv_bytes(resp.content, delimiter=";")
        logger.info("Downloaded {} frivillig records", len(result))
        return result


async def download_parti() -> list[dict[str, Any]]:
    """Download political parties (CSV)."""
    logger.info("Downloading parti from {}", PARTI_URL)
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(PARTI_URL)
        resp.raise_for_status()
        result = parse_csv_bytes(resp.content, delimiter=";")
        logger.info("Downloaded {} parti records", len(result))
        return result
