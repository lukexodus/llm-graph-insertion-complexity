"""tests/test_bounded_bucket_strategy.py — STRAT-004
====================================================
Conformance, invariant, determinism, lifecycle, diagnostics, and mutation-killing
tests for BoundedBucketStrategy (Strategy 4).
"""

from __future__ import annotations

import json
from typing import Any, Callable, Sequence

import numpy as np
import pytest

from graph_insertion.decision import PairwiseDecisionStep
from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph, embed_text
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    run_sweep_experiment,
)
from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
from graph_insertion.strategies.bounded_bucket import (
    DEFAULT_N_BITS,
    DEFAULT_S_MAX,
    DEFAULT_S_MIN,
    DEFAULT_SEED,
    BoundedBucketStrategy,
    BucketEntry,
)
from graph_insertion.strategy import (
    NarrowingStrategy,
    Shortlist,
    candidate_upper_bound,
    insert_node,
)
from tests.controllable_embedder import ControllableEmbedder, vector_with_cosine
from tests.test_strategy_interface import FakeDecisionStep, StrategyConformanceSuite


def _assert_no_numpy_types(obj: Any) -> None:
    """Assert recursively that no NumPy scalar or array types appear in a structure."""
    if isinstance(obj, (np.generic, np.ndarray)):
        raise AssertionError(f"Found numpy type {type(obj)} in {obj!r}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_numpy_types(k)
            _assert_no_numpy_types(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _assert_no_numpy_types(item)


def _assert_partition_invariants(
    strat: BoundedBucketStrategy, expected_nodes: set[str]
) -> None:
    """Verify size bounds, global (gray, name) strict ordering, and exact node coverage."""
    n = len(expected_nodes)
    assert strat._n == n
    segs = strat._segments

    if n == 0:
        assert segs == []
        return

    if n < strat.s_min:
        assert len(segs) == 1
        assert len(segs[0]) == n
    else:
        assert len(segs) >= 1
        for seg in segs:
            assert strat.s_min <= len(seg) <= strat.s_max

    all_entries: list[BucketEntry] = []
    for seg in segs:
        for i in range(len(seg) - 1):
            assert seg[i].sort_key() < seg[i + 1].sort_key()
        all_entries.extend(seg)

    for i in range(len(all_entries) - 1):
        assert all_entries[i].sort_key() < all_entries[i + 1].sort_key()

    seen_names = [e.name for e in all_entries]
    assert len(seen_names) == n
    assert set(seen_names) == expected_nodes


# ===========================================================================
# 1. StrategyConformanceSuite Subclasses
# ===========================================================================


class TestBoundedBucketDefaultConformance(StrategyConformanceSuite):
    """Proves BoundedBucketStrategy satisfies the StrategyConformanceSuite contract at defaults."""

    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(
        self,
    ) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
            strat = BoundedBucketStrategy()
            strat.setup(graph, embedder)
            return strat

        return _factory


class TestBoundedBucketSmallParamsConformance(StrategyConformanceSuite):
    """Proves BoundedBucketStrategy satisfies the StrategyConformanceSuite contract with small bounds."""

    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(
        self,
    ) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
            strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=6, seed=7)
            strat.setup(graph, embedder)
            return strat

        return _factory


# ===========================================================================
# 2. Constructor Parameter Validation
# ===========================================================================


class TestInitValidation:
    """Proves __init__ rejects bools, non-ints, s_min < 2, s_max < 2 * s_min, and out-of-range n_bits."""

    @pytest.mark.parametrize("bad_val", [True, False, 2.5, "5", None, [5]])
    def test_non_int_or_bool_rejected_for_all_params(self, bad_val: Any) -> None:
        """Proves each of s_min, s_max, n_bits, and seed rejects bool and non-int values."""
        with pytest.raises(ValueError, match="s_min must be an integer"):
            BoundedBucketStrategy(s_min=bad_val, s_max=10)
        with pytest.raises(ValueError, match="s_max must be an integer"):
            BoundedBucketStrategy(s_min=5, s_max=bad_val)
        with pytest.raises(ValueError, match="n_bits must be an integer"):
            BoundedBucketStrategy(n_bits=bad_val)
        with pytest.raises(ValueError, match="seed must be an integer"):
            BoundedBucketStrategy(seed=bad_val)

    @pytest.mark.parametrize("bad_s_min", [1, 0, -1, -10])
    def test_s_min_below_two_rejected(self, bad_s_min: int) -> None:
        """Proves s_min < 2 raises ValueError even when s_max >= 2 * s_min."""
        with pytest.raises(ValueError, match="s_min must be >= 2"):
            BoundedBucketStrategy(s_min=bad_s_min, s_max=10)

    @pytest.mark.parametrize(
        "s_min,bad_s_max",
        [(2, 3), (2, 2), (3, 5), (5, 9), (5, 5), (10, 19)],
    )
    def test_s_max_below_two_s_min_rejected(
        self, s_min: int, bad_s_max: int
    ) -> None:
        """Proves s_max < 2 * s_min raises ValueError."""
        with pytest.raises(ValueError, match="s_max must be >= 2 \\* s_min"):
            BoundedBucketStrategy(s_min=s_min, s_max=bad_s_max)

    @pytest.mark.parametrize("bad_n_bits", [0, -1, 63, 64, 100])
    def test_n_bits_out_of_range_rejected(self, bad_n_bits: int) -> None:
        """Proves n_bits outside [1, 62] raises ValueError."""
        with pytest.raises(ValueError, match="n_bits must be between 1 and 62"):
            BoundedBucketStrategy(n_bits=bad_n_bits)

    def test_valid_boundary_parameters_accepted(self) -> None:
        """Proves boundary settings (s_min=2, s_max=4, n_bits=1 and n_bits=62) succeed."""
        s1 = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=1, seed=-7)
        assert (s1.s_min, s1.s_max, s1.n_bits, s1.seed) == (2, 4, 1, -7)
        s2 = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=62, seed=0)
        assert s2.n_bits == 62


# ===========================================================================
# 3. Strategy Name, uses_embeddings, and config()
# ===========================================================================


class TestInterfaceAndConfig:
    """Proves permanent strategy name, uses_embeddings class attribute, and config() schema."""

    def test_name_uses_embeddings_and_config_keys(self) -> None:
        """Proves BoundedBucketStrategy exposes permanent name, uses_embeddings=True, and 4 int config keys."""
        assert BoundedBucketStrategy.name == "bounded_bucket"
        assert BoundedBucketStrategy.uses_embeddings is True

        strat = BoundedBucketStrategy()
        assert strat.name == "bounded_bucket"
        assert strat.uses_embeddings is True
        assert (strat.s_min, strat.s_max, strat.n_bits, strat.seed) == (
            DEFAULT_S_MIN,
            DEFAULT_S_MAX,
            DEFAULT_N_BITS,
            DEFAULT_SEED,
        )

        cfg = strat.config()
        assert cfg == {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
        assert set(cfg.keys()) == {"s_min", "s_max", "n_bits", "seed"}
        for k, v in cfg.items():
            assert isinstance(v, int) and not isinstance(v, bool), f"Key {k} not plain int"
        _assert_no_numpy_types(cfg)
        assert json.loads(json.dumps(cfg)) == cfg


# ===========================================================================
# 4. max_candidates and Call Bounds Over D-35 Sweep and Accuracy Mode
# ===========================================================================


class TestMaxCandidatesAndBudgets:
    """Proves max_candidates formula and planned-call upper bounds across sweep and accuracy matrices."""

    def test_max_candidates_values_and_negative_clamping(self) -> None:
        """Proves max_candidates returns max(0, min(s_max, n_existing)) before setup()."""
        strat = BoundedBucketStrategy(s_min=5, s_max=10)
        expected = {
            -5: 0,
            -1: 0,
            0: 0,
            3: 3,
            5: 5,
            10: 10,
            50: 10,
            2000: 10,
        }
        for n_val, exp in expected.items():
            assert strat.max_candidates(n_val) == exp
            assert candidate_upper_bound(strat, n_val) == max(0, min(n_val, exp))

    def test_d35_sweep_and_accuracy_planned_call_bounds(self) -> None:
        """Proves D-35 sweep bounds (600, 300, 1200) and accuracy bounds (590, 295, 1180)."""
        sweep_sizes = (50, 100, 200, 500, 1000, 2000)
        sweep_trials = 10
        accuracy_n_existing = [28] * 29 + [140] * 30

        cases = [
            (5, 10, 600, 590),
            (2, 5, 300, 295),
            (10, 20, 1200, 1180),
        ]
        for s_min, s_max, exp_sweep, exp_acc in cases:
            strat = BoundedBucketStrategy(s_min=s_min, s_max=s_max)
            sweep_bound = sum(
                candidate_upper_bound(strat, sz) * sweep_trials
                for sz in sweep_sizes
            )
            acc_bound = sum(
                candidate_upper_bound(strat, n_ex)
                for n_ex in accuracy_n_existing
            )
            assert sweep_bound == exp_sweep
            assert acc_bound == exp_acc


# ===========================================================================
# 5. Partition Size Invariants, Global Ordering, and Node Coverage
# ===========================================================================


class TestPartitionInvariants:
    """Proves size bounds, strictly increasing (gray, name) order, and exact coverage across sizes."""

    def test_invariants_after_batch_setup_for_n_0_to_60(self) -> None:
        """Proves batch setup() satisfies partition invariants for every n in 0..60."""
        embedder = FakeEmbedder(dim=16, seed=42)
        for n in range(0, 61):
            graph = ConceptGraph()
            names = {f"node_{i:03d}" for i in range(n)}
            for name in sorted(names):
                graph.add_node(name)
            strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=8, seed=11)
            strat.setup(graph, embedder)
            _assert_partition_invariants(strat, names)

    @pytest.mark.parametrize("n", [100, 500, 2000])
    def test_invariants_after_batch_setup_large_n(self, n: int) -> None:
        """Proves batch setup() satisfies partition invariants at n in {100, 500, 2000}."""
        embedder = FakeEmbedder(dim=32, seed=99)
        graph = ConceptGraph()
        names = {f"concept_{i:04d}" for i in range(n)}
        for name in sorted(names):
            graph.add_node(name)
        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=12, seed=42)
        strat.setup(graph, embedder)
        _assert_partition_invariants(strat, names)

    def test_invariants_across_65_sequential_inserts_from_empty(self) -> None:
        """Proves partition invariants hold after every single insert from n=0 to n=65."""
        embedder = FakeEmbedder(dim=16, seed=77)
        meter = MeteredEmbedder(embedder)
        decision = FakeDecisionStep(make_edge=False)
        graph = ConceptGraph()
        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=8, seed=42)
        strat.setup(graph, meter)

        expected_nodes: set[str] = set()
        _assert_partition_invariants(strat, expected_nodes)

        for i in range(65):
            new_name = f"seq_node_{i:03d}"
            insert_node(
                strat, graph, decision, new_name, metered_embedder=meter
            )
            expected_nodes.add(new_name)
            _assert_partition_invariants(strat, expected_nodes)


