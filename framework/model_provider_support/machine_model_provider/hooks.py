"""Hookspec names for model-provider-support plugin."""

HOOKSPECS = {
    "before_model_invoke": {"firstresult": False},
    "after_model_invoke": {"firstresult": False},
    "on_model_error": {"firstresult": False},
}
