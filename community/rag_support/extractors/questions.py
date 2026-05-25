"""Generate potential questions using LLM."""

from __future__ import annotations
from typing import Any
from rag_support.extractors.base import MetadataExtractor


class QuestionsExtractor(MetadataExtractor):
    def __init__(self, llm: Any = None, max_questions: int = 5) -> None:
        self.llm = llm
        self.max_questions = max_questions

    async def extract(self, text: str, **kwargs: object) -> dict[str, Any]:
        if self.llm is None:
            return {"questions": []}
        prompt = (
            f"Generate up to {self.max_questions} questions that the following text could answer. "
            "Return one question per line, nothing else.\n\n"
            f"Text: {text[:2000]}"
        )
        response = await self.llm.generate(prompt)
        questions = [q.strip() for q in response.strip().splitlines() if q.strip()]
        return {"questions": questions[: self.max_questions]}
