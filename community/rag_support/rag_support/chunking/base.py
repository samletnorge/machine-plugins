"""Abstract base class for text chunkers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rag_support.models import Chunk


class Chunker(ABC):
    """Abstract base for all chunking strategies.

    Subclasses implement chunk() to split text into a list of Chunk objects.
    """

    @abstractmethod
    def chunk(self, text: str, **kwargs: object) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: The text to chunk.
            **kwargs: Strategy-specific parameters.

        Returns:
            Ordered list of Chunk objects.
        """
        ...
