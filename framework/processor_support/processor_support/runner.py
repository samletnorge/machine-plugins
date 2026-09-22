"""ProcessorRunner — sequential processor chain execution.

Runs processors in order, filtering by phase (input/output).
If any processor returns a TripWire, the chain stops immediately.
"""

from __future__ import annotations

from typing import Literal

from loguru import logger

from .base import Processor, ProcessorData, ProcessorResult, TripWire


class ProcessorRunner:
    """Executes a sequential chain of processors.

    Args:
        processors: Ordered list of processors to execute.
    """

    def __init__(self, processors: list[Processor]) -> None:
        self.processors = processors

    async def run(
        self, data: ProcessorData, phase: Literal["input", "output"]
    ) -> ProcessorResult:
        """Run the processor chain for the given phase.

        Args:
            data: The data to process.
            phase: "input" (before agent) or "output" (after agent).

        Returns:
            ProcessorData if all processors passed, or TripWire if aborted.
        """
        current: ProcessorData = data

        for proc in self.processors:
            if not self._should_run(proc, phase):
                continue

            logger.debug(f"Running processor '{proc.name}' (phase={phase})")
            result = await proc.process(current)

            if isinstance(result, TripWire):
                logger.warning(
                    f"TripWire from processor '{proc.name}': {result.reason}"
                )
                return result

            current = result

        return current

    @staticmethod
    def _should_run(proc: Processor, phase: Literal["input", "output"]) -> bool:
        """Check if a processor should run in the given phase."""
        if proc.type == "both":
            return True
        return proc.type == phase
