"""src/graph_insertion/strategies/ann_retrieval.py — STRAT-003
============================================================
Strategy 3: Approximate nearest-neighbour (ANN) top-k retrieval using FAISS HNSW.

Purpose
-------
Shortlists the top-k most similar existing concepts to a newly inserted
concept using an approximate nearest-neighbour index (FAISS IndexHNSWFlat),
ordered by descending cosine similarity (thesis Chapter 3, Section 3.2.4
[Strategy C]).

Decisions cited:
  - [D-21]: Embedding payload is the bare concept name via embed_text(name).
    Never embed domain context or descriptions.
  - [D-24]: Narrowing-only contract; read ConceptGraph immutably; no LLM calls.
  - [D-25]: Untimed setup(); incremental update in on_inserted() timed via update_s.
    For this strategy, update_s represents a real algorithmic HNSW graph insertion
    cost into an index of n vectors.
  - [D-26], [D-28]: Single-embedding invariant: new_name embedded exactly once
    in shortlist(), cached, and reused in on_inserted(). No embedding in update.
  - [D-35](4)(5): Embedding model is all-MiniLM-L6-v2 on CPU; parameters fixed
    a priori: k=10, M=16, efConstruction=200, efSearch=64 (updated to 128 per [D-55]);
    no tuning on evaluation corpora.
  - [D-41]: max_candidates defined as min(k, n_existing); guard bound evaluates
    to exactly 600 calls over the D-35 sweep matrix (6 sizes x 10 trials x 10).
  - [D-47]: Locked Strategy 3 specification: IndexHNSWFlat with inner product on
    L2-normalised unit vectors, single-threaded determinism (omp_set_num_threads(1)),
    -1 padding filtering, exact_topk_overlap diagnostic computed in diagnostics(),
    all-or-nothing setup(), and guarded faiss import.
  - [D-55]: Strategy 3 review amendments: shortlist() cache clearing on entry (A-1),
    default ef_search updated from 64 to 128 (A-3), and max_cosine documentation note (A-2).

Key semantics & design choices:
  - Similarity metric: Inner product on L2-normalised float32 vectors. This is
    mathematically identical to cosine similarity, requires no per-query
    renormalisation of indexed vectors, and preserves consistent similarity
    interpretation across Strategy 2 and Strategy 3.
  - HNSW index: Uses faiss.IndexHNSWFlat(d, M, faiss.METRIC_INNER_PRODUCT) with
    index.hnsw.efConstruction = ef_construction set before adding vectors, and
    index.hnsw.efSearch = ef_search set before querying. IndexFlatIP is exact,
    not approximate, and is therefore rejected for Strategy 3.
  - Determinism: OpenMP multi-threading during HNSW batch add is non-deterministic.
    setup() calls faiss.omp_set_num_threads(1) before index construction, and
    builds from sorted(graph.nodes()) in a single batch add call. This ensures
    reproducible graph structure and search results across identical runs.
  - Padding and tie-breaking: FAISS pads search results with label -1 when the
    index contains fewer elements than requested or when graph traversal finds
    fewer candidates. All -1 labels are stripped. Shortlisted candidates are
    ordered by (-score, name) descending by cosine, ties broken by concept name
    ascending.
  - Top-k without threshold: Negative cosine scores are retained if they fall
    within the top-k nearest neighbours. No similarity cutoff is applied.
  - Approximation fidelity diagnostic: exact_topk_overlap measures the fraction of
    returned candidates that belong to the exact top-k_eff set by cosine over the
    vectors present in the index at query time (excluding new_name). It is computed
    strictly inside diagnostics() using index.reconstruct_n() outside every timed
    window (D-25, D-28), so exact matrix operations never inflate shortlist_s.
  - Edge parameter: Accepted and ignored in on_inserted() because Strategy 3
    indexing depends entirely on concept embedding geometry; graph topology
    does not alter the vector index.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from graph_insertion.embedding import Embedder
from graph_insertion.graph_representation import (
    ConceptGraph,
    _validate_concept_name,
    embed_text,
)
from graph_insertion.strategy import Shortlist


class AnnRetrievalStrategy:
    """Strategy 3: Shortlists the top-k nearest candidate concepts using FAISS HNSW.

    Attributes
    ----------
    name:
        Canonical strategy identifier string: "ann_retrieval".
    uses_embeddings:
        Always True.
    k:
        Maximum number of candidates to retrieve (default 10).
    seed:
        Seed stored for factory-shape consistency (unused algorithmically; determinism
        comes from single-threaded build in sorted order, not a random seed).
    M:
        HNSW number of bi-directional links per node (default 16).
    ef_construction:
        HNSW search depth during index construction (default 200).
    ef_search:
        HNSW search depth during nearest-neighbour queries (default 128 per [D-55]).
    """

    name: str = "ann_retrieval"
    uses_embeddings: bool = True

    def __init__(
        self,
        k: int = 10,
        seed: int = 42,
        M: int = 16,
        ef_construction: int = 200,
        ef_search: int = 128,
    ) -> None:
        if faiss is None:
            raise ImportError(
                "FAISS is not installed. Install with `pip install -e '.[ann]'` "
                "or `pip install faiss-cpu==1.15.1`."
            )

        for param_name, val, min_val in [
            ("k", k, 1),
            ("M", M, 2),
            ("ef_construction", ef_construction, 1),
            ("ef_search", ef_search, 1),
        ]:
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"{param_name} must be an integer, got {type(val).__name__}")
            if val < min_val:
                raise ValueError(f"{param_name} must be >= {min_val}, got {val}")

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"seed must be an integer, got {type(seed).__name__}")

        self.k: int = int(k)
        self.seed: int = int(seed)
        self.M: int = int(M)
        self.ef_construction: int = int(ef_construction)
        self.ef_search: int = int(ef_search)

        self._embedder: Optional[Embedder] = None
        self._setup_called: bool = False

        self._dim: Optional[int] = None
        self._index: Any = None
        self._names: list[str] = []
        self._name_to_idx: dict[str, int] = {}

        self._cached_new_name: Optional[str] = None
        self._cached_new_vec: Optional[np.ndarray] = None

        self._last_shortlist_size: int = 0
        self._last_max_cosine: Optional[float] = None
        self._last_query_vec: Optional[np.ndarray] = None
        self._last_returned_candidates: tuple[str, ...] = ()
        self._n_at_query: int = 0
        self._query_name: Optional[str] = None
        self._cached_exact_topk_overlap: Optional[float] = None

    def max_candidates(self, n_existing: int) -> int:
        """Return upper bound on candidates shortlisted when graph has n_existing nodes.

        Works before setup() to compute pre-flight planned LLM budgets ([D-41]).
        """
        return max(0, min(self.k, n_existing))

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        """Initialise strategy state and index initial graph nodes using FAISS HNSW.

        Untimed preparation per [D-25]. Calling setup() twice resets all state.
        A failed setup() leaves the strategy in the not-set-up state (all-or-nothing).

        Parameters
        ----------
        graph:
            ConceptGraph to read initial nodes from (read immutably).
        embedder:
            Injected Embedder instance. Retained by identity as self._embedder.
        """
        # All-or-nothing: clear state immediately at top of setup()
        self._setup_called = False
        self._embedder = None

        self._dim = None
        self._index = None
        self._names = []
        self._name_to_idx = {}

        self._cached_new_name = None
        self._cached_new_vec = None

        self._last_shortlist_size = 0
        self._last_max_cosine = None
        self._last_query_vec = None
        self._last_returned_candidates = ()
        self._n_at_query = 0
        self._query_name = None
        self._cached_exact_topk_overlap = None

        nodes = sorted(graph.nodes())
        n = len(nodes)

        if n == 0:
            # Empty graph: index is created lazily on first shortlist()
            self._embedder = embedder
            self._setup_called = True
            return

        texts = [embed_text(node) for node in nodes]
        raw_mat = embedder.embed_many(texts)

        if not isinstance(raw_mat, np.ndarray) or raw_mat.ndim != 2:
            got_type = type(raw_mat).__name__ if not isinstance(raw_mat, np.ndarray) else f"{raw_mat.ndim}-D"
            raise ValueError(f"embed_many must return a 2-D ndarray, got {got_type}")
        if raw_mat.shape[0] != n:
            raise ValueError(f"embed_many returned {raw_mat.shape[0]} rows, expected {n}")
        if not np.all(np.isfinite(raw_mat)):
            raise ValueError("embed_many returned non-finite embedding vectors")

        norms = np.linalg.norm(raw_mat, axis=1)
        for i, norm_val in enumerate(norms):
            if norm_val == 0.0 or not np.isfinite(norm_val):
                raise ValueError(f"Zero-norm embedding vector for node {nodes[i]!r}")

        dim = raw_mat.shape[1]
        if dim == 0:
            raise ValueError("Embedding dimension must be >= 1, got 0")

        # L2-normalise rows once on ingest
        normed_mat = (raw_mat / norms[:, np.newaxis]).astype(np.float32, copy=False)
        normed_mat = np.ascontiguousarray(normed_mat, dtype=np.float32)

        # Single-threaded build for determinism ([D-47])
        faiss.omp_set_num_threads(1)
        index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = self.ef_construction
        index.hnsw.efSearch = self.ef_search
        index.add(normed_mat)

        self._dim = dim
        self._index = index
        self._names = list(nodes)
        self._name_to_idx = {name: i for i, name in enumerate(nodes)}

        # Set success flags only after all validation and setup has passed
        self._embedder = embedder
        self._setup_called = True

    def shortlist(self, new_name: str) -> Shortlist:
        """Retrieve top-k nearest candidate concepts using FAISS HNSW.

        Always embeds new_name exactly once first via embed_text(new_name), normalises it,
        and caches it for on_inserted().

        Parameters
        ----------
        new_name:
            Bare concept name to evaluate.

        Returns
        -------
        Shortlist:
            Candidates ordered by (-score, name) and matching float scores.

        Notes
        -----
        `max_cosine` in diagnostics is taken over the raw search results and
        includes `new_name`'s own row if `new_name` is already indexed (would be
        1.0 in such cases). This is unreachable through `insert_node` but
        documented for completeness per [D-50](4) and [D-55].
        """
        # Clear per-insertion cache as first executable statement (D-58) so any
        # failed shortlist() call leaves no cached vector from an earlier shortlist
        self._cached_new_name = None
        self._cached_new_vec = None

        if not self._setup_called or self._embedder is None:
            raise RuntimeError("setup() must be called before shortlist()")

        _validate_concept_name(new_name)

        # Invalidate cached diagnostic overlap for previous query
        self._cached_exact_topk_overlap = None

        # Always embed new_name first via embed_text(new_name) [D-21]
        raw_vec = self._embedder.embed(embed_text(new_name))

        if not isinstance(raw_vec, np.ndarray) or raw_vec.ndim != 1:
            got_type = type(raw_vec).__name__ if not isinstance(raw_vec, np.ndarray) else f"{raw_vec.ndim}-D"
            raise ValueError(f"Embedding for {new_name!r} must be 1-D ndarray, got {got_type}")
        if not np.all(np.isfinite(raw_vec)):
            raise ValueError(f"Embedding for {new_name!r} contains non-finite values")

        norm = float(np.linalg.norm(raw_vec))
        if norm == 0.0 or not np.isfinite(norm):
            raise ValueError(f"Zero-norm embedding vector for concept {new_name!r}")

        if self._dim is not None:
            if raw_vec.shape[0] != self._dim:
                raise ValueError(
                    f"Dimension mismatch for {new_name!r}: expected {self._dim}, got {raw_vec.shape[0]}"
                )
        else:
            # First vector seen (empty graph at setup): initialize lazy index
            dim = raw_vec.shape[0]
            if dim == 0:
                raise ValueError("Embedding dimension must be >= 1, got 0")
            self._dim = dim
            faiss.omp_set_num_threads(1)
            self._index = faiss.IndexHNSWFlat(dim, self.M, faiss.METRIC_INNER_PRODUCT)
            self._index.hnsw.efConstruction = self.ef_construction
            self._index.hnsw.efSearch = self.ef_search

        normed_vec = (raw_vec / norm).astype(np.float32, copy=False)
        normed_vec = np.ascontiguousarray(normed_vec, dtype=np.float32)

        # Cache normalized vector for on_inserted()
        self._cached_new_name = new_name
        self._cached_new_vec = normed_vec

        n_indexed = self._index.ntotal if self._index is not None else 0
        self._n_at_query = n_indexed
        self._query_name = new_name
        self._last_query_vec = normed_vec

        if n_indexed == 0:
            self._last_shortlist_size = 0
            self._last_max_cosine = None
            self._last_returned_candidates = ()
            return Shortlist(candidates=(), scores=())

        # Ensure efSearch is set before search
        self._index.hnsw.efSearch = self.ef_search

        is_indexed = new_name in self._name_to_idx
        k_eff = min(self.k + 1, n_indexed) if is_indexed else min(self.k, n_indexed)

        q_2d = normed_vec.reshape(1, -1)
        distances, labels = self._index.search(q_2d, k_eff)

        # Filter out padding (-1), duplicates, and new_name
        candidates_with_scores: list[tuple[str, float]] = []
        seen: set[str] = set()
        for dist, label in zip(distances[0], labels[0]):
            if label == -1:
                continue
            cand_name = self._names[label]
            if cand_name == new_name or cand_name in seen:
                continue
            seen.add(cand_name)
            candidates_with_scores.append((cand_name, float(dist)))

        # Order by (-score, name): descending by cosine, ties broken by concept name ascending
        candidates_with_scores.sort(key=lambda item: (-item[1], item[0]))

        final_items = candidates_with_scores[: self.k]
        candidates = tuple(cand for cand, _ in final_items)
        scores = tuple(score for _, score in final_items)

        self._last_shortlist_size = len(candidates)
        valid_dists = [float(dist) for dist, lbl in zip(distances[0], labels[0]) if lbl != -1]
        self._last_max_cosine = max(valid_dists) if valid_dists else None
        self._last_returned_candidates = candidates

        return Shortlist(candidates=candidates, scores=scores)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        """Add newly inserted concept vector into the FAISS HNSW index.

        Reuses the normalized vector cached during shortlist(); makes zero embedding calls.
        edges parameter is accepted and ignored because Strategy 3 indexing relies solely
        on concept vector similarity in embedding space.

        Parameters
        ----------
        new_name:
            Concept name that was inserted into the graph.
        edges:
            Canonical directed edges involving new_name (ignored).
        """
        if self._cached_new_name is None or self._cached_new_name != new_name:
            raise RuntimeError(
                f"on_inserted({new_name!r}) called without matching shortlist() call "
                f"(cached: {self._cached_new_name!r})"
            )
        if self._cached_new_vec is None:
            raise RuntimeError(f"No cached vector for concept {new_name!r}")
        if new_name in self._name_to_idx:
            raise ValueError(f"Concept {new_name!r} is already present in the index")

        cached_vec = self._cached_new_vec
        self._cached_new_name = None
        self._cached_new_vec = None

        vec_2d = cached_vec.reshape(1, -1)
        self._index.add(vec_2d)

        idx = len(self._names)
        self._names.append(new_name)
        self._name_to_idx[new_name] = idx

    def config(self) -> dict[str, Any]:
        """Return strategy configuration hyperparameters."""
        return {
            "k": self.k,
            "M": self.M,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "metric": "inner_product_on_unit_vectors",
            "index": "IndexHNSWFlat",
            "faiss_threads": 1,
            "faiss_version": faiss.__version__ if faiss is not None else None,
            "seed": self.seed,
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return operational diagnostics for the most recent insertion trial.

        exact_topk_overlap is computed here outside every timed window using
        index.reconstruct_n() to isolate exact calculation from shortlist_s.

        Note: `max_cosine` is the maximum over the raw search results across the
        whole index, including `new_name`'s own row if `new_name` is already indexed
        (would be 1.0 in such cases). This is unreachable through `insert_node`
        but documented for completeness per [D-50](4) and [D-55].
        """
        index_size = self._index.ntotal if self._index is not None else 0

        if self._cached_exact_topk_overlap is None:
            if self._n_at_query > 0 and self._last_query_vec is not None and self._index is not None:
                reconstructed = self._index.reconstruct_n(0, self._n_at_query)
                cosines = reconstructed @ self._last_query_vec
                names_at_query = self._names[: self._n_at_query]
                valid_items = [
                    (float(cosines[i]), names_at_query[i])
                    for i in range(self._n_at_query)
                    if names_at_query[i] != self._query_name
                ]
                valid_items.sort(key=lambda item: (-item[0], item[1]))
                k_eff = min(self.k, len(valid_items))
                exact_set = {name for _, name in valid_items[:k_eff]}

                if len(self._last_returned_candidates) == 0:
                    overlap = 1.0 if k_eff == 0 else 0.0
                else:
                    matched = sum(1 for c in self._last_returned_candidates if c in exact_set)
                    overlap = float(matched / len(self._last_returned_candidates))

                self._cached_exact_topk_overlap = overlap
            else:
                self._cached_exact_topk_overlap = None

        return {
            "top_k": self.k,
            "index_size": index_size,
            "shortlist_size": self._last_shortlist_size,
            "max_cosine": self._last_max_cosine,
            "ef_search": self.ef_search,
            "exact_topk_overlap": self._cached_exact_topk_overlap,
        }
