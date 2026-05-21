"""GraphRAG -- graph-aware retrieval with semantic edges.

Builds a knowledge graph from documents where:
- Nodes = document chunks
- Edges = semantic similarity above a threshold

Query: embed query -> find nearest nodes -> traverse edges for context.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from machine_core.plugins.vectorstore_support.schemas import SearchResult


class GraphNode(BaseModel):
    id: str
    text: str
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str = "related"
    weight: float = 1.0


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._edges: list[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)
        self._adjacency[edge.source].append(edge.target)
        self._adjacency[edge.target].append(edge.source)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> list[GraphNode]:
        neighbor_ids = self._adjacency.get(node_id, [])
        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def traverse(self, start_id: str, max_depth: int = 2) -> list[GraphNode]:
        if start_id not in self.nodes:
            return []
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(start_id, 0)]
        result: list[GraphNode] = []
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                result.append(node)
            if depth < max_depth:
                for neighbor_id in self._adjacency.get(node_id, []):
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, depth + 1))
        return result


class GraphRAG:
    def __init__(
        self,
        embedder: Any,
        similarity_threshold: float = 0.7,
        max_traverse_depth: int = 2,
    ) -> None:
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.max_traverse_depth = max_traverse_depth
        self.graph = KnowledgeGraph()

    async def build(self, documents: list[dict[str, str]]) -> None:
        if not documents:
            return
        texts = [d["text"] for d in documents]
        embeddings = await self.embedder.embed_batch(texts)
        for doc, emb in zip(documents, embeddings):
            self.graph.add_node(
                GraphNode(
                    id=doc["id"],
                    text=doc["text"],
                    embedding=emb,
                    metadata={k: v for k, v in doc.items() if k not in ("id", "text")},
                )
            )
        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                sim = self._cosine_sim(embeddings[i], embeddings[j])
                if sim >= self.similarity_threshold:
                    self.graph.add_edge(
                        GraphEdge(
                            source=documents[i]["id"],
                            target=documents[j]["id"],
                            relation="semantic_similarity",
                            weight=sim,
                        )
                    )
        logger.info(
            f"GraphRAG built: {len(self.graph.nodes)} nodes, {len(self.graph._edges)} edges"
        )

    async def query(self, query_text: str, top_k: int = 5) -> list[SearchResult]:
        if not self.graph.nodes:
            return []
        query_embedding = await self.embedder.embed(query_text)
        scored: list[tuple[str, float]] = []
        for node_id, node in self.graph.nodes.items():
            if node.embedding:
                sim = self._cosine_sim(query_embedding, node.embedding)
                scored.append((node_id, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        seeds = scored[: max(1, top_k // 2)]
        seen: set[str] = set()
        results: list[SearchResult] = []
        for seed_id, seed_score in seeds:
            traversed = self.graph.traverse(seed_id, max_depth=self.max_traverse_depth)
            for node in traversed:
                if node.id in seen:
                    continue
                seen.add(node.id)
                score = (
                    self._cosine_sim(query_embedding, node.embedding)
                    if node.embedding
                    else 0.0
                )
                results.append(
                    SearchResult(
                        id=node.id,
                        text=node.text,
                        score=score,
                        metadata=node.metadata,
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
