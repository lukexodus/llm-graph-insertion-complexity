"""src/graph_insertion/strategies/bounded_bucket.py — STRAT-004
==============================================================
Strategy 4: Bounded-bucket partitioning adapted from EraRAG Algorithms 1 and 3.

Purpose
-------
Organises existing concept nodes into size-bounded segments along a 1-D ordering
of random-hyperplane LSH codes so that inserting a new concept compares it only
against the members of a single home segment of size at most ``s_max`` (thesis
Chapter 3, Section 3.2.5 [Strategy D]).

Literature & Adaptation Scope
-----------------------------
This strategy is adapted from the structural bounded-bucket principle of EraRAG
(Zhang et al., arXiv:2506.20963; hyperplane LSH with stored hyperplanes, §III-B;
size-bounded split and merge, Algorithm 1, §III-C; incremental insertion,
Algorithm 3, §III-E; amortised bound, Theorem 4). Only the single-layer
structural partitioning principle is adapted: multi-layer hierarchy, chunk
summarisation, and collapsed tree retrieval are not used. Because EraRAG does
not specify how an oversize bucket is split or how adjacent buckets are ordered,
the concrete mechanisms implemented here—ordering codes by inverse reflected
binary Gray rank ``(gray, name)``, bisecting oversize segments at ``len // 2``,
and resolving adjacency via the boundary proximity tuple—are design choices of
this study, not claims about EraRAG's unstated internals.

Decisions Cited
---------------
  - [D-21]: Embedding payload is the bare concept name via ``embed_text(name)``.
  - [D-24]: Narrowing-only contract; read ``ConceptGraph`` immutably; no LLM calls.
  - [D-25]: Untimed ``setup()``; incremental update in ``on_inserted()`` timed via
    ``update_s``.
  - [D-26], [D-28]: Single-embedding invariant: ``new_name`` is embedded exactly
    once in ``shortlist()``, cached, and reused in ``on_inserted()`` with zero
    embedding calls during update.
  - [D-35](4)(5): Parameters fixed a priori (``s_min=5``, ``s_max=10``,
    ``n_bits=12``, ``seed=42``); sensitivity settings ``(2, 5)`` and ``(10, 20)``.
  - [D-41]: ``max_candidates(n_existing)`` returns ``max(0, min(self.s_max, n_existing))``.
  - [D-50]: Pre-allocated matrix capacity ``max(16, 2 * n)`` in ``setup()`` with
    doubling growth; all-or-nothing ``setup()`` leaving the strategy not set up
    on any failure; ``float64`` hyperplane dot-product projection.
  - [D-58]: ``shortlist()`` clears the per-insertion cache and per-query
    diagnostic fields as its very first executable statements before any check.
  - [D-59]: Strategy 4 normative specification, invariants, complexity, and
    diagnostics.

Bounds & Sufficiency Note
-------------------------
``__init__`` enforces ``s_min >= 2`` and ``s_max >= 2 * s_min``. The relation
``s_max >= 2 * s_min`` is a chosen convention for post-split headroom; it is a
sufficient condition for midpoint bisection closure, not a necessary one
(``s_max >= 2 * s_min - 1`` already guarantees ``(s_max + 1) // 2 >= s_min``).

Complexity of ``on_inserted(new_name, edges)``
----------------------------------------------
  - Hashing: ``O(n_bits * d)`` in ``shortlist()`` (cached and reused in ``on_inserted()``).
  - Home segment lookup (``_locate_home``): ``O(log M)`` binary search over ``M`` segments.
  - Segment insertion and midpoint bisection: ``O(s_max)`` on a list of length ``<= s_max + 1``.
  - Segment list replacement on split: ``O(M)`` C-level pointer shift in Python ``list`` slice assignment.
  - Matrix row write: ``O(d)`` into pre-allocated ``float32`` storage (no reallocation on the first
    insert after ``setup()``, and amortised ``O(d)`` via capacity doubling across streams).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from graph_insertion.embedding import Embedder
from graph_insertion.graph_representation import (
    ConceptGraph,
    _validate_concept_name,
    embed_text,
)
from graph_insertion.strategy import Shortlist

DEFAULT_S_MIN: int = 5
DEFAULT_S_MAX: int = 10
DEFAULT_N_BITS: int = 12
DEFAULT_SEED: int = 42


@dataclass(frozen=True)
class BucketEntry:
    """Immutable metadata record for an indexed concept inside a segment."""

    gray: int
    name: str
    code: int
    row: int

    def sort_key(self) -> tuple[int, str]:
        """Return the canonical global ordering key ``(gray, name)``."""
        return (self.gray, self.name)


class BoundedBucketStrategy:
    """Strategy 4: Bounded-bucket partitioning adapted from EraRAG Algorithms 1 and 3.

    Attributes
    ----------
    name:
        Permanent strategy identifier: ``"bounded_bucket"``.
    uses_embeddings:
        Always ``True``.
    s_min:
        Minimum segment size for graphs with ``n >= s_min`` (default 5).
    s_max:
        Maximum segment size and shortlist cap (default 10).
        Note: ``s_max >= 2 * s_min`` is enforced as a chosen sufficient convention
        for headroom, not a necessary condition (``s_max >= 2 * s_min - 1`` already
        makes a midpoint bisection of ``s_max + 1`` items legal).
    n_bits:
        Number of stored random hyperplanes (default 12).
    seed:
        Seed for the NumPy ``default_rng`` hyperplane generator (default 42).
    """

    name: str = "bounded_bucket"
    uses_embeddings: bool = True

    def __init__(
        self,
        s_min: int = DEFAULT_S_MIN,
        s_max: int = DEFAULT_S_MAX,
        n_bits: int = DEFAULT_N_BITS,
        seed: int = DEFAULT_SEED,
    ) -> None:
        for param_name, val in [
            ("s_min", s_min),
            ("s_max", s_max),
            ("n_bits", n_bits),
            ("seed", seed),
        ]:
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(
                    f"{param_name} must be an integer, got {type(val).__name__}"
                )

        if s_min < 2:
            raise ValueError(f"s_min must be >= 2, got {s_min}")
        if s_max < 2 * s_min:
            raise ValueError(
                f"s_max must be >= 2 * s_min ({2 * s_min}), got {s_max}"
            )
        if n_bits < 1 or n_bits > 62:
            raise ValueError(f"n_bits must be between 1 and 62, got {n_bits}")

        self.s_min: int = int(s_min)
        self.s_max: int = int(s_max)
        self.n_bits: int = int(n_bits)
        self.seed: int = int(seed)

        self._embedder: Optional[Embedder] = None
        self._setup_called: bool = False

        self._dim: Optional[int] = None
        self._hyperplanes: Optional[np.ndarray] = None
        self._mat: Optional[np.ndarray] = None
        self._names: list[str] = []
        self._name_to_idx: dict[str, int] = {}
        self._entry_by_name: dict[str, BucketEntry] = {}
        self._segments: list[list[BucketEntry]] = []
        self._n: int = 0

        self._cached_new_name: Optional[str] = None
        self._cached_new_vec: Optional[np.ndarray] = None
        self._cached_new_code: Optional[int] = None
        self._cached_new_gray: Optional[int] = None

        self._shortlist_called: bool = False
        self._last_bucket_id: Optional[int] = None
        self._last_bucket_gray_min: Optional[int] = None
        self._last_bucket_gray_max: Optional[int] = None
        self._last_query_code: Optional[int] = None
        self._last_query_gray_rank: Optional[int] = None
        self._last_code_existed_in_bucket: bool = False
        self._last_inside_bucket_span: bool = False
        self._last_bucket_size_at_shortlist: int = 0
        self._last_bucket_size: int = 0
        self._last_shortlist_size: int = 0
        self._last_split_occurred: bool = False
        self._last_merge_occurred: bool = False
        self._last_query_vec: Optional[np.ndarray] = None
        self._last_returned_candidates: tuple[str, ...] = ()
        self._last_shortlist_codes: tuple[int, ...] = ()
        self._n_at_query: int = 0
        self._query_name: Optional[str] = None
        self._cached_exact_topk_overlap: Optional[float] = None

    def max_candidates(self, n_existing: int) -> int:
        """Return upper bound on candidates shortlisted when graph has ``n_existing`` nodes.

        Works before ``setup()`` to compute pre-flight planned LLM budgets ([D-41]).
        """
        return max(0, min(self.s_max, n_existing))

    def _draw_hyperplanes(self, dim: int) -> np.ndarray:
        """Draw ``n_bits`` random hyperplanes in R^dim from ``default_rng(self.seed)``.

        Row normalisation to unit length is cosmetic because hyperplane sign bits
        (``dots >= 0.0``) are scale-invariant for positive row norms; kept for clean
        geometric representation of rows as unit normals.
        """
        rng = np.random.default_rng(self.seed)
        raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        return (raw / norms).astype(np.float64, copy=False)

    def _gray_rank(self, code: int) -> int:
        """Compute inverse reflected-Gray rank via prefix XOR shift-doubling."""
        g = int(code)
        shift = 1
        while shift < self.n_bits:
            g ^= g >> shift
            shift <<= 1
        return int(g)

    def _hamming(self, a: int, b: int) -> int:
        """Return Hamming distance between integer bit codes ``a`` and ``b``."""
        return (int(a) ^ int(b)).bit_count()

    def _hash_vector(self, vec: np.ndarray) -> tuple[int, int]:
        """Project normalised 1-D vector in float64 and return ``(code, gray)``."""
        assert self._hyperplanes is not None
        vec64 = np.asarray(vec, dtype=np.float64)
        dots = vec64 @ self._hyperplanes.T
        code = 0
        for r in range(self.n_bits):
            bit = 1 if float(dots[r]) >= 0.0 else 0
            code |= bit << (self.n_bits - 1 - r)
        gray = self._gray_rank(code)
        return int(code), int(gray)

    def _hash_matrix(self, mat: np.ndarray) -> tuple[list[int], list[int]]:
        """Project normalised 2-D matrix in one float64 product and return ``(codes, grays)``."""
        assert self._hyperplanes is not None
        mat64 = np.asarray(mat, dtype=np.float64)
        dots = mat64 @ self._hyperplanes.T
        codes_arr = np.zeros(mat64.shape[0], dtype=np.int64)
        for r in range(self.n_bits):
            bit_col = (dots[:, r] >= 0.0).astype(np.int64)
            codes_arr |= np.left_shift(bit_col, self.n_bits - 1 - r)
        codes = [int(c) for c in codes_arr]
        grays = [self._gray_rank(c) for c in codes]
        return codes, grays

    @staticmethod
    def _bisect_recursive(
        entries: list[BucketEntry], s_max: int
    ) -> list[list[BucketEntry]]:
        """Recursively bisect ``entries`` at ``len // 2`` until every piece has size ``<= s_max``."""
        if len(entries) <= s_max:
            return [entries]
        mid = len(entries) // 2
        return BoundedBucketStrategy._bisect_recursive(
            entries[:mid], s_max
        ) + BoundedBucketStrategy._bisect_recursive(entries[mid:], s_max)

    def _choose_neighbour(
        self,
        left_seg: Optional[list[BucketEntry]],
        right_seg: Optional[list[BucketEntry]],
        cur_first_code: int,
        cur_first_gray: int,
        cur_last_code: int,
        cur_last_gray: int,
    ) -> str:
        """Choose ``'left'`` or ``'right'`` neighbour using the Section 2.5 proximity tuple."""
        if left_seg is None:
            return "right"
        if right_seg is None:
            return "left"
        left_key = (
            self._hamming(left_seg[-1].code, cur_first_code),
            cur_first_gray - left_seg[-1].gray,
            len(left_seg),
            0,
        )
        right_key = (
            self._hamming(cur_last_code, right_seg[0].code),
            right_seg[0].gray - cur_last_gray,
            len(right_seg),
            1,
        )
        return "left" if left_key <= right_key else "right"

    def _locate_home(self, gray: int, name: str, code: int) -> tuple[int, bool]:
        """Locate ``(home_idx, inside_span)`` in ``O(log M)`` via binary search on segment last-keys.

        Read-only; never mutates segment state.
        """
        if not self._segments:
            raise RuntimeError("Cannot locate home segment in an empty index")

        key = (gray, name)
        lo = 0
        hi = len(self._segments) - 1
        pos = len(self._segments)
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._segments[mid][-1].sort_key() >= key:
                pos = mid
                hi = mid - 1
            else:
                lo = mid + 1

        if (
            pos < len(self._segments)
            and self._segments[pos][0].sort_key() <= key <= self._segments[pos][-1].sort_key()
        ):
            return pos, True
        if pos == 0:
            return 0, False
        if pos == len(self._segments):
            return len(self._segments) - 1, False

        side = self._choose_neighbour(
            self._segments[pos - 1],
            self._segments[pos],
            code,
            gray,
            code,
            gray,
        )
        home_idx = (pos - 1) if side == "left" else pos
        return home_idx, False

    def _insert_entry(self, entry: BucketEntry) -> None:
        """Insert ``entry`` into its home segment and split at ``len // 2`` if size exceeds ``s_max``."""
        n_before = self._n - 1
        if not self._segments:
            self._segments = [[entry]]
            self._last_split_occurred = False
            self._last_merge_occurred = False
            self._last_bucket_size = 1
            return

        home_idx, inside_span = self._locate_home(
            entry.gray, entry.name, entry.code
        )
        merge_occurred = (not inside_span) and (n_before >= 1)
        seg = self._segments[home_idx]

        ins_pos = 0
        entry_key = entry.sort_key()
        while ins_pos < len(seg) and seg[ins_pos].sort_key() < entry_key:
            ins_pos += 1
        seg.insert(ins_pos, entry)

        if len(seg) > self.s_max:
            mid = len(seg) // 2
            left_half = seg[:mid]
            right_half = seg[mid:]
            self._segments[home_idx : home_idx + 1] = [left_half, right_half]
            self._last_split_occurred = True
            self._last_bucket_size = (
                len(left_half) if ins_pos < mid else len(right_half)
            )
        else:
            self._last_split_occurred = False
            self._last_bucket_size = len(seg)

        self._last_merge_occurred = merge_occurred

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        """Initialise strategy state and build the bounded-bucket partition in batch (Algorithm 1 style).

        Untimed preparation per [D-25]. Calling ``setup()`` a second time resets all state.
        A failed ``setup()`` (first or second) leaves the strategy in the not-set-up state ([D-50](3)).
        """
        # Reset to not-set-up state immediately at the top of setup() (D-50(3))
        self._setup_called = False
        self._embedder = None

        self._dim = None
        self._hyperplanes = None
        self._mat = None
        self._names = []
        self._name_to_idx = {}
        self._entry_by_name = {}
        self._segments = []
        self._n = 0

        self._cached_new_name = None
        self._cached_new_vec = None
        self._cached_new_code = None
        self._cached_new_gray = None

        self._shortlist_called = False
        self._last_bucket_id = None
        self._last_bucket_gray_min = None
        self._last_bucket_gray_max = None
        self._last_query_code = None
        self._last_query_gray_rank = None
        self._last_code_existed_in_bucket = False
        self._last_inside_bucket_span = False
        self._last_bucket_size_at_shortlist = 0
        self._last_bucket_size = 0
        self._last_shortlist_size = 0
        self._last_split_occurred = False
        self._last_merge_occurred = False
        self._last_query_vec = None
        self._last_returned_candidates = ()
        self._last_shortlist_codes = ()
        self._n_at_query = 0
        self._query_name = None
        self._cached_exact_topk_overlap = None

        nodes = sorted(graph.nodes())
        n = len(nodes)

        if n == 0:
            self._embedder = embedder
            self._setup_called = True
            return

        texts = [embed_text(node) for node in nodes]
        raw_mat = embedder.embed_many(texts)

        if not isinstance(raw_mat, np.ndarray) or raw_mat.ndim != 2:
            raise ValueError(
                f"embed_many must return a 2-D ndarray, got {type(raw_mat)}"
            )
        if raw_mat.shape[0] != n:
            raise ValueError(
                f"embed_many returned {raw_mat.shape[0]} rows, expected {n}"
            )
        if not np.all(np.isfinite(raw_mat)):
            raise ValueError("embed_many returned non-finite embedding vectors")

        norms = np.linalg.norm(raw_mat, axis=1)
        for i, norm_val in enumerate(norms):
            if norm_val == 0.0 or not np.isfinite(norm_val):
                raise ValueError(
                    f"Zero-norm embedding vector for node {nodes[i]!r}"
                )

        dim = int(raw_mat.shape[1])
        if dim == 0:
            raise ValueError("Embedding dimension must be >= 1, got 0")

        normed_mat = (raw_mat / norms[:, np.newaxis]).astype(np.float32)

        # Build everything in locals first before committing to self
        hyperplanes = self._draw_hyperplanes(dim)
        self._hyperplanes = hyperplanes
        codes, grays = self._hash_matrix(normed_mat)

        entries = [
            BucketEntry(gray=grays[i], name=nodes[i], code=codes[i], row=i)
            for i in range(n)
        ]
        entry_by_name = {e.name: e for e in entries}
        entries.sort(key=lambda e: e.sort_key())

        if n < self.s_min:
            segments: list[list[BucketEntry]] = [entries]
        else:
            # Group consecutive entries with identical gray (identical code) into raw buckets
            raw_buckets: list[list[BucketEntry]] = []
            for e in entries:
                if not raw_buckets or raw_buckets[-1][-1].gray != e.gray:
                    raw_buckets.append([e])
                else:
                    raw_buckets[-1].append(e)

            # Split every raw bucket larger than s_max by recursive midpoint bisection
            segments = []
            for bucket in raw_buckets:
                segments.extend(self._bisect_recursive(bucket, self.s_max))

            # Merge undersize segments (< s_min) left-to-right.
            # Termination argument: let M = len(segments) and U = sum_j max(0, s_min - len(S_j)).
            # In every merge step where len(S_i) < s_min:
            #   - If len(combined) <= s_max: M strictly decreases by 1 and U does not increase.
            #   - If len(combined) > s_max: since len(S_i) <= s_min - 1, the chosen neighbour had
            #     size > s_min (deficit 0), and bisecting combined (size in [s_max + 1, s_max + s_min - 1])
            #     at len // 2 produces two segments both in [s_min, s_max] (deficit 0), so M is
            #     unchanged while U strictly decreases by (s_min - len(S_i)) >= 1.
            # Hence M + U <= 2n is a non-negative integer potential that strictly decreases on
            # every merge step, guaranteeing termination in at most 2n iterations.
            i = 0
            while i < len(segments) and len(segments) > 1:
                if len(segments[i]) < self.s_min:
                    cur = segments[i]
                    left_seg = segments[i - 1] if i > 0 else None
                    right_seg = (
                        segments[i + 1] if i + 1 < len(segments) else None
                    )
                    side = self._choose_neighbour(
                        left_seg,
                        right_seg,
                        cur[0].code,
                        cur[0].gray,
                        cur[-1].code,
                        cur[-1].gray,
                    )
                    nbr_idx = (i - 1) if side == "left" else (i + 1)
                    lo_idx = min(i, nbr_idx)
                    hi_idx = max(i, nbr_idx)
                    combined = segments[lo_idx] + segments[hi_idx]
                    if len(combined) <= self.s_max:
                        segments[lo_idx : hi_idx + 1] = [combined]
                    else:
                        mid = len(combined) // 2
                        segments[lo_idx : hi_idx + 1] = [
                            combined[:mid],
                            combined[mid:],
                        ]
                    i = max(0, lo_idx)
                else:
                    i += 1

        capacity = max(16, 2 * n)
        mat = np.zeros((capacity, dim), dtype=np.float32)
        mat[:n] = normed_mat

        self._dim = dim
        self._mat = mat
        self._names = list(nodes)
        self._name_to_idx = {name: idx for idx, name in enumerate(nodes)}
        self._entry_by_name = entry_by_name
        self._segments = segments
        self._n = n

        self._embedder = embedder
        self._setup_called = True

    def shortlist(self, new_name: str) -> Shortlist:
        """Produce a shortlist of candidate concepts from the home segment of ``new_name``.

        Does not mutate ``_segments``, ``_mat``, or ``_n``. Clears per-insertion cache
        and per-query diagnostic fields as the first executable statements ([D-58]).
        """
        # 1. Clear cache and per-query diagnostic fields as the FIRST executable statements (D-58)
        self._cached_new_name = None
        self._cached_new_vec = None
        self._cached_new_code = None
        self._cached_new_gray = None

        self._shortlist_called = False
        self._last_bucket_id = None
        self._last_bucket_gray_min = None
        self._last_bucket_gray_max = None
        self._last_query_code = None
        self._last_query_gray_rank = None
        self._last_code_existed_in_bucket = False
        self._last_inside_bucket_span = False
        self._last_bucket_size_at_shortlist = 0
        self._last_bucket_size = 0
        self._last_shortlist_size = 0
        self._last_split_occurred = False
        self._last_merge_occurred = False
        self._last_query_vec = None
        self._last_returned_candidates = ()
        self._last_shortlist_codes = ()
        self._n_at_query = 0
        self._query_name = None
        self._cached_exact_topk_overlap = None

        # 2. Not-set-up check and concept name validation
        if not self._setup_called or self._embedder is None:
            raise RuntimeError("setup() must be called before shortlist()")

        _validate_concept_name(new_name)

        # 3. Embed once and validate vector exactly as Strategy 3 does
        raw_vec = self._embedder.embed(embed_text(new_name))

        if not isinstance(raw_vec, np.ndarray) or raw_vec.ndim != 1:
            got_type = (
                type(raw_vec).__name__
                if not isinstance(raw_vec, np.ndarray)
                else f"{raw_vec.ndim}-D"
            )
            raise ValueError(
                f"Embedding for {new_name!r} must be 1-D ndarray, got {got_type}"
            )
        if not np.all(np.isfinite(raw_vec)):
            raise ValueError(
                f"Embedding for {new_name!r} contains non-finite values"
            )

        norm = float(np.linalg.norm(raw_vec))
        if norm == 0.0 or not np.isfinite(norm):
            raise ValueError(
                f"Zero-norm embedding vector for concept {new_name!r}"
            )

        if self._dim is not None:
            if raw_vec.shape[0] != self._dim:
                raise ValueError(
                    f"Dimension mismatch for {new_name!r}: expected {self._dim}, got {raw_vec.shape[0]}"
                )
        else:
            dim = int(raw_vec.shape[0])
            if dim == 0:
                raise ValueError("Embedding dimension must be >= 1, got 0")
            self._dim = dim
            self._hyperplanes = self._draw_hyperplanes(dim)
            self._mat = np.zeros((16, dim), dtype=np.float32)

        # 4. Normalise to float32, hash in float64, cache vector, code and gray
        q = (raw_vec / norm).astype(np.float32, copy=False)
        q = np.ascontiguousarray(q, dtype=np.float32)
        code, gray = self._hash_vector(q)

        self._cached_new_name = new_name
        self._cached_new_vec = q
        self._cached_new_code = code
        self._cached_new_gray = gray

        self._shortlist_called = True
        self._last_query_code = code
        self._last_query_gray_rank = gray
        self._last_query_vec = q
        self._n_at_query = self._n
        self._query_name = new_name

        # 5. Empty index: return empty tuples
        if self._n == 0:
            return Shortlist(candidates=(), scores=())

        # 6. Locate home segment in O(log M), score its members, sort by (-score, name)
        assert self._mat is not None
        home_idx, inside_span = self._locate_home(gray, new_name, code)
        seg = self._segments[home_idx]

        self._last_bucket_id = int(home_idx)
        self._last_bucket_gray_min = int(seg[0].gray)
        self._last_bucket_gray_max = int(seg[-1].gray)
        self._last_inside_bucket_span = bool(inside_span)
        self._last_bucket_size_at_shortlist = len(seg)
        self._last_bucket_size = len(seg)
        self._last_code_existed_in_bucket = any(e.code == code for e in seg)

        filtered_entries = [e for e in seg if e.name != new_name]
        if not filtered_entries:
            self._last_shortlist_size = 0
            self._last_returned_candidates = ()
            self._last_shortlist_codes = ()
            return Shortlist(candidates=(), scores=())

        rows = [e.row for e in filtered_entries]
        sub_mat = self._mat[rows]
        raw_scores = sub_mat @ q

        paired = [
            (float(raw_scores[i]), filtered_entries[i].name, filtered_entries[i].code)
            for i in range(len(filtered_entries))
        ]
        paired.sort(key=lambda item: (-item[0], item[1]))

        candidates = tuple(name for _, name, _ in paired)
        scores = tuple(score for score, _, _ in paired)
        shortlist_codes = tuple(c_code for _, _, c_code in paired)

        self._last_shortlist_size = len(candidates)
        self._last_returned_candidates = candidates
        self._last_shortlist_codes = shortlist_codes

        return Shortlist(candidates=candidates, scores=scores)

    def on_inserted(
        self, new_name: str, edges: tuple[tuple[str, str], ...]
    ) -> None:
        """Incrementally insert ``new_name`` into its home segment and locally split on overflow.

        Reuses the cached embedding and hash from ``shortlist()``; makes zero embedder calls.
        The ``edges`` parameter is accepted and ignored because partitioning depends only on
        concept embeddings.

        Complexity
        ----------
        - Hashing: ``O(n_bits * d)`` performed in ``shortlist()`` and reused from cache.
        - Home lookup (``_locate_home``): ``O(log M)`` binary search over ``M`` segments.
        - Segment insertion and midpoint bisection: ``O(s_max)``.
        - Segment list slice assignment on split: ``O(M)`` C-level pointer shift, which is bounded.
        - Matrix row write: ``O(d)`` (capacity ``max(16, 2 * n)`` prevents reallocation on the
          first timed insert after ``setup()``, and doubling growth gives amortised ``O(d)``).
        """
        if (
            self._cached_new_name is None
            or self._cached_new_name != new_name
            or self._cached_new_vec is None
            or self._cached_new_code is None
            or self._cached_new_gray is None
        ):
            raise RuntimeError(
                f"on_inserted({new_name!r}) called without matching shortlist() call"
            )
        if new_name in self._name_to_idx:
            raise ValueError(
                f"Concept {new_name!r} is already present in the index"
            )

        vec = self._cached_new_vec
        code = self._cached_new_code
        gray = self._cached_new_gray

        self._cached_new_name = None
        self._cached_new_vec = None
        self._cached_new_code = None
        self._cached_new_gray = None

        assert self._dim is not None

        if self._mat is None:
            self._mat = np.zeros((16, self._dim), dtype=np.float32)
        elif self._n >= self._mat.shape[0]:
            new_capacity = self._mat.shape[0] * 2
            new_mat = np.zeros((new_capacity, self._dim), dtype=np.float32)
            new_mat[: self._n] = self._mat[: self._n]
            self._mat = new_mat

        row = self._n
        self._mat[row] = vec
        self._names.append(new_name)
        self._name_to_idx[new_name] = row
        self._n += 1

        entry = BucketEntry(gray=gray, name=new_name, code=code, row=row)
        self._entry_by_name[new_name] = entry
        self._insert_entry(entry)

    def _compute_exact_topk_overlap(self) -> Optional[float]:
        """Compute fraction of exact top-m cosine neighbours contained in the returned shortlist.

        ``m = min(self.s_max, n_at_query)`` (excluding ``_query_name``, ties broken by name).
        Returns ``1.0`` when ``n_at_query == 0``, and ``None`` before any ``shortlist()`` call.
        """
        if not self._shortlist_called or self._last_query_vec is None:
            return None
        if self._n_at_query == 0:
            return 1.0

        assert self._mat is not None
        cosines = self._mat[: self._n_at_query] @ self._last_query_vec
        names_at_query = self._names[: self._n_at_query]
        valid_items = [
            (float(cosines[i]), names_at_query[i])
            for i in range(self._n_at_query)
            if names_at_query[i] != self._query_name
        ]
        valid_items.sort(key=lambda item: (-item[0], item[1]))
        m = min(self.s_max, len(valid_items))
        if m == 0:
            return 1.0

        exact_set = {name for _, name in valid_items[:m]}
        matched = sum(
            1 for cand in self._last_returned_candidates if cand in exact_set
        )
        return float(matched / m)

    def config(self) -> dict[str, Any]:
        """Return strategy configuration hyperparameters as plain Python ``int`` values."""
        return {
            "s_min": int(self.s_min),
            "s_max": int(self.s_max),
            "n_bits": int(self.n_bits),
            "seed": int(self.seed),
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return JSON-serialisable operational diagnostics for the most recent trial.

        Computed outside the timed windows (``shortlist_s`` and ``update_s``).
        Note that ``exact_topk_overlap`` measures partition loss plus embedding loss
        together (relative to exact top-m cosine over the index), whereas
        ``min_hamming_to_shortlist`` shows how close in Hamming space the
        Gray-interval home segment is to the query code.
        """
        if self._cached_exact_topk_overlap is None and self._shortlist_called:
            self._cached_exact_topk_overlap = self._compute_exact_topk_overlap()

        num_segments = len(self._segments)
        if num_segments > 0:
            seg_sizes = [len(s) for s in self._segments]
            min_seg_size = int(min(seg_sizes))
            max_seg_size = int(max(seg_sizes))
            mean_seg_size = float(sum(seg_sizes) / num_segments)
        else:
            min_seg_size = 0
            max_seg_size = 0
            mean_seg_size = 0.0

        if (
            self._last_query_code is not None
            and len(self._last_shortlist_codes) > 0
        ):
            min_hamming: Optional[int] = int(
                min(
                    self._hamming(self._last_query_code, c_code)
                    for c_code in self._last_shortlist_codes
                )
            )
        else:
            min_hamming = None

        return {
            "bucket_id": (
                int(self._last_bucket_id)
                if self._last_bucket_id is not None
                else None
            ),
            "bucket_gray_min": (
                int(self._last_bucket_gray_min)
                if self._last_bucket_gray_min is not None
                else None
            ),
            "bucket_gray_max": (
                int(self._last_bucket_gray_max)
                if self._last_bucket_gray_max is not None
                else None
            ),
            "query_code": (
                int(self._last_query_code)
                if self._last_query_code is not None
                else None
            ),
            "query_gray_rank": (
                int(self._last_query_gray_rank)
                if self._last_query_gray_rank is not None
                else None
            ),
            "code_existed_in_bucket": bool(self._last_code_existed_in_bucket),
            "inside_bucket_span": bool(self._last_inside_bucket_span),
            "bucket_size_at_shortlist": int(self._last_bucket_size_at_shortlist),
            "bucket_size": int(self._last_bucket_size),
            "shortlist_size": int(self._last_shortlist_size),
            "split_occurred": bool(self._last_split_occurred),
            "merge_occurred": bool(self._last_merge_occurred),
            "num_segments": int(num_segments),
            "min_segment_size": int(min_seg_size),
            "max_segment_size": int(max_seg_size),
            "mean_segment_size": float(mean_seg_size),
            "exact_topk_overlap": (
                float(self._cached_exact_topk_overlap)
                if self._cached_exact_topk_overlap is not None
                else None
            ),
            "min_hamming_to_shortlist": min_hamming,
        }
