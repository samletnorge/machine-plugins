"""Tests for GraphRAG."""

import pytest
from rag_support.graph import (
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    GraphRAG,
)
from vectorstore_support.schemas import SearchResult


def test_graph_node():
    node = GraphNode(
        id="n1", text="Python", embedding=[1.0, 0.0], metadata={"type": "language"}
    )
    assert node.id == "n1"


def test_graph_edge():
    edge = GraphEdge(source="n1", target="n2", relation="is_a", weight=0.9)
    assert edge.source == "n1"


def test_knowledge_graph_add_and_get():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="n1", text="Python", embedding=[1.0]))
    kg.add_node(GraphNode(id="n2", text="Language", embedding=[0.5]))
    kg.add_edge(GraphEdge(source="n1", target="n2", relation="is_a"))
    assert kg.get_node("n1") is not None
    assert len(kg.get_neighbors("n1")) == 1


def test_knowledge_graph_traverse():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", text="A", embedding=[1.0]))
    kg.add_node(GraphNode(id="b", text="B", embedding=[0.5]))
    kg.add_node(GraphNode(id="c", text="C", embedding=[0.3]))
    kg.add_edge(GraphEdge(source="a", target="b", relation="related"))
    kg.add_edge(GraphEdge(source="b", target="c", relation="related"))
    nodes = kg.traverse("a", max_depth=2)
    assert len(nodes) == 3


class MockEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [hash(text) % 100 / 100.0]

    async def embed_batch(self, texts, **kw):
        return [await self.embed(t) for t in texts]


async def test_graph_rag_build_and_query():
    graph_rag = GraphRAG(embedder=MockEmbedder())
    documents = [
        {"id": "d1", "text": "Python is a programming language."},
        {"id": "d2", "text": "Programming languages include Python and Java."},
        {"id": "d3", "text": "Java runs on JVM."},
    ]
    await graph_rag.build(documents)
    assert len(graph_rag.graph.nodes) > 0
    results = await graph_rag.query("What is Python?", top_k=3)
    assert isinstance(results, list)


def test_empty_graph():
    kg = KnowledgeGraph()
    assert kg.get_node("nonexistent") is None
    assert kg.get_neighbors("nonexistent") == []
    assert kg.traverse("nonexistent") == []
