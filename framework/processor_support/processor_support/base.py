"""Base types for the processor pipeline.

ProcessorData: the data flowing through the pipeline.
TripWire: abort signal — if any processor returns TripWire, the chain stops.
Processor: ABC that all processors implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Union

from pydantic import BaseModel, Field


class ProcessorData(BaseModel):
    """Data flowing through the processor pipeline.

    Attributes:
        text: The text content being processed (user prompt or agent response).
        metadata: Arbitrary key-value metadata passed along the chain.
    """

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def replace(self, **kwargs: Any) -> ProcessorData:
        """Return a copy with field overrides (immutable update)."""
        return self.model_copy(update=kwargs)


class TripWire(BaseModel):
    """Abort signal for the processor pipeline.

    If any processor returns a TripWire instead of ProcessorData,
    the pipeline immediately stops and the TripWire is returned as
    an error to the caller.

    Attributes:
        processor_name: Name of the processor that triggered the abort.
        reason: Human-readable reason for aborting.
    """

    processor_name: str
    reason: str


# Result type for processor.process()
ProcessorResult = Union[ProcessorData, TripWire]


class Processor(ABC):
    """Abstract base class for all processors.

    Subclass and implement process(). Set name and type.

    Attributes:
        name: Unique processor identifier.
        type: When this processor runs — "input" (before agent), "output"
              (after agent), or "both".
    """

    name: str = "unnamed"
    type: Literal["input", "output", "both"] = "both"

    @abstractmethod
    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Process data. Return ProcessorData to continue or TripWire to abort."""
        ...
