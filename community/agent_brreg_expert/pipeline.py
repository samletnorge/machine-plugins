"""BrregPipeline — ingest + retrieve for Norwegian company data."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from loguru import logger

try:
    from embeddings.schemas import EmbeddingRequest
    from rag_support.models import RankedResult
    from vectorstore_support.schemas import SearchRequest, UpsertRequest
except ImportError:
    # Lightweight fallbacks for testing without full framework
    from dataclasses import dataclass, field as dc_field

    @dataclass
    class EmbeddingRequest:  # type: ignore[no-redef]
        input: str | list[str] = ""
        model_ref: str | None = None
        parameters: dict = dc_field(default_factory=dict)

    @dataclass
    class RankedResult:  # type: ignore[no-redef]
        id: str = ""
        text: str = ""
        original_score: float = 0.0
        rerank_score: float = 0.0
        metadata: dict = dc_field(default_factory=dict)

    @dataclass
    class SearchRequest:  # type: ignore[no-redef]
        query_vector: list = dc_field(default_factory=list)
        top_k: int = 10
        table: str = ""

    @dataclass
    class UpsertRequest:  # type: ignore[no-redef]
        id: str = ""
        vector: list = dc_field(default_factory=list)
        text: str = ""
        metadata: dict = dc_field(default_factory=dict)
        table: str = ""


from .ingestor import (
    download_entities,
    download_sub_entities,
    download_roles,
    download_frivillig,
    download_parti,
)
from .merger import merge_entities


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
        embedding_provider = self._config.get("embedding_provider", "ollama")

        # Step 1: Download all registries
        # Download entities first (largest file, ~200MB) to avoid server throttling
        logger.info("brreg-pipeline: starting bulk download...")
        try:
            entities = await download_entities()
        except Exception as e:
            logger.error("Failed to download entities: {}", e)
            return {"status": "error", "error": str(e)}

        # Download remaining in parallel (smaller files)
        sub_entities, roles, frivillig, parti = await asyncio.gather(
            download_sub_entities(),
            download_roles(),
            download_frivillig(),
            download_parti(),
            return_exceptions=True,
        )

        # Handle partial failures
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
        merge_start = time.monotonic()
        merged_docs = merge_entities(
            entities,
            sub_entities,
            roles,
            frivillig_records=frivillig,
            parti_records=parti,
        )
        logger.info(
            "brreg-pipeline: merged into {} documents in {:.1f}s",
            len(merged_docs),
            time.monotonic() - merge_start,
        )

        # Step 3: Process documents in batches (chunk → batch embed → upsert)
        # We use structured metadata from the registry data directly.
        # LLM-based extraction is available but skipped for bulk (too slow at 1M+ docs).
        embedder = self._machine.resolve("embedding", embedding_provider)
        vectorstore = self._machine.resolve("vector_store", "lancedb")
        chunker = self._machine.resolve("chunker", "json")

        if not embedder or not vectorstore:
            return {"status": "error", "error": "Missing embedder or vectorstore"}

        docs_processed = 0
        chunks_upserted = 0
        total_docs = len(merged_docs)

        # Batch settings
        embed_batch_size = self._config.get("embed_batch_size", 4096)
        upsert_batch_size = self._config.get("upsert_batch_size", 1000)
        flush_count = 0

        try:
            from tqdm import tqdm

            progress = tqdm(total=total_docs, desc="Ingesting", unit="doc")
        except ImportError:
            progress = None

        # Accumulate chunks for batch embedding
        pending_texts: list[str] = []
        pending_meta: list[dict] = []

        async def flush_pending() -> None:
            """Embed and upsert a batch of pending chunks."""
            nonlocal chunks_upserted, flush_count
            if not pending_texts:
                return
            flush_count += 1
            batch_size = len(pending_texts)
            embed_start = time.monotonic()
            try:
                embed_result = await embedder.embed(
                    EmbeddingRequest(input=pending_texts)
                )
                vectors = embed_result.vectors
            except Exception as e:
                logger.warning(
                    "Batch embedding failed ({} texts): {}", len(pending_texts), e
                )
                pending_texts.clear()
                pending_meta.clear()
                return
            embed_ms = (time.monotonic() - embed_start) * 1000

            upsert_batch = []
            for i, vec in enumerate(vectors):
                m = pending_meta[i]
                upsert_batch.append(
                    UpsertRequest(
                        id=m["chunk_id"],
                        vector=vec,
                        text=m["text"],
                        metadata=m["metadata"],
                        table=table,
                    )
                )
            chunks_upserted += len(upsert_batch)

            # Upsert in sub-batches
            upsert_start = time.monotonic()
            for j in range(0, len(upsert_batch), upsert_batch_size):
                await vectorstore.upsert(upsert_batch[j : j + upsert_batch_size])
            upsert_ms = (time.monotonic() - upsert_start) * 1000

            docs_per_sec = batch_size / max((embed_ms + upsert_ms) / 1000, 1e-9)
            logger.info(
                "brreg-pipeline: flush {} — texts={}, embed_ms={:.0f}, upsert_ms={:.0f}, throughput={:.1f} chunks/s",
                flush_count,
                batch_size,
                embed_ms,
                upsert_ms,
                docs_per_sec,
            )
            if progress:
                progress.set_postfix(
                    embed_ms=f"{embed_ms:.0f}",
                    upsert_ms=f"{upsert_ms:.0f}",
                    flush=flush_count,
                )

            pending_texts.clear()
            pending_meta.clear()

        for doc in merged_docs:
            org_nr = doc.get("organisasjonsnummer", "unknown")
            doc_json = json.dumps(doc, ensure_ascii=False, default=str)

            # Only chunk if document exceeds 30K chars (~40K token context window)
            # Most company records are 1-5KB, so they stay as a single chunk.
            if chunker and len(doc_json) > 30000:
                chunks = chunker.chunk(doc_json)
            else:
                chunks = [
                    type("C", (), {"text": doc_json, "index": 0, "metadata": {}})()
                ]

            # Extract structured metadata (no LLM needed)
            name = doc.get("navn", "")
            kommune = ""
            addr = doc.get("forretningsadresse")
            if isinstance(addr, dict):
                kommune = addr.get("kommune", "")
            naeringskode = ""
            nk = doc.get("naeringskode1")
            if isinstance(nk, dict):
                naeringskode = nk.get("kode", "")
            org_type = ""
            of = doc.get("organisasjonsform")
            if isinstance(of, dict):
                org_type = of.get("kode", "")

            for chunk in chunks:
                chunk_id = f"{org_nr}_{chunk.index}"
                embed_text = chunk.text[:2000]

                pending_texts.append(embed_text)
                pending_meta.append(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk.text,
                        "metadata": {
                            "org_nr": org_nr,
                            "name": name,
                            "kommune": kommune,
                            "naeringskode": naeringskode,
                            "type": org_type,
                        },
                    }
                )

                if len(pending_texts) >= embed_batch_size:
                    await flush_pending()

            docs_processed += 1
            if progress:
                progress.update(1)
            elif docs_processed % 10000 == 0:
                logger.info(
                    "brreg-pipeline: processed {}/{} documents",
                    docs_processed,
                    total_docs,
                )

        # Flush remaining
        await flush_pending()

        if progress:
            progress.close()

        duration = time.monotonic() - start
        logger.info(
            "brreg-pipeline: ingestion complete — {} docs, {} chunks in {:.1f}s",
            docs_processed,
            chunks_upserted,
            duration,
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
        embedding_provider = self._config.get("embedding_provider", "ollama")

        embedder = self._machine.resolve("embedding", embedding_provider)
        vectorstore = self._machine.resolve("vector_store", "lancedb")
        reranker = self._machine.resolve("reranker", "llm")

        if not embedder or not vectorstore:
            logger.warning(
                "brreg-pipeline: retrieve called but embedder/vectorstore missing"
            )
            return []

        # Embed query
        embed_result = await embedder.embed(EmbeddingRequest(input=query))
        query_vector = embed_result.vectors[0]

        # Vector search
        candidates = await vectorstore.search(
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
