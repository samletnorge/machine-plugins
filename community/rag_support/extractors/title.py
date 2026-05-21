"""Extract document title using LLM."""

from __future__ import annotations
from typing import Any
from machine_core.plugins.rag_support.extractors.base import MetadataExtractor


class TitleExtractor(MetadataExtractor):
    def __init__(self, llm: Any = None) -> None:
        self.llm = llm

    async def extract(self, text: str, **kwargs: object) -> dict[str, Any]:
        if self.llm is None:
            first_line = text.strip().split("\n")[0][:100]
            return {"title": first_line}
        prompt = (
            "Extract or generate a concise title for the following text. "
            "Return ONLY the title, nothing else.\n\n"
            f"Text: {text[:2000]}"
        )
        title = await self.llm.generate(prompt)
        return {"title": title.strip()}
