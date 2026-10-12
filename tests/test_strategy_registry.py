"""tests/test_strategy_registry.py — INFRA-007
==============================================
Unit tests for ``graph_insertion.strategies.registry`` and lazy exports in
``graph_insertion.strategies``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from graph_insertion.strategies.registry import (
    PARAM_APPLICABILITY,
    STRATEGY_FACTORIES,
    build_strategy_slug,
    check_applicability,
    derive_default_run_id,
)
from scripts.run_experiment import STRATEGY_REGISTRY, StubNarrowingStrategy


class TestStrategyRegistry:
    """Verify STRATEGY_FACTORIES registration, defaults, parameter forwarding, and lazy imports."""

    def test_registry_keys_complete_and_aliased(self) -> None:
        expected = {
            "null",
            "stub",
            "brute_force",
            "embedding_threshold",
            "ann_retrieval",
            "bounded_bucket",
        }
        assert set(STRATEGY_FACTORIES.keys()) == expected
        assert STRATEGY_REGISTRY is STRATEGY_FACTORIES

    def test_every_strategy_constructs_with_defaults(self) -> None:
        s_null = STRATEGY_FACTORIES["null"](42, None)
        assert s_null.name == "null"
        assert s_null.config() == {"seed": 42, "k": 1}

        s_stub = STRATEGY_FACTORIES["stub"](42, None)
        assert isinstance(s_stub, StubNarrowingStrategy)
        assert s_stub.config() == {"name": "stub_narrowing", "top_k": 5}

        s_bf = STRATEGY_FACTORIES["brute_force"](42, None)
        assert s_bf.name == "brute_force"
        assert s_bf.config() == {"seed": 42}

        s_et = STRATEGY_FACTORIES["embedding_threshold"](42, None)
        assert s_et.name == "embedding_threshold"
        assert s_et.config() == {"theta": 0.6, "seed": 42}

        s_ann = STRATEGY_FACTORIES["ann_retrieval"](42, None)
        assert s_ann.name == "ann_retrieval"
        ann_cfg = s_ann.config()
        assert ann_cfg["k"] == 10
        assert ann_cfg["ef_search"] == 128
        assert ann_cfg["M"] == 16
        assert ann_cfg["ef_construction"] == 200
        assert ann_cfg["seed"] == 42

        s_bb = STRATEGY_FACTORIES["bounded_bucket"](42, None)
        assert s_bb.name == "bounded_bucket"
        assert s_bb.config() == {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}

    def test_legacy_two_arg_calls_work_for_null_and_stub(self) -> None:
        s_null_default = STRATEGY_FACTORIES["null"](42, None)
        assert s_null_default.config() == {"seed": 42, "k": 1}

        s_null_custom = STRATEGY_FACTORIES["null"](99, 7)
        assert s_null_custom.config() == {"seed": 99, "k": 7}

        s_stub_default = STRATEGY_FACTORIES["stub"](42, None)
        assert s_stub_default.config()["top_k"] == 5

        s_stub_custom = STRATEGY_FACTORIES["stub"](42, 3)
        assert s_stub_custom.config()["top_k"] == 3

    def test_parameters_and_seed_reach_strategy_config(self) -> None:
        # embedding_threshold: theta and seed
        s_et = STRATEGY_FACTORIES["embedding_threshold"](101, None, theta=0.4)
        assert s_et.config() == {"theta": 0.4, "seed": 101}

        # ann_retrieval: k, ef_search, and seed (ensure k and ef_search are not swapped)
        s_ann = STRATEGY_FACTORIES["ann_retrieval"](202, 5, ef_search=64)
        ann_cfg = s_ann.config()
        assert ann_cfg["k"] == 5
        assert ann_cfg["ef_search"] == 64
        assert ann_cfg["seed"] == 202

        s_ann_2 = STRATEGY_FACTORIES["ann_retrieval"](203, 20, ef_search=256)
        ann_cfg_2 = s_ann_2.config()
        assert ann_cfg_2["k"] == 20
        assert ann_cfg_2["ef_search"] == 256
        assert ann_cfg_2["seed"] == 203

        # bounded_bucket: s_min, s_max, n_bits, and seed (ensure s_min and s_max are not swapped)
        s_bb = STRATEGY_FACTORIES["bounded_bucket"](
            303, None, s_min=2, s_max=5, n_bits=10
        )
        assert s_bb.config() == {"s_min": 2, "s_max": 5, "n_bits": 10, "seed": 303}

        # brute_force: seed
        s_bf = STRATEGY_FACTORIES["brute_force"](404, None)
        assert s_bf.config() == {"seed": 404}

        # null: seed and k
        s_null = STRATEGY_FACTORIES["null"](505, 4)
        assert s_null.config() == {"seed": 505, "k": 4}

    def test_applicability_matrix(self) -> None:
        assert check_applicability("null", "k") is True
        assert check_applicability("stub", "k") is True
        assert check_applicability("ann_retrieval", "k") is True
        assert check_applicability("brute_force", "k") is False
        assert check_applicability("embedding_threshold", "k") is False
        assert check_applicability("bounded_bucket", "k") is False

        assert check_applicability("embedding_threshold", "theta") is True
        for s in ("null", "stub", "brute_force", "ann_retrieval", "bounded_bucket"):
            assert check_applicability(s, "theta") is False

        assert check_applicability("ann_retrieval", "ef_search") is True
        for s in ("null", "stub", "brute_force", "embedding_threshold", "bounded_bucket"):
            assert check_applicability(s, "ef_search") is False

        for p in ("s_min", "s_max", "n_bits"):
            assert check_applicability("bounded_bucket", p) is True
            for s in ("null", "stub", "brute_force", "embedding_threshold", "ann_retrieval"):
                assert check_applicability(s, p) is False

    def test_ann_retrieval_factory_without_faiss_raises_import_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import graph_insertion.strategies.ann_retrieval as ann_mod

        monkeypatch.setattr(ann_mod, "faiss", None)
        with pytest.raises(ImportError, match="pip install"):
            STRATEGY_FACTORIES["ann_retrieval"](42, 10)

    def test_strategies_init_and_registry_import_without_faiss_and_sentence_transformers_subprocess(
        self,
    ) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        src_dir = repo_root / "src"
        code = (
            "import sys\n"
            "sys.modules['faiss'] = None\n"
            "sys.modules['sentence_transformers'] = None\n"
            "import graph_insertion.strategies as s\n"
            "import graph_insertion.strategies.registry as r\n"
            "import graph_insertion.embedding_minilm as em\n"
            "assert 'faiss' not in sys.modules or sys.modules['faiss'] is None\n"
            "assert 'sentence_transformers' not in sys.modules or sys.modules['sentence_transformers'] is None\n"
            "assert hasattr(s, 'NullStrategy')\n"
            "assert set(r.STRATEGY_FACTORIES.keys()) == {'null', 'stub', 'brute_force', 'embedding_threshold', 'ann_retrieval', 'bounded_bucket'}\n"
            # Non-faiss strategies instantiate cleanly when faiss & sentence_transformers are blocked
            "assert r.STRATEGY_FACTORIES['null'](42, None).config() == {'seed': 42, 'k': 1}\n"
            "assert r.STRATEGY_FACTORIES['brute_force'](42, None).config() == {'seed': 42}\n"
            "assert r.STRATEGY_FACTORIES['embedding_threshold'](42, None).config() == {'theta': 0.6, 'seed': 42}\n"
            "assert r.STRATEGY_FACTORIES['bounded_bucket'](42, None).config() == {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(repo_root),
            env={"PYTHONPATH": f"{src_dir}:{repo_root}"},
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"

    def test_slug_and_default_run_id_derivation(self) -> None:
        assert derive_default_run_id("sweep", "brute_force", {"seed": 42}) == "sweep_brute_force"
        assert derive_default_run_id("sweep", "brute_force", {"seed": 7}) == "sweep_brute_force_seed7"
        assert (
            derive_default_run_id("sweep", "embedding_threshold", {"theta": 0.6, "seed": 42})
            == "sweep_embedding_threshold_theta0.6"
        )
        assert (
            derive_default_run_id("sweep", "ann_retrieval", {"k": 10, "ef_search": 128, "seed": 42})
            == "sweep_ann_retrieval_k10_ef128"
        )
        assert (
            derive_default_run_id(
                "sweep", "bounded_bucket", {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
            )
            == "sweep_bounded_bucket_smin5_smax10_nb12"
        )
        assert derive_default_run_id("sweep", "null", {"k": 1, "seed": 42}) == "sweep_null_k1"
        assert derive_default_run_id("sweep", "stub", {"top_k": 5}) == "sweep_stub_k5"
