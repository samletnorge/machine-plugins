# agent-brreg-expert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a community plugin that provides a Norwegian companies expert agent backed by full RAG ingestion of all Brønnøysundregistrene registries + live API tools.

**Architecture:** Plugin registers into 3 categories: `tool` (generated from OpenAPI), `rag_pipeline` (ingest + retrieve), and `agent` (RAG → tool_filter → LLM loop). Setup fetches Brreg OpenAPI spec and generates tools. Ingestion bulk-downloads all registries, merges per org number, chunks, extracts metadata, embeds summaries, upserts to LanceDB. Query retrieves from vectorstore, reranks, filters tools, runs agent loop.

**Tech Stack:** Python 3.12+, httpx (HTTP/downloads), machine-core plugin system, rag_support (chunkers/extractors/rerankers), embeddings (qwen3-embedding:8b), vectorstore_support (LanceDB), tool_openapi (spec→tools), tool_filter_rag (semantic tool selection), agent_support (AgentDefinition/AgentRunResult schemas).

---

## File Structure

```
machine-plugins/community/agent_brreg_expert/
├── __init__.py           # BrregExpertPlugin class (setup: fetch spec, gen tools, register)
├── manifest.json         # Plugin manifest
├── pyproject.toml        # Package metadata + deps
├── pipeline.py           # BrregPipeline (ingest + retrieve methods)
├── ingestor.py           # Bulk download logic (streaming JSON/CSV)
├── merger.py             # Merge entities + sub-entities + roles per org nr
├── runner.py             # BrregAgentRunner (RAG → tool_filter → LLM loop)
└── tests/
    ├── __init__.py
    ├── test_merger.py    # Unit tests for merge logic
    ├── test_ingestor.py  # Unit tests for download parsing (mocked)
    ├── test_pipeline.py  # Integration tests for pipeline (mocked deps)
    └── test_runner.py    # Integration tests for agent runner (mocked deps)
```

---

### Task 1: Scaffold — manifest.json + pyproject.toml + empty __init__.py

**Files:**
- Create: `community/agent_brreg_expert/manifest.json`
- Create: `community/agent_brreg_expert/pyproject.toml`
- Create: `community/agent_brreg_expert/__init__.py`

- [ ] **Step 1: Create manifest.json**

```json
{
  "name": "agent_brreg_expert",
  "version": "0.1.0",
  "description": "Norwegian companies expert — RAG + live Brreg API tools",
  "schema_version": "1.0.0",
  "language": "python",
  "capabilities": ["agent:register", "rag_pipeline:register", "tool:register"],
  "dependencies": ["tool_openapi", "tool_filter_rag", "rag_support"],
  "hooks_subscribed": {},
  "events_subscribed": [],
  "config_schema": {
    "spec_url": {
      "type": "string",
      "default": "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/openapi.json"
    },
    "vectorstore_table": {
      "type": "string",
      "default": "brreg_companies"
    },
    "retrieve_top_k": {
      "type": "integer",
      "default": 20
    },
    "rerank_top_k": {
      "type": "integer",
      "default": 5
    },
    "tool_filter_top_k": {
      "type": "integer",
      "default": 5
    },
    "model_ref": {
      "type": "string",
      "default": "ollama/gemma4:latest"
    }
  },
  "transport": {
    "type": "in-process",
    "entry_point": "agent_brreg_expert:BrregExpertPlugin"
  }
}
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "agent_brreg_expert"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27"]


[tool.hatch.build.targets.wheel]
packages = ["."]
sources = {"." = "agent_brreg_expert"}


[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Create __init__.py stub**

```python
"""agent-brreg-expert: Norwegian companies expert with RAG + live Brreg API tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class BrregExpertPlugin:
    """Plugin that registers a Brreg RAG pipeline and expert agent."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, **kwargs: Any) -> None:
        self._config = kwargs.get("config", {})

    async def setup(self, ctx: "PluginContext") -> None:
        # TODO: implement in Task 5
        pass

    async def shutdown(self, **kwargs: Any) -> None:
        pass
