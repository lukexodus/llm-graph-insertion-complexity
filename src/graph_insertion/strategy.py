"""
strategy.py — INFRA-002
=======================
Strategy interface contract, data structures, and shared insertion driver.

Decisions:
  - Narrowing-only strategy contract with external shared decision step ([D-24]).
  - Timing and metrics accounting model ([D-25]).
  - Strategy hardening and embedder accounting pass ([D-26], [D-28]).
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
    apply_s:
        Wall-clock seconds spent committing nodes and edges to ConceptGraph.
    update_s:
        Wall-clock seconds spent updating the strategy's internal state in on_inserted().
    total_s:
        Total operational wall-clock seconds for insertion: shortlist_s + decide_s + apply_s + update_s.
        Validation overhead is tracked separately in validate_s and excluded from total_s ([D-28]).
    validate_s:
        Wall-clock seconds spent performing shortlist contract and edge validation checks.
    embedding_calls_in_update:
        Number of embedding calls made during on_inserted() (must be 0 under [D-26]/[D-28]).
    embed_in_update_s:
        Cumulative seconds spent generating embeddings during on_inserted().
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
    apply_s: float
    update_s: float
    total_s: float
    validate_s: float
    embedding_calls_in_update: int = 0
    embed_in_update_s: float = 0.0
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
    *,
    metered_embedder: MeteredEmbedder,
) -> InsertionResult:
    """Execute the canonical end-to-end insertion pipeline for a new concept.

    Sequences:
      0. Embedder identity validation: if strategy._embedder is not None and is not
         metered_embedder, raise ValueError before any shortlist call or mutation ([D-28]).
      1. Precondition checks: validate new_name format and ensure it does not already exist.
      2. Candidate narrowing: strategy.shortlist(new_name).
      3. Shortlist contract enforcement: candidates are valid graph nodes, no duplicates,
         new_name excluded, scores length matches candidates (timed via validate_s).
      4. Shared decision step: decision_step.decide(new_name, shortlist).
      5. Pre-mutation edge validation: canonical, involves new_name, other endpoint
         in shortlist, no self-loops, no duplicates (timed via validate_s).
      6. Graph mutation: add new_name and canonical edges to ConceptGraph (timed via apply_s).
      7. Incremental index update: strategy.on_inserted(new_name, edges) (timed via update_s).
      8. Embedding accounting across whole window & diagnostics collation.

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
        Required MeteredEmbedder for tracking embedding time and calls during narrowing
        and update ([D-28]).

    Returns
    -------
    InsertionResult
        Structured outcome containing inserted node, shortlist, edges, and full metrics.
    """
    if not isinstance(metered_embedder, MeteredEmbedder):
        raise TypeError(
            f"metered_embedder must be an instance of MeteredEmbedder, got {type(metered_embedder).__name__}"
        )

    strat_embedder = getattr(strategy, "_embedder", None)
    if strat_embedder is not None and strat_embedder is not metered_embedder:
        raise ValueError(
            f"MeteredEmbedder mismatch: strategy {strategy.name!r} holds embedder {strat_embedder!r}, "
            f"which is not identical to metered_embedder passed to insert_node: {metered_embedder!r}. "
            "The metered_embedder passed to insert_node must be identical to the strategy's internal embedder."
        )

    _validate_concept_name(new_name)
    if graph.has_node(new_name):
        raise ValueError(f"Node {new_name!r} already exists in graph.")

    n_before = graph.num_nodes()

    embed_calls_start = metered_embedder.calls
    embed_time_start = metered_embedder.cumulative_seconds

    # Step 1: Candidate narrowing
    t0 = time.perf_counter()
    shortlist_res = strategy.shortlist(new_name)
    t1 = time.perf_counter()
    shortlist_s = t1 - t0

    # Step 1b: Shortlist contract enforcement (timed as part of validate_s)
    t_v0 = time.perf_counter()
    if not isinstance(shortlist_res.candidates, tuple):
        raise ValueError(
            f"Strategy {strategy.name!r} returned invalid shortlist: candidates must be a tuple"
        )
    if new_name in shortlist_res.candidates:
        raise ValueError(
            f"Strategy {strategy.name!r} returned invalid shortlist: candidate list contains inserted node {new_name!r}"
        )
    if len(shortlist_res.candidates) != len(set(shortlist_res.candidates)):
        raise ValueError(
            f"Strategy {strategy.name!r} returned invalid shortlist: contains duplicate candidates"
        )
    for c in shortlist_res.candidates:
        if not graph.has_node(c):
            raise ValueError(
                f"Strategy {strategy.name!r} returned invalid shortlist: candidate {c!r} is not an existing graph node"
            )
    if shortlist_res.scores is not None:
        if len(shortlist_res.scores) != len(shortlist_res.candidates):
            raise ValueError(
                f"Strategy {strategy.name!r} returned invalid shortlist: scores length ({len(shortlist_res.scores)}) does not match candidates length ({len(shortlist_res.candidates)})"
            )
    val_shortlist_s = time.perf_counter() - t_v0

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

    # Step 2b: Pre-mutation edge validation before touching the graph (timed as part of validate_s)
    t_v1 = time.perf_counter()
    if not isinstance(outcome.edges, tuple):
        raise ValueError("Decision step edges must be a tuple")
    if len(outcome.edges) != len(set(outcome.edges)):
        raise ValueError(
            f"Decision step returned duplicate edges: {outcome.edges!r}"
        )
    for edge in outcome.edges:
        if not isinstance(edge, tuple) or len(edge) != 2:
            raise ValueError(f"Decided edge {edge!r} is not a 2-tuple")
        prereq, dependent = edge
        if not isinstance(prereq, str) or not isinstance(dependent, str):
            raise ValueError(f"Decided edge endpoints must be strings, got {edge!r}")
        if prereq == dependent:
            raise ValueError(
                f"Decided edge is a self-loop: {prereq!r} -> {dependent!r}"
            )
        if prereq != new_name and dependent != new_name:
            raise ValueError(
                f"Decided edge ({prereq!r}, {dependent!r}) does not involve inserted node {new_name!r}"
            )
        other = dependent if prereq == new_name else prereq
        if other not in shortlist_res.candidates:
            raise ValueError(
                f"Decided edge endpoint {other!r} was not in the shortlisted candidates: {shortlist_res.candidates!r}"
            )
    val_edge_s = time.perf_counter() - t_v1
    validate_s = val_shortlist_s + val_edge_s

    # Step 3: Mutate graph (timed via apply_s)
    t_apply_start = time.perf_counter()
    graph.add_node(new_name)
    for prereq, dependent in outcome.edges:
        graph.add_prereq_edge(prereq, dependent)
    apply_s = time.perf_counter() - t_apply_start

    # Step 4: Incremental update of strategy state
    embed_calls_before_update = metered_embedder.calls
    embed_time_before_update = metered_embedder.cumulative_seconds

    t4 = time.perf_counter()
    strategy.on_inserted(new_name, outcome.edges)
    t5 = time.perf_counter()
    update_s = t5 - t4

    embed_calls_after_update = metered_embedder.calls
    embed_time_after_update = metered_embedder.cumulative_seconds

    embedding_calls_in_update = embed_calls_after_update - embed_calls_before_update
    embed_in_update_s = embed_time_after_update - embed_time_before_update

    # Total operational wall-clock time (validation excluded per [D-28])
    total_s = shortlist_s + decide_s + apply_s + update_s

    embed_calls_total = metered_embedder.calls - embed_calls_start
    embed_s = metered_embedder.cumulative_seconds - embed_time_start

    # Step 5: Collate metrics
    try:
        diag = strategy.diagnostics()
    except Exception as e:
        diag = {"diagnostics_error": repr(e)}

    metrics = InsertionMetrics(
        n_before=n_before,
        shortlist_size=len(shortlist_res.candidates),
        llm_calls=outcome.llm_calls,
        embedding_calls=embed_calls_total,
        embed_s=embed_s,
        shortlist_s=shortlist_s,
        decide_s=decide_s,
        apply_s=apply_s,
        update_s=update_s,
        total_s=total_s,
        validate_s=validate_s,
        embedding_calls_in_update=embedding_calls_in_update,
        embed_in_update_s=embed_in_update_s,
        extra=diag,
    )

    return InsertionResult(
        new_name=new_name,
        shortlist=shortlist_res,
        edges=outcome.edges,
        metrics=metrics,
    )
