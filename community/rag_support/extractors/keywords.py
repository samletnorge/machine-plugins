"""Extract keywords using LLM."""

from __future__ import annotations
from typing import Any
from machine_core.plugins.rag_support.extractors.base import MetadataExtractor


class KeywordsExtractor(MetadataExtractor):
    def __init__(self, llm: Any = None, max_keywords: int = 10) -> None:
        self.llm = llm
        self.max_keywords = max_keywords

    async def extract(self, text: str, **kwargs: object) -> dict[str, Any]:
        if self.llm is None:
            words = text.lower().split()
            unique = list(dict.fromkeys(w for w in words if len(w) > 3))
            return {"keywords": unique[: self.max_keywords]}
        prompt = (
            f"Extract up to {self.max_keywords} keywords from the following text. "
            "Return them as a comma-separated list, nothing else.\n\n"
            f"Text: {text[:2000]}"
        )
        response = await self.llm.generate(prompt)
        keywords = [k.strip() for k in response.split(",") if k.strip()]
        return {"keywords": keywords[: self.max_keywords]}
