"""Bulk download logic for Brønnøysundregistrene data."""

from __future__ import annotations

import csv
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
    """Parse JSON bytes (expected to be a JSON array) into list of dicts."""
    if not data or data.strip() == b"":
        return []
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


async def download_entities() -> list[dict[str, Any]]:
    """Download all entities from Enhetsregisteret."""
    logger.info("Downloading entities from {}", ENHETER_URL)
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(ENHETER_URL)
        resp.raise_for_status()
        result = parse_json_stream(resp.content)
        logger.info("Downloaded {} entities", len(result))
        return result


async def download_sub_entities() -> list[dict[str, Any]]:
    """Download all sub-entities from Enhetsregisteret."""
    logger.info("Downloading sub-entities from {}", UNDERENHETER_URL)
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(UNDERENHETER_URL)
        resp.raise_for_status()
        result = parse_json_stream(resp.content)
        logger.info("Downloaded {} sub-entities", len(result))
        return result


async def download_roles() -> list[dict[str, Any]]:
    """Download all roles (zipped JSON)."""
    logger.info("Downloading roles from {}", ROLLER_URL)
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(ROLLER_URL)
        resp.raise_for_status()

        # Roles come as a zip file containing JSON
        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            names = zf.namelist()
            if not names:
                return []
            data = zf.read(names[0])
            result = parse_json_stream(data)
            logger.info("Downloaded {} role records", len(result))
            return result
        except zipfile.BadZipFile:
            # Maybe it's raw JSON
            result = parse_json_stream(resp.content)
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