```

- [ ] **Step 4: Commit**

```bash
git add community/agent_brreg_expert/manifest.json community/agent_brreg_expert/pyproject.toml community/agent_brreg_expert/__init__.py
git commit --no-verify -m "feat(brreg-expert): scaffold plugin with manifest and pyproject"
```

---

### Task 2: Merger — merge entities + sub-entities + roles per org number

**Files:**
- Create: `community/agent_brreg_expert/merger.py`
- Create: `community/agent_brreg_expert/tests/__init__.py`
- Create: `community/agent_brreg_expert/tests/test_merger.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for merger.py — merging Brreg data per org number."""

from agent_brreg_expert.merger import merge_entities


def test_merge_basic():
    """Entities with matching sub-entities and roles are merged."""
    entities = [
        {"organisasjonsnummer": "123456789", "navn": "TestAS", "organisasjonsform": {"kode": "AS"}},
        {"organisasjonsnummer": "987654321", "navn": "AnnetAS", "organisasjonsform": {"kode": "AS"}},
    ]
    sub_entities = [
        {"organisasjonsnummer": "100000001", "overordnetEnhet": "123456789", "navn": "Sub1"},
        {"organisasjonsnummer": "100000002", "overordnetEnhet": "123456789", "navn": "Sub2"},
    ]
    roles = [
        {"organisasjonsnummer": "123456789", "rollegrupper": [{"type": {"kode": "STYR"}, "roller": [{"person": {"navn": {"fornavn": "Ola", "etternavn": "Nord"}}}]}]},
    ]

    result = merge_entities(entities, sub_entities, roles)

    assert len(result) == 2
    test_as = next(r for r in result if r["organisasjonsnummer"] == "123456789")
    assert len(test_as["_underenheter"]) == 2
    assert len(test_as["_roller"]) == 1
    assert test_as["_underenheter"][0]["navn"] == "Sub1"

    annet_as = next(r for r in result if r["organisasjonsnummer"] == "987654321")
    assert annet_as["_underenheter"] == []
    assert annet_as["_roller"] == []


def test_merge_empty():
    """Empty input returns empty."""
    assert merge_entities([], [], []) == []


def test_merge_frivillig():
    """Frivillig data merges onto matching entity."""
    entities = [
        {"organisasjonsnummer": "111111111", "navn": "Forening"},
    ]
    frivillig = [
        {"orgnr": "111111111", "kategori": "Idrett"},
    ]

    result = merge_entities(entities, [], [], frivillig_records=frivillig)

    assert result[0]["_frivillig"] == {"orgnr": "111111111", "kategori": "Idrett"}


def test_merge_parti():
    """Parti data merges onto matching entity."""
    entities = [
        {"organisasjonsnummer": "222222222", "navn": "Partiet"},
    ]
    parti = [
        {"orgnr": "222222222", "partinavn": "Testpartiet"},
    ]

    result = merge_entities(entities, [], [], parti_records=parti)

    assert result[0]["_parti"] == {"orgnr": "222222222", "partinavn": "Testpartiet"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_merger.py -v`
Expected: FAIL with ImportError (merger.py doesn't exist)

- [ ] **Step 3: Implement merger.py**

```python
"""Merge Brreg registry data per organisation number."""

from __future__ import annotations

from typing import Any


def merge_entities(
    entities: list[dict[str, Any]],
    sub_entities: list[dict[str, Any]],
    roles: list[dict[str, Any]],
    frivillig_records: list[dict[str, Any]] | None = None,
    parti_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge sub-entities, roles, frivillig, and parti data onto main entities.

    Args:
        entities: Main entity records from Enhetsregisteret.
        sub_entities: Sub-entity records (have 'overordnetEnhet' linking to parent).
        roles: Role records (keyed by 'organisasjonsnummer').
        frivillig_records: Voluntary org records (keyed by 'orgnr').
        parti_records: Political party records (keyed by 'orgnr').

    Returns:
        List of merged entity dicts with _underenheter, _roller, _frivillig, _parti fields.
    """
    if not entities:
        return []

    # Index sub-entities by parent org number
    sub_by_parent: dict[str, list[dict[str, Any]]] = {}
    for sub in sub_entities:
        parent = sub.get("overordnetEnhet", "")
        if parent:
            sub_by_parent.setdefault(parent, []).append(sub)

    # Index roles by org number
    roles_by_org: dict[str, list[dict[str, Any]]] = {}
    for role_record in roles:
        org_nr = role_record.get("organisasjonsnummer", "")
        if org_nr:
            roles_by_org.setdefault(org_nr, []).append(role_record)

    # Index frivillig by org number
    frivillig_by_org: dict[str, dict[str, Any]] = {}
    if frivillig_records:
        for record in frivillig_records:
            org_nr = record.get("orgnr", "")
            if org_nr:
                frivillig_by_org[org_nr] = record

    # Index parti by org number
    parti_by_org: dict[str, dict[str, Any]] = {}
    if parti_records:
        for record in parti_records:
            org_nr = record.get("orgnr", "")
            if org_nr:
                parti_by_org[org_nr] = record

    # Merge
    merged: list[dict[str, Any]] = []
    for entity in entities:
        org_nr = entity.get("organisasjonsnummer", "")
        doc = {**entity}
        doc["_underenheter"] = sub_by_parent.get(org_nr, [])
        doc["_roller"] = roles_by_org.get(org_nr, [])

        if org_nr in frivillig_by_org:
            doc["_frivillig"] = frivillig_by_org[org_nr]
        if org_nr in parti_by_org:
            doc["_parti"] = parti_by_org[org_nr]

        merged.append(doc)

    return merged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_merger.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add community/agent_brreg_expert/merger.py community/agent_brreg_expert/tests/__init__.py community/agent_brreg_expert/tests/test_merger.py