# ===========================================================================
# 6. Determinism and Insertion-Order Invariance
# ===========================================================================


class TestDeterminism:
    """Proves two builds on graphs with different node insertion orders produce identical state."""

    def test_node_addition_order_invariance(self) -> None:
        """Proves hyperplanes, segments, shortlists, and diagnostics are identical regardless of graph node order."""
        names = [f"concept_{i:03d}" for i in range(35)]
        g_forward = ConceptGraph()
        for name in names:
            g_forward.add_node(name)

        g_reverse = ConceptGraph()
        for name in reversed(names):
            g_reverse.add_node(name)

        emb1 = FakeEmbedder(dim=16, seed=42)
        emb2 = FakeEmbedder(dim=16, seed=42)

        s1 = BoundedBucketStrategy(s_min=4, s_max=8, n_bits=10, seed=42)
        s2 = BoundedBucketStrategy(s_min=4, s_max=8, n_bits=10, seed=42)
        s1.setup(g_forward, emb1)
        s2.setup(g_reverse, emb2)

        assert s1._hyperplanes is not None and s2._hyperplanes is not None
        assert np.array_equal(s1._hyperplanes, s2._hyperplanes)
        assert s1._names == s2._names
        assert s1._segments == s2._segments

        for q in ["probe_alpha", "probe_beta", "probe_gamma"]:
            sl1 = s1.shortlist(q)
            sl2 = s2.shortlist(q)
            assert sl1 == sl2
            assert s1.diagnostics() == s2.diagnostics()


# ===========================================================================
# 7. Hyperplanes Drawing, Lazy Initialisation, and Validation Rollback
# ===========================================================================


class TestHyperplanes:
    """Proves hyperplane shape, dtype, unit row norms, regeneration on second setup, and lazy init."""

    def test_hyperplane_properties_and_regeneration(self) -> None:
        """Proves _hyperplanes has shape (n_bits, dim), float64, unit rows, and regenerates identically."""
        graph = ConceptGraph()
        graph.add_node("n0")
        graph.add_node("n1")
        embedder = FakeEmbedder(dim=24, seed=42)

        strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=12, seed=123)
        strat.setup(graph, embedder)

        H1 = strat._hyperplanes
        assert H1 is not None
        assert H1.shape == (12, 24)
        assert H1.dtype == np.float64
        row_norms = np.linalg.norm(H1, axis=1)
        assert np.allclose(row_norms, 1.0, atol=1e-12)

        # Mutate copy and re-run setup() to verify identical regeneration
        H1_copy = H1.copy()
        strat.setup(graph, embedder)
        assert strat._hyperplanes is not None
        assert np.array_equal(strat._hyperplanes, H1_copy)

    def test_lazy_hyperplanes_match_non_empty_setup_and_rollback_on_bad_first_query(
        self,
    ) -> None:
        """Proves empty setup draws identical hyperplanes on first valid shortlist and commits nothing on failure."""
        embedder = FakeEmbedder(dim=16, seed=42)
        g_nonempty = ConceptGraph()
        g_nonempty.add_node("a")
        s_nonempty = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=10, seed=99)
        s_nonempty.setup(g_nonempty, embedder)

        s_lazy = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=10, seed=99)
        s_lazy.setup(ConceptGraph(), embedder)
        assert s_lazy._dim is None
        assert s_lazy._hyperplanes is None
        assert s_lazy._mat is None

        # Failing first shortlist on empty index must not commit _dim, _hyperplanes, or _mat
        bad_emb = ControllableEmbedder(
            {"bad_zero": np.zeros(16, dtype=np.float32)}, dim=16
        )
        s_fail_lazy = BoundedBucketStrategy(
            s_min=2, s_max=5, n_bits=10, seed=99
        )
        s_fail_lazy.setup(ConceptGraph(), bad_emb)
        with pytest.raises(ValueError, match="Zero-norm"):
            s_fail_lazy.shortlist("bad_zero")
        assert s_fail_lazy._dim is None
        assert s_fail_lazy._hyperplanes is None
        assert s_fail_lazy._mat is None

        # Valid first shortlist on empty index initialises identical hyperplanes
        sl = s_lazy.shortlist("a")
        assert sl == Shortlist(candidates=(), scores=())
        assert s_lazy._dim == 16
        assert s_lazy._hyperplanes is not None
        assert s_nonempty._hyperplanes is not None
        assert np.array_equal(s_lazy._hyperplanes, s_nonempty._hyperplanes)


# ===========================================================================
# 8. Hash Functions, Gray Rank, MSB Packing, Exact Zero Dot, Float64 Projection
# ===========================================================================


class TestHashingAndGrayOrder:
    """Proves _gray_rank bijection, MSB-first bit packing, dot==0.0 -> bit 1, and float64 projection."""

    def test_gray_rank_all_4096_12bit_codes(self) -> None:
        """Proves _gray_rank is the inverse of g ^ (g >> 1) for all 4,096 12-bit codes and adjacent ranks differ by 1 bit."""
        strat = BoundedBucketStrategy(n_bits=12)
        code_for_rank: dict[int, int] = {}
        for code in range(4096):
            g = strat._gray_rank(code)
            assert 0 <= g < 4096
            # Reference forward Gray code: g ^ (g >> 1) must equal code
            assert (g ^ (g >> 1)) == code
            code_for_rank[g] = code

        assert len(code_for_rank) == 4096
        for g in range(4095):
            assert strat._hamming(code_for_rank[g], code_for_rank[g + 1]) == 1

    def test_msb_first_packing_and_exact_zero_dot_product(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves hyperplane 0 is MSB and dot == 0.0 yields bit 1 in both batch and single-vector paths."""
        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=3, seed=42)
        # 3 axis-aligned hyperplanes in R^4: e_0, e_1, e_2
        fixed_H = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ],
            dtype=np.float64,
        )
        monkeypatch.setattr(strat, "_draw_hyperplanes", lambda dim: fixed_H)

        # n_pos0_neg12 has dots (+1, -1, -1) -> bits (1, 0, 0) -> MSB code = 4 (not LSB 1)
        # n_zero_all has vector (0, 0, 0, 1) -> exact 0.0 dot with all 3 planes -> bits (1, 1, 1) -> code = 7
        vectors = {
            "n_msb": np.array([1.0, -1.0, -1.0, 0.0], dtype=np.float32),
            "n_zero": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
            "q_zero": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
            "q_lsb": np.array([-1.0, -1.0, 1.0, 0.0], dtype=np.float32),
        }
        emb = ControllableEmbedder(vectors, dim=4)
        graph = ConceptGraph()
        graph.add_node("n_msb")
        graph.add_node("n_zero")
        strat.setup(graph, emb)

        assert strat._entry_by_name["n_msb"].code == 0b100
        assert strat._entry_by_name["n_zero"].code == 0b111

        strat.shortlist("q_zero")
        assert strat.diagnostics()["query_code"] == 0b111

        strat.shortlist("q_lsb")
        assert strat.diagnostics()["query_code"] == 0b001

    def test_float64_projection_distinguishes_sub_float32_cancellation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves projection is computed in float64 rather than float32 (kills M-29)."""
        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=1, seed=42)
        # In float64, -0.5 - 1e-12 is strictly less than -0.5; in float32 it rounds to -0.5.
        raw_h = np.array([[0.5, -0.5, 0.5, -0.5 - 1e-12]], dtype=np.float64)
        raw_h /= np.linalg.norm(raw_h, axis=1, keepdims=True)
        monkeypatch.setattr(strat, "_draw_hyperplanes", lambda dim: raw_h)

        # v = [0.5, 0.5, 0.5, 0.5] is exact in both float32 and float64.
        # float64 dot is negative (< 0.0 -> bit 0); float32 dot cancels to 0.0 (>= 0.0 -> bit 1).
        v = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        emb = ControllableEmbedder({"node_a": v, "probe_a": v}, dim=4)
        graph = ConceptGraph()
        graph.add_node("node_a")
        strat.setup(graph, emb)

        assert strat._entry_by_name["node_a"].code == 0
        strat.shortlist("probe_a")
        assert strat.diagnostics()["query_code"] == 0


# ===========================================================================
# 9. Forced Split and Duplicate Vectors
# ===========================================================================


