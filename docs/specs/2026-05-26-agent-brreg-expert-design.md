# Design Spec: agent-brreg-expert Plugin

**Date:** 2026-05-26  
**Status:** Approved  
**Author:** Drivy  

---

## Overview

A community plugin that provides a **Norwegian companies expert agent** backed by full RAG ingestion of all Brønnøysundregistrene (Brreg) registries plus live API tools.

### What it registers

| Category | Name | Purpose |
|----------|------|---------|
| `rag_pipeline` | `brreg-companies` | Ingestion + retrieval of all Brreg data |
| `agent` | `brreg-expert` | Norwegian companies expert (RAG + live tools) |
| `tool` | `brreg_*` (dynamic) | Auto-generated from Brreg OpenAPI spec |

---

## Plugin Structure

```
machine-plugins/community/agent_brreg_expert/
├── __init__.py           # BrregExpertPlugin — setup(), registers pipeline + agent
├── manifest.json         # capabilities: [agent:register, rag_pipeline:register, tool:register]
├── pipeline.py           # BrregPipeline — ingest() and retrieve() methods
├── ingestor.py           # Bulk download logic (enheter, underenheter, roller, frivillig, parti)
├── merger.py             # Merges entity + sub-entities + roles into per-company JSON docs
├── runner.py             # BrregAgentRunner — the agent loop (RAG → tool_filter → LLM)
└── pyproject.toml        # deps: httpx, tool_openapi, rag_support, etc.
```

---

## Configuration

```toml
[tool.machine-core.plugin_configs.agent-brreg-expert]
spec_url = "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/openapi.json"
vectorstore_table = "brreg_companies"
retrieve_top_k = 20
rerank_top_k = 5
tool_filter_top_k = 5
model_ref = "ollama/gemma4:latest"
```

### Config Schema (manifest.json)

```json
{
  "name": "agent-brreg-expert",
  "version": "0.1.0",
  "capabilities": ["agent:register", "rag_pipeline:register", "tool:register"],
  "config_schema": {
    "spec_url": {
      "type": "string",
      "default": "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/openapi.json",
      "description": "Brreg OpenAPI spec URL"
    },
    "vectorstore_table": {
      "type": "string",
      "default": "brreg_companies",
      "description": "LanceDB table name for company vectors"
    },
    "retrieve_top_k": {
      "type": "integer",
      "default": 20,
      "description": "Number of vectors to retrieve before reranking"
    },
    "rerank_top_k": {
      "type": "integer",
      "default": 5,
      "description": "Number of chunks after reranking"
    },
    "tool_filter_top_k": {
      "type": "integer",
      "default": 5,
      "description": "Number of tools to select per query"
    },
    "model_ref": {
      "type": "string",
      "default": "ollama/gemma4:latest",
      "description": "LLM model reference for the agent"
    }
  }
}
```

---

## Setup Flow

Called once during `machine dev` startup:

```python
async def setup(self, ctx: PluginContext):
    # 1. Fetch OpenAPI spec from Brreg
    spec = await fetch_spec(self._config["spec_url"])

    # 2. Generate tools from spec via tool_openapi
    tool_generator = ctx._machine.resolve("tool", "__openapi_generator__")
    tools = tool_generator["generate_tools"](spec, spec_url="https://data.brreg.no/enhetsregisteret/api")

    # 3. Register generated tools
    for tool in tools:
        ctx.register("tool", f"brreg_{tool.name}", tool)

    # 4. Index tools in tool_filter_rag for semantic selection
    filter_rag = ctx._machine.resolve("tool", "__filter_rag__")
    await filter_rag["index_tools"](tools)

    # 5. Register the RAG pipeline
    ctx.register("rag_pipeline", "brreg-companies", BrregPipeline(machine=ctx._machine, config=self._config))

    # 6. Register the agent
    ctx.register("agent", "brreg-expert", BrregAgentRunner(machine=ctx._machine, config=self._config))
```

---

## Ingestion Flow

**Trigger:** `POST /api/rag_pipeline/brreg-companies/ingest`

### Step 1: Bulk Download (parallel)

| Source | URL Pattern | Format | ~Size |
|--------|-------------|--------|-------|
| Enheter (main entities) | `/enhetsregisteret/api/enheter/lastned` | JSON stream | ~900K records |
| Underenheter (sub-entities) | `/enhetsregisteret/api/underenheter/lastned` | JSON stream | ~1M records |
| Roller (roles/board members) | `/enhetsregisteret/api/roller/totalbestand` | Zipped JSON | all roles |
| Frivillighetsregisteret | `/frivillighetsregisteret/.../totalbestand/csv` | CSV | voluntary orgs |
| Partiregisteret | `/partiregisteret/api/lastned/csv` | CSV | political parties |

### Step 2: Merge per org number

```
For each entity (organisasjonsnummer):
  - Attach sub-entities as _underenheter[] (grouped by overordnetEnhet)
  - Attach roles as _roller[] (grouped by organisasjonsnummer)
  - Merge frivillig data as additional fields on matching orgs
  - Merge parti data as additional fields on matching orgs
```

Output: one merged JSON document per company/organization.

### Step 3: Process each merged document