git commit --no-verify -m "feat(brreg-expert): implement merger — groups sub-entities/roles/frivillig/parti per org"
```

---

### Task 3: Ingestor — bulk download + parse (streaming JSON/CSV)

**Files:**
- Create: `community/agent_brreg_expert/ingestor.py`
- Create: `community/agent_brreg_expert/tests/test_ingestor.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for ingestor.py — bulk download + parse logic."""

import json
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from agent_brreg_expert.ingestor import (
    download_entities,
    download_sub_entities,
    download_roles,
    download_frivillig,
    download_parti,
    parse_json_stream,
    parse_csv_bytes,
)


def test_parse_json_stream():
    """JSON array bytes are parsed into list of dicts."""
    data = json.dumps([
        {"organisasjonsnummer": "123", "navn": "A"},
        {"organisasjonsnummer": "456", "navn": "B"},
    ]).encode()
    result = parse_json_stream(data)
    assert len(result) == 2
    assert result[0]["navn"] == "A"


def test_parse_json_stream_empty():
    """Empty JSON array returns empty list."""
    assert parse_json_stream(b"[]") == []


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


@pytest.mark.asyncio
async def test_download_entities_success():
    """download_entities fetches and parses JSON."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = json.dumps([{"organisasjonsnummer": "999"}]).encode()

    with patch("agent_brreg_expert.ingestor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await download_entities()
        assert len(result) == 1
        assert result[0]["organisasjonsnummer"] == "999"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_ingestor.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement ingestor.py**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_ingestor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add community/agent_brreg_expert/ingestor.py community/agent_brreg_expert/tests/test_ingestor.py
git commit --no-verify -m "feat(brreg-expert): implement ingestor — bulk download with JSON/CSV/ZIP parsing"
```

---

### Task 4: Pipeline — BrregPipeline with ingest() and retrieve()

**Files:**
- Create: `community/agent_brreg_expert/pipeline.py`
- Create: `community/agent_brreg_expert/tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for pipeline.py — BrregPipeline ingest + retrieve."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agent_brreg_expert.pipeline import BrregPipeline


@pytest.fixture
def mock_machine():
    """Create a mock machine with all necessary resolvers."""
    machine = MagicMock()

    # Mock embedder
    embedder = AsyncMock()
    embedder.embed = AsyncMock(return_value=MagicMock(vectors=[[0.1] * 4096]))

    # Mock vectorstore
    vectorstore = AsyncMock()
    vectorstore.upsert = AsyncMock()
    vectorstore.search = AsyncMock(return_value=[
        MagicMock(id="123_0", score=0.9, text='{"navn": "Equinor"}', metadata={"org_nr": "123"}),
        MagicMock(id="456_0", score=0.7, text='{"navn": "DNB"}', metadata={"org_nr": "456"}),
    ])

    # Mock chunker
    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[
        MagicMock(text='{"navn": "TestAS"}', index=0, metadata={}),
    ])

    # Mock extractors
    summary_extractor = AsyncMock()
    summary_extractor.extract = AsyncMock(return_value=MagicMock(summary="TestAS is a Norwegian company."))

    keywords_extractor = AsyncMock()
    keywords_extractor.extract = AsyncMock(return_value=MagicMock(keywords=["technology", "oslo"]))

    # Mock reranker
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(return_value=[
        MagicMock(id="123_0", text='{"navn": "Equinor"}', rerank_score=0.95, metadata={"org_nr": "123"}),
    ])

    def resolve(category, name):
        mapping = {
            ("embedding", "ollama"): embedder,
            ("vector_store", "lancedb"): vectorstore,
            ("chunker", "json"): chunker,
            ("metadata_extractor", "summary"): summary_extractor,
            ("metadata_extractor", "keywords"): keywords_extractor,
            ("reranker", "llm"): reranker,
        }
        return mapping.get((category, name))

    machine.resolve = resolve
    return machine


@pytest.fixture
def config():
    return {
        "vectorstore_table": "brreg_companies",
        "retrieve_top_k": 20,
        "rerank_top_k": 5,
    }


@pytest.mark.asyncio
async def test_retrieve(mock_machine, config):
    """Retrieve embeds query, searches vectorstore, reranks."""
    pipeline = BrregPipeline(machine=mock_machine, config=config)
    results = await pipeline.retrieve(query="Hvem eier Equinor?")

    # Should call embed, search, rerank
    mock_machine.resolve("embedding", "ollama").embed.assert_called_once()
    mock_machine.resolve("vector_store", "lancedb").search.assert_called_once()
    mock_machine.resolve("reranker", "llm").rerank.assert_called_once()
    assert len(results) == 1