class TestForcedSplitAndDuplicates:
    """Proves midpoint bisection on s_max + 1 items and deterministic tie-splitting on duplicate vectors."""

    def test_forced_split_at_s_max_plus_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves inserting the (s_max + 1)-th node into a segment splits it into len // 2 and len - len // 2."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=2, seed=42)
        fixed_H = np.array(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float64
        )
        monkeypatch.setattr(strat, "_draw_hyperplanes", lambda dim: fixed_H)

        same_vec = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)
        names = [f"c_{i:02d}" for i in range(5)]
        vecs = {name: same_vec for name in names}
        vecs["c_05"] = same_vec
        vecs["c_06"] = same_vec

        emb = ControllableEmbedder(vecs, dim=4)
        meter = MeteredEmbedder(emb)
        graph = ConceptGraph()
        for name in names:
            graph.add_node(name)

        strat.setup(graph, meter)
        assert len(strat._segments) == 1
        assert len(strat._segments[0]) == 5

        # Inserting the 6th item reaches exactly s_max=6: must NOT split (kills M-15)
        res5 = insert_node(
            strat,
            graph,
            FakeDecisionStep(make_edge=False),
            "c_05",
            metered_embedder=meter,
        )
        diag5 = res5.metrics.extra
        assert diag5["split_occurred"] is False
        assert diag5["num_segments"] == 1
        assert [len(s) for s in strat._segments] == [6]
        assert diag5["bucket_size"] == 6

        # Inserting the 7th item reaches s_max + 1 = 7: MUST split into (3, 4)
        res = insert_node(
            strat,
            graph,
            FakeDecisionStep(make_edge=False),
            "c_06",
            metered_embedder=meter,
        )
        diag = res.metrics.extra
        assert diag["split_occurred"] is True
        assert diag["num_segments"] == 2
        assert [len(s) for s in strat._segments] == [3, 4]
        assert [e.name for e in strat._segments[0]] == ["c_00", "c_01", "c_02"]
        assert [e.name for e in strat._segments[1]] == [
            "c_03",
            "c_04",
            "c_05",
            "c_06",
        ]
        # c_06 landed in the second half of size 4
        assert diag["bucket_size"] == 4

    def test_duplicate_vectors_in_setup_and_insert_split_by_name(self) -> None:
        """Proves 2 * s_max + 3 identical vectors terminate in setup() and insert_node() and split by name."""
        s_min, s_max = 3, 6
        count = 2 * s_max + 3  # 15
        same_vec = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
        names = [f"dup_{i:02d}" for i in range(count)]
        vecs = {name: same_vec for name in names}
        vecs["dup_99"] = same_vec

        emb = ControllableEmbedder(vecs, dim=4)
        meter = MeteredEmbedder(emb)
        graph = ConceptGraph()
        for name in names:
            graph.add_node(name)

        strat = BoundedBucketStrategy(s_min=s_min, s_max=s_max, n_bits=4, seed=42)
        strat.setup(graph, meter)
        _assert_partition_invariants(strat, set(names))
        # 15 items bisected recursively: 15 -> (7, 8) -> (3, 4, 4, 4)
        assert [len(s) for s in strat._segments] == [3, 4, 4, 4]

        insert_node(
            strat,
            graph,
            FakeDecisionStep(make_edge=False),
            "dup_99",
            metered_embedder=meter,
        )
        _assert_partition_invariants(strat, set(names) | {"dup_99"})


# ===========================================================================
# 10 & 11. Forced Merge, Gap Insertion, and 4-Component Neighbour Rule
# ===========================================================================


