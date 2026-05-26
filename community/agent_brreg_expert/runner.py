"""BrregAgentRunner — Norwegian companies expert agent."""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

try:
    from agent_support.schemas import AgentDefinition, AgentRunResult, AgentStep
except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class AgentDefinition:
        name: str = ""
        model_ref: str | None = None
        instruction: str | None = None
        max_steps: int | None = None

    @dataclass
    class AgentRunResult:
        agent_name: str = ""
        output: str = ""
        steps: list = field(default_factory=list)
        duration_ms: float = 0.0

    @dataclass
    class AgentStep:
        step_type: str = ""
        detail: dict = field(default_factory=dict)
        duration_ms: float | None = None


try:
    from tool_support.schemas import ToolDefinition
except ImportError:
    ToolDefinition = Any


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
        definition: Any,
        input: str,
        tools: list | None = None,
        context: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run the brreg-expert agent: RAG retrieve -> tool filter -> delegate to basic runner."""
        start = time.monotonic()
        steps: list[AgentStep] = []

        # Step 1: RAG Retrieve
        pipeline = self._machine.resolve("rag_pipeline", "brreg-companies")
        rag_results = []
        if pipeline:
            try:
                rag_results = await pipeline.retrieve(query=input)
                steps.append(
                    AgentStep(
                        step_type="rag_retrieve",
                        detail={"results_count": len(rag_results)},
                        duration_ms=(time.monotonic() - start) * 1000,
                    )
                )
            except Exception as e:
                logger.warning("brreg-expert: RAG retrieve failed: {}", e)
                steps.append(AgentStep(step_type="rag_error", detail={"error": str(e)}))

        # Step 2: Tool Filter — select relevant Brreg API tools
        tool_filter_top_k = self._config.get("tool_filter_top_k", 5)
        filter_rag = self._machine.resolve("tool", "__filter_rag__")
        selected_tool_names: list[str] = []

        if filter_rag:
            # Enrich query with RAG context for better tool selection
            context_summaries = (
                [r.metadata.get("summary", r.text[:200]) for r in rag_results]
                if rag_results
                else []
            )
            enriched_query = input
            if context_summaries:
                enriched_query = f"{input}\n\nContext:\n" + "\n".join(
                    context_summaries[:3]
                )

            try:
                filter_results = await filter_rag.filter(
                    enriched_query, top_k=tool_filter_top_k
                )
                selected_tool_names = [
                    r.metadata.get("name", r.id) for r in filter_results
                ]
                steps.append(
                    AgentStep(
                        step_type="tool_filter",
                        detail={"selected_tools": selected_tool_names},
                    )
                )
            except Exception as e:
                logger.warning("brreg-expert: tool filter failed: {}", e)

        # Resolve selected tools from registry
        all_tools = self._machine.list_category("tool")
        selected_tools: list = []
        for name in selected_tool_names:
            tool = all_tools.get(name)
            if tool is not None:
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
            model_ref=getattr(definition, "model_ref", None)
            or self._config.get("model_ref", "ollama/gemma4:latest"),
            instruction=instruction,
            max_steps=getattr(definition, "max_steps", None) or 10,
        )

        result = await basic_runner.run(
            definition=enriched_definition,
            input=input,
            tools=selected_tools,
            context=context,
        )

        # Merge steps
        all_steps = steps + (getattr(result, "steps", None) or [])
        duration_ms = (time.monotonic() - start) * 1000

        return AgentRunResult(
            agent_name="brreg-expert",
            output=getattr(result, "output", ""),
            steps=all_steps,
            duration_ms=duration_ms,
        )
