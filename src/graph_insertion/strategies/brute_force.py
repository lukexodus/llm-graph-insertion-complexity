"""
strategies/brute_force.py — STRAT-001
=====================================
BruteForceStrategy: brute-force candidate-narrowing strategy.

Purpose:
  Control / baseline strategy for incremental LLM-driven graph insertion.
  Shortlists every existing node in the graph (except new_name) for pairwise
  relationship evaluation against the newly inserted concept node.
  Expected cost is exactly llm_calls == n_existing per insertion by construction
  (single-call pairwise decision step per D-29).

Decisions:
  - [D-24]: Narrowing-only strategy contract with external shared decision step.
            BruteForceStrategy produces the exhaustive candidate set and makes
            zero direct LLM calls.
  - [D-29]: Pairwise decision step contract. Shortlisting all n_existing nodes
            yields exactly n_existing pairwise calls.
  - [D-38](2): Non-embedding strategy conformance semantics. uses_embeddings = False,
            _embedder stays None, zero embedding activity during setup, shortlist,
            and update.
  - [D-41]: Strategy-aware candidate bound max_candidates(n_existing) returns
            max(0, n_existing), an exact upper bound evaluating to 38,500 total
            calls over the D-35 sweep matrix (6 sizes x 10 trials). Works before setup().

Implementation Details:
  - sorted(): Candidates are sorted ascending to guarantee determinism independent
    of graph node insertion order and PYTHONHASHSEED.
  - scores: Uniform 0.0 tuples matching candidate length (brute force performs no ranking).
  - Stateless: Reads ConceptGraph live without local copies or indexes; on_inserted is a no-op.
"""

from __future__ import annotations

from typing import Any, Optional

from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.strategy import Shortlist


class BruteForceStrategy:
    """Brute-force narrowing strategy shortlisting all existing nodes.

    Attributes
    ----------
    name:
        Strategy identifier string, locked as "brute_force".
    uses_embeddings:
        Always False. The conformance suite uses this flag to flip embedding assertions.
    seed:
        Seed stored for factory shape consistency; unused by the algorithm.
    """

    name: str = "brute_force"
    uses_embeddings: bool = False

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Any = None
        self._last_candidate_count: int = 0

    def setup(self, graph: ConceptGraph, embedder: Any) -> None:
        """Bind strategy to initial graph topology.

        Embedder is accepted for protocol compatibility but discarded.
        self._embedder remains None so insert_node's identity check is bypassed.
        """
        self._graph = graph
        self._embedder = None

    def shortlist(self, new_name: str) -> Shortlist:
        """Return all existing nodes in the graph sorted ascending, excluding new_name.

        Scores are uniform 0.0 since brute force performs no ranking.
        """
        if self._graph is None:
            raise RuntimeError("setup() must be called before shortlist()")

        candidates = tuple(sorted(n for n in self._graph.nodes() if n != new_name))
        scores = tuple(0.0 for _ in candidates)
        self._last_candidate_count = len(candidates)
        return Shortlist(candidates=candidates, scores=scores)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        """No-op: BruteForceStrategy maintains no internal index or cache."""

    def max_candidates(self, n_existing: int) -> int:
        """Return upper bound on candidates shortlisted when graph has n_existing nodes.

        For BruteForceStrategy, all n_existing nodes are shortlisted (exact bound).
        Can be evaluated before setup().
        """
        return max(0, n_existing)

    def config(self) -> dict[str, Any]:
        """Return strategy configuration hyperparameters."""
        return {"seed": self.seed}

    def diagnostics(self) -> dict[str, Any]:
        """Return operational diagnostics for the most recent insertion trial."""
        return {"candidate_count": self._last_candidate_count}