class TestMergeAndNeighbourRule:
    """Proves forced merge in setup(), gap merge in on_inserted(), and each component of _choose_neighbour."""

    @staticmethod
    def _vec_for_code(code: int, n_bits: int) -> np.ndarray:
        """Construct a vector in R^n_bits whose sign bits with identity hyperplanes equal code."""
        v = np.zeros(n_bits, dtype=np.float32)
        for r in range(n_bits):
            bit = (code >> (n_bits - 1 - r)) & 1
            v[r] = 1.0 if bit == 1 else -1.0
        return v

    def test_neighbour_rule_component_1_hamming_decisive_over_gray_gap(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves smaller Hamming distance wins even when the other neighbour has a smaller Gray-rank gap (kills M-25)."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )

        # In 4-bit Gray rank:
        # Left segment at gray=1 (code=0b0001=1), 3 nodes
        # Middle undersized bucket at gray=4 (code=0b0110=6), 1 node:
        #   - to Left (gray=1, code=1): hamming(1, 6) = 3, gray_gap = 4 - 1 = 3
        #   - to Right (gray=8, code=0b1100=12): hamming(6, 12) = 2, gray_gap = 8 - 4 = 4
        # Hamming (2 < 3) chooses Right even though Left has smaller gray_gap (3 < 4)!
        vecs: dict[str, np.ndarray] = {}
        for i in range(3):
            vecs[f"left_{i}"] = self._vec_for_code(0b0001, 4)
        vecs["mid_0"] = self._vec_for_code(0b0110, 4)
        for i in range(3):
            vecs[f"right_{i}"] = self._vec_for_code(0b1100, 4)
        # Also test a gap query at gray=4 (code=0b0110) on a 2-segment index (Left and Right only)
        vecs["gap_query"] = self._vec_for_code(0b0110, 4)

        emb = ControllableEmbedder(vecs, dim=4)
        g_merge = ConceptGraph()
        for name in ["left_0", "left_1", "left_2", "mid_0", "right_0", "right_1", "right_2"]:
            g_merge.add_node(name)

        strat.setup(g_merge, emb)
        assert len(strat._segments) == 2
        # mid_0 must have merged into Right (segment 1), leaving Left of size 3 and Right of size 4
        assert [e.name for e in strat._segments[0]] == ["left_0", "left_1", "left_2"]
        assert [e.name for e in strat._segments[1]] == [
            "mid_0",
            "right_0",
            "right_1",
            "right_2",
        ]

        # Now test gap query on Left + Right without mid_0
        g_gap = ConceptGraph()
        for name in ["left_0", "left_1", "left_2", "right_0", "right_1", "right_2"]:
            g_gap.add_node(name)
        strat.setup(g_gap, emb)
        sl = strat.shortlist("gap_query")
        assert set(sl.candidates) == {"right_0", "right_1", "right_2"}
        diag_before = strat.diagnostics()
        assert diag_before["bucket_id"] == 1
        assert diag_before["inside_bucket_span"] is False
        assert diag_before["merge_occurred"] is False

        strat.on_inserted("gap_query", ())
        diag_after = strat.diagnostics()
        assert diag_after["merge_occurred"] is True
        assert diag_after["split_occurred"] is False
        assert "gap_query" in [e.name for e in strat._segments[1]]

    def test_neighbour_rule_component_2_gray_gap_decisive_when_hamming_tied(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves smaller Gray-rank gap wins when Hamming distances are equal, even if the other neighbour is smaller."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )

        # Middle at gray=3 (code=0b0010=2):
        # Left at gray=0 (code=0b0000=0): hamming(0, 2) = 1, gray_gap = 3 - 0 = 3, len = 3
        # Right at gray=4 (code=0b0110=6): hamming(2, 6) = 1, gray_gap = 4 - 3 = 1, len = 4
        # Both have Hamming 1; Right has smaller gray_gap (1 < 3) despite larger size (4 > 3).
        vecs: dict[str, np.ndarray] = {}
        for i in range(3):
            vecs[f"left_{i}"] = self._vec_for_code(0b0000, 4)
        vecs["mid_0"] = self._vec_for_code(0b0010, 4)
        for i in range(4):
            vecs[f"right_{i}"] = self._vec_for_code(0b0110, 4)
        vecs["gap_q"] = self._vec_for_code(0b0010, 4)

        emb = ControllableEmbedder(vecs, dim=4)
        g_merge = ConceptGraph()
        for k in vecs:
            if k != "gap_q":
                g_merge.add_node(k)
        strat.setup(g_merge, emb)
        assert [len(s) for s in strat._segments] == [3, 5]
        assert "mid_0" in [e.name for e in strat._segments[1]]

        g_gap = ConceptGraph()
        for k in vecs:
            if k not in {"mid_0", "gap_q"}:
                g_gap.add_node(k)
        strat.setup(g_gap, emb)
        sl = strat.shortlist("gap_q")
        assert set(sl.candidates) == {"right_0", "right_1", "right_2", "right_3"}

    def test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves smaller neighbour size wins on Hamming+Gray tie (kills M-26), and left wins on full tie (kills M-19)."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )

        # Middle at gray=2 (code=0b0011=3):
        # Left at gray=1 (code=0b0001=1): hamming(1, 3) = 1, gray_gap = 1
        # Right at gray=3 (code=0b0010=2): hamming(3, 2) = 1, gray_gap = 1
        # Case A: len(Left)=4, len(Right)=3 -> Right wins by smaller size (3 < 4)
        vecs_a: dict[str, np.ndarray] = {}
        for i in range(4):
            vecs_a[f"left_{i}"] = self._vec_for_code(0b0001, 4)
        vecs_a["mid_0"] = self._vec_for_code(0b0011, 4)
        for i in range(3):
            vecs_a[f"right_{i}"] = self._vec_for_code(0b0010, 4)
        vecs_a["gap_q"] = self._vec_for_code(0b0011, 4)

        emb_a = ControllableEmbedder(vecs_a, dim=4)
        g_a = ConceptGraph()
        for k in vecs_a:
            if k != "gap_q":
                g_a.add_node(k)
        strat.setup(g_a, emb_a)
        assert [len(s) for s in strat._segments] == [4, 4]
        assert "mid_0" in [e.name for e in strat._segments[1]]

        g_a_gap = ConceptGraph()
        for k in vecs_a:
            if k not in {"mid_0", "gap_q"}:
                g_a_gap.add_node(k)
        strat.setup(g_a_gap, emb_a)
        sl_a = strat.shortlist("gap_q")
        assert set(sl_a.candidates) == {"right_0", "right_1", "right_2"}

        # Case B: len(Left)=3, len(Right)=3 -> full tie on (hamming=1, gray_gap=1, len=3), Left wins (0 < 1)
        g_b = ConceptGraph()
        for name in [
            "left_0",
            "left_1",
            "left_2",
            "mid_0",
            "right_0",
            "right_1",
            "right_2",
        ]:
            g_b.add_node(name)
        strat.setup(g_b, emb_a)
        assert [len(s) for s in strat._segments] == [4, 3]
        assert "mid_0" in [e.name for e in strat._segments[0]]

        g_b_gap = ConceptGraph()
        for name in ["left_0", "left_1", "left_2", "right_0", "right_1", "right_2"]:
            g_b_gap.add_node(name)
        strat.setup(g_b_gap, emb_a)
        sl_b = strat.shortlist("gap_q")
        assert set(sl_b.candidates) == {"left_0", "left_1", "left_2"}

        # Verify on_inserted uses the exact same tie-break in the gap case (kills M-32)
        strat.on_inserted("gap_q", ())
        assert "gap_q" in [e.name for e in strat._segments[0]]

    def test_setup_merge_rebalances_when_combined_exceeds_s_max(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves merging an undersize bucket of size 2 with a neighbour of size 5 (> s_max=6) bisects into (3, 4) (kills M-20)."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        vecs: dict[str, np.ndarray] = {}
        for i in range(2):
            vecs[f"small_{i}"] = self._vec_for_code(0b0000, 4)
        for i in range(5):
            vecs[f"big_{i}"] = self._vec_for_code(0b0001, 4)
        emb = ControllableEmbedder(vecs, dim=4)
        graph = ConceptGraph()
        for k in vecs:
            graph.add_node(k)
        strat.setup(graph, emb)
        assert [len(s) for s in strat._segments] == [3, 4]
        _assert_partition_invariants(strat, set(vecs.keys()))


# ===========================================================================
# 12. Shortlist Non-Mutation, Ordering, Normalization, and Boundary Lookup
# ===========================================================================


class TestShortlistSemanticsAndBoundaries:
    """Proves shortlist() is read-only, normalizes vectors, sorts by (-score, name), and matches _locate_home boundaries."""

    def test_shortlist_read_only_and_matches_insertion_segment(self) -> None:
        """Proves shortlist() never mutates _segments, _mat, or _n and selects the exact home segment used by on_inserted()."""
        graph = ConceptGraph()
        for i in range(18):
            graph.add_node(f"node_{i:02d}")
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=8, seed=42)
        strat.setup(graph, embedder)

        segs_before = [list(s) for s in strat._segments]
        mat_before = strat._mat[: strat._n].copy()
        n_before = strat._n

        sl1 = strat.shortlist("new_probe")
        sl2 = strat.shortlist("new_probe")
        assert sl1 == sl2
        assert isinstance(sl1.candidates, tuple)
        assert isinstance(sl1.scores, tuple)
        assert "new_probe" not in sl1.candidates
        assert strat._segments == segs_before
        assert strat._n == n_before
        assert np.array_equal(strat._mat[: strat._n], mat_before)

        home_id = strat.diagnostics()["bucket_id"]
        assert home_id is not None
        home_members_before = {e.name for e in strat._segments[home_id]}
        assert set(sl1.candidates) == home_members_before

        # If home segment has < s_max items, after on_inserted its members equal shortlist + {"new_probe"}
        strat.on_inserted("new_probe", ())
        if not strat.diagnostics()["split_occurred"]:
            home_members_after = {e.name for e in strat._segments[home_id]}
            assert home_members_after == home_members_before | {"new_probe"}

    def test_shortlist_ordering_ties_and_unnormalised_vectors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves shortlist normalizes query and indexed vectors and sorts by (-score, name) (kills M-12, M-13)."""
        strat = BoundedBucketStrategy(s_min=2, s_max=6, n_bits=2, seed=42)
        monkeypatch.setattr(
            strat,
            "_draw_hyperplanes",
            lambda dim: np.array(
                [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float64
            ),
        )
        base = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)
        base_unit = base / np.linalg.norm(base)
        v_90 = vector_with_cosine(base_unit, 0.90)
        v_80 = vector_with_cosine(base_unit, 0.80)

        # Scale vectors by arbitrary positive magnitudes to test L2 normalisation
        vecs = {
            "zeta_tie": 5.0 * v_90,
            "alpha_tie": 0.02 * v_90,
            "beta_low": 12.0 * v_80,
            "query_node": 9.5 * base_unit,
        }
        emb = ControllableEmbedder(vecs, dim=4)
        graph = ConceptGraph()
        for name in ["zeta_tie", "alpha_tie", "beta_low"]:
            graph.add_node(name)

        strat.setup(graph, emb)
        # Also query an already-indexed name to prove defensive self-exclusion
        sl_self = strat.shortlist("alpha_tie")
        assert "alpha_tie" not in sl_self.candidates

        sl = strat.shortlist("query_node")
        assert sl.candidates == ("alpha_tie", "zeta_tie", "beta_low")
        assert sl.scores is not None
        assert np.allclose(sl.scores, (0.90, 0.90, 0.80), atol=1e-5)

    def test_locate_home_exact_segment_boundaries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves _locate_home returns inside_span=True at both seg[0].sort_key() and seg[-1].sort_key() (kills M-23, M-24)."""
        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        vecs = {
            "a0": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),
            "a1": TestMergeAndNeighbourRule._vec_for_code(0b0001, 4),
            "b0": TestMergeAndNeighbourRule._vec_for_code(0b0110, 4),
            "b1": TestMergeAndNeighbourRule._vec_for_code(0b1100, 4),
        }
        emb = ControllableEmbedder(vecs, dim=4)
        graph = ConceptGraph()
        for k in vecs:
            graph.add_node(k)
        strat.setup(graph, emb)
        # Force 2 segments of size 2: [a0, a1] and [b0, b1]
        strat._segments = [
            [strat._entry_by_name["a0"], strat._entry_by_name["a1"]],
            [strat._entry_by_name["b0"], strat._entry_by_name["b1"]],
        ]

        # Exact left boundary of segment 0 and segment 1
        e_a0 = strat._entry_by_name["a0"]
        assert strat._locate_home(e_a0.gray, e_a0.name, e_a0.code) == (0, True)
        e_b0 = strat._entry_by_name["b0"]
        assert strat._locate_home(e_b0.gray, e_b0.name, e_b0.code) == (1, True)

        # Exact right boundary of segment 0 and segment 1
        e_a1 = strat._entry_by_name["a1"]
        assert strat._locate_home(e_a1.gray, e_a1.name, e_a1.code) == (0, True)
        e_b1 = strat._entry_by_name["b1"]
        assert strat._locate_home(e_b1.gray, e_b1.name, e_b1.code) == (1, True)


# ===========================================================================
# 13 & 14. Lifecycle, D-58 Cache & Diagnostic Clearing, and setup() Failure Semantics
# ===========================================================================


class _SelectiveFailingEmbedder:
    """Test helper that fails on a specific concept text according to fail_mode."""

    def __init__(
        self, base: Embedder, fail_concept: str, fail_mode: str
    ) -> None:
        self.base = base
        self.fail_text = embed_text(fail_concept)
        self.fail_mode = fail_mode

    def embed(self, text: str) -> np.ndarray:
        if text == self.fail_text:
            if self.fail_mode == "raises":
                raise RuntimeError("Simulated embedder error")
            if self.fail_mode == "zero_norm":
                return np.zeros(16, dtype=np.float32)
            if self.fail_mode == "nan":
                v = np.ones(16, dtype=np.float32)
                v[0] = np.nan
                return v
            if self.fail_mode == "dim_mismatch":
                return np.ones(8, dtype=np.float32)
            if self.fail_mode == "non_1d":
                return np.ones((2, 8), dtype=np.float32)
        return self.base.embed(text)

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        return self.base.embed_many(texts)


class TestLifecycleAndSetupSemantics:
    """Proves D-58 cache/diagnostic clearing on shortlist failure, on_inserted guards, and all-or-nothing setup()."""

    @pytest.mark.parametrize(
        "fail_mode,bad_arg,exc_type,exc_match",
        [
            ("empty_name", "", ValueError, "cannot be empty"),
            ("txt_suffix", "bad_node.txt", ValueError, r"cannot end in '\.txt'"),
            ("raises", "failing_node", RuntimeError, "Simulated embedder error"),
            ("zero_norm", "failing_node", ValueError, "Zero-norm"),
            ("nan", "failing_node", ValueError, "non-finite"),
            ("dim_mismatch", "failing_node", ValueError, "Dimension mismatch"),
            ("non_1d", "failing_node", ValueError, "1-D ndarray"),
        ],
    )
    def test_d58_failed_shortlist_clears_cache_and_query_diagnostics(
        self,
        fail_mode: str,
        bad_arg: str,
        exc_type: type[Exception],
        exc_match: str,
    ) -> None:
        """Proves any failed shortlist() clears cache and resets per-query diagnostics at entry (kills M-11, M-28)."""
        graph = ConceptGraph()
        graph.add_node("existing_node")
        base_emb = FakeEmbedder(dim=16, seed=42)
        emb = _SelectiveFailingEmbedder(base_emb, "failing_node", fail_mode)
        strat = BoundedBucketStrategy(s_min=2, s_max=5)
        strat.setup(graph, emb)

        res = strat.shortlist("good_node")
        assert len(res.candidates) == 1
        assert strat._cached_new_name == "good_node"
        assert strat._cached_new_vec is not None
        assert strat.diagnostics()["bucket_id"] == 0
        assert strat.diagnostics()["shortlist_size"] == 1
        assert strat.diagnostics()["exact_topk_overlap"] == 1.0

        with pytest.raises(exc_type, match=exc_match):
            strat.shortlist(bad_arg)

        assert strat._cached_new_name is None
        assert strat._cached_new_vec is None
        assert strat._cached_new_code is None
        assert strat._cached_new_gray is None

        # Per-query diagnostics must also be reset after the failed shortlist (kills M-28)
        diag = strat.diagnostics()
        assert diag["bucket_id"] is None
        assert diag["query_code"] is None
        assert diag["query_gray_rank"] is None
        assert diag["shortlist_size"] == 0
        assert diag["exact_topk_overlap"] is None
        assert diag["min_hamming_to_shortlist"] is None

        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("good_node", ())

    def test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name(
        self,
    ) -> None:
        """Proves on_inserted rejects missing shortlist, second call, duplicate node, and invalidated shortlist (kills M-17, M-18)."""
        graph = ConceptGraph()
        graph.add_node("n0")
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = BoundedBucketStrategy(s_min=2, s_max=5)
        strat.setup(graph, embedder)

        # 1. on_inserted without shortlist
        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("unqueried", ())

        # 2. Second shortlist for a different name invalidates the first
        strat.shortlist("first_cand")
        strat.shortlist("second_cand")
        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("first_cand", ())

        # 3. Valid on_inserted succeeds, and calling on_inserted a second time raises RuntimeError
        strat.on_inserted("second_cand", ())
        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("second_cand", ())

        # 4. Duplicate node (already indexed) raises ValueError
        strat.shortlist("n0")
        with pytest.raises(ValueError, match="already present in the index"):
            strat.on_inserted("n0", ())

    @pytest.mark.parametrize("fail_mode", ["zero_row", "nan_row", "non_2d", "wrong_rows"])
    def test_failed_first_and_second_setup_leaves_strategy_not_set_up(
        self, fail_mode: str
    ) -> None:
        """Proves a failed first or second setup() leaves the strategy not set up and clears state (kills M-09)."""

        class _BadBatchEmbedder:
            def embed(self, text: str) -> np.ndarray:
                return np.ones(4, dtype=np.float32)

            def embed_many(self, texts: Sequence[str]) -> Any:
                if fail_mode == "zero_row":
                    m = np.ones((len(texts), 4), dtype=np.float32)
                    m[0] = 0.0
                    return m
                if fail_mode == "nan_row":
                    m = np.ones((len(texts), 4), dtype=np.float32)
                    m[0, 0] = np.nan
                    return m
                if fail_mode == "non_2d":
                    return np.ones(4, dtype=np.float32)
                if fail_mode == "wrong_rows":
                    return np.ones((len(texts) + 1, 4), dtype=np.float32)
                raise ValueError(fail_mode)

        graph = ConceptGraph()
        graph.add_node("n0")
        good_emb = FakeEmbedder(dim=4, seed=42)
        bad_emb = _BadBatchEmbedder()

        strat = BoundedBucketStrategy(s_min=2, s_max=4)
        # Failed first setup
        with pytest.raises(ValueError):
            strat.setup(graph, bad_emb)  # type: ignore[arg-type]
        assert not strat._setup_called
        with pytest.raises(RuntimeError, match="setup\\(\\) must be called"):
            strat.shortlist("probe")

        # Valid setup followed by shortlist
        strat.setup(graph, good_emb)
        strat.shortlist("probe")
        assert strat.diagnostics()["num_segments"] == 1

        # Failed second setup leaves strategy NOT set up and clears segments/caches
        with pytest.raises(ValueError):
            strat.setup(graph, bad_emb)  # type: ignore[arg-type]
        assert not strat._setup_called
        assert strat._embedder is None
        assert strat._cached_new_name is None
        assert strat.diagnostics()["num_segments"] == 0
        with pytest.raises(RuntimeError, match="setup\\(\\) must be called"):
            strat.shortlist("probe")

        # Valid re-setup recovers cleanly
        strat.setup(graph, good_emb)
        assert strat.shortlist("probe").candidates == ("n0",)


# ===========================================================================
# 15 & 16. Embedding Accounting, Matrix Capacity, and Edge Cases
# ===========================================================================


class TestEmbeddingAccountingAndEdgeCases:
    """Proves single-embedding reuse, no reallocation on first insert, doubling growth, and small-n edge cases."""

    @pytest.mark.parametrize("n", [1, 50, 500])
    def test_first_insert_after_setup_does_not_reallocate_matrix(
        self, n: int
    ) -> None:
        """Proves _mat buffer address is unchanged on the first on_inserted() after setup() (kills M-10)."""
        graph = ConceptGraph()
        for i in range(n):
            graph.add_node(f"node_{i:04d}")
        raw_emb = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_emb)
        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=10, seed=42)
        strat.setup(graph, meter)
        meter.reset()

        assert strat._mat is not None
        assert strat._mat.shape[0] == max(16, 2 * n)
        ptr_before = strat._mat.ctypes.data

        res = insert_node(
            strat,
            graph,
            FakeDecisionStep(make_edge=False),
            "first_inserted",
            metered_embedder=meter,
        )
        assert res.metrics.embedding_calls == 1
        assert res.metrics.embedding_calls_in_update == 0
        assert strat._mat.ctypes.data == ptr_before

    def test_doubling_growth_preserves_all_rows_over_200_inserts(self) -> None:
        """Proves matrix doubling across 200 sequential inserts preserves every earlier normalised vector."""
        graph = ConceptGraph()
        raw_emb = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_emb)
        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=10, seed=42)
        strat.setup(graph, meter)

        expected_vecs: dict[str, np.ndarray] = {}
        for i in range(200):
            name = f"grow_{i:03d}"
            raw_v = raw_emb.embed(embed_text(name))
            expected_vecs[name] = (raw_v / np.linalg.norm(raw_v)).astype(
                np.float32
            )
            insert_node(
                strat,
                graph,
                FakeDecisionStep(make_edge=False),
                name,
                metered_embedder=meter,
            )

        assert strat._mat is not None
        for name, exp_v in expected_vecs.items():
            row = strat._name_to_idx[name]
            assert np.allclose(strat._mat[row], exp_v, atol=1e-6)

    def test_edge_cases_n0_n1_n_less_than_s_min_and_single_segment_branch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves n=0, n=1, and n < s_min single-segment branch without calling _choose_neighbour (kills M-27)."""
        embedder = FakeEmbedder(dim=16, seed=42)

        # n = 0
        s0 = BoundedBucketStrategy(s_min=5, s_max=10)
        s0.setup(ConceptGraph(), embedder)
        assert s0.shortlist("first") == Shortlist(candidates=(), scores=())
        s0.on_inserted("first", ())
        assert len(s0._segments) == 1 and len(s0._segments[0]) == 1

        # n = 1
        g1 = ConceptGraph()
        g1.add_node("only_node")
        s1 = BoundedBucketStrategy(s_min=5, s_max=10)
        s1.setup(g1, embedder)
        sl1 = s1.shortlist("second_node")
        assert sl1.candidates == ("only_node",)
        s1.on_inserted("second_node", ())
        assert len(s1._segments) == 1 and len(s1._segments[0]) == 2

        # n = 3 < s_min = 5: must take the direct n < s_min single-segment branch without calling _choose_neighbour
        g3 = ConceptGraph()
        for name in ["c_a", "c_b", "c_c"]:
            g3.add_node(name)
        s3 = BoundedBucketStrategy(s_min=5, s_max=10)
        choose_calls: list[int] = []
        orig_choose = s3._choose_neighbour

        def _spy_choose(*args: Any, **kwargs: Any) -> str:
            choose_calls.append(1)
            return orig_choose(*args, **kwargs)

        monkeypatch.setattr(s3, "_choose_neighbour", _spy_choose)
        s3.setup(g3, embedder)
        assert len(s3._segments) == 1 and len(s3._segments[0]) == 3
        assert choose_calls == []


# ===========================================================================
# 17. Diagnostics Schema, Lazy Overlap, Min Hamming, and Driver Smoke
# ===========================================================================


class TestDiagnostics:
    """Proves 18-key JSON-safe diagnostics, lazy exact_topk_overlap, and min_hamming_to_shortlist."""

    EXPECTED_KEYS = {
        "bucket_id",
        "bucket_gray_min",
        "bucket_gray_max",
        "query_code",
        "query_gray_rank",
        "code_existed_in_bucket",
        "inside_bucket_span",
        "bucket_size_at_shortlist",
        "bucket_size",
        "shortlist_size",
        "split_occurred",
        "merge_occurred",
        "num_segments",
        "min_segment_size",
        "max_segment_size",
        "mean_segment_size",
        "exact_topk_overlap",
        "min_hamming_to_shortlist",
    }

    def test_diagnostics_lifecycle_lazy_overlap_and_min_hamming(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves diagnostics JSON safety across all states, lazy overlap calculation (kills M-21), and min_hamming_to_shortlist."""
        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=4, seed=42)

        # 1. Before setup()
        d0 = strat.diagnostics()
        assert set(d0.keys()) == self.EXPECTED_KEYS
        assert d0["exact_topk_overlap"] is None
        assert d0["min_hamming_to_shortlist"] is None
        _assert_no_numpy_types(d0)
        json.dumps(d0)

        # 2. Empty setup() and shortlist() on empty index -> overlap is 1.0, min_hamming is None
        emb_empty = FakeEmbedder(dim=4, seed=42)
        strat.setup(ConceptGraph(), emb_empty)
        d_setup_empty = strat.diagnostics()
        assert d_setup_empty["exact_topk_overlap"] is None

        strat.shortlist("first_q")
        assert strat._cached_exact_topk_overlap is None  # Lazy: not computed in shortlist()
        d_empty_q = strat.diagnostics()
        assert strat._cached_exact_topk_overlap == 1.0
        assert d_empty_q["exact_topk_overlap"] == 1.0
        assert d_empty_q["min_hamming_to_shortlist"] is None
        _assert_no_numpy_types(d_empty_q)
        json.dumps(d_empty_q)

        # 3. Hand-built case for min_hamming_to_shortlist and exact_topk_overlap
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        vecs = {
            "n0": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),  # code 0
            "n1": TestMergeAndNeighbourRule._vec_for_code(0b0011, 4),  # code 3
            "q": TestMergeAndNeighbourRule._vec_for_code(0b0111, 4),  # code 7 (hamming 1 to code 3, 3 to code 0)
        }
        emb = ControllableEmbedder(vecs, dim=4)
        g = ConceptGraph()
        g.add_node("n0")
        g.add_node("n1")
        strat.setup(g, emb)

        strat.shortlist("q")
        assert strat._cached_exact_topk_overlap is None  # Still None before diagnostics()
        d_q = strat.diagnostics()
        assert d_q["min_hamming_to_shortlist"] == 1
        assert d_q["exact_topk_overlap"] == 1.0

        strat.on_inserted("q", ())
        d_ins = strat.diagnostics()
        assert set(d_ins.keys()) == self.EXPECTED_KEYS
        assert d_ins["bucket_size"] == 3
        _assert_no_numpy_types(d_ins)
        json.dumps(d_ins)

    def test_exact_topk_overlap_matches_independent_float64_reference_through_driver(
        self,
    ) -> None:
        """Proves exact_topk_overlap in metrics.extra matches an independent float64 brute-force top-m calculation."""
        graph = ConceptGraph()
        init_names = [f"node_{i:03d}" for i in range(40)]
        for name in init_names:
            graph.add_node(name)

        raw_emb = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_emb)
        decision = FakeDecisionStep(make_edge=False)
        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=10, seed=42)
        strat.setup(graph, meter)

        for probe in ["probe_0", "probe_1", "probe_2"]:
            existing_names = sorted(graph.nodes())
            raw_mat = raw_emb.embed_many([embed_text(x) for x in existing_names])
            mat64 = raw_mat.astype(np.float64)
            mat64 /= np.linalg.norm(mat64, axis=1, keepdims=True)

            q_raw = raw_emb.embed(embed_text(probe)).astype(np.float64)
            q64 = q_raw / np.linalg.norm(q_raw)
            cosines = mat64 @ q64
            ranked = sorted(
                [(float(cosines[i]), existing_names[i]) for i in range(len(existing_names))],
                key=lambda item: (-item[0], item[1]),
            )
            m = min(strat.s_max, len(ranked))
            exact_top_m = {name for _, name in ranked[:m]}

            res = insert_node(
                strat, graph, decision, probe, metered_embedder=meter
            )
            expected_overlap = sum(
                1 for c in res.shortlist.candidates if c in exact_top_m
            ) / m
            assert set(res.metrics.extra.keys()) == self.EXPECTED_KEYS
            assert np.isclose(
                res.metrics.extra["exact_topk_overlap"], expected_overlap
            )

    def test_harness_sweep_smoke(self, tmp_path: Any) -> None:
        """Proves BoundedBucketStrategy runs end-to-end through run_sweep_experiment."""
        names = [f"concept_{i:04d}" for i in range(100)]
        name_source = SyntheticNameSource(
            names=names, domain_context="computer science"
        )
        client = MeteredLLMClient(FakeLLMClient())
        decision_step = PairwiseDecisionStep(client)
        cfg = HarnessConfig(
            mode="sweep",
            run_id="test_bb_smoke",
            output_dir=tmp_path / "bb_smoke",
            seed=42,
            sweep_sizes=(15, 30),
            sweep_trials_per_size=2,
            confirm=True,
        )
        out = run_sweep_experiment(
            config=cfg,
            strategy_factory=lambda: BoundedBucketStrategy(
                s_min=5, s_max=10, n_bits=12, seed=42
            ),
            decision_step=decision_step,
            embedder_factory=lambda: FakeEmbedder(dim=16, seed=42),
            name_source=name_source,
        )
        assert out["status"] == "completed"
        raw_lines = (
            (tmp_path / "bb_smoke" / "raw.jsonl").read_text().strip().splitlines()
        )
        assert len(raw_lines) == 4
        for line in raw_lines:
            rec = json.loads(line)
            assert rec["strategy"] == "bounded_bucket"
            assert 5 <= rec["metrics"]["shortlist_size"] <= 10
            assert set(rec["metrics"]["extra"].keys()) == self.EXPECTED_KEYS


