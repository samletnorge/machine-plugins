"""Tests for runner.py — BrregAgentRunner."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agent_brreg_expert.runner import BrregAgentRunner


@pytest.fixture
def mock_machine():
    machine = MagicMock()

    # Mock pipeline (retrieve returns ranked results)
    pipeline = AsyncMock()
    pipeline.retrieve = AsyncMock(
        return_value=[
            MagicMock(
                id="123_0",
                text='{"navn": "Equinor", "organisasjonsnummer": "923609016"}',
                metadata={
                    "org_nr": "923609016",
                    "summary": "Equinor ASA is a Norwegian energy company",
                },
            ),
        ]
    )

    # Mock tool filter
    filter_rag = AsyncMock()
    filter_rag.filter = AsyncMock(
        return_value=[
            MagicMock(
                id="brreg_hentEnhet",
                text="brreg_hentEnhet: Get entity by org number",
                metadata={"name": "brreg_hentEnhet"},
            ),
        ]
    )

    # Mock agent runner (basic)
    basic_runner = AsyncMock()
    basic_runner.run = AsyncMock(
        return_value=MagicMock(
            agent_name="brreg-expert",
            output="Equinor ASA (org.nr 923609016) har følgende styremedlemmer: ...",
            steps=[],
            duration_ms=1500.0,
        )
    )

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
        definition=MagicMock(
            name="brreg-expert", model_ref="ollama/gemma4:latest", max_steps=10
        ),
        input="Hvem sitter i styret til Equinor?",
        tools=[],
    )

    assert result.output is not None
    assert "Equinor" in result.output
    # Pipeline retrieve was called
    mock_machine.resolve(
        "rag_pipeline", "brreg-companies"
    ).retrieve.assert_called_once()
    # Tool filter was called
    mock_machine.resolve("tool", "__filter_rag__").filter.assert_called_once()
    # Basic runner was called
    mock_machine.resolve("agent", "basic").run.assert_called_once()


@pytest.mark.asyncio
async def test_run_empty_rag(mock_machine, config):
    """Runner handles empty RAG results gracefully."""
    mock_machine.resolve("rag_pipeline", "brreg-companies").retrieve.return_value = []
    runner = BrregAgentRunner(machine=mock_machine, config=config)

    result = await runner.run(
        definition=MagicMock(
            name="brreg-expert", model_ref="ollama/gemma4:latest", max_steps=10
        ),
        input="Hva er org nr til Google?",
        tools=[],
    )

    # Should still produce output (agent uses tools)
    assert result.output is not None


@pytest.mark.asyncio
async def test_run_no_pipeline(mock_machine, config):
    """Runner works even if pipeline is not yet registered."""
    original_resolve = mock_machine.resolve

    def resolve_no_pipeline(category, name):
        if category == "rag_pipeline":
            return None
        return original_resolve(category, name)

    mock_machine.resolve = resolve_no_pipeline

    runner = BrregAgentRunner(machine=mock_machine, config=config)
    result = await runner.run(
        definition=MagicMock(
            name="brreg-expert", model_ref="ollama/gemma4:latest", max_steps=10
        ),
        input="Test query",
        tools=[],
    )
    assert result.output is not None
