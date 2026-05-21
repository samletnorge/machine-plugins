"""Generate summary using LLM."""

from __future__ import annotations
from typing import Any
from machine_core.plugins.rag_support.extractors.base import MetadataExtractor


class SummaryExtractor(MetadataExtractor):
    def __init__(self, llm: Any = None, max_words: int = 50) -> None:
        self.llm = llm
        self.max_words = max_words

    async def extract(self, text: str, **kwargs: object) -> dict[str, Any]:
        if self.llm is None:
            return {"summary": text[:200].strip()}
        prompt = (
            f"Summarize the following text in at most {self.max_words} words. "
            "Return ONLY the summary.\n\n"
            f"Text: {text[:3000]}"
        )
        summary = await self.llm.generate(prompt)
        return {"summary": summary.strip()}
