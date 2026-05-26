"""Hookspec names for agent_support plugin."""

HOOKSPECS = {
    "before_agent_run": {"firstresult": False},
    "after_agent_run": {"firstresult": False},
    "on_agent_handoff": {"firstresult": True},
    "on_agent_step": {"firstresult": False},
    "on_agent_error": {"firstresult": False},
}
