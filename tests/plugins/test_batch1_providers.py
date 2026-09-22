"""Integration tests for the LLM provider plugins."""

from tests.conftest import discover_manifests

EXPECTED_PROVIDERS = [
    "provider_ollama",
    "provider_azure_openai",
    "provider_grok",
    "provider_groq",
    "provider_google_gemini",
    "provider_vertex_gemini",
    "provider_vertex_claude",
    "provider_github_copilot",
]


def test_all_llm_providers_discoverable():
    """All 8 LLM provider manifests should be discoverable."""
    manifests = {m.name for m in discover_manifests()}
    for name in EXPECTED_PROVIDERS:
        assert name in manifests, f"Missing manifest: {name}"


async def test_ollama_provider_loads_and_registers(machine_with_all_plugins):
    """The reference provider registers itself under model_provider."""
    assert "ollama" in machine_with_all_plugins.list_category("model_provider")