@pytest.mark.asyncio
async def test_ingest_processes_merged_docs(mock_machine, config):
    """Ingest downloads, merges, chunks, extracts, embeds, upserts."""
    pipeline = BrregPipeline(machine=mock_machine, config=config)

    # Mock the download functions
    with patch("agent_brreg_expert.pipeline.download_entities", new_callable=AsyncMock) as dl_ent, \
         patch("agent_brreg_expert.pipeline.download_sub_entities", new_callable=AsyncMock) as dl_sub, \
         patch("agent_brreg_expert.pipeline.download_roles", new_callable=AsyncMock) as dl_roles, \
         patch("agent_brreg_expert.pipeline.download_frivillig", new_callable=AsyncMock) as dl_friv, \
         patch("agent_brreg_expert.pipeline.download_parti", new_callable=AsyncMock) as dl_parti:

        dl_ent.return_value = [{"organisasjonsnummer": "123", "navn": "TestAS"}]
        dl_sub.return_value = []
        dl_roles.return_value = []
        dl_friv.return_value = []
        dl_parti.return_value = []

        result = await pipeline.ingest()

        assert result["status"] == "completed"
        assert result["documents_processed"] == 1
        # Vectorstore upsert should have been called
        mock_machine.resolve("vector_store", "lancedb").upsert.assert_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_pipeline.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement pipeline.py**

