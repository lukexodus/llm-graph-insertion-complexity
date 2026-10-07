"""
strategies/null.py — INFRA-005
===============================
NullStrategy: random-k shortlist candidate-narrowing strategy.

Purpose:
  Lower-bound control and harness exit-criterion test.
  Selects k distinct existing nodes uniformly at random (no embeddings, no LLM
  during shortlisting). Passes candidates to the shared decision step, producing
  exactly k LLM calls per insertion (or fewer when fewer than k nodes exist).

Decisions:
  - [D-38](1): NullStrategy definition, k=1 default, random shortlist semantics.
  - Draws from sorted(graph.nodes()) to be PYTHONHASHSEED-independent.
  - Re-seeds random.Random(seed) on each shortlist() call so that result depends
    only on (seed, graph state), not call history.
"""

from __future__ import annotations

import random
from typing import Any, Optional

from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.strategy import Shortlist


class NullStrategy:
    """Trivial random-k narrowing strategy for harness testing and lower-bound baseline.

    Selects up to k existing nodes uniformly at random from the graph,
    excluding the new node. Uses no embeddings and makes no LLM calls
    during shortlisting.

    Attributes
    ----------
    name:
        Strategy identifier string, registered as "null".
    uses_embeddings:
        Always False. The conformance suite uses this flag to flip embedding assertions.
    seed:
        Random seed for reproducible shortlisting.
    k:
        Maximum number of candidates to shortlist per insertion (default 1).
    """

    name: str = "null"
    uses_embeddings: bool = False

    def __init__(self, seed: int = 42, k: int = 1) -> None:
        self.seed = seed
        self.k = k
        self._graph: Optional[ConceptGraph] = None
        # _embedder is intentionally never set (remains None).
        # insert_node skips the identity check when _embedder is None.
        self._embedder = None

    def setup(self, graph: ConceptGraph, embedder: Any) -> None:
        """Bind strategy to the initial graph. Embedder is accepted but not stored.

        Parameters
        ----------
        graph:
            The current ConceptGraph (read-only reference; strategy must not mutate it).
        embedder:
            Accepted for protocol compatibility but intentionally discarded.
            self._embedder remains None.
        """
        self._graph = graph
        # Deliberately NOT: self._embedder = embedder
        # This is the contract for non-embedding strategies.

    def shortlist(self, new_name: str) -> Shortlist:
        """Return up to k distinct existing nodes sampled uniformly at random.

        Samples from sorted(graph.nodes()) for PYTHONHASHSEED independence.
        Re-seeded per call so result depends only on (seed, graph contents, new_name),
        not on call order.

        Parameters
        ----------
        new_name:
            The concept name being inserted (excluded from candidates).
        """
        assert self._graph is not None, "setup() must be called before shortlist()"
        existing = [n for n in sorted(self._graph.nodes()) if n != new_name]
        if not existing:
            return Shortlist(candidates=(), scores=())
        rng = random.Random(self.seed)
        selected = rng.sample(existing, min(self.k, len(existing)))
        # Scores: uniform 0.0 (null strategy has no meaningful ranking)
        return Shortlist(
            candidates=tuple(selected),
            scores=tuple(0.0 for _ in selected),
        )

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        """No-op: NullStrategy carries no internal index to update."""

    def config(self) -> dict[str, Any]:
        """Return strategy configuration hyperparameters."""
        return {"seed": self.seed, "k": self.k}

    def diagnostics(self) -> dict[str, Any]:
        """Return operational diagnostics for the most recent shortlist call."""
        n = len(list(self._graph.nodes())) if self._graph is not None else 0
        return {"k": self.k, "candidate_count": n}

    def max_candidates(self, n_existing: int) -> int:
        """Return the maximum number of candidates this strategy will shortlist given n_existing nodes.

        For NullStrategy, at most min(k, n_existing) candidates are shortlisted.
        """
        return min(self.k, n_existing)
