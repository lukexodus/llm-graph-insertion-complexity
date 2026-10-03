"""
strategy.py — INFRA-002
=======================
Strategy interface contract, data structures, and shared insertion driver.

Decisions:
  - Narrowing-only strategy contract with external shared decision step ([D-24]).
  - Timing and metrics accounting model ([D-25]).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from graph_insertion.embedding import Embedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph, _validate_concept_name


@dataclass(frozen=True)
class Shortlist:
    """The shortlisted candidate nodes produced by a narrowing strategy.

    Attributes
    ----------
    candidates:
        Tuple of existing concept names from the graph, ordered by strategy preference.
        Must not contain duplicates, must be a subset of existing graph nodes,
        and must exclude the new node.
    scores:
        Optional tuple of matching similarity/relevance scores corresponding to candidates.
    """
    candidates: tuple[str, ...]
    scores: Optional[tuple[float, ...]] = None


@dataclass(frozen=True)
class DecisionOutcome:
    """Outcome of the shared decision step.

    Attributes
    ----------
    edges:
        Tuple of canonical (prereq, dependent) edges decided by the LLM ([D-23]).
        Each edge must involve the newly inserted node.
    llm_calls:
        Number of LLM API calls executed during this decision step.
    llm_seconds:
        Cumulative wall-clock time spent awaiting LLM responses.
    """
    edges: tuple[tuple[str, str], ...]
    llm_calls: int
    llm_seconds: float


@dataclass(frozen=True)
class InsertionMetrics:
    """Timing and resource metrics recorded for a single node insertion.

    Attributes
    ----------
    n_before:
        Number of nodes in the graph before insertion.
    shortlist_size:
        Number of candidate concepts shortlisted.
    llm_calls:
        Total LLM API calls executed during the decision step.
    embedding_calls:
        Number of embedding calls made during narrowing.
    embed_s:
        Wall-clock seconds spent generating embeddings during narrowing.
    shortlist_s:
        Total wall-clock seconds for candidate narrowing (includes embed_s).
    decide_s:
        Wall-clock seconds spent in the shared decision step.
    update_s:
        Wall-clock seconds spent updating the strategy's internal index (on_inserted).
    total_s:
        Total end-to-end wall-clock seconds for the insertion operation.
    extra:
        Arbitrary diagnostic metadata emitted by the strategy (e.g. comparisons, bucket id).
    """
    n_before: int
    shortlist_size: int
    llm_calls: int
    embedding_calls: int
    embed_s: float
    shortlist_s: float
    decide_s: float
    update_s: float
    total_s: float
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InsertionResult:
    """Complete result of inserting a new concept into the graph.

    Attributes
    ----------
    new_name:
        Canonical concept name inserted.
    shortlist:
        Shortlist of candidate concepts evaluated.
    edges:
        Canonical edges (prereq, dependent) established in the graph.
    metrics:
        Timing and resource measurements for this insertion trial.
    """
    new_name: str
    shortlist: Shortlist
    edges: tuple[tuple[str, str], ...]
    metrics: InsertionMetrics


@runtime_checkable
class DecisionStep(Protocol):
    """Protocol for the shared LLM decision step (implemented outside strategies)."""

    def decide(
        self,
        new_name: str,
        candidates: tuple[str, ...],
        domain_context: Optional[str] = None,
    ) -> DecisionOutcome:
        """Decide prerequisite relationships between new_name and candidates."""
        ...


@runtime_checkable
class NarrowingStrategy(Protocol):
    """Protocol for candidate-narrowing strategies."""

    name: str

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        """Bind strategy to initial graph topology and build internal index.

        Untimed (pre-trial preparation). Strategies read graph but must NOT mutate it.
        """
        ...

    def shortlist(self, new_name: str) -> Shortlist:
        """Produce a shortlist of candidate concepts for new_name.

        Precondition: new_name is not already present in the graph.
        Must not mutate the graph.
        """
        ...

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        """Notify strategy that new_name and edges have been committed to the graph.

        Allows the strategy to incrementally update internal embeddings/indexes/buckets.
        """
        ...

    def config(self) -> dict[str, Any]:
        """Return strategy configuration hyperparameters for reporting."""
        ...

    def diagnostics(self) -> dict[str, Any]:
        """Return operational diagnostics for the most recent insertion trial."""
        ...


def insert_node(
    strategy: NarrowingStrategy,
    graph: ConceptGraph,
    decision_step: DecisionStep,
    new_name: str,
    metered_embedder: Optional[MeteredEmbedder] = None,
) -> InsertionResult:
    """Execute the canonical end-to-end insertion pipeline for a new concept.

    Sequences:
      1. Precondition checks: validate new_name format and ensure it does not already exist.
      2. Candidate narrowing: strategy.shortlist(new_name).
      3. Shared decision step: decision_step.decide(new_name, shortlist).
      4. Graph mutation: add new_name and canonical edges to ConceptGraph.
      5. Incremental index update: strategy.on_inserted(new_name, edges).
      6. Metrics gathering and return.

    Parameters
    ----------
    strategy:
        The candidate-narrowing strategy under test.
    graph:
        The in-memory ConceptGraph to insert into.
    decision_step:
        The shared decision-making step.
    new_name:
        The bare concept name string to insert.
    metered_embedder:
        Optional MeteredEmbedder for tracking embedding time and calls during narrowing.

    Returns
    -------
    InsertionResult
        Structured outcome containing inserted node, shortlist, edges, and full metrics.
    """
    _validate_concept_name(new_name)
    if graph.has_node(new_name):
        raise ValueError(f"Node {new_name!r} already exists in graph.")

    n_before = graph.num_nodes()

    embed_calls_before = metered_embedder.calls if metered_embedder else 0
    embed_time_before = metered_embedder.cumulative_seconds if metered_embedder else 0.0

    t_total_start = time.perf_counter()

    # Step 1: Candidate narrowing
    t0 = time.perf_counter()
    shortlist_res = strategy.shortlist(new_name)
    t1 = time.perf_counter()
    shortlist_s = t1 - t0

    embed_calls_delta = (
        (metered_embedder.calls - embed_calls_before) if metered_embedder else 0
    )
    embed_s = (
        (metered_embedder.cumulative_seconds - embed_time_before)
        if metered_embedder
        else 0.0
    )

    # Step 2: Shared decision step (empty shortlist skips LLM calls per item 8)
    if len(shortlist_res.candidates) == 0:
        outcome = DecisionOutcome(edges=(), llm_calls=0, llm_seconds=0.0)
        decide_s = 0.0
    else:
        t2 = time.perf_counter()
        outcome = decision_step.decide(
            new_name, shortlist_res.candidates, graph.domain_context
        )
        t3 = time.perf_counter()
        decide_s = t3 - t2

    # Step 3: Mutate graph (driver owns graph mutations)
    graph.add_node(new_name)
    for prereq, dependent in outcome.edges:
        if prereq != new_name and dependent != new_name:
            raise ValueError(
                f"Decided edge ({prereq!r}, {dependent!r}) does not involve inserted node {new_name!r}"
            )
        graph.add_prereq_edge(prereq, dependent)

    # Step 4: Incremental update of strategy state
    t4 = time.perf_counter()
    strategy.on_inserted(new_name, outcome.edges)
    t5 = time.perf_counter()
    update_s = t5 - t4

    total_s = time.perf_counter() - t_total_start

    # Step 5: Collate metrics
    try:
        diag = strategy.diagnostics()
    except Exception:
        diag = {}

    metrics = InsertionMetrics(
        n_before=n_before,
        shortlist_size=len(shortlist_res.candidates),
        llm_calls=outcome.llm_calls,
        embedding_calls=embed_calls_delta,
        embed_s=embed_s,
        shortlist_s=shortlist_s,
        decide_s=decide_s,
        update_s=update_s,
        total_s=total_s,
        extra=diag,
    )

    return InsertionResult(
        new_name=new_name,
        shortlist=shortlist_res,
        edges=outcome.edges,
        metrics=metrics,
    )
