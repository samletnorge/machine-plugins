"""Tests for metadata extractors."""

import pytest
from rag_support.extractors.base import MetadataExtractor
from rag_support.extractors.title import TitleExtractor
from rag_support.extractors.summary import SummaryExtractor
from rag_support.extractors.keywords import KeywordsExtractor
from rag_support.extractors.questions import QuestionsExtractor


class MockLLM:
    async def generate(self, prompt: str) -> str:
        if "title" in prompt.lower():
            return "Test Document Title"
        if "summary" in prompt.lower() or "summarize" in prompt.lower():
            return "This is a test summary."
        if "keyword" in prompt.lower():
            return "keyword1, keyword2, keyword3"
        if "question" in prompt.lower():
            return "What is this?\nWhy does it matter?\nHow does it work?"
        return "mock response"


@pytest.fixture
def mock_llm():
    return MockLLM()


class TestTitleExtractor:
    def test_is_extractor(self):
        assert issubclass(TitleExtractor, MetadataExtractor)

    async def test_extracts_title(self, mock_llm):
        ext = TitleExtractor(llm=mock_llm)
        result = await ext.extract("This is a document about Python programming.")
        assert "title" in result
        assert isinstance(result["title"], str)
        assert len(result["title"]) > 0

    async def test_fallback_without_llm(self):
        ext = TitleExtractor(llm=None)
        result = await ext.extract("First line of text\nSecond line")
        assert "title" in result


class TestSummaryExtractor:
    def test_is_extractor(self):
        assert issubclass(SummaryExtractor, MetadataExtractor)

    async def test_extracts_summary(self, mock_llm):
        ext = SummaryExtractor(llm=mock_llm)
        result = await ext.extract("Long document text here with many details...")
        assert "summary" in result
        assert isinstance(result["summary"], str)


class TestKeywordsExtractor:
    def test_is_extractor(self):
        assert issubclass(KeywordsExtractor, MetadataExtractor)

    async def test_extracts_keywords(self, mock_llm):
        ext = KeywordsExtractor(llm=mock_llm)
        result = await ext.extract("Python is a programming language used for AI.")
        assert "keywords" in result
        assert isinstance(result["keywords"], list)
        assert len(result["keywords"]) > 0


class TestQuestionsExtractor:
    def test_is_extractor(self):
        assert issubclass(QuestionsExtractor, MetadataExtractor)

    async def test_extracts_questions(self, mock_llm):
        ext = QuestionsExtractor(llm=mock_llm)
        result = await ext.extract("Machine learning is a subset of AI.")
        assert "questions" in result
        assert isinstance(result["questions"], list)
        assert len(result["questions"]) > 0
