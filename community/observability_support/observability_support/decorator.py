"""@traced decorator for user-defined functions."""

from __future__ import annotations

import inspect
import functools
from typing import Any, Callable, TypeVar

from observability_support.tracer import MachineTracer
from observability_support.spans import SpanKind

F = TypeVar("F", bound=Callable[..., Any])


def traced(
    tracer: MachineTracer,
    kind: SpanKind,
    name: str | None = None,
    **span_kwargs: Any,
) -> Callable[[F], F]:
    """Decorator that wraps a sync or async function in a traced span.

    Args:
        tracer: The MachineTracer instance.
        kind: SpanKind for the operation.
        name: Override span name (defaults to function.__name__).
        **span_kwargs: Extra attributes passed to create_span_attributes.
    """

    def decorator(fn: F) -> F:
        span_name = name or fn.__name__

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with tracer.async_span(span_name, kind=kind, **span_kwargs):
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.span(span_name, kind=kind, **span_kwargs):
                    return fn(*args, **kwargs)

            return sync_wrapper  # type: ignore

    return decorator
