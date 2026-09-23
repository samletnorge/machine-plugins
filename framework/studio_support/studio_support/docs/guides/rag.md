# RAG

Retrieval-Augmented Generation lets an agent answer from your own documents. In machine-core
this is a set of composable categories: **chunkers**, **metadata extractors**, **embedders**,
**vector stores**, **rerankers**, and the **RAG pipeline** that wires them together.

## The pieces

| Category | Defined by | Registered by |
|----------|-----------|---------------|
| `chunker` | `rag_support` | `rag_support` (built-ins) |
| `reranker` | `rag_support` | `rag_support` (when configured) |
| `metadata_extractor` | `rag_support` | `rag_support` (when configured) |
| `rag_pipeline` | `rag_support` | `rag_support` / your project |
| `embedding` | `embeddings` | `embeddings_ollama`, `embeddings_google`, ... |
| `vector_store` | `vectorstore_support` | `vectorstore_lancedb`, ... |

## Enable it

```toml
plugins = [
    "rag_support",
    "embeddings",
    "vectorstore_support",
    "embeddings_ollama",        # or embeddings_sentence_transformers / embeddings_google
    "vectorstore_lancedb",
    "provider_ollama",          # if you want LLM-backed reranking/extraction
    "...",
]
```

## Built-in chunkers

`rag_support` always registers these (no dependencies):

| Name | Behavior |
|------|----------|
| `chunker/recursive` | Recursively splits on `\n\n`, `\n`, sentences, words. |
| `chunker/sentence` | Groups sentences. |
| `chunker/token` | Splits by tokenizer tokens (`cl100k_base` by default). |
| `chunker/markdown` | Splits on markdown headers. |
| `chunker/html` | Splits on block tags. |
| `chunker/json` | Splits JSON into items. |
| `chunker/code` | Language-aware splitting (Python supported). |

A `semantic` chunker is registered **only** when an embedding provider is configured.

```python
chunker = machine.resolve("chunker", "recursive")
chunks = chunker.chunk("some long text ...")
# [Chunk(text=..., index=0, metadata={}), ...]
```

## Optional LLM/embedder-backed components

These register only when the matching `[tool.machine-core.plugin_configs.rag_support]` block
is present:

```toml
[tool.machine-core.plugin_configs.rag_support]
semantic_chunker = { provider = "ollama", model = "qwen3-embedding:8b", similarity_threshold = 0.5 }
reranker_llm = { provider = "ollama", model = "llama3.2" }
reranker_cross_encoder = { model = "cross-encoder/ms-marco-MiniLM-L-6-v2" }
extractor_llm = { provider = "ollama", model = "llama3.2" }
```

| Config key | Registers |
|------------|-----------|
| `semantic_chunker` | `chunker/semantic` (resolves an `embedding` provider). |
| `reranker_llm` | `reranker/llm`. |
| `reranker_cross_encoder` | `reranker/cross_encoder` (needs `sentence-transformers`). |
| `extractor_llm` | `metadata_extractor/title`, `summary`, `keywords`, `questions`. |

> **Note:** These use **lazy** provider resolution, so `rag_support` can load before the
> model/embedding providers exist. The first call resolves the provider from the registry.

## Build a pipeline

```python
from rag_support.pipeline import RAGPipeline
from rag_support.models import IngestDocument

pipeline = RAGPipeline(
    chunker=machine.resolve("chunker", "recursive"),
    extractors=[
        machine.resolve("metadata_extractor", "title"),
        machine.resolve("metadata_extractor", "keywords"),
    ] if machine.resolve("metadata_extractor", "title") else [],
    vector_store=machine.resolve("vector_store", "lancedb"),
    embedder=machine.resolve("embedding", "ollama"),
    reranker=machine.resolve("reranker", "llm"),
    table="docs",
)
```

`RAGPipeline` accepts anything with `embed(text)` and `embed_batch(texts)` for the embedder;
`rag_support.adapters.EmbedderAdapter` bridges an `embedding` provider to that interface.

### Ingest

```python
count = await pipeline.ingest([
    IngestDocument(id="doc-1", text="machine-core is a plugin kernel...", metadata={"source": "handbook"}),
])
print(count)   # number of vector documents stored
```

`ingest` runs: **chunk → extract metadata → embed → upsert**. Each stored vector's id is
`"{doc.id}::{chunk.index}"`.

### Retrieve

```python
results = await pipeline.retrieve(query="What is machine-core?", top_k=5, rerank=True)
for r in results:
    print(r.score, r.text)
```

`retrieve` runs: **embed query → vector search → optional rerank**. It returns
`SearchResult` objects (or `RankedResult` when reranked).

## Register a pipeline as a service

Register the pipeline under `rag_pipeline` so the HTTP server and Studio can use it:

```python
@machine.when_ready
async def _register_rag():
    machine.register("rag_pipeline", "docs", pipeline)
```

Operations: `ingest` (POST), `retrieve` (POST), `list` (GET):

```bash
curl -s -X POST http://127.0.0.1:8008/api/rag_pipeline/docs/retrieve \
  -H 'content-type: application/json' \
  -d '{"query": "What is machine-core?", "top_k": 5}'
```

## GraphRAG

For graph-style retrieval:

```python
from rag_support.graph import GraphRAG

graph = GraphRAG(embedder=machine.resolve("embedding", "ollama"), similarity_threshold=0.7)
await graph.build([
    {"id": "a", "text": "..."},
    {"id": "b", "text": "..."},
])
results = await graph.query("...", top_k=5)
```

`GraphRAG` links nodes whose embeddings are similar and traverses neighbors at query time.

## The assistant pattern

Retrieval is most useful when an agent uses it as a tool. Two common approaches:

1. **Retrieval tool.** Wrap `pipeline.retrieve` in a `@tool` so the model decides when to
   search. See [Build a RAG assistant](build-a-rag-assistant.md).
2. **Pre-fetch.** Retrieve `top_k` chunks for the user's message and inject them into the
   agent's instruction before running.

## HTTP routes

| Route | Description |
|-------|-------------|
| `GET /api/chunker` | List chunkers. |
| `POST /api/chunker/{name}/chunk` | Chunk text. |
| `GET /api/reranker` | List rerankers. |
| `POST /api/reranker/{name}/rerank` | Rerank results. |
| `GET /api/metadata_extractor` | List extractors. |
| `POST /api/metadata_extractor/{name}/extract` | Extract metadata. |
| `GET /api/rag_pipeline` | List pipelines. |
| `POST /api/rag_pipeline/{name}/ingest` | Ingest documents. |
| `POST /api/rag_pipeline/{name}/retrieve` | Retrieve chunks. |

---

**Read next:** [Build a RAG assistant](build-a-rag-assistant.md) ·
[Model providers](model-providers.md) · [Memory](memory.md)

**Source:** `community/rag_support/`, `framework/vectorstore_support/`,
`framework/embeddings/`.
