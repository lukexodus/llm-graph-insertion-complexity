"""strategies/stub.py — StubNarrowingStrategy implementation.

Provides a minimal deterministic candidate-narrowing strategy for harness testing
and dry runs without external dependencies.
"""

from __future__ import annotations

from typing import Any, Optional

from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.strategy import Embedder, NarrowingStrategy, Shortlist


class StubNarrowingStrategy:
    """Minimal deterministic narrowing strategy for harness testing and dry runs."""

    name: str = "stub_narrowing"
    uses_embeddings: bool = False

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = top_k
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Optional[Embedder] = None

    def setup(self, graph: ConceptGraph, embedder: Any) -> None:
        self._graph = graph
        self._embedder = None

    def shortlist(self, new_name: str) -> Shortlist:
        if not self._graph:
            return Shortlist(candidates=())
        nodes = sorted(self._graph.nodes())
        candidates = tuple(nodes[: self.top_k])
        return Shortlist(candidates=candidates)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        pass

    def config(self) -> dict[str, Any]:
        return {"name": self.name, "top_k": self.top_k}

    def diagnostics(self) -> dict[str, Any]:
        return {}

    def max_candidates(self, n_existing: int) -> int:
        return min(self.top_k, n_existing)
