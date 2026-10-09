"""src/graph_insertion/strategies/embedding_threshold.py — STRAT-002
===================================================================
Strategy 2: Embedding-similarity thresholding.

Purpose
-------
Shortlists existing nodes whose cosine similarity with the new concept
exceeds a fixed threshold theta (thesis Chapter 3, Section 3.2.3 [Strategy B]).

Decisions cited:
  - [D-21]: Embedding payload is the bare concept name via embed_text(name).
    Never embed domain context or descriptions.
  - [D-24]: Narrowing-only contract; read ConceptGraph immutably; no LLM calls.
  - [D-25]: Untimed setup(); incremental update in on_inserted() timed via update_s.
  - [D-26], [D-28]: Single-embedding invariant: new_name embedded exactly once
    in shortlist(), cached, and reused in on_inserted(). No embedding in update.
  - [D-35](4)(5): Embedding model is all-MiniLM-L6-v2 on CPU; default theta = 0.6;
    sensitivity runs at 0.4 and 0.5.
  - [D-41]: No max_candidates method defined; candidate_upper_bound falls back
    to brute force n.
  - [D-46]: Strategy 2 semantics, strict '>' thresholding, amortised O(d) append,
    and ordering (-score, name).

Key semantics & design choices:
  - Similarity metric: Cosine similarity over L2-normalised float32 vectors.
    Index rows are normalised once upon ingest (setup and on_inserted).
    The query vector is normalised once in shortlist(). The index matrix is
    never renormalised per query.
  - Strict threshold: A node is shortlisted iff score > theta (strictly greater;
    thesis Section 3.2.3: "exceeds a fixed threshold", not '>=').
  - Vectorised computation: Uses a single matrix-vector product (mat[:n] @ q)
    rather than a Python loop over n, keeping shortlist computation fast.
  - Amortised O(d) insertion update: Internal matrix buffer grows via capacity
    doubling, starting with capacity `max(16, 2n)` after `setup()` on a graph of
    n nodes. This ensures the first timed `on_inserted()` call (in the sweep
    harness, which performs exactly one insertion per trial after setup) never
    reallocates, and subsequent insertions trigger O(n·d) reallocation only at
    powers of two, achieving amortised O(d) cost per insertion without polluting
    the timed `update_s` metric (D-25).
  - Ordering: Candidates sorted by (-score, name) descending by cosine, ties
    broken by concept name ascending.
  - Zero-candidate shortlists: Expected when no concept exceeds theta (e.g. with
    bare-name MiniLM at theta 0.6). This is a legitimate research result, not
    an error, resulting in 0 LLM calls in the driver.
  - Float precision: Scores are computed in float32 without clipping, so a score
    may exceed 1.0 by minor floating-point rounding error (~1e-7).
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from graph_insertion.embedding import Embedder
from graph_insertion.graph_representation import ConceptGraph, _validate_concept_name, embed_text
from graph_insertion.strategy import Shortlist

DEFAULT_THETA: float = 0.6


class EmbeddingThresholdStrategy:
    """Strategy 2: Shortlists candidate concepts whose cosine similarity exceeds theta.

    Attributes
    ----------
    name:
        Canonical strategy identifier string: "embedding_threshold".
    uses_embeddings:
        Always True.
    theta:
        Similarity threshold in [-1.0, 1.0].
    seed:
        Random seed for configuration logging.
    """

    name: str = "embedding_threshold"
    uses_embeddings: bool = True

    def __init__(self, theta: float = DEFAULT_THETA, seed: int = 42) -> None:
        if isinstance(theta, bool) or not isinstance(theta, (int, float)):
            raise ValueError(f"theta must be a real number, got {type(theta).__name__}")
        if not np.isfinite(theta) or theta < -1.0 or theta > 1.0:
            raise ValueError(f"theta must be a finite number within [-1.0, 1.0], got {theta!r}")

        self.theta: float = float(theta)
        self.seed: int = int(seed)

        self._embedder: Optional[Embedder] = None
        self._setup_called: bool = False
        self._shortlist_called: bool = False

        self._dim: Optional[int] = None
        self._mat: Optional[np.ndarray] = None
        self._names: list[str] = []
        self._name_to_idx: dict[str, int] = {}
        self._n: int = 0

        self._cached_new_name: Optional[str] = None
        self._cached_new_vec: Optional[np.ndarray] = None

        self._last_comparisons: int = 0
        self._last_shortlist_size: int = 0
        self._last_max_cosine: Optional[float] = None

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        """Initialise strategy state and index initial graph nodes.

        Untimed preparation per [D-25]. Calling setup() twice resets all state.
        A failed setup() leaves the strategy in the not-set-up state.

        Parameters
        ----------
        graph:
            ConceptGraph to read initial nodes from (read immutably).
        embedder:
            Injected Embedder instance. Retained by identity as self._embedder.
        """
        # Clear state immediately (all-or-nothing semantics per F-3)
        self._setup_called = False
        self._embedder = None
        self._shortlist_called = False

        self._cached_new_name = None
        self._cached_new_vec = None
        self._last_comparisons = 0
        self._last_shortlist_size = 0
        self._last_max_cosine = None

        self._dim = None
        self._mat = None
        self._names = []
        self._name_to_idx = {}
        self._n = 0

        nodes = sorted(graph.nodes())
        n = len(nodes)

        if n == 0:
            # Set success flags only after validation passes
            self._embedder = embedder
            self._setup_called = True
            return

        texts = [embed_text(node) for node in nodes]
        raw_mat = embedder.embed_many(texts)

        if not isinstance(raw_mat, np.ndarray) or raw_mat.ndim != 2:
            raise ValueError(f"embed_many must return a 2-D ndarray, got {type(raw_mat)}")
        if raw_mat.shape[0] != n:
            raise ValueError(f"embed_many returned {raw_mat.shape[0]} rows, expected {n}")
        if not np.all(np.isfinite(raw_mat)):
            raise ValueError("embed_many returned non-finite embedding vectors")

        norms = np.linalg.norm(raw_mat, axis=1)
        for i, norm_val in enumerate(norms):
            if norm_val == 0.0 or not np.isfinite(norm_val):
                raise ValueError(f"Zero-norm embedding vector for node {nodes[i]!r}")

        dim = raw_mat.shape[1]
        self._dim = dim

        normed_mat = (raw_mat / norms[:, np.newaxis]).astype(np.float32)

        capacity = max(16, 2 * n)
        self._mat = np.zeros((capacity, dim), dtype=np.float32)
        self._mat[:n] = normed_mat
        self._names = list(nodes)
        self._name_to_idx = {name: i for i, name in enumerate(nodes)}
        self._n = n

        # Set success flags only after all validation and setup has passed
        self._embedder = embedder
        self._setup_called = True

    def shortlist(self, new_name: str) -> Shortlist:
        """Produce a shortlist of candidate concepts whose cosine similarity exceeds theta.

        Always embeds new_name exactly once, normalises it, and caches it for on_inserted().
        
        Note: `max_cosine` in `diagnostics()` is the maximum over the whole index,
        including new_name's own row if new_name is already indexed. This is unreachable
        through `insert_node` (which rejects existing names as precondition) but is
        documented for completeness.

        Parameters
        ----------
        new_name:
            Bare concept name to evaluate.

        Returns
        -------
        Shortlist:
            Candidates ordered by (-score, name) and matching float scores.
        """
        if not self._setup_called or self._embedder is None:
            raise RuntimeError("setup() must be called before shortlist()")

        _validate_concept_name(new_name)

        # Always embed new_name first via embed_text(new_name) [D-21]
        raw_vec = self._embedder.embed(embed_text(new_name))
        vec_arr = np.asarray(raw_vec)

        if vec_arr.ndim != 1:
            raise ValueError(f"Embedding for {new_name!r} must be 1-D, got shape {vec_arr.shape}")
        if not np.all(np.isfinite(vec_arr)):
            raise ValueError(f"Embedding for {new_name!r} contains non-finite values")

        norm = float(np.linalg.norm(vec_arr))
        if norm == 0.0:
            raise ValueError(f"Zero-norm embedding vector for concept {new_name!r}")

        if self._dim is not None:
            if len(vec_arr) != self._dim:
                raise ValueError(
                    f"Dimension mismatch for {new_name!r}: expected {self._dim}, got {len(vec_arr)}"
                )
        else:
            # First vector seen (empty graph at setup)
            self._dim = len(vec_arr)
            self._mat = np.zeros((16, self._dim), dtype=np.float32)

        q = (vec_arr / norm).astype(np.float32)

        self._cached_new_name = new_name
        self._cached_new_vec = q
        self._shortlist_called = True

        if self._n == 0:
            self._last_comparisons = 0
            self._last_shortlist_size = 0
            self._last_max_cosine = None
            return Shortlist(candidates=(), scores=())

        assert self._mat is not None
        scores = self._mat[: self._n] @ q

        max_cos = float(np.max(scores))
        self._last_max_cosine = max_cos
        self._last_comparisons = self._n

        # Strict thresholding in float64: score > theta
        mask = scores.astype(np.float64) > self.theta
        qualifying_indices = np.where(mask)[0]

        candidates_with_scores: list[tuple[float, str]] = []
        for idx in qualifying_indices:
            cand_name = self._names[idx]
            if cand_name != new_name:
                candidates_with_scores.append((float(scores[idx]), cand_name))

        # Order by (-score, name)
        candidates_with_scores.sort(key=lambda item: (-item[0], item[1]))

        candidates = tuple(cand for _, cand in candidates_with_scores)
        scores_tuple = tuple(score for score, _ in candidates_with_scores)

        self._last_shortlist_size = len(candidates)
        return Shortlist(candidates=candidates, scores=scores_tuple)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        """Incrementally update embedding index with the newly inserted concept.

        Reuses the normalised embedding cached during shortlist(). Never embeds new_name.
        edges parameter is accepted and ignored because Strategy 2 relies solely on
        concept embeddings rather than graph edge topology.

        Parameters
        ----------
        new_name:
            Bare concept name inserted.
        edges:
            Committed graph edges involving new_name (ignored).
        """
        if self._cached_new_name != new_name or self._cached_new_vec is None:
            raise RuntimeError(
                f"on_inserted called for {new_name!r} without matching prior shortlist() call"
            )

        if new_name in self._name_to_idx:
            raise ValueError(f"Node {new_name!r} already indexed in embedding threshold strategy")

        vec = self._cached_new_vec
        self._cached_new_name = None
        self._cached_new_vec = None

        assert self._dim is not None

        if self._mat is None:
            self._mat = np.zeros((16, self._dim), dtype=np.float32)
        elif self._n >= self._mat.shape[0]:
            # Capacity doubling for amortised O(d) appends
            new_capacity = self._mat.shape[0] * 2
            new_mat = np.zeros((new_capacity, self._dim), dtype=np.float32)
            new_mat[: self._n] = self._mat
            self._mat = new_mat

        self._mat[self._n] = vec
        self._name_to_idx[new_name] = self._n
        self._names.append(new_name)
        self._n += 1

    def config(self) -> dict[str, Any]:
        """Return strategy configuration hyperparameters."""
        return {"theta": self.theta, "seed": self.seed}

    def diagnostics(self) -> dict[str, Any]:
        """Return operational diagnostics for the most recent insertion trial.

        All values use plain Python types (int, float, None) to guarantee JSON serializability.
        
        Note: `max_cosine` is the maximum over the whole index, including new_name's
        own row if new_name is already indexed (would be 1.0 in such cases). This is
        unreachable through `insert_node` but documented for completeness.
        """
        return {
            "cosine_comparisons": int(self._last_comparisons),
            "threshold": float(self.theta),
            "shortlist_size": int(self._last_shortlist_size),
            "max_cosine": float(self._last_max_cosine) if self._last_max_cosine is not None else None,
            "index_size": int(self._n),
        }