# ===========================================================================
# 18. Sequential Stream Without Cascades (m = 200 Inserts From n = 0)
# ===========================================================================


class TestSequentialStreamNoCascades:
    """Proves m=200 sequential inserts from n=0 never cascade and enforce >= s_min inserts between splits."""

    def test_200_sequential_inserts_no_cascades_and_amortisation_gap(
        self,
    ) -> None:
        """Proves each insert alters at most 1 segment into at most 2 and any split child receives >= s_min inserts before re-splitting."""
        embedder = FakeEmbedder(dim=16, seed=123)
        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=12, seed=42)
        strat.setup(ConceptGraph(), embedder)

        # Track how many insertions each currently active segment has received since it was created by a split
        inserts_since_split: list[int] = []

        for step in range(200):
            name = f"stream_{step:04d}"
            segs_before = [tuple(e.name for e in s) for s in strat._segments]

            sl = strat.shortlist(name)
            home_idx = strat.diagnostics()["bucket_id"]
            strat.on_inserted(name, ())

            segs_after = [tuple(e.name for e in s) for s in strat._segments]
            diag = strat.diagnostics()

            if step == 0:
                assert len(segs_after) == 1
                inserts_since_split = [0]
                continue

            assert home_idx is not None
            inserts_since_split[home_idx] += 1

            if not diag["split_occurred"]:
                # Exactly 1 segment grew by 1; all other segments are untouched
                assert len(segs_after) == len(segs_before)
                for idx in range(len(segs_before)):
                    if idx != home_idx:
                        assert segs_after[idx] == segs_before[idx]
                    else:
                        assert set(segs_after[idx]) == set(segs_before[idx]) | {
                            name
                        }
                        assert set(sl.candidates) == set(segs_before[idx])
            else:
                # Split occurred: the segment must have received at least s_min insertions since its last split
                assert inserts_since_split[home_idx] >= strat.s_min
                # Exactly 1 segment turned into 2; all other segments untouched
                assert len(segs_after) == len(segs_before) + 1
                assert segs_after[:home_idx] == segs_before[:home_idx]
                assert segs_after[home_idx + 2 :] == segs_before[home_idx + 1 :]
                combined_after = set(segs_after[home_idx]) | set(
                    segs_after[home_idx + 1]
                )
                assert combined_after == set(segs_before[home_idx]) | {name}
                # Reset split counters for the two new child segments
                inserts_since_split[home_idx : home_idx + 1] = [0, 0]


