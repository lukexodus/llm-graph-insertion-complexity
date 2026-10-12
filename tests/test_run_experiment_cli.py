"""tests/test_run_experiment_cli.py — INFRA-007
===============================================
Comprehensive CLI tests for ``scripts/run_experiment.py``:
  - Test 2: CLI parsing, applicability checks (exit 2), out-of-range ValueError (exit 1, no traceback)
  - Test 3: ``--strategy ann_retrieval --dry-run`` with faiss blocked (exit 1, install hint)
  - Test 4: Run-directory slugs for every row of section 2.D, ``--seed`` slug suffix,
            ``--run-id`` / ``--output-dir`` precedence, ``strategy_config.json`` sidecar,
            ``--resume`` mismatch refusal, and older directory warning without sidecar
  - Test 5: ``--live`` and ``--embedder`` gates
  - Test 6: Planned-calls upper bounds from parsed CLI arguments over the D-35 sweep matrix
  - Test 7: End-to-end offline CLI smoke for all four strategies in sweep and accuracy modes
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

from graph_insertion.harness import HarnessConfig
from graph_insertion.strategies.registry import (
    STRATEGY_FACTORIES,
    derive_default_run_id,
)
from scripts.run_experiment import (
    STRATEGY_REGISTRY,
    build_parser,
    compute_planned_calls_upper_bound,
    main,
)


# ---------------------------------------------------------------------------
# Section 2.D Table of Runs (4 primary + 8 sensitivity configurations)
# ---------------------------------------------------------------------------

SECTION_2D_RUNS: list[tuple[str, list[str], str, int, dict[str, Any]]] = [
    # (label, cli_tokens, expected_sweep_dir, expected_d35_bound, expected_keyed_config)
    (
        "primary_s1_brute_force",
        ["--strategy", "brute_force"],
        "results/sweep_brute_force",
        38500,
        {"seed": 42},
    ),
    (
        "primary_s2_embedding_threshold",
        ["--strategy", "embedding_threshold"],
        "results/sweep_embedding_threshold_theta0.6",
        38500,
        {"theta": 0.6, "seed": 42},
    ),
    (
        "primary_s3_ann_retrieval",
        ["--strategy", "ann_retrieval"],
        "results/sweep_ann_retrieval_k10_ef128",
        600,
        {"k": 10, "ef_search": 128, "seed": 42},
    ),
    (
        "primary_s4_bounded_bucket",
        ["--strategy", "bounded_bucket"],
        "results/sweep_bounded_bucket_smin5_smax10_nb12",
        600,
        {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42},
    ),
    (
        "sens_s2_theta_0.4",
        ["--strategy", "embedding_threshold", "--theta", "0.4"],
        "results/sweep_embedding_threshold_theta0.4",
        38500,
        {"theta": 0.4, "seed": 42},
    ),
    (
        "sens_s2_theta_0.5",
        ["--strategy", "embedding_threshold", "--theta", "0.5"],
        "results/sweep_embedding_threshold_theta0.5",
        38500,
        {"theta": 0.5, "seed": 42},
    ),
    (
        "sens_s3_k_5",
        ["--strategy", "ann_retrieval", "-k", "5"],
        "results/sweep_ann_retrieval_k5_ef128",
        300,
        {"k": 5, "ef_search": 128, "seed": 42},
    ),
    (
        "sens_s3_k_20",
        ["--strategy", "ann_retrieval", "-k", "20"],
        "results/sweep_ann_retrieval_k20_ef128",
        1200,
        {"k": 20, "ef_search": 128, "seed": 42},
    ),
    (
        "sens_s3_ef_64",
        ["--strategy", "ann_retrieval", "--ef-search", "64"],
        "results/sweep_ann_retrieval_k10_ef64",
        600,
        {"k": 10, "ef_search": 64, "seed": 42},
    ),
    (
        "sens_s3_ef_256",
        ["--strategy", "ann_retrieval", "--ef-search", "256"],
        "results/sweep_ann_retrieval_k10_ef256",
        600,
        {"k": 10, "ef_search": 256, "seed": 42},
    ),
    (
        "sens_s4_smin2_smax5",
        ["--strategy", "bounded_bucket", "--s-min", "2", "--s-max", "5"],
        "results/sweep_bounded_bucket_smin2_smax5_nb12",
        300,
        {"s_min": 2, "s_max": 5, "n_bits": 12, "seed": 42},
    ),
    (
        "sens_s4_smin10_smax20",
        ["--strategy", "bounded_bucket", "--s-min", "10", "--s-max", "20"],
        "results/sweep_bounded_bucket_smin10_smax20_nb12",
        1200,
        {"s_min": 10, "s_max": 20, "n_bits": 12, "seed": 42},
    ),
]


class TestCLIParsingAndApplicability:
    """Section 3 Test 2: CLI parsing, applicability checks, and out-of-range errors."""

    def test_strategy_choices_match_registry_keys(self) -> None:
        parser = build_parser()
        strat_action = next(a for a in parser._actions if a.dest == "strategy")
        assert list(strat_action.choices) == list(STRATEGY_FACTORIES.keys())
        assert list(strat_action.choices) == list(STRATEGY_REGISTRY.keys())

        k_action = next(a for a in parser._actions if a.dest == "k")
        assert k_action.default is None
        assert "null, stub and ann_retrieval" in (k_action.help or "")

    @pytest.mark.parametrize(
        "strategy,flag_tokens,expected_flag_name",
        [
            ("null", ["--theta", "0.5"], "--theta"),
            ("null", ["--ef-search", "64"], "--ef-search"),
            ("stub", ["--theta", "0.5"], "--theta"),
            ("brute_force", ["-k", "5"], "-k/--k"),
            ("brute_force", ["--s-max", "10"], "--s-max"),
            ("brute_force", ["--theta", "0.5"], "--theta"),
            ("embedding_threshold", ["-k", "5"], "-k/--k"),
            ("embedding_threshold", ["--ef-search", "64"], "--ef-search"),
            ("embedding_threshold", ["--s-min", "5"], "--s-min"),
            ("ann_retrieval", ["--theta", "0.5"], "--theta"),
            ("ann_retrieval", ["--s-min", "5"], "--s-min"),
            ("ann_retrieval", ["--n-bits", "12"], "--n-bits"),
            ("bounded_bucket", ["-k", "10"], "-k/--k"),
            ("bounded_bucket", ["--theta", "0.5"], "--theta"),
            ("bounded_bucket", ["--ef-search", "128"], "--ef-search"),
        ],
    )
    def test_inapplicable_flag_exits_2_naming_flag_and_strategy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        strategy: str,
        flag_tokens: list[str],
        expected_flag_name: str,
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["run_experiment.py", "--dry-run", "--strategy", strategy, *flag_tokens],
        )
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2
        err = capsys.readouterr().err
        assert expected_flag_name in err
        assert strategy in err

    @pytest.mark.parametrize(
        "cli_args",
        [
            ["--strategy", "embedding_threshold", "--theta", "1.5"],
            ["--strategy", "embedding_threshold", "--theta", "-1.5"],
            ["--strategy", "ann_retrieval", "-k", "0"],
            ["--strategy", "ann_retrieval", "--ef-search", "0"],
            ["--strategy", "bounded_bucket", "--s-min", "1"],
            ["--strategy", "bounded_bucket", "--s-min", "6", "--s-max", "10"],
            ["--strategy", "bounded_bucket", "--n-bits", "0"],
            ["--strategy", "bounded_bucket", "--n-bits", "63"],
            ["--strategy", "null", "-k", "0"],
            ["--strategy", "stub", "-k", "-1"],
        ],
    )
    def test_out_of_range_values_exit_1_without_traceback(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cli_args: list[str],
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["run_experiment.py", "--dry-run", *cli_args],
        )
        rc = main()
        assert rc == 1
        err = capsys.readouterr().err
        assert err.startswith("ERROR:")
        assert "Traceback" not in err


class TestAnnRetrievalWithoutFaiss:
    """Section 3 Test 3: --strategy ann_retrieval --dry-run without faiss fails cleanly."""

    def test_ann_retrieval_dry_run_without_faiss_exits_1_with_install_hint(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import graph_insertion.strategies.ann_retrieval as ann_mod

        monkeypatch.setattr(ann_mod, "faiss", None)
        monkeypatch.setattr(
            "sys.argv",
            ["run_experiment.py", "--mode", "sweep", "--strategy", "ann_retrieval", "--dry-run"],
        )
        rc = main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "ERROR:" in err
        assert "faiss" in err.lower()
        assert "pip install" in err
        assert "Traceback" not in err


class TestRunDirectoryKeysAndSidecarGuard:
    """Section 3 Test 4: Slugs, precedence, sidecar content, and --resume mismatch refusal."""

    @pytest.mark.parametrize(
        "label,cli_tokens,expected_sweep_dir,expected_bound,expected_keyed_cfg",
        SECTION_2D_RUNS,
    )
    def test_section_2d_default_run_directories_and_bounds_via_cli(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        label: str,
        cli_tokens: list[str],
        expected_sweep_dir: str,
        expected_bound: int,
        expected_keyed_cfg: dict[str, Any],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            ["run_experiment.py", "--mode", "sweep", "--dry-run", *cli_tokens],
        )
        rc = main()
        assert rc == 0, f"Failed for {label}: {capsys.readouterr().err}"
        out = capsys.readouterr().out
        assert f"Default/resolved output directory: {expected_sweep_dir}" in out
        assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_bound}" in out

        slug_part = expected_sweep_dir.removeprefix("results/")
        assert re.fullmatch(r"[a-z0-9._-]+", slug_part) is not None

        # Dry run must not create output directory or sidecar file on disk (INFRA-007-P Step D)
        run_dir = tmp_path / expected_sweep_dir
        assert not run_dir.exists(), f"dry-run should not create {run_dir}"
        assert list(tmp_path.iterdir()) == []

        # Also check accuracy mode slug derivation and keyed strategy config
        parser = build_parser()
        args = parser.parse_args(["--mode", "accuracy", *cli_tokens])
        strat = STRATEGY_FACTORIES[args.strategy](
            args.seed,
            args.k,
            theta=args.theta,
            ef_search=args.ef_search,
            s_min=args.s_min,
            s_max=args.s_max,
            n_bits=args.n_bits,
        )
        cfg = strat.config()
        for k, v in expected_keyed_cfg.items():
            assert cfg[k] == v
        acc_dir = f"results/{derive_default_run_id('accuracy', args.strategy, cfg)}"
        assert acc_dir == expected_sweep_dir.replace("results/sweep_", "results/accuracy_", 1)

    @pytest.mark.parametrize(
        "cli_tokens,expected_dir",
        [
            (
                ["--strategy", "brute_force", "--seed", "99"],
                "results/sweep_brute_force_seed99",
            ),
            (
                ["--strategy", "embedding_threshold", "--seed", "99"],
                "results/sweep_embedding_threshold_theta0.6_seed99",
            ),
            (
                ["--strategy", "ann_retrieval", "--seed", "99"],
                "results/sweep_ann_retrieval_k10_ef128_seed99",
            ),
            (
                ["--strategy", "bounded_bucket", "--seed", "99"],
                "results/sweep_bounded_bucket_smin5_smax10_nb12_seed99",
            ),
            (
                ["--strategy", "null", "--seed", "99"],
                "results/sweep_null_k1_seed99",
            ),
        ],
    )
    def test_non_default_seed_included_in_default_directory_and_strategy_config(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        cli_tokens: list[str],
        expected_dir: str,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            ["run_experiment.py", "--mode", "sweep", "--dry-run", *cli_tokens],
        )
        rc = main()
        assert rc == 0
        out = capsys.readouterr().out
        assert f"Default/resolved output directory: {expected_dir}" in out
        # Dry run must not create directory or sidecar (INFRA-007-P Step D)
        assert not (tmp_path / expected_dir).exists()

        # Real tiny run writes strategy_config.json with seed 99
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                *cli_tokens,
            ],
        )
        assert main() == 0
        capsys.readouterr()
        sidecar = json.loads((tmp_path / expected_dir / "strategy_config.json").read_text())
        assert sidecar["config"]["seed"] == 99

    def test_explicit_run_id_and_output_dir_precedence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        # 1. Explicit --run-id wins over default slug; dry-run writes nothing to disk
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--run-id",
                "custom_run_123",
                "--dry-run",
            ],
        )
        assert main() == 0
        out1 = capsys.readouterr().out
        assert "Default/resolved output directory: results/custom_run_123" in out1
        assert not (tmp_path / "results" / "custom_run_123").exists()

        # 2. Explicit --output-dir wins over both default slug and --run-id; dry-run writes nothing to disk
        explicit_dir = tmp_path / "my_explicit_dir"
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--run-id",
                "custom_run_123",
                "--output-dir",
                str(explicit_dir),
                "--dry-run",
            ],
        )
        assert main() == 0
        out2 = capsys.readouterr().out
        assert f"Default/resolved output directory: {explicit_dir}" in out2
        assert not explicit_dir.exists()

    def test_sidecar_written_and_resume_mismatch_refused(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        run_dir = tmp_path / "run_ann"
        # Run 1: real offline trial run with ann_retrieval k=10
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "ann_retrieval",
                "-k",
                "10",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--output-dir",
                str(run_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        sidecar_path = run_dir / "strategy_config.json"
        raw_path = run_dir / "raw.jsonl"
        assert sidecar_path.exists()
        assert raw_path.exists()

        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        assert set(sidecar.keys()) == {
            "strategy",
            "config",
            "embedder",
            "mode",
            "command_line_params",
        }
        assert sidecar["strategy"] == "ann_retrieval"
        assert sidecar["config"]["k"] == 10
        assert sidecar["config"]["ef_search"] == 128
        assert sidecar["mode"] == "sweep"

        # Mismatch 1: change k from 10 to 5 on --resume
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "ann_retrieval",
                "-k",
                "5",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(run_dir),
            ],
        )
        assert main() == 1
        err_k = capsys.readouterr().err
        assert "mismatch" in err_k.lower()
        assert "'k': 10" in err_k
        assert "'k': 5" in err_k

        # Mismatch 2: change strategy to embedding_threshold (--theta 0.5)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--theta",
                "0.5",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(run_dir),
            ],
        )
        assert main() == 1
        err_strat = capsys.readouterr().err
        assert "mismatch" in err_strat.lower()
        assert "ann_retrieval" in err_strat
        assert "embedding_threshold" in err_strat

        # Mismatch 3: change theta on an embedding_threshold run
        et_dir = tmp_path / "run_et"
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--theta",
                "0.6",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--output-dir",
                str(et_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--theta",
                "0.4",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(et_dir),
            ],
        )
        assert main() == 1
        err_theta = capsys.readouterr().err
        assert "mismatch" in err_theta.lower()
        assert "0.6" in err_theta
        assert "0.4" in err_theta

        # Matching --resume succeeds
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--theta",
                "0.6",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(et_dir),
            ],
        )
        assert main() == 0

    def test_older_directory_with_raw_jsonl_but_no_sidecar_warns_and_does_not_refuse(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        legacy_dir = tmp_path / "legacy_run"
        legacy_dir.mkdir(parents=True)
        raw_path = legacy_dir / "raw.jsonl"
        raw_path.write_text(
            json.dumps({"key": "sweep::null::6::0", "status": "success", "strategy": "null"})
            + "\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "null",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(legacy_dir),
            ],
        )
        rc = main()
        assert rc == 0
        err = capsys.readouterr().err
        assert "WARNING:" in err
        assert not (legacy_dir / "strategy_config.json").exists()


class TestLiveAndEmbedderGates:
    """Section 3 Test 5: --live and --embedder gates."""

    @pytest.mark.parametrize(
        "strategy",
        ["embedding_threshold", "ann_retrieval", "bounded_bucket"],
    )
    def test_live_with_embedding_strategy_and_fake_embedder_refused_before_key_or_client(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        strategy: str,
    ) -> None:
        # Remove DEEPSEEK_API_KEY and omit --names-file to prove refusal happens BEFORE both
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--live",
                "--mode",
                "sweep",
                "--strategy",
                strategy,
                "--embedder",
                "fake",
            ],
        )
        rc = main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "ERROR:" in err
        assert "--embedder minilm" in err
        assert "DEEPSEEK_API_KEY" not in err

    @pytest.mark.parametrize(
        "strategy,embedder",
        [
            ("embedding_threshold", "minilm"),
            ("ann_retrieval", "minilm"),
            ("bounded_bucket", "minilm"),
            ("brute_force", "fake"),
            ("brute_force", "minilm"),
            ("null", "fake"),
            ("null", "minilm"),
        ],
    )
    def test_live_dry_run_exits_0_for_all_strategies_without_api_key(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        strategy: str,
        embedder: str,
    ) -> None:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        names_file = tmp_path / "names.json"
        names_file.write_text(
            json.dumps([f"valid_concept_{i:04d}" for i in range(2005)]),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--live",
                "--dry-run",
                "--mode",
                "sweep",
                "--strategy",
                strategy,
                "--embedder",
                embedder,
                "--names-file",
                str(names_file),
            ],
        )
        rc = main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "LIVE EXPERIMENT PRE-FLIGHT ESTIMATE" in out
        assert f"Strategy:                      {strategy}" in out
        assert "Dry run complete" in out


class TestPlannedCallsBoundsFromCLI:
    """Section 3 Test 6: Planned-calls bounds over the D-35 sweep matrix driven by parsed CLI args."""

    @pytest.mark.parametrize(
        "label,cli_tokens,expected_sweep_dir,expected_bound,expected_keyed_cfg",
        SECTION_2D_RUNS,
    )
    def test_d35_sweep_matrix_planned_calls_upper_bound(
        self,
        tmp_path: Path,
        label: str,
        cli_tokens: list[str],
        expected_sweep_dir: str,
        expected_bound: int,
        expected_keyed_cfg: dict[str, Any],
    ) -> None:
        parser = build_parser()
        args = parser.parse_args(["--mode", "sweep", *cli_tokens])
        strat = STRATEGY_FACTORIES[args.strategy](
            args.seed,
            args.k,
            theta=args.theta,
            ef_search=args.ef_search,
            s_min=args.s_min,
            s_max=args.s_max,
            n_bits=args.n_bits,
        )
        cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=tuple(args.sweep_sizes),
            sweep_trials_per_size=args.sweep_trials,
            seed=args.seed,
        )
        bound = compute_planned_calls_upper_bound(
            config=cfg,
            corpora=None,
            strategy=strat,
            raw_jsonl_path=tmp_path / "nonexistent_raw.jsonl",
        )
        assert bound.full_plan_bound == expected_bound, f"Mismatch for {label}"
        assert bound.remaining_bound == expected_bound, f"Mismatch for {label}"
        assert bound.full_plan_trials == 60


class TestEndToEndOfflineCLISmoke:
    """Section 3 Test 7: End-to-end offline CLI smoke for all four strategies."""

    @pytest.mark.parametrize(
        "strategy",
        ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"],
    )
    def test_sweep_and_accuracy_offline_smoke(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        strategy: str,
    ) -> None:
        # 1. Sweep mode at tiny sizes [6, 8] x 1 trial
        sweep_dir = tmp_path / f"smoke_sweep_{strategy}"
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                strategy,
                "--sweep-sizes",
                "6",
                "8",
                "--sweep-trials",
                "1",
                "--confirm",
                "--output-dir",
                str(sweep_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        for fname in ("raw.jsonl", "summary.csv", "manifest.json", "strategy_config.json"):
            assert (sweep_dir / fname).exists(), f"Missing {fname} in {sweep_dir}"

        sweep_records = [
            json.loads(line)
            for line in (sweep_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(sweep_records) == 2
        assert all(r["strategy"] == strategy and r["status"] == "success" for r in sweep_records)
        sweep_sidecar = json.loads((sweep_dir / "strategy_config.json").read_text(encoding="utf-8"))
        assert sweep_sidecar["strategy"] == strategy

        # 2. Accuracy mode on DSA (capped with --max-llm-calls 1 so smoke completes in <0.1s)
        acc_dir = tmp_path / f"smoke_acc_{strategy}"
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "accuracy",
                "--corpus",
                "DSA",
                "--strategy",
                strategy,
                "--max-llm-calls",
                "1",
                "--confirm",
                "--output-dir",
                str(acc_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        for fname in ("raw.jsonl", "summary.csv", "manifest.json", "strategy_config.json"):
            assert (acc_dir / fname).exists(), f"Missing {fname} in {acc_dir}"

        acc_records = [
            json.loads(line)
            for line in (acc_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(acc_records) >= 1
        assert all(r["strategy"] == strategy and r["status"] == "success" for r in acc_records)
        acc_sidecar = json.loads((acc_dir / "strategy_config.json").read_text(encoding="utf-8"))
        assert acc_sidecar["strategy"] == strategy


class _CLIStubSentenceTransformer:
    """Deterministic offline stub for sentence_transformers.SentenceTransformer in CLI tests."""

    instances: list["_CLIStubSentenceTransformer"] = []

    def __init__(
        self,
        model_name_or_path: str,
        *,
        revision: str | None = None,
        device: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.revision = revision
        self.device = device
        self.kwargs = kwargs
        self.encode_calls: int = 0
        _CLIStubSentenceTransformer.instances.append(self)

    def encode(self, sentences: Any, **kwargs: Any) -> Any:
        import hashlib
        import numpy as np

        self.encode_calls += 1
        if isinstance(sentences, str):
            digest = hashlib.sha256(sentences.encode("utf-8")).digest()
            rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
            vec = rng.standard_normal(384).astype(np.float32)
            return vec / (np.linalg.norm(vec) + 1e-12)
        rows = []
        for s in sentences:
            digest = hashlib.sha256(str(s).encode("utf-8")).digest()
            rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
            vec = rng.standard_normal(384).astype(np.float32)
            rows.append(vec / (np.linalg.norm(vec) + 1e-12))
        return np.vstack(rows).astype(np.float32)


def _install_stub_st(
    monkeypatch: pytest.MonkeyPatch,
    version: str = "3.1.1",
    revision_pin: str = "a" * 40,
    version_pin: str = "3.1.1",
) -> tuple[type[_CLIStubSentenceTransformer], Any]:
    import types
    import graph_insertion.embedding_minilm as minilm_mod

    _CLIStubSentenceTransformer.instances.clear()
    mod = types.ModuleType("sentence_transformers")
    mod.SentenceTransformer = _CLIStubSentenceTransformer  # type: ignore[attr-defined]
    mod.__version__ = version  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)
    monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", version_pin)
    monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", revision_pin)
    return _CLIStubSentenceTransformer, mod


class TestINFRA007PAmendments:
    """INFRA-007-P tests for resume-guard embedder/mode checks, minilm execution & timing, and dry-run/git_dirty."""

    def test_resume_guard_embedder_identity_and_mode_and_non_resume_existing_raw(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        """Kills R-M11, P-M3, P-M4: guard checks embedder block, mode, and non-resume runs with existing raw.jsonl."""
        stub_cls, st_mod = _install_stub_st(
            monkeypatch,
            version="3.1.1",
            revision_pin="1" * 40,
            version_pin="3.1.1",
        )

        # 1. Start a 'fake' embedder run
        fake_dir = tmp_path / "run_fake_et"
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "fake",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--output-dir",
                str(fake_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        # 1a. Resuming a 'fake' run with '--embedder minilm' is refused (exit 1, shows both blocks; kills P-M3)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "minilm",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(fake_dir),
            ],
        )
        assert main() == 1
        err_type = capsys.readouterr().err
        assert "embedder" in err_type.lower() and "mismatch" in err_type.lower()
        assert "'type': 'fake'" in err_type
        assert "'type': 'minilm'" in err_type

        # 1b. Non---resume run into a directory with raw.jsonl and mismatching sidecar is refused (kills R-M11)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--theta",
                "0.4",
                "--embedder",
                "fake",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--output-dir",
                str(fake_dir),
            ],
        )
        assert main() == 1
        err_no_resume = capsys.readouterr().err
        assert "mismatch" in err_no_resume.lower()

        # 1c. Mode change (sweep vs accuracy in the same directory) is refused (kills P-M4)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "accuracy",
                "--corpus",
                "DSA",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "fake",
                "--max-llm-calls",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(fake_dir),
            ],
        )
        assert main() == 1
        err_mode = capsys.readouterr().err
        assert "mode mismatch" in err_mode.lower()
        assert "'sweep'" in err_mode and "'accuracy'" in err_mode

        # 2. Start a 'minilm' embedder run
        minilm_dir = tmp_path / "run_minilm_et"
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "minilm",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--output-dir",
                str(minilm_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        # 2a. Matching resume with minilm passes
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "minilm",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--resume",
                "--output-dir",
                str(minilm_dir),
            ],
        )
        assert main() == 0
        capsys.readouterr()

        # 2b. minilm revision change refused
        import graph_insertion.embedding_minilm as minilm_mod

        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "2" * 40)
        assert main() == 1
        err_rev = capsys.readouterr().err
        assert "embedder configuration mismatch" in err_rev.lower()
        assert "1" * 40 in err_rev and "2" * 40 in err_rev

        # Restore revision, change installed sentence_transformers version -> refused
        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "1" * 40)
        st_mod.__version__ = "3.2.0"
        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.2.0")
        assert main() == 1
        err_ver = capsys.readouterr().err
        assert "sentence_transformers_version" in err_ver
        assert "3.1.1" in err_ver and "3.2.0" in err_ver

        # 2c. Legacy pre-INFRA-007-P sidecar without sentence_transformers_version key warns once and succeeds
        st_mod.__version__ = "3.1.1"
        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
        sidecar_path = minilm_dir / "strategy_config.json"
        sc_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        del sc_data["embedder"]["sentence_transformers_version"]
        sidecar_path.write_text(json.dumps(sc_data, indent=2), encoding="utf-8")

        assert main() == 0
        err_legacy = capsys.readouterr().err
        assert "WARNING:" in err_legacy
        assert "sentence_transformers_version" in err_legacy

    def test_minilm_offline_execution_and_construction_timing_kills_rm19_and_pm5(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        """Kills R-M19 and P-M5: offline --embedder minilm runs end-to-end; never constructed without --confirm or on --dry-run."""
        stub_rev = "abcdef0123456789abcdef0123456789abcdef01"
        stub_cls, _ = _install_stub_st(
            monkeypatch,
            version="3.1.1",
            revision_pin=stub_rev,
            version_pin="3.1.1",
        )

        # 1. Without --confirm and without --dry-run: MiniLMEmbedder constructor is NEVER called (kills P-M5)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "minilm",
                "--sweep-sizes",
                "12",
                "--sweep-trials",
                "1",
                "--output-dir",
                str(tmp_path / "no_confirm_dir"),
            ],
        )
        assert main() == 1
        err_nc = capsys.readouterr().err
        assert "--confirm" in err_nc
        assert len(stub_cls.instances) == 0

        # 2. With --dry-run: MiniLMEmbedder constructor is NEVER called
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--embedder",
                "minilm",
                "--sweep-sizes",
                "12",
                "--sweep-trials",
                "1",
                "--dry-run",
                "--output-dir",
                str(tmp_path / "dry_run_dir"),
            ],
        )
        assert main() == 0
        capsys.readouterr()
        assert len(stub_cls.instances) == 0

        # 3. End-to-end offline --embedder minilm --confirm for embedding_threshold and bounded_bucket (sizes (12, 30), 2 trials) (kills R-M19)
        for strat_name in ("embedding_threshold", "bounded_bucket"):
            stub_cls.instances.clear()
            out_dir = tmp_path / f"minilm_e2e_{strat_name}"
            monkeypatch.setattr(
                "sys.argv",
                [
                    "run_experiment.py",
                    "--mode",
                    "sweep",
                    "--strategy",
                    strat_name,
                    "--embedder",
                    "minilm",
                    "--sweep-sizes",
                    "12",
                    "30",
                    "--sweep-trials",
                    "2",
                    "--confirm",
                    "--output-dir",
                    str(out_dir),
                ],
            )
            assert main() == 0, f"Failed for {strat_name}: {capsys.readouterr().err}"
            capsys.readouterr()

            assert len(stub_cls.instances) == 1
            assert stub_cls.instances[0].revision == stub_rev
            assert stub_cls.instances[0].encode_calls == 8

            sidecar = json.loads((out_dir / "strategy_config.json").read_text(encoding="utf-8"))
            assert sidecar["embedder"]["type"] == "minilm"
            assert sidecar["embedder"]["revision"] == stub_rev
            assert sidecar["embedder"]["sentence_transformers_version"] == "3.1.1"
            assert sidecar["embedder"]["dim"] == 384

            records = [
                json.loads(line)
                for line in (out_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(records) == 4
            assert all(r["status"] == "success" and r["strategy"] == strat_name for r in records)
            assert all(r["metrics"]["embedding_calls"] == 1 for r in records)

    def test_dry_run_creates_nothing_and_real_run_sidecar_before_trial1_and_git_dirty_false_kills_rm26_and_pm6(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        """Kills R-M26 and P-M6: dry-run creates nothing on disk; real run records git_dirty==False and writes sidecar before trial 1."""
        import subprocess
        import graph_insertion.harness as harness_mod

        # 1. Offline --dry-run creates nothing in tmp_path (kills P-M6)
        empty_check_dir = tmp_path / "dry_run_workspace"
        empty_check_dir.mkdir()
        monkeypatch.chdir(empty_check_dir)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "embedding_threshold",
                "--dry-run",
            ],
        )
        assert main() == 0
        capsys.readouterr()
        assert list(empty_check_dir.iterdir()) == []

        # 2. Clean git repo under tmp_path: real offline --confirm run records git_dirty == False in manifest.json
        clean_repo = tmp_path / "clean_git_repo"
        clean_repo.mkdir()
        subprocess.run(["git", "init"], cwd=clean_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=clean_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clean_repo, check=True)
        (clean_repo / "README.md").write_text("clean repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=clean_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=clean_repo, check=True, capture_output=True)

        monkeypatch.chdir(clean_repo)
        monkeypatch.setattr(harness_mod, "REPO_ROOT", clean_repo)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "null",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
            ],
        )
        assert main() == 0
        capsys.readouterr()

        default_out = clean_repo / "results" / "sweep_null_k1"
        manifest = json.loads((default_out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["git_dirty"] is False
        assert (default_out / "strategy_config.json").exists()

        # 3. Ordering & crash-safety check: sidecar exists BEFORE the first trial starts (kills R-M26)
        crash_dir = tmp_path / "crash_trial1_dir"
        sidecar_existed_at_trial_1: list[bool] = []

        import scripts.run_experiment as run_exp_mod

        class _CrashOnTrial1DecisionStep:
            PROMPT_VERSION = "v2"

            def decide(
                self,
                new_name: str,
                candidates: tuple[str, ...],
                domain_context: str | None = None,
            ) -> Any:
                sidecar_existed_at_trial_1.append((crash_dir / "strategy_config.json").exists())
                raise RuntimeError("simulated crash during trial 1")

        monkeypatch.setattr(
            run_exp_mod,
            "PairwiseDecisionStep",
            lambda client: _CrashOnTrial1DecisionStep(),
        )
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--mode",
                "sweep",
                "--strategy",
                "null",
                "--sweep-sizes",
                "6",
                "--sweep-trials",
                "1",
                "--confirm",
                "--fail-fast",
                "--output-dir",
                str(crash_dir),
            ],
        )
        assert main() == 1
        capsys.readouterr()
        assert sidecar_existed_at_trial_1 == [True]
        assert (crash_dir / "strategy_config.json").exists()

