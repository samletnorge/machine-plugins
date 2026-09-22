"""Abstract base class for metadata extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MetadataExtractor(ABC):
    """Abstract base for metadata extraction from text."""

    @abstractmethod
    async def extract(self, text: str, **kwargs: object) -> dict[str, Any]:
        """Extract metadata from text.

        Args:
            text: The text to extract metadata from.
            **kwargs: Extractor-specific parameters.

        Returns:
            Dict of extracted metadata key-value pairs.
        """
        ...
