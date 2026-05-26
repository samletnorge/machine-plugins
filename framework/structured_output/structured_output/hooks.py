"""Hookspec names for structured_output plugin."""

HOOKSPECS = {
    "before_generate_object": {"firstresult": False},
    "after_generate_object": {"firstresult": False},
    "on_validation_retry": {"firstresult": False},
}