```python
"""BrregPipeline — ingest + retrieve for Norwegian company data."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from loguru import logger

from embeddings.schemas import EmbeddingRequest
from rag_support.models import RankedResult
from vectorstore_support.schemas import SearchRequest, SearchResult, UpsertRequest

from .ingestor import (
    download_entities,
    download_sub_entities,
    download_roles,
    download_frivillig,
    download_parti,
)
from .merger import merge_entities

# Batch size for upsert operations
UPSERT_BATCH_SIZE = 100


class BrregPipeline:
    """RAG pipeline for Brønnøysundregistrene company data."""

    description = "Norwegian companies RAG pipeline — ingest all Brreg registries, retrieve with reranking"

    def __init__(self, machine: Any, config: dict[str, Any]) -> None:
        self._machine = machine
        self._config = config

    async def ingest(self, **kwargs: Any) -> dict[str, Any]:
        """Full ingestion: download → merge → chunk → extract → embed → upsert."""
        start = time.monotonic()
        table = self._config.get("vectorstore_table", "brreg_companies")

        # Step 1: Download all registries in parallel
        logger.info("brreg-pipeline: starting bulk download...")
        entities, sub_entities, roles, frivillig, parti = await asyncio.gather(
            download_entities(),
            download_sub_entities(),
            download_roles(),
            download_frivillig(),
            download_parti(),
            return_exceptions=True,
        )

        # Handle partial failures
        if isinstance(entities, Exception):
            logger.error("Failed to download entities: {}", entities)
            return {"status": "error", "error": str(entities)}
        if isinstance(sub_entities, Exception):
            logger.warning("Failed to download sub-entities: {}", sub_entities)
            sub_entities = []
        if isinstance(roles, Exception):
            logger.warning("Failed to download roles: {}", roles)
            roles = []
        if isinstance(frivillig, Exception):
            logger.warning("Failed to download frivillig: {}", frivillig)
            frivillig = []
        if isinstance(parti, Exception):
            logger.warning("Failed to download parti: {}", parti)
            parti = []

        # Step 2: Merge per org number
        logger.info("brreg-pipeline: merging {} entities...", len(entities))
        merged_docs = merge_entities(
            entities, sub_entities, roles,
            frivillig_records=frivillig,
            parti_records=parti,
        )
        logger.info("brreg-pipeline: merged into {} documents", len(merged_docs))

        # Step 3: Process each document (chunk → extract → embed → upsert)
        embedder = self._machine.resolve("embedding", "ollama")
        vectorstore = self._machine.resolve("vector_store", "lancedb")
        chunker = self._machine.resolve("chunker", "json")
        summary_extractor = self._machine.resolve("metadata_extractor", "summary")
        keywords_extractor = self._machine.resolve("metadata_extractor", "keywords")

        if not embedder or not vectorstore:
            return {"status": "error", "error": "Missing embedder or vectorstore"}

        docs_processed = 0
        chunks_upserted = 0
        upsert_batch: list[UpsertRequest] = []

        for doc in merged_docs:
            org_nr = doc.get("organisasjonsnummer", "unknown")
            doc_json = json.dumps(doc, ensure_ascii=False, default=str)

            # Chunk
            chunks = chunker.chunk(doc_json) if chunker else [type("C", (), {"text": doc_json, "index": 0, "metadata": {}})()]

            for chunk in chunks:
                chunk_id = f"{org_nr}_{chunk.index}"

                # Extract metadata
                summary_text = ""
                keywords = []
                if summary_extractor:
                    try:
                        meta = await summary_extractor.extract(chunk.text)
                        summary_text = meta.summary or ""
                    except Exception as e:
                        logger.debug("Summary extraction failed for {}: {}", chunk_id, e)

                if keywords_extractor:
                    try:
                        meta = await keywords_extractor.extract(chunk.text)
                        keywords = meta.keywords or []
                    except Exception as e:
                        logger.debug("Keywords extraction failed for {}: {}", chunk_id, e)

                # Embed the summary (or chunk text if no summary)
                embed_text = summary_text if summary_text else chunk.text[:2000]
                try:
                    embed_result = await embedder.embed(EmbeddingRequest(input=embed_text))
                    vector = embed_result.vectors[0]
                except Exception as e:
                    logger.warning("Embedding failed for {}: {}", chunk_id, e)
                    continue

                # Build upsert record
                metadata = {
                    "org_nr": org_nr,
                    "name": doc.get("navn", ""),
                    "keywords": keywords,
                    "kommune": doc.get("forretningsadresse", {}).get("kommune", ""),
                    "naeringskode": doc.get("naeringskode1", {}).get("kode", "") if isinstance(doc.get("naeringskode1"), dict) else "",
                    "type": doc.get("organisasjonsform", {}).get("kode", "") if isinstance(doc.get("organisasjonsform"), dict) else "",
                    "summary": summary_text,
                }

                upsert_batch.append(UpsertRequest(
                    id=chunk_id,
                    vector=vector,
                    text=chunk.text,  # Full JSON — lossless
                    metadata=metadata,
                    table=table,
                ))
                chunks_upserted += 1

                # Flush batch
                if len(upsert_batch) >= UPSERT_BATCH_SIZE:
                    await vectorstore.upsert(upsert_batch)
                    upsert_batch = []

            docs_processed += 1
            if docs_processed % 1000 == 0:
                logger.info("brreg-pipeline: processed {}/{} documents", docs_processed, len(merged_docs))

        # Flush remaining
        if upsert_batch:
            await vectorstore.upsert(upsert_batch)

        duration = time.monotonic() - start
        logger.info(
            "brreg-pipeline: ingestion complete — {} docs, {} chunks in {:.1f}s",
            docs_processed, chunks_upserted, duration,
        )
        return {
            "status": "completed",
            "documents_processed": docs_processed,
            "chunks_upserted": chunks_upserted,
            "duration_seconds": round(duration, 1),
        }

    async def retrieve(self, query: str, **kwargs: Any) -> list[RankedResult]:
        """Retrieve relevant chunks: embed → vector search → rerank."""
        table = self._config.get("vectorstore_table", "brreg_companies")
        retrieve_top_k = self._config.get("retrieve_top_k", 20)
        rerank_top_k = self._config.get("rerank_top_k", 5)

        embedder = self._machine.resolve("embedding", "ollama")
        vectorstore = self._machine.resolve("vector_store", "lancedb")
        reranker = self._machine.resolve("reranker", "llm")

        if not embedder or not vectorstore:
            logger.warning("brreg-pipeline: retrieve called but embedder/vectorstore missing")
            return []

        # Embed query
        embed_result = await embedder.embed(EmbeddingRequest(input=query))
        query_vector = embed_result.vectors[0]

        # Vector search
        candidates: list[SearchResult] = await vectorstore.search(
            SearchRequest(
                query_vector=query_vector,
                top_k=retrieve_top_k,
                table=table,
            )
        )

        if not candidates:
            return []

        # Rerank
        if reranker:
            ranked = await reranker.rerank(query=query, results=candidates)
            return ranked[:rerank_top_k]

        # No reranker — return raw results as RankedResult
        return [
            RankedResult(
                id=c.id,
                text=c.text or "",
                original_score=c.score,
                rerank_score=c.score,
                metadata=c.metadata,
            )
            for c in candidates[:rerank_top_k]
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_pipeline.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add community/agent_brreg_expert/pipeline.py community/agent_brreg_expert/tests/test_pipeline.py
git commit --no-verify -m "feat(brreg-expert): implement BrregPipeline — ingest + retrieve with reranking"
```

---

### Task 5: Runner — BrregAgentRunner (RAG → tool_filter → LLM loop)

