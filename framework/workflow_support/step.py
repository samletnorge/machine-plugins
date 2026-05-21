"""Step primitives for workflow execution."""

from __future__ import annotations

import enum
from typing import Any, Callable

from pydantic import BaseModel


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepContext(BaseModel):
    """Context passed to every step function at execution time."""

    model_config = {"arbitrary_types_allowed": True}

    input_data: Any
    state: dict[str, Any]
    previous_output: Any | None = None
    machine: Any | None = None


class Step:
    """A single executable unit in a workflow."""

    def __init__(
        self,
        fn: Callable,
        name: str,
        input_schema: type[BaseModel],
        output_schema: type[BaseModel],
    ) -> None:
        self.fn = fn
        self.name = name
        self.input_schema = input_schema
        self.output_schema = output_schema

    async def execute(self, ctx: StepContext) -> BaseModel:
        """Run the step function and validate its output."""
        result = await self.fn(ctx)
        if not isinstance(result, self.output_schema):
            raise TypeError(
                f"Step '{self.name}' output must be {self.output_schema.__name__}, "
                f"got {type(result).__name__}"
            )
        return result

    def __repr__(self) -> str:
        return f"Step(name={self.name!r})"


def step(
    fn: Callable | None = None,
    *,
    name: str | None = None,
    input_schema: type[BaseModel],
    output_schema: type[BaseModel],
) -> Step | Callable[..., Step]:
    """Decorator to create a Step from an async function."""

    def decorator(f: Callable) -> Step:
        step_name = name if name is not None else f.__name__
        return Step(
            fn=f, name=step_name, input_schema=input_schema, output_schema=output_schema
        )

    if fn is not None:
        return decorator(fn)
    return decorator
