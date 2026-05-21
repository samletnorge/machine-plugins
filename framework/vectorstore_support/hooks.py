"""Hook specifications for vectorstore-support."""

HOOKSPECS: dict = {
    "before_search": {"firstresult": False},
    "after_search": {"firstresult": False},
    "before_upsert": {"firstresult": False},
    "after_upsert": {"firstresult": False},
}
