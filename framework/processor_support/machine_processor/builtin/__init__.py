"""Built-in processors for common use cases.

Imports are lazy to allow incremental development — each processor
is imported only when accessed.
"""


def __getattr__(name):
    """Lazy import built-in processors."""
    _imports = {
        "PIIProcessor": ".pii",
        "ModerationProcessor": ".moderation",
        "PromptInjectionProcessor": ".prompt_injection",
        "TokenLimiterProcessor": ".token_limiter",
        "CostGuardProcessor": ".cost_guard",
        "RegexFilterProcessor": ".regex_filter",
        "ToolSearchProcessor": ".tool_search",
        "CacheProcessor": ".cache",
    }
    if name in _imports:
        import importlib

        module = importlib.import_module(_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PIIProcessor",
    "ModerationProcessor",
    "PromptInjectionProcessor",
    "TokenLimiterProcessor",
    "CostGuardProcessor",
    "RegexFilterProcessor",
    "ToolSearchProcessor",
    "CacheProcessor",
]
