"""Response cache processor.

Caches processor pipeline outputs keyed by input text hash, with TTL expiry.
Intended to be used as an output processor — caches agent responses.
Can also be used as input processor to short-circuit repeated requests.
"""

from __future__ import annotations

import hashlib
import time

from ..base import Processor, ProcessorData, ProcessorResult


class CacheProcessor(Processor):
    """Cache responses with TTL-based expiry.

    Args:
        ttl_seconds: Time-to-live in seconds for cached entries.
    """

    name = "cache"
    type = "both"

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, ProcessorData]] = {}

    def _hash_key(self, text: str) -> str:
        """Create a hash key from input text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def store(self, text: str, data: ProcessorData) -> None:
        """Manually store a cached response."""
        key = self._hash_key(text)
        self._cache[key] = (time.monotonic(), data)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Check cache. Return cached data if hit, otherwise pass through."""
        key = self._hash_key(data.text)

        if key in self._cache:
            stored_time, cached_data = self._cache[key]
            if (time.monotonic() - stored_time) <= self.ttl_seconds:
                new_meta = {**cached_data.metadata, "cache_hit": True}
                return cached_data.replace(metadata=new_meta)
            else:
                # Expired
                del self._cache[key]

        return data