**Files:**
- Create: `community/agent_brreg_expert/runner.py`
- Create: `community/agent_brreg_expert/tests/test_runner.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for runner.py — BrregAgentRunner."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agent_brreg_expert.runner import BrregAgentRunner
from agent_support.schemas import AgentDefinition


@pytest.fixture
def mock_machine():
    machine = MagicMock()

    # Mock pipeline (retrieve returns ranked results)
    pipeline = AsyncMock()
    pipeline.retrieve = AsyncMock(return_value=[
        MagicMock(id="123_0", text='{"navn": "Equinor", "organisasjonsnummer": "923609016"}', metadata={"org_nr": "923609016", "summary": "Equinor ASA is a Norwegian energy company"}),
    ])

    # Mock tool filter
    filter_rag = AsyncMock()
    filter_rag.filter = AsyncMock(return_value=[
        MagicMock(id="brreg_hentEnhet", text="brreg_hentEnhet: Get entity by org number", metadata={"name": "brreg_hentEnhet"}),
    ])

    # Mock agent runner (basic)
    basic_runner = AsyncMock()
    basic_runner.run = AsyncMock(return_value=MagicMock(
        agent_name="brreg-expert",
        output="Equinor ASA (org.nr 923609016) har følgende styremedlemmer: ...",
        steps=[],
        duration_ms=1500.0,
    ))

    # Mock tools registry
    tools = {
        "brreg_hentEnhet": MagicMock(name="brreg_hentEnhet", description="Get entity"),
    }

    def resolve(category, name):
        mapping = {
            ("rag_pipeline", "brreg-companies"): pipeline,
            ("tool", "__filter_rag__"): filter_rag,
            ("agent", "basic"): basic_runner,
        }
        return mapping.get((category, name))

    def list_category(category):
        if category == "tool":
            return tools
        return {}

    machine.resolve = resolve
    machine.list_category = list_category
    return machine


@pytest.fixture
def config():
    return {
        "model_ref": "ollama/gemma4:latest",
        "tool_filter_top_k": 5,
        "vectorstore_table": "brreg_companies",
        "retrieve_top_k": 20,
        "rerank_top_k": 5,
    }


@pytest.mark.asyncio
async def test_run_full_flow(mock_machine, config):
    """Runner retrieves, filters tools, delegates to basic agent."""
    runner = BrregAgentRunner(machine=mock_machine, config=config)

    result = await runner.run(
        definition=AgentDefinition(name="brreg-expert", model_ref="ollama/gemma4:latest"),
        input="Hvem sitter i styret til Equinor?",
        tools=[],
    )

    assert result.output is not None
    assert "Equinor" in result.output
    # Pipeline retrieve was called
    mock_machine.resolve("rag_pipeline", "brreg-companies").retrieve.assert_called_once()
    # Tool filter was called
    mock_machine.resolve("tool", "__filter_rag__").filter.assert_called_once()


@pytest.mark.asyncio
async def test_run_empty_rag(mock_machine, config):
    """Runner handles empty RAG results gracefully."""
    mock_machine.resolve("rag_pipeline", "brreg-companies").retrieve.return_value = []
    runner = BrregAgentRunner(machine=mock_machine, config=config)

    result = await runner.run(
        definition=AgentDefinition(name="brreg-expert", model_ref="ollama/gemma4:latest"),
        input="Hva er org nr til Google?",
        tools=[],
    )

    # Should still produce output (agent uses tools)
    assert result.output is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_runner.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement runner.py**

```python
"""BrregAgentRunner — Norwegian companies expert agent."""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from agent_support.schemas import AgentDefinition, AgentRunResult, AgentStep
from tool_support.schemas import ToolDefinition


SYSTEM_PROMPT = """Du er en norsk bedriftsekspert med dyp kunnskap om Brønnøysundregistrene.

Du har tilgang til:
1. Forhåndshentet kontekst fra registrene (vedlagt nedenfor)
2. Live API-verktøy for å hente fersk data fra Brreg

Instruksjoner:
- Svar alltid på norsk med mindre brukeren skriver på engelsk.
- Bruk konteksten først. Hvis den ikke er tilstrekkelig, bruk verktøyene.
- Oppgi alltid organisasjonsnummer når du refererer til en bedrift.
- Vær presis og faktabasert. Ikke gjett.
- Hvis du ikke finner informasjonen, si det tydelig.
"""


