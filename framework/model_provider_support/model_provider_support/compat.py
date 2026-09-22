"""Compatibility helpers for reading pydantic-ai run results.

pydantic-ai 1.x/2.x expose ``AgentRunResult.output`` and a ``usage`` object with
``input_tokens`` / ``output_tokens`` / ``total_tokens``. Older code read
``result.data`` and called ``result.usage()`` with ``request_tokens`` /
``response_tokens``, which no longer works. These helpers centralise the correct
access so every provider stays consistent.
"""

from __future__ import annotations

from typing import Any


def agent_run_output(result: Any) -> Any:
    """Return the text/output of a pydantic-ai run result."""
    return getattr(result, "output", None)


def agent_run_usage(result: Any) -> dict[str, int]:
    """Return a token-usage dict from a pydantic-ai run result."""
    usage = getattr(result, "usage", None)
    if usage is None:
        return {}
    return {
        "prompt_tokens": getattr(usage, "input_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "output_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }
