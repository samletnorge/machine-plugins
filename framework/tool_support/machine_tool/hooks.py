"""Hookspec names for tool-support plugin."""

HOOKSPECS = {
    "before_tool_call": {"firstresult": False},
    "after_tool_call": {"firstresult": False},
    "on_tool_error": {"firstresult": False},
}