class BrregAgentRunner:
    """Agent runner that combines RAG retrieval with live Brreg API tools."""

    description = "Norwegian companies expert — RAG context + live Brreg tools"
    supports_streaming = False
    supports_tools = True

    def __init__(self, machine: Any, config: dict[str, Any]) -> None:
        self._machine = machine
        self._config = config

    async def run(
        self,
        definition: AgentDefinition,
        input: str,
        tools: list[ToolDefinition] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run the brreg-expert agent: RAG retrieve → tool filter → delegate to basic runner."""
        start = time.monotonic()
        steps: list[AgentStep] = []

        # Step 1: RAG Retrieve
        pipeline = self._machine.resolve("rag_pipeline", "brreg-companies")
        rag_results = []
        if pipeline:
            try:
                rag_results = await pipeline.retrieve(query=input)
                steps.append(AgentStep(
                    step_type="rag_retrieve",
                    detail={"results_count": len(rag_results)},
                    duration_ms=(time.monotonic() - start) * 1000,
                ))
            except Exception as e:
                logger.warning("brreg-expert: RAG retrieve failed: {}", e)
                steps.append(AgentStep(step_type="rag_error", detail={"error": str(e)}))

        # Step 2: Tool Filter — select relevant Brreg API tools
        tool_filter_top_k = self._config.get("tool_filter_top_k", 5)
        filter_rag = self._machine.resolve("tool", "__filter_rag__")
        selected_tool_names: list[str] = []

        if filter_rag:
            # Enrich query with RAG context for better tool selection
            context_summaries = [
                r.metadata.get("summary", r.text[:200]) for r in rag_results
            ] if rag_results else []
            enriched_query = input
            if context_summaries:
                enriched_query = f"{input}\n\nContext:\n" + "\n".join(context_summaries[:3])

            try:
                filter_results = await filter_rag.filter(enriched_query, top_k=tool_filter_top_k)
                selected_tool_names = [r.metadata.get("name", r.id) for r in filter_results]
                steps.append(AgentStep(
                    step_type="tool_filter",
                    detail={"selected_tools": selected_tool_names},
                ))
            except Exception as e:
                logger.warning("brreg-expert: tool filter failed: {}", e)

        # Resolve selected tools from registry
        all_tools = self._machine.list_category("tool")
        selected_tools: list[ToolDefinition] = []
        for name in selected_tool_names:
            tool = all_tools.get(name)
            if tool and isinstance(tool, ToolDefinition):
                selected_tools.append(tool)

        # Step 3: Build context block from RAG results
        context_block = ""
        if rag_results:
            chunks = []
            for i, r in enumerate(rag_results, 1):
                org_nr = r.metadata.get("org_nr", "?")
                name = r.metadata.get("name", "") or r.metadata.get("summary", "")
                chunks.append(f"[{i}] Org.nr: {org_nr} | {name}\n{r.text[:3000]}")
            context_block = "\n\n---\n\n".join(chunks)

        # Step 4: Delegate to basic agent runner with enriched prompt
        basic_runner = self._machine.resolve("agent", "basic")
        if not basic_runner:
            return AgentRunResult(
                agent_name="brreg-expert",
                output="Error: no agent runtime available",
                steps=steps,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Build instruction with RAG context injected
        instruction = SYSTEM_PROMPT
        if context_block:
            instruction += f"\n\n## Relevant data fra registrene:\n\n{context_block}"

        enriched_definition = AgentDefinition(
            name="brreg-expert",
            model_ref=definition.model_ref or self._config.get("model_ref", "ollama/gemma4:latest"),
            instruction=instruction,
            max_steps=definition.max_steps or 10,
        )

        result = await basic_runner.run(
            definition=enriched_definition,
            input=input,
            tools=selected_tools,
            context=context,
        )

        # Merge steps
        all_steps = steps + (result.steps or [])
        duration_ms = (time.monotonic() - start) * 1000

        return AgentRunResult(
            agent_name="brreg-expert",
            output=result.output,
            steps=all_steps,
            duration_ms=duration_ms,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/valiantlynx/projects/samletnorge-ai/machine-plugins && uv run pytest community/agent_brreg_expert/tests/test_runner.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add community/agent_brreg_expert/runner.py community/agent_brreg_expert/tests/test_runner.py
git commit --no-verify -m "feat(brreg-expert): implement BrregAgentRunner — RAG + tool_filter + LLM loop"
```

---

### Task 6: Plugin setup — wire everything in __init__.py

**Files:**
- Modify: `community/agent_brreg_expert/__init__.py`

- [ ] **Step 1: Implement the full setup method**

```python
"""agent-brreg-expert: Norwegian companies expert with RAG + live Brreg API tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


async def _fetch_spec(url: str) -> dict[str, Any]:
    """Fetch OpenAPI spec from URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


class BrregExpertPlugin:
    """Plugin that registers a Brreg RAG pipeline and expert agent."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, **kwargs: Any) -> None:
        self._config = kwargs.get("config", {})

    async def setup(self, ctx: "PluginContext") -> None:
        from .pipeline import BrregPipeline
        from .runner import BrregAgentRunner

        spec_url = self._config.get(
            "spec_url",
            "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/openapi.json",
        )

        # 1. Fetch OpenAPI spec and generate tools
        try:
            spec = await _fetch_spec(spec_url)
            tool_generator = ctx._machine.resolve("tool", "__openapi_generator__")
            if tool_generator:
                tools = tool_generator["generate_tools"](spec, spec_url=spec_url)
                logger.info("brreg-expert: generated {} tools from OpenAPI spec", len(tools))

                # 2. Register tools
                for tool in tools:
                    ctx.register("tool", f"brreg_{tool.name}", tool)

                # 3. Index tools in filter_rag
                filter_rag = ctx._machine.resolve("tool", "__filter_rag__")
                if filter_rag:
                    await filter_rag.index_tools(tools)
                    logger.info("brreg-expert: indexed {} tools in filter_rag", len(tools))
            else:
                logger.warning("brreg-expert: tool_openapi not available — no live tools")
        except Exception as e:
            logger.warning("brreg-expert: failed to generate tools from spec: {}", e)

        # 4. Register pipeline
        pipeline = BrregPipeline(machine=ctx._machine, config=self._config)
        ctx.register("rag_pipeline", "brreg-companies", pipeline)

        # 5. Register agent
        runner = BrregAgentRunner(machine=ctx._machine, config=self._config)
        ctx.register("agent", "brreg-expert", runner)

        logger.info("brreg-expert: setup complete — pipeline + agent registered")

    async def shutdown(self, **kwargs: Any) -> None:
        pass
```

- [ ] **Step 2: Verify plugin loads in test project**

Add the plugin to `my-project/pyproject.toml` and run `machine dev` to verify it loads without errors.

Add to `[tool.machine-core]` plugins list:
```toml
"agent_brreg_expert" = {source = "path", path = "../machine-plugins/community/agent_brreg_expert"}
```

Add config:
```toml
[tool.machine-core.plugin_configs.agent-brreg-expert]
spec_url = "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/openapi.json"
vectorstore_table = "brreg_companies"
retrieve_top_k = 20
rerank_top_k = 5
tool_filter_top_k = 5
model_ref = "ollama/gemma4:latest"
```

Run: `cd /home/valiantlynx/projects/samletnorge-ai/my-project && machine dev`
Expected: See "brreg-expert: setup complete" in logs, new routes at `/api/rag_pipeline/brreg-companies/ingest`, `/api/agent/brreg-expert/run`

- [ ] **Step 3: Commit**

```bash
git add community/agent_brreg_expert/__init__.py
git commit --no-verify -m "feat(brreg-expert): wire full setup — spec fetch, tool gen, pipeline + agent registration"
```

---

### Task 7: End-to-end smoke test — verify API endpoints work

**Files:** None (manual verification)

- [ ] **Step 1: Verify routes are registered**

Run: `curl -s http://localhost:8787/api | python -m json.tool | grep brreg`
Expected: See `rag_pipeline/brreg-companies` and `agent/brreg-expert` routes

- [ ] **Step 2: Test retrieve (empty — pre-ingestion)**

```bash
curl -s -X POST http://localhost:8787/api/rag_pipeline/brreg-companies/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "Equinor"}' | python -m json.tool
```
Expected: Empty results (no data ingested yet) — no crash

- [ ] **Step 3: Test agent run (relies on tools only — no RAG data yet)**

```bash
curl -s -X POST http://localhost:8787/api/agent/brreg-expert/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Hva er organisasjonsnummeret til Equinor?"}' | python -m json.tool
```
Expected: Agent uses live Brreg tools to answer (may take a few seconds for LLM)

- [ ] **Step 4: Test small ingestion (optional — only if time/bandwidth allows)**

```bash
curl -s -X POST http://localhost:8787/api/rag_pipeline/brreg-companies/ingest \
  -H "Content-Type: application/json" | python -m json.tool
```
Expected: Returns status with documents_processed count (may take 30+ min for full)

- [ ] **Step 5: Final commit — add plugin to scaffold defaults (optional)**

If working, update `machine-plugins/framework/cli_support/cli_support/scaffolds/pyproject.toml.j2` to include `agent_brreg_expert` as an optional plugin comment.

```bash
git commit --no-verify -m "docs(brreg-expert): end-to-end verification complete"
```

---

## Summary of Commits

1. `feat(brreg-expert): scaffold plugin with manifest and pyproject`
2. `feat(brreg-expert): implement merger — groups sub-entities/roles/frivillig/parti per org`
3. `feat(brreg-expert): implement ingestor — bulk download with JSON/CSV/ZIP parsing`
4. `feat(brreg-expert): implement BrregPipeline — ingest + retrieve with reranking`
5. `feat(brreg-expert): implement BrregAgentRunner — RAG + tool_filter + LLM loop`
6. `feat(brreg-expert): wire full setup — spec fetch, tool gen, pipeline + agent registration`
7. `docs(brreg-expert): end-to-end verification complete`