# ===========================================================================
# 19. Post-Review Amendments (STRAT-004-A: Gap A and Gap B)
# ===========================================================================


class TestPostReviewAmendments:
    """Closes STRAT-004-R review test gaps A (merge_occurred inside span) and B (second setup diagnostics reset)."""

    def test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves merge_occurred is False on empty index and inside-span inserts (with/without split) and True in gaps (kills A-01)."""
        vecs = {
            "a_0": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),  # gray=0
            "a_1": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),  # gray=0
            "b_0": TestMergeAndNeighbourRule._vec_for_code(0b0010, 4),  # gray=3
            "b_1": TestMergeAndNeighbourRule._vec_for_code(0b0010, 4),  # gray=3
            "b_2": TestMergeAndNeighbourRule._vec_for_code(0b0010, 4),  # gray=3
            "in_no_split": TestMergeAndNeighbourRule._vec_for_code(0b0001, 4),  # gray=1 (inside [0, 3])
            "in_with_split": TestMergeAndNeighbourRule._vec_for_code(0b0011, 4),  # gray=2 (inside [0, 3])
            "gap_node": TestMergeAndNeighbourRule._vec_for_code(0b1100, 4),  # gray=8 (outside [0, 3])
        }
        emb = ControllableEmbedder(vecs, dim=4)

        # 1. Insertion into an EMPTY index (n_before == 0): merge_occurred is False (direct and via insert_node)
        strat_empty = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat_empty, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        strat_empty.setup(ConceptGraph(), emb)
        strat_empty.shortlist("a_0")
        strat_empty.on_inserted("a_0", ())
        d_empty_direct = strat_empty.diagnostics()
        assert d_empty_direct["merge_occurred"] is False
        assert d_empty_direct["split_occurred"] is False

        strat_empty_drv = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat_empty_drv, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        g_empty_drv = ConceptGraph()
        meter_empty = MeteredEmbedder(emb)
        strat_empty_drv.setup(g_empty_drv, meter_empty)
        res_empty = insert_node(
            strat_empty_drv,
            g_empty_drv,
            FakeDecisionStep(make_edge=False),
            "a_0",
            metered_embedder=meter_empty,
        )
        assert res_empty.metrics.extra["merge_occurred"] is False
        assert res_empty.metrics.extra["split_occurred"] is False

        # 2. Direct strategy calls: inside-span without split, inside-span with split, and gap insertion
        strat_direct = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat_direct, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        g_direct = ConceptGraph()
        for init_name in ["a_0", "a_1", "b_0", "b_1", "b_2"]:
            g_direct.add_node(init_name)
        strat_direct.setup(g_direct, emb)
        assert [len(s) for s in strat_direct._segments] == [5]

        # 2a. Inside span, no split (size 5 -> 6 <= s_max=6)
        strat_direct.shortlist("in_no_split")
        assert strat_direct.diagnostics()["inside_bucket_span"] is True
        strat_direct.on_inserted("in_no_split", ())
        d_in_no_split = strat_direct.diagnostics()
        assert d_in_no_split["inside_bucket_span"] is True
        assert d_in_no_split["split_occurred"] is False
        assert d_in_no_split["merge_occurred"] is False

        # 2b. Inside span, with split (size 6 -> 7 > s_max=6, splits into [3, 4])
        strat_direct.shortlist("in_with_split")
        assert strat_direct.diagnostics()["inside_bucket_span"] is True
        strat_direct.on_inserted("in_with_split", ())
        d_in_split = strat_direct.diagnostics()
        assert d_in_split["inside_bucket_span"] is True
        assert d_in_split["split_occurred"] is True
        assert d_in_split["merge_occurred"] is False

        # 2c. Gap insertion (gray=8 > max gray=3): inside_bucket_span is False, merge_occurred is True
        strat_direct.shortlist("gap_node")
        assert strat_direct.diagnostics()["inside_bucket_span"] is False
        strat_direct.on_inserted("gap_node", ())
        d_gap = strat_direct.diagnostics()
        assert d_gap["inside_bucket_span"] is False
        assert d_gap["split_occurred"] is False
        assert d_gap["merge_occurred"] is True

        # 3. Same sequence through insert_node with FakeDecisionStep
        strat_drv = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat_drv, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        g_drv = ConceptGraph()
        for init_name in ["a_0", "a_1", "b_0", "b_1", "b_2"]:
            g_drv.add_node(init_name)
        meter = MeteredEmbedder(emb)
        strat_drv.setup(g_drv, meter)

        res_no_split = insert_node(
            strat_drv,
            g_drv,
            FakeDecisionStep(make_edge=False),
            "in_no_split",
            metered_embedder=meter,
        )
        assert res_no_split.metrics.extra["inside_bucket_span"] is True
        assert res_no_split.metrics.extra["split_occurred"] is False
        assert res_no_split.metrics.extra["merge_occurred"] is False

        res_split = insert_node(
            strat_drv,
            g_drv,
            FakeDecisionStep(make_edge=False),
            "in_with_split",
            metered_embedder=meter,
        )
        assert res_split.metrics.extra["inside_bucket_span"] is True
        assert res_split.metrics.extra["split_occurred"] is True
        assert res_split.metrics.extra["merge_occurred"] is False

        res_gap = insert_node(
            strat_drv,
            g_drv,
            FakeDecisionStep(make_edge=False),
            "gap_node",
            metered_embedder=meter,
        )
        assert res_gap.metrics.extra["inside_bucket_span"] is False
        assert res_gap.metrics.extra["split_occurred"] is False
        assert res_gap.metrics.extra["merge_occurred"] is True

    def test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves a second setup() (valid or failed) resets all per-query diagnostics before any new shortlist() (kills A-02)."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )
        vecs = {
            f"n_{i:02d}": TestMergeAndNeighbourRule._vec_for_code(i % 16, 4)
            for i in range(16)
        }
        vecs["a"] = TestMergeAndNeighbourRule._vec_for_code(0b1111, 4)
        emb = ControllableEmbedder(vecs, dim=4)

        g1 = ConceptGraph()
        for i in range(6):
            g1.add_node(f"n_{i:02d}")
        strat.setup(g1, emb)

        # Populate all per-query fields, cached overlap, split_occurred, and merge_occurred
        strat.shortlist("a")
        d_populated = strat.diagnostics()
        assert d_populated["bucket_id"] is not None
        assert d_populated["exact_topk_overlap"] is not None
        assert d_populated["query_code"] is not None
        assert d_populated["query_gray_rank"] is not None
        assert d_populated["shortlist_size"] == 6
        assert d_populated["bucket_size"] == 6
        assert d_populated["min_hamming_to_shortlist"] is not None
        strat.on_inserted("a", ())
        assert strat.diagnostics()["split_occurred"] is True
        assert strat.diagnostics()["merge_occurred"] is True

        # 1. Valid second setup() on a larger 12-node graph g2 BEFORE any new shortlist()
        g2 = ConceptGraph()
        for i in range(12):
            g2.add_node(f"n_{i:02d}")
        strat.setup(g2, emb)

        d_after_valid_setup = strat.diagnostics()
        _assert_no_numpy_types(d_after_valid_setup)
        json.dumps(d_after_valid_setup)
        assert d_after_valid_setup["bucket_id"] is None
        assert d_after_valid_setup["bucket_gray_min"] is None
        assert d_after_valid_setup["bucket_gray_max"] is None
        assert d_after_valid_setup["exact_topk_overlap"] is None
        assert d_after_valid_setup["query_code"] is None
        assert d_after_valid_setup["query_gray_rank"] is None
        assert d_after_valid_setup["code_existed_in_bucket"] is False
        assert d_after_valid_setup["inside_bucket_span"] is False
        assert d_after_valid_setup["bucket_size_at_shortlist"] == 0
        assert d_after_valid_setup["bucket_size"] == 0
        assert d_after_valid_setup["shortlist_size"] == 0
        assert d_after_valid_setup["split_occurred"] is False
        assert d_after_valid_setup["merge_occurred"] is False
        assert d_after_valid_setup["min_hamming_to_shortlist"] is None
        # Partition-level diagnostics must describe the NEW 12-node graph g2
        assert d_after_valid_setup["num_segments"] == len(strat._segments) >= 2
        assert d_after_valid_setup["min_segment_size"] >= 3
        assert d_after_valid_setup["max_segment_size"] <= 6
        assert np.isclose(
            d_after_valid_setup["mean_segment_size"],
            12.0 / d_after_valid_setup["num_segments"],
        )

        # 2. Re-populate per-query diagnostics on g2, then call a FAILED second setup() (zero-norm row)
        strat.shortlist("a")
        assert strat.diagnostics()["bucket_id"] is not None
        assert strat.diagnostics()["exact_topk_overlap"] is not None

        class _ZeroRowBatchEmbedder:
            def embed(self, text: str) -> np.ndarray:
                return np.ones(4, dtype=np.float32)

            def embed_many(self, texts: Sequence[str]) -> np.ndarray:
                m = np.ones((len(texts), 4), dtype=np.float32)
                m[0] = 0.0
                return m

        with pytest.raises(ValueError, match="Zero-norm"):
            strat.setup(g2, _ZeroRowBatchEmbedder())  # type: ignore[arg-type]

        assert not strat._setup_called
        assert strat._embedder is None
        with pytest.raises(RuntimeError, match="setup\\(\\) must be called"):
            strat.shortlist("a")

        d_after_failed_setup = strat.diagnostics()
        _assert_no_numpy_types(d_after_failed_setup)
        json.dumps(d_after_failed_setup)
        assert d_after_failed_setup["bucket_id"] is None
        assert d_after_failed_setup["bucket_gray_min"] is None
        assert d_after_failed_setup["bucket_gray_max"] is None
        assert d_after_failed_setup["exact_topk_overlap"] is None
        assert d_after_failed_setup["query_code"] is None
        assert d_after_failed_setup["query_gray_rank"] is None
        assert d_after_failed_setup["code_existed_in_bucket"] is False
        assert d_after_failed_setup["inside_bucket_span"] is False
        assert d_after_failed_setup["bucket_size_at_shortlist"] == 0
        assert d_after_failed_setup["bucket_size"] == 0
        assert d_after_failed_setup["shortlist_size"] == 0
        assert d_after_failed_setup["split_occurred"] is False
        assert d_after_failed_setup["merge_occurred"] is False
        assert d_after_failed_setup["min_hamming_to_shortlist"] is None
        assert d_after_failed_setup["num_segments"] == 0
        assert d_after_failed_setup["min_segment_size"] == 0
        assert d_after_failed_setup["max_segment_size"] == 0
        assert d_after_failed_setup["mean_segment_size"] == 0.0


class TestPostReviewScoringAndTies:
    """Post-review tests closing M-38 (global row scoring), M-12 (tie-break), and M-42 (bucket_size_at_shortlist)."""

    @staticmethod
    def _cos_f64(a: np.ndarray, b: np.ndarray) -> float:
        a64 = np.asarray(a, dtype=np.float64)
        b64 = np.asarray(b, dtype=np.float64)
        na = float(np.linalg.norm(a64))
        nb = float(np.linalg.norm(b64))
        return float(np.dot(a64 / na, b64 / nb))

    def test_shortlist_scores_use_global_matrix_row_in_nonzero_segment_and_after_inserts(
        self,
    ) -> None:
        """Proves shortlist() scores each candidate using its global matrix row e.row, not its 0..k-1 segment offset (kills M-38)."""
        rng = np.random.default_rng(12345)
        vecs: dict[str, np.ndarray] = {}
        for i in range(18):
            v = rng.standard_normal(16).astype(np.float32)
            v /= float(np.linalg.norm(v))
            vecs[f"node_{i:02d}"] = v

        # Extra vectors for queries and sequential insertions whose names sort before "node_*"
        for tag in ("q_batch", "aa_ins_1", "ab_ins_2", "ac_ins_3", "q_after_ins"):
            v = rng.standard_normal(16).astype(np.float32)
            v /= float(np.linalg.norm(v))
            vecs[tag] = v

        emb = ControllableEmbedder(vecs, dim=16)
        g = ConceptGraph()
        for i in range(18):
            g.add_node(f"node_{i:02d}")

        strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=6, seed=7)
        strat.setup(g, emb)
        assert len(strat._segments) >= 3

        # 1. Batch setup() path: pick a query that lands in the last segment (bucket_id > 0)
        last_seg = strat._segments[-1]
        vecs["q_batch"] = vecs[last_seg[0].name].copy()
        emb_batch = ControllableEmbedder(vecs, dim=16)
        strat.setup(g, emb_batch)

        sl = strat.shortlist("q_batch")
        diag = strat.diagnostics()
        home_idx = diag["bucket_id"]
        assert home_idx is not None and home_idx == len(strat._segments) - 1 > 0
        home_seg = strat._segments[home_idx]

        # Precondition for killing M-38: global matrix row e.row differs from local segment offset idx
        assert any(e.row != idx for idx, e in enumerate(home_seg))
        assert len(sl.candidates) == len(home_seg) > 0
        assert set(sl.candidates) == {e.name for e in home_seg}

        for cand_name, score in zip(sl.candidates, sl.scores):
            expected = self._cos_f64(vecs["q_batch"], vecs[cand_name])
            assert abs(score - expected) < 1e-6, (
                f"Candidate {cand_name} score {score} != expected cosine {expected}"
            )

        # 2. Post-on_inserted() path: append 3 nodes whose global rows are at the tail of _mat
        for ins_idx, ins_name in enumerate(("aa_ins_1", "ab_ins_2", "ac_ins_3")):
            # Aim at the last segment so the inserted nodes land in a non-zero segment
            target_seg = strat._segments[-1]
            v_ins = vecs[target_seg[ins_idx % len(target_seg)].name].copy()
            vecs[ins_name] = v_ins
            emb_batch.set_vector(ins_name, v_ins)

            strat.shortlist(ins_name)
            g.add_node(ins_name)
            strat.on_inserted(ins_name, ())

        # Find a non-zero segment containing at least one post-setup inserted node
        target_seg_idx = None
        for seg_i in range(len(strat._segments) - 1, 0, -1):
            seg_names = {e.name for e in strat._segments[seg_i]}
            if seg_names & {"aa_ins_1", "ab_ins_2", "ac_ins_3"}:
                target_seg_idx = seg_i
                break
        assert target_seg_idx is not None and target_seg_idx > 0
        post_seg = strat._segments[target_seg_idx]
        assert any(e.row != idx for idx, e in enumerate(post_seg))

        # Query that segment using a vector with the same Gray code as post_seg[0]
        # and verify every candidate's score against independent float64 cosine
        q_vec = vecs[post_seg[0].name].copy()
        vecs["q_after_ins"] = q_vec
        emb_batch.set_vector("q_after_ins", q_vec)

        sl_post = strat.shortlist("q_after_ins")
        assert strat.diagnostics()["bucket_id"] == target_seg_idx > 0
        assert len(sl_post.candidates) == len(post_seg) > 0
        assert set(sl_post.candidates) == {e.name for e in post_seg}
        for cand_name, score in zip(sl_post.candidates, sl_post.scores):
            expected = self._cos_f64(vecs["q_after_ins"], vecs[cand_name])
            assert abs(score - expected) < 1e-6

    def test_shortlist_name_tiebreak_reorders_reverse_alphabetical_segment_entries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves shortlist() breaks equal-score ties by ascending name even when segment order is reverse-alphabetical (kills M-12 no-tie-break variant)."""
        strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=4, seed=42)
        # First 4 coordinates drive the 4 hyperplanes; 5th coordinate is orthogonal to all hyperplanes
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, 5, dtype=np.float64)
        )

        def vec5_for_gray(gray_rank: int, fifth: float) -> np.ndarray:
            # Binary code corresponding to gray_rank: code = gray ^ (gray >> 1)
            code = gray_rank ^ (gray_rank >> 1)
            coords = [
                1.0 if ((code >> (3 - b)) & 1) else -1.0 for b in range(4)
            ] + [fifth]
            return np.array(coords, dtype=np.float32)

        # Case A: exact non-zero float32 score tie (all candidates have norm sqrt(5) and 5th coord 1.0)
        # Assign gray ranks 1 < 2 < 3 to "z_first", "m_middle", "a_second" so segment order is reverse-alphabetical
        vecs_nonzero = {
            "z_first": vec5_for_gray(1, 1.0),
            "m_middle": vec5_for_gray(2, 1.0),
            "a_second": vec5_for_gray(3, 1.0),
            "q_nonzero": np.array([-1.0, -1.0, -1.0, -1.0, 0.0], dtype=np.float32),
        }
        # Query purely along the 5th axis so dot product with each candidate is identically 1/sqrt(5)
        vecs_nonzero["q_axis5"] = np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)

        g1 = ConceptGraph()
        for name in ("z_first", "m_middle", "a_second"):
            g1.add_node(name)
        emb1 = ControllableEmbedder(vecs_nonzero, dim=5)
        strat.setup(g1, emb1)

        assert len(strat._segments) == 1
        seg_entries = strat._segments[0]
        # Precondition: segment entries have strictly increasing Gray rank and reverse-alphabetical names
        assert [e.gray for e in seg_entries] == [1, 2, 3]
        assert [e.name for e in seg_entries] == ["z_first", "m_middle", "a_second"]

        sl_nonzero = strat.shortlist("q_axis5")
        assert sl_nonzero.candidates == ("a_second", "m_middle", "z_first")
        assert len(set(sl_nonzero.scores)) == 1
        assert np.isclose(sl_nonzero.scores[0], 1.0 / np.sqrt(5.0), atol=1e-6)

        # Case B: exact 0.0 float32 score tie (candidates have 5th coord 0.0, query is along 5th axis)
        vecs_zero = {
            "z_first": vec5_for_gray(1, 0.0),
            "m_middle": vec5_for_gray(2, 0.0),
            "a_second": vec5_for_gray(3, 0.0),
            "q_axis5": np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        }
        emb2 = ControllableEmbedder(vecs_zero, dim=5)
        strat.setup(g1, emb2)
        assert [e.name for e in strat._segments[0]] == ["z_first", "m_middle", "a_second"]

        sl_zero = strat.shortlist("q_axis5")
        assert sl_zero.candidates == ("a_second", "m_middle", "z_first")
        assert sl_zero.scores == (0.0, 0.0, 0.0)

    def test_bucket_size_at_shortlist_inside_span_gap_self_member_and_preserved_across_split(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Proves bucket_size_at_shortlist equals len(seg) >= 1 on inside-span, gap, and self-member queries and stays equal to pre-split size after a split in on_inserted() (kills M-42)."""
        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
        monkeypatch.setattr(
            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
        )

        # Build a 2-segment graph of 8 nodes:
        # Segment 0 gets 4 nodes at gray ranks 1, 2, 3, 4; Segment 1 gets 4 nodes at gray ranks 10, 11, 12, 13
        def vec4_for_gray(gray_rank: int) -> np.ndarray:
            code = gray_rank ^ (gray_rank >> 1)
            return TestMergeAndNeighbourRule._vec_for_code(code, 4)

        vecs: dict[str, np.ndarray] = {}
        g = ConceptGraph()
        for g_rank in (1, 2, 3, 4, 10, 11, 12, 13):
            name = f"n_{g_rank:02d}"
            vecs[name] = vec4_for_gray(g_rank)
            g.add_node(name)

        vecs["q_inside"] = vec4_for_gray(2)  # inside Segment 0 span [1, 4]
        vecs["q_gap_1"] = vec4_for_gray(5)   # in gap (4, 10), closer to Segment 0
        vecs["q_gap_2"] = vec4_for_gray(6)   # in gap, will bring Segment 0 to size 6
        vecs["q_split"] = vec4_for_gray(7)   # 7th node in Segment 0 -> triggers split (6 -> 7 -> 3 + 4)

        emb = ControllableEmbedder(vecs, dim=4)
        strat.setup(g, emb)
        assert len(strat._segments) == 2
        assert [len(s) for s in strat._segments] == [4, 4]

        # 1. Inside-span query (not yet in graph)
        strat.shortlist("q_inside")
        d_in = strat.diagnostics()
        seg_in = strat._segments[d_in["bucket_id"]]
        seg_in_names = {e.name for e in seg_in}
        assert d_in["inside_bucket_span"] is True
        assert d_in["bucket_size_at_shortlist"] == len(seg_in) == 4 >= 1
        assert d_in["bucket_size_at_shortlist"] == d_in["shortlist_size"] + (
            1 if "q_inside" in seg_in_names else 0
        )

        # 2. Query where new_name is already a member of the segment (self-exclusion in shortlist_size)
        strat.shortlist("n_02")
        d_self = strat.diagnostics()
        seg_self = strat._segments[d_self["bucket_id"]]
        seg_self_names = {e.name for e in seg_self}
        assert "n_02" in seg_self_names
        assert d_self["bucket_size_at_shortlist"] == len(seg_self) == 4 >= 1
        assert d_self["shortlist_size"] == 3
        assert d_self["bucket_size_at_shortlist"] == d_self["shortlist_size"] + (
            1 if "n_02" in seg_self_names else 0
        )

        # 3. Gap query (outside every segment span)
        strat.shortlist("q_gap_1")
        d_gap = strat.diagnostics()
        seg_gap = strat._segments[d_gap["bucket_id"]]
        seg_gap_names = {e.name for e in seg_gap}
        assert d_gap["inside_bucket_span"] is False
        assert d_gap["bucket_size_at_shortlist"] == len(seg_gap) == 4 >= 1
        assert d_gap["bucket_size_at_shortlist"] == d_gap["shortlist_size"] + (
            1 if "q_gap_1" in seg_gap_names else 0
        )
        g.add_node("q_gap_1")
        strat.on_inserted("q_gap_1", ())
        assert strat.diagnostics()["bucket_size_at_shortlist"] == 4
        assert strat.diagnostics()["bucket_size"] == 5

        # Insert a 6th node into Segment 0 so its size reaches s_max = 6
        strat.shortlist("q_gap_2")
        assert strat.diagnostics()["bucket_size_at_shortlist"] == 5
        g.add_node("q_gap_2")
        strat.on_inserted("q_gap_2", ())
        assert strat.diagnostics()["bucket_size_at_shortlist"] == 5
        assert strat.diagnostics()["bucket_size"] == 6
        assert strat.diagnostics()["split_occurred"] is False

        # 4. Query and insert 7th node into Segment 0 -> triggers split (6 + 1 = 7 -> 3 and 4)
        strat.shortlist("q_split")
        d_before_split = strat.diagnostics()
        assert d_before_split["bucket_size_at_shortlist"] == 6
        assert d_before_split["bucket_size"] == 6
        assert d_before_split["shortlist_size"] == 6

        g.add_node("q_split")
        strat.on_inserted("q_split", ())
        d_after_split = strat.diagnostics()
        assert d_after_split["split_occurred"] is True
        # bucket_size_at_shortlist MUST remain the pre-insert segment size (6),
        # while bucket_size updates to the post-split home half size (4 for the right half containing q_split)
        assert d_after_split["bucket_size_at_shortlist"] == 6
        assert d_after_split["bucket_size"] == 4


