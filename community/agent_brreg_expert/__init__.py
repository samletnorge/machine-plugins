"""agent-brreg-expert: Norwegian companies expert with RAG + live Brreg API tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class BrregExpertPlugin:
    """Plugin that registers a Brreg RAG pipeline and expert agent."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    async def initialize(self, **kwargs: Any) -> None:
        self._config = kwargs.get("config", {})

    async def setup(self, ctx: "PluginContext") -> None:
        """Wire up: fetch OpenAPI spec → generate tools → index → register pipeline + agent."""
        machine = ctx._machine
        config = self._config

        spec_url = config.get(
            "spec_url",
            "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/openapi.json",
        )

        # --- 1. Fetch OpenAPI spec and generate tools ---
        tools = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(spec_url)
                resp.raise_for_status()
                spec_dict = resp.json()

            generator = machine.resolve("tool", "__openapi_generator__")
            if generator:
                tools = generator["generate_tools"](spec_dict, spec_url=spec_url)
                logger.info(
                    "brreg-expert: generated {} tools from OpenAPI spec", len(tools)
                )
            else:
                logger.warning(
                    "brreg-expert: tool_openapi not available, no live tools"
                )
        except Exception as e:
            logger.error("brreg-expert: failed to fetch/parse OpenAPI spec: {}", e)

        # --- 2. Register each generated tool ---
        for tool in tools:
            ctx.register("tool", f"brreg_{tool.name}", tool)

        # --- 3. Index tools in the RAG filter (skip if already indexed) ---
        filter_rag = machine.resolve("tool", "__filter_rag__")
        if filter_rag and tools:
            try:
                # Check if tools are already indexed by searching for a known tool
                test_results = await filter_rag.filter("hentEnhet", top_k=1)
                if test_results:
                    logger.info(
                        "brreg-expert: tools already indexed, skipping re-index"
                    )
                else:
                    await filter_rag.index_tools(tools)
                    logger.info("brreg-expert: indexed {} tools in filter", len(tools))
            except Exception:
                # First time or error — index
                try:
                    await filter_rag.index_tools(tools)
                    logger.info("brreg-expert: indexed {} tools in filter", len(tools))
                except Exception as e:
                    logger.warning("brreg-expert: tool indexing failed: {}", e)

        # --- 4. Register RAG pipeline ---
        from .pipeline import BrregPipeline

        pipeline = BrregPipeline(machine=machine, config=config)
        ctx.register("rag_pipeline", "brreg-companies", pipeline)

        # --- 5. Register agent runner ---
        from .runner import BrregAgentRunner

        runner = BrregAgentRunner(machine=machine, config=config)
        ctx.register("agent", "brreg-expert", runner)

        logger.info(
            "brreg-expert: setup complete (tools={}, pipeline=✓, agent=✓)", len(tools)
        )

    async def shutdown(self, **kwargs: Any) -> None:
        pass