```
For each merged company doc:
  a. Chunk with JSON chunker (max ~40K tokens per chunk — matching qwen3-embedding:8b's 40K context window)
  b. Extract metadata:
     - keywords extractor → industry terms, location, names
     - summary extractor → natural language summary
  c. Embed the SUMMARY (qwen3-embedding:8b, 4096 dims, 40K context)
  d. Upsert to LanceDB:
     - id: "{org_number}_{chunk_index}"
     - vector: embedded summary (4096 dims)
     - text: FULL JSON (lossless — agent sees everything)
     - metadata: {org_nr, name, keywords[], kommune, naeringskode, type}
```

### Key Design Decision: Embed Summary, Store Full JSON

- **Why embed the summary?** Natural language has better semantic matching. A query "oljeselskap i Stavanger" matches a summary "Equinor ASA is a Norwegian oil company headquartered in Stavanger" much better than raw JSON fields.
- **Why store full JSON in text?** The agent needs lossless access to structured data (org numbers, addresses, roles, NACE codes). Summaries lose detail.
- **40K context window** of qwen3-embedding:8b means summaries can be long and descriptive without truncation concerns.

---

## Query Flow

**Trigger:** `POST /api/agent/brreg-expert/run`  
**Input:** `{"messages": [{"role": "user", "content": "Hvem sitter i styret til Equinor?"}]}`

### Step 1: RAG Retrieve (`pipeline.retrieve`)

```python
async def retrieve(self, query: str) -> list[SearchResult]:
    # 1a. Embed user query
    embedder = self._machine.resolve("embedding", "ollama")
    query_vector = await embedder["embed"](EmbeddingRequest(texts=[query]))

    # 1b. Vector search LanceDB
    vectorstore = self._machine.resolve("vector_store", "lancedb")
    candidates = await vectorstore["search"](SearchRequest(
        table=self._config["vectorstore_table"],
        vector=query_vector.embeddings[0],
        top_k=self._config["retrieve_top_k"],  # 20
    ))

    # 1c. Rerank with LLM reranker
    reranker = self._machine.resolve("reranker", "llm")
    reranked = await reranker["rerank"](RerankerRequest(
        query=query,
        documents=[c.text for c in candidates],
        top_k=self._config["rerank_top_k"],  # 5
    ))

    return reranked
```

### Step 2: Tool Filter (enriched query)

```python
# Combine user question + retrieved context for better tool selection
enriched = f"{query}\n\nContext:\n" + "\n".join(chunk.metadata.get("summary", "") for chunk in rag_results)

filter_rag = self._machine.resolve("tool", "__filter_rag__")
selected_tools = await filter_rag["filter"](enriched, top_k=self._config["tool_filter_top_k"])
```

### Step 3: Agent LLM Loop

```python
# Follows BasicAgentRunner pattern
system_prompt = """Du er en norsk bedriftsekspert. Du har tilgang til data fra Brønnøysundregistrene.
Bruk den vedlagte konteksten for å svare. Hvis konteksten ikke er tilstrekkelig,
bruk verktøyene for å hente fersk data fra Brreg API."""

# Inject RAG context into messages
context_block = format_rag_context(rag_results)
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "system", "content": f"Relevant data:\n{context_block}"},
    *user_messages,
]

# LLM loop with tool calling (max iterations)
result = await agent_loop(
    model_ref=self._config["model_ref"],
    messages=messages,
    tools=selected_tools,
    max_iterations=10,
)
```

---

## API Endpoints (auto-generated by route_generator)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/rag_pipeline/brreg-companies/ingest` | Trigger full ingestion |
| `POST` | `/api/rag_pipeline/brreg-companies/retrieve` | Retrieve relevant chunks |
| `POST` | `/api/agent/brreg-expert/run` | Run the agent (full pipeline) |
| `GET` | `/api/tool/brreg_*` | Individual Brreg API tools (auto-registered) |

---

## Dependencies

```toml
[project]
dependencies = [
    "httpx>=0.27",
    "machine-core",
]
```

No additional deps needed — `tool_openapi`, `rag_support`, `embeddings`, `vectorstore_support` are all resolved from the machine registry at runtime.

---

## Error Handling

- **Ingestion failures**: If a bulk download fails, log error and continue with available data. Partial ingestion is acceptable.
- **Merge conflicts**: If org number appears in multiple registries with conflicting data, prefer Enhetsregisteret as source of truth.
- **Empty vectorstore**: If `retrieve()` is called before `ingest()`, return empty results and log a warning (agent will rely solely on live tools).
- **Tool call failures**: If a Brreg API tool returns error (rate limit, 404), include error context in agent prompt so it can explain to user.

---

## Performance Considerations

- **Ingestion is expensive** (~2M records). Expected time: 30-60 minutes for full ingestion.
- **Incremental updates**: Future enhancement — use Brreg change feeds (`/oppdateringer`) instead of full bulk download.
- **Memory during ingestion**: Stream JSON, don't load all into memory. Process in batches of ~10K orgs.
- **LanceDB dimension lock**: Table must be created fresh with 4096-dim vectors. Delete `./data/lancedb/{table}` if dimension mismatch occurs.

---

## Future Enhancements (out of scope for v0.1)

1. **Incremental ingestion** via change feeds
2. **Multi-language summaries** (Norwegian + English)
3. **Graph relationships** — map ownership chains between companies
4. **Scheduled re-ingestion** — periodic background updates
5. **Confidence scoring** — indicate when RAG context may be stale
