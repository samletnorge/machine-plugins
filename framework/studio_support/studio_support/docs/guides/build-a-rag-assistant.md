# Build a RAG assistant

You will build an assistant that answers questions from your own documents. It uses
`rag_support` for chunking and retrieval, an embedder, a vector store, and an agent that
calls retrieval as a tool.

## What you need

- The `machine` CLI and a scaffolded project ([Quickstart](../getting-started/quickstart.md)).
- Either Ollama running locally, or a hosted embedding provider.
- A vector store plugin (`vectorstore_lancedb` is in the scaffold).

## 1. Confirm the plugins

The scaffold already includes most of what you need. Ensure these are in
`[tool.machine-core].plugins`:

```toml
plugins = [
    "rag_support",
    "embeddings",
    "vectorstore_support",
    "embeddings_ollama",
    "vectorstore_lancedb",
    "provider_ollama",
    "tool_support",
    "agent_support",
    "agent_runtime_basic",
    "server_support",
    "tool_filter_rag",
]
```

Then:

```bash
uv sync
ollama pull qwen3-embedding:8b
ollama pull llama3.2
```

## 2. Build the RAG pipeline

Create `src/rag.py`:

```python
"""RAG pipeline and retrieval tool for the docs assistant."""
from rag_support.models import IngestDocument
from rag_support.pipeline import RAGPipeline


def build_pipeline(machine) -> RAGPipeline:
    """Assemble a pipeline from whatever the plugins registered."""
    chunker = machine.resolve("chunker", "recursive")
    embedder = machine.resolve("embedding", "ollama")

    stores = machine.list_category("vector_store")
    if not stores:
        raise RuntimeError("No vector_store registered. Add vectorstore_lancedb.")
    vector_store = next(iter(stores.values()))

    # Optional: LLM reranking and metadata extraction, if configured.
    extractors = [
        extractor
        for name in ("title", "keywords")
        if (extractor := machine.resolve("metadata_extractor", name)) is not None
    ]
    reranker = machine.resolve("reranker", "llm")

    return RAGPipeline(
        chunker=chunker,
        extractors=extractors,
        vector_store=vector_store,
        embedder=embedder,
        reranker=reranker,
        table="docs",
    )
```

> **Tip:** `rag_support` registers its LLM-backed components (semantic chunker, rerankers,
> extractors) only when the matching config is present. If `reranker/llm` is `None`, the
> pipeline simply skips reranking. See [RAG](rag.md#optional-llmembedder-backed-components).

## 3. Ingest your documents

Create `scripts/ingest.py`:

```python
import asyncio
from pathlib import Path

from src.main import machine
from src.rag import build_pipeline
from rag_support.models import IngestDocument


async def main():
    await machine.start()
    pipeline = build_pipeline(machine)

    docs = []
    for path in Path("docs").glob("*.md"):
        docs.append(
            IngestDocument(
                id=path.stem,
                text=path.read_text(encoding="utf-8"),
                metadata={"source": str(path)},
            )
        )

    count = await pipeline.ingest(docs)
    print(f"Ingested {count} chunks from {len(docs)} documents")


asyncio.run(main())
```

Put a few markdown files in `docs/` and run:

```bash
uv run python scripts/ingest.py
```

## 4. Expose retrieval as a tool

Add to `src/rag.py`:

```python
from tool_support import tool


def make_retrieval_tool(machine):
    pipeline = build_pipeline(machine)

    @tool(name="search_docs", description="Search the internal documentation for relevant passages.")
    async def search_docs(query: str, top_k: int = 4) -> str:
        results = await pipeline.retrieve(query, top_k=top_k, rerank=True)
        if not results:
            return "No relevant documents found."
        blocks = []
        for r in results:
            text = getattr(r, "text", None) or ""
            score = getattr(r, "score", getattr(r, "rerank_score", 0.0))
            blocks.append(f"[{score:.2f}] {text}")
        return "\n\n".join(blocks)

    return search_docs.__tool_definition__
```

## 5. Wire it into the assistant

Edit `src/main.py`:

```python
@machine.when_ready
async def _register_project_items() -> None:
    from agent_support.schemas import AgentDefinition

    from .agents.example import ExampleAgent
    from .rag import make_retrieval_tool

    search_tool = make_retrieval_tool(machine)
    machine.register("tool", search_tool.name, search_tool)

    docs_agent = AgentDefinition(
        name="docs_assistant",
        description="Answers questions from internal documentation.",
        model_ref="ollama/llama3.2",
        tool_refs=["search_docs"],
        instruction=(
            "You answer questions using the internal documentation. "
            "Always call search_docs first, then answer using only the retrieved passages. "
            "If the passages do not contain the answer, say you do not know."
        ),
    )

    class DocsAgent:
        description = docs_agent.description

        async def run(self, input: str, context=None):
            runtime = machine.resolve("agent", "basic")
            tools = [machine.resolve("tool", "search_docs")]
            result = await runtime.run(docs_agent, input, tools, context)
            return result.output

    machine.register("agent", "docs", DocsAgent())
```

## 6. Ask questions

```bash
machine dev
# then, in another terminal:
curl -s -X POST http://127.0.0.1:8008/api/agent/docs/run \
  -H 'content-type: application/json' \
  -d '"How do I reset my password?"'
```

Or open `/_studio/chat` and pick `docs`.

## 7. Verify retrieval quality

Test the pipeline directly:

```bash
curl -s -X POST http://127.0.0.1:8008/api/rag_pipeline/docs/retrieve \
  -H 'content-type: application/json' \
  -d '{"query": "password reset", "top_k": 5, "rerank": true}'
```

If results are poor:

- try `chunker/markdown` or `chunker/semantic` instead of `recursive`,
- enable `extractor_llm` so chunks carry titles and keywords,
- enable `reranker_llm` and pass `rerank=true`,
- increase `top_k`.

## 8. Register the pipeline for reuse

If you want the HTTP pipeline route too, register it under `rag_pipeline`:

```python
machine.register("rag_pipeline", "docs", build_pipeline(machine))
```

Now `POST /api/rag_pipeline/docs/ingest` and `/retrieve` are available.

## Recap

| Piece | Plugin |
|-------|--------|
| Chunking | `rag_support` |
| Embeddings | `embeddings_ollama` |
| Vector store | `vectorstore_lancedb` |
| Retrieval tool | your `@tool` |
| The answer | `provider_ollama` + `agent_runtime_basic` |

---

**Read next:** [RAG](rag.md) · [Tools](tools.md) · [Build a tool-using agent](build-a-tool-using-agent.md)

**Source:** `community/rag_support/`, `framework/tool_support/`,
`framework/vectorstore_support/`, `community/embeddings_ollama/`.
