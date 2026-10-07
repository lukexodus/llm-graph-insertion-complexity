"""
harness.py — INFRA-004
======================
Measurement harness for graph insertion experiments:
  1. Accuracy Runner: Leave-one-out evaluation on DSA and Metacademy ground-truth corpora.
  2. Sweep Runner: Cost-only sweep on synthetic concept name sets across scaling sizes.

Decisions:
  - MEKG_with7nodes domain context and DSA unjudged row scoring policy ([D-30]).
  - Measurement harness trial isolation, overhead accounting, and safety controls ([D-31]).
  - Embedder identity verification and validation timing isolation ([D-28]).
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
import sys
import time
from typing import Any, Callable, Optional, Sequence, Union

from graph_insertion.embedding import Embedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.llm import LLMTransportError
from graph_insertion.loader import LoadedCorpus, load_corpus
from graph_insertion.scoring import (
    AggregateScore,
    NodeScore,
    aggregate_scores,
    score_node_insertion,
)
from graph_insertion.strategy import (
    DecisionStep,
    InsertionMetrics,
    InsertionResult,
    NarrowingStrategy,
    insert_node,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ===========================================================================
# Synthetic Name Source Abstraction
# ===========================================================================

@dataclass(frozen=True)
class SyntheticNameSource:
    """Source of synthetic concept names for cost sweep experiments.

    Attributes
    ----------
    names:
        Sequence of valid snake_case concept names.
    domain_context:
        Optional domain context string for the graph (e.g. "computer science").
    """
    names: Sequence[str]
    domain_context: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.names:
            raise ValueError("SyntheticNameSource must contain at least one name.")
        if len(set(self.names)) != len(self.names):
            raise ValueError("SyntheticNameSource contains duplicate names.")


# ===========================================================================
# Harness Configuration
# ===========================================================================

@dataclass
class HarnessConfig:
    """Configuration for an experimental measurement run.

    Attributes
    ----------
    mode:
        Experiment mode: "accuracy" or "sweep".
    run_id:
        Unique identifier for the run. If empty, auto-generated.
    output_dir:
        Directory where artifacts (manifest.json, raw.jsonl, summary.csv) are stored.
        Defaults to results/<run_id>.
    seed:
        Random seed for sampling and reproducibility.
    repeats:
        Number of repeats for accuracy evaluations (default 1, since T=0 is deterministic).
    metacademy_sample_size:
        Number of held-out nodes sampled from Metacademy (default 30).
    sweep_sizes:
        Graph sizes (n existing concepts) evaluated in cost sweep mode.
    sweep_trials_per_size:
        Number of independent trials evaluated per size in sweep mode (default 10).
    max_llm_calls:
        Safety cap on total LLM API calls across the current execution process.
        Note: counts successful insertions only, evaluated before each trial via
        cumulative_llm_calls; can overshoot by one insertion trial; does not
        persist/carry across --resume invocations.
    dry_run:
        If True, plans and prints insertions and estimated calls without executing.
    confirm:
        Must be True for live runs to proceed without dry_run safety abort.
    resume:
        If True, skips completed trial keys already recorded in raw.jsonl.
    retry_failed:
        If True alongside resume, re-runs trials that previously failed.
    fail_fast:
        If True, aborts immediately on the first trial exception.
    """
    mode: str = "accuracy"
    run_id: str = ""
    output_dir: Optional[Path] = None
    seed: int = 42
    repeats: int = 1
    metacademy_sample_size: int = 30
    sweep_sizes: tuple[int, ...] = (50, 100, 200, 500, 1000, 2000)
    sweep_trials_per_size: int = 10
    max_llm_calls: Optional[int] = None
    dry_run: bool = False
    confirm: bool = False
    resume: bool = False
    retry_failed: bool = False
    fail_fast: bool = False

    def __post_init__(self) -> None:
        if self.mode not in ("accuracy", "sweep"):
            raise ValueError(f"Unknown harness mode: {self.mode}. Must be 'accuracy' or 'sweep'.")
        if not self.run_id:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            self.run_id = f"{ts}_{self.mode}"
        if self.output_dir is None:
            self.output_dir = Path("results") / self.run_id
        else:
            self.output_dir = Path(self.output_dir)


# ===========================================================================
# Secret Sanitization & Environment Inspection
# ===========================================================================

SECRET_KEY_PATTERN = re.compile(
    r"(api_?key|secret|password|credential|private_?key|auth|bearer|(?:^|_)token(?:$|_))",
    re.IGNORECASE,
)


def sanitize_metadata(obj: Any) -> Any:
    """Recursively scrub sensitive credential strings from metadata structures."""
    if isinstance(obj, str):
        if obj.startswith("sk-") or "bearer " in obj.lower():
            return "[REDACTED]"
        return obj
    elif isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_str = str(k)
            if SECRET_KEY_PATTERN.search(k_str):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_metadata(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_metadata(elem) for elem in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_metadata(elem) for elem in obj)
    return obj


def get_git_info(cwd: Optional[Path] = None) -> dict[str, Any]:
    """Inspect current git repository commit and dirty working tree status."""
    target_dir = cwd or REPO_ROOT
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=target_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=target_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return {"git_commit": commit, "git_dirty": bool(status)}
    except Exception:
        return {"git_commit": "unknown", "git_dirty": False}


def get_library_versions(
    packages: Sequence[str] = ("networkx", "pytest", "httpx", "numpy")
) -> dict[str, str]:
    """Retrieve installed versions of core project dependencies."""
    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    return versions


def _extract_metered_llm(decision_step: Any) -> Optional[Any]:
    """Extract an underlying MeteredLLMClient if exposed by the decision step."""
    if hasattr(decision_step, "llm_client") and hasattr(decision_step.llm_client, "snapshot"):
        return decision_step.llm_client
    if hasattr(decision_step, "snapshot"):
        return decision_step
    return None


def _extract_model_and_prompt_info(decision_step: Any) -> dict[str, Any]:
    """Extract model ID, observed models, base_url, and prompt version from decision step or client."""
    configured_model: Optional[str] = None
    observed_model_ids: list[str] = []
    base_url: Optional[str] = None
    prompt_version: Optional[str] = None
    temperature: Optional[float] = None
    thinking_mode: Optional[str] = None
    max_tokens: Optional[int] = None

    if hasattr(decision_step, "PROMPT_VERSION"):
        prompt_version = str(getattr(decision_step, "PROMPT_VERSION"))

    client = None
    if hasattr(decision_step, "llm_client"):
        client = getattr(decision_step, "llm_client")
    elif hasattr(decision_step, "complete"):
        client = decision_step

    if client is not None:
        if hasattr(client, "model_ids_seen"):
            observed_model_ids = sorted(list(client.model_ids_seen))

        inner_client = getattr(client, "client", client)

        for c in (inner_client, client):
            if hasattr(c, "model") and getattr(c, "model"):
                configured_model = str(getattr(c, "model"))
                break
            elif hasattr(c, "model_id") and getattr(c, "model_id"):
                configured_model = str(getattr(c, "model_id"))
                break

        for c in (inner_client, client):
            if hasattr(c, "base_url") and getattr(c, "base_url"):
                base_url = str(getattr(c, "base_url"))
                break

        for c in (inner_client, client):
            if hasattr(c, "temperature"):
                temperature = getattr(c, "temperature")
                break

        for c in (inner_client, client):
            if hasattr(c, "thinking"):
                t_obj = getattr(c, "thinking")
                thinking_mode = t_obj.get("type", None) if isinstance(t_obj, dict) else (str(t_obj) if t_obj is not None else None)
                break
            elif hasattr(c, "thinking_mode"):
                thinking_mode = str(getattr(c, "thinking_mode"))
                break

        for c in (inner_client, client):
            if hasattr(c, "max_tokens"):
                max_tokens = getattr(c, "max_tokens")
                break

    if prompt_version is None:
        try:
            from graph_insertion.decision import PROMPT_VERSION
            prompt_version = PROMPT_VERSION
        except ImportError:
            pass

    return {
        "configured_model": configured_model,
        "observed_model_ids": observed_model_ids,
        "base_url": base_url,
        "prompt_version": prompt_version,
        "temperature": temperature,
        "thinking_mode": thinking_mode,
        "max_tokens": max_tokens,
    }


# ===========================================================================
# Results Persistence & Summary Computation
# ===========================================================================

def load_existing_results(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    """Load previously recorded insertion records from raw.jsonl."""
    if not jsonl_path.exists():
        return {}
    results = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                key = rec.get("key")
                if key:
                    results[key] = rec
            except Exception:
                continue
    return results


def compute_metric_stats(values: Sequence[float]) -> dict[str, float]:
    """Calculate mean, median, stdev, min, and max for a sequence of values."""
    if not values:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    vals = list(values)
    mean_val = float(statistics.mean(vals))
    median_val = float(statistics.median(vals))
    std_val = float(statistics.stdev(vals)) if len(vals) > 1 else 0.0
    return {
        "mean": mean_val,
        "median": median_val,
        "std": std_val,
        "min": float(min(vals)),
        "max": float(max(vals)),
    }


def write_manifest(
    output_dir: Path,
    config: HarnessConfig,
    strategy_config: dict[str, Any],
    decision_step: Any,
) -> None:
    """Write run metadata and execution parameters to manifest.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    git_info = get_git_info()
    model_info = _extract_model_and_prompt_info(decision_step)

    data = {
        "run_id": config.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": config.mode,
        "git_commit": git_info["git_commit"],
        "git_dirty": git_info["git_dirty"],
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "libraries": get_library_versions(),
        "strategy_config": strategy_config,
        "configured_model": model_info["configured_model"],
        "observed_model_ids": model_info["observed_model_ids"],
        "base_url": model_info["base_url"],
        "temperature": model_info["temperature"],
        "thinking_mode": model_info["thinking_mode"],
        "max_tokens": model_info["max_tokens"],
        "prompt_version": model_info["prompt_version"],
        "model_id": model_info["configured_model"],
        "seeds": {"seed": config.seed},
        "sizes": list(config.sweep_sizes) if config.mode == "sweep" else [],
        "metacademy_sample_size": config.metacademy_sample_size if config.mode == "accuracy" else None,
        "repeats": config.repeats,
        "dry_run": config.dry_run,
    }

    sanitized = sanitize_metadata(data)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2)


def generate_summary_csv(jsonl_path: Path, csv_path: Path, mode: str) -> None:
    """Generate summary.csv aggregated from records stored in raw.jsonl."""
    records_by_key: dict[str, dict[str, Any]] = {}
    if not jsonl_path.exists():
        return
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if line:
                try:
                    rec = json.loads(line)
                    key = rec.get("key") or f"unkeyed_{idx}"
                    records_by_key[key] = rec
                except Exception:
                    pass

    records = list(records_by_key.values())
    if not records:
        return

    # Group records by (strategy, corpus) for accuracy, or (strategy, size) for sweep
    groups: dict[tuple[str, Any], list[dict[str, Any]]] = {}
    for r in records:
        strat = r.get("strategy", "unknown")
        if mode == "accuracy":
            grp_key = r.get("corpus", "unknown")
        else:
            grp_key = r.get("size", r.get("n_before", 0))
        groups.setdefault((strat, grp_key), []).append(r)

    rows: list[dict[str, Any]] = []

    for (strat, grp_key), group_recs in groups.items():
        total_trials = len(group_recs)
        successes = [r for r in group_recs if r.get("status") == "success"]
        num_success = len(successes)
        num_failed = total_trials - num_success

        n_with_retries = sum(1 for r in successes if r.get("retries", 0) > 0)

        row: dict[str, Any] = {
            "strategy": strat,
            "mode": mode,
            "corpus_or_size": grp_key,
            "num_trials": total_trials,
            "num_success": num_success,
            "num_failed": num_failed,
            "n_with_retries": n_with_retries,
        }

        # Graph node counts
        n_vals = [r["metrics"]["n_before"] for r in successes if "metrics" in r]
        row["n"] = int(statistics.mean(n_vals)) if n_vals else 0

        # Timing and metric distributions over all successes
        timing_keys = (
            "total_s",
            "shortlist_s",
            "decide_s",
            "apply_s",
            "update_s",
            "validate_s",
        )
        for tk in timing_keys:
            vals = [r["metrics"][tk] for r in successes if "metrics" in r and tk in r["metrics"]]
            st = compute_metric_stats(vals)
            for metric_stat, val in st.items():
                row[f"{tk}_{metric_stat}"] = val

        # total_s breakdown over zero-retry insertions
        zero_retry_successes = [r for r in successes if r.get("retries", 0) == 0]
        zero_retry_total_s = [
            r["metrics"]["total_s"]
            for r in zero_retry_successes
            if "metrics" in r and "total_s" in r["metrics"]
        ]
        zero_st = compute_metric_stats(zero_retry_total_s)
        for metric_stat, val in zero_st.items():
            row[f"total_s_zero_retries_{metric_stat}"] = val

        # Harness wall time and unaccounted time
        harness_vals = [r.get("harness_wall_s", 0.0) for r in successes]
        h_st = compute_metric_stats(harness_vals)
        for stat, val in h_st.items():
            row[f"harness_wall_s_{stat}"] = val

        unaccounted_vals = [r.get("unaccounted_s", 0.0) for r in successes]
        u_st = compute_metric_stats(unaccounted_vals)
        for stat, val in u_st.items():
            row[f"unaccounted_s_{stat}"] = val

        # Counts: llm_calls, shortlist_size, embedding_calls
        count_keys = ("llm_calls", "shortlist_size", "embedding_calls")
        for ck in count_keys:
            cvals = [r["metrics"][ck] for r in successes if "metrics" in r and ck in r["metrics"]]
            c_st = compute_metric_stats([float(x) for x in cvals])
            row[f"{ck}_mean"] = c_st["mean"]
            row[f"{ck}_median"] = c_st["median"]
            row[f"{ck}_sum"] = sum(cvals)
            row[f"{ck}_min"] = c_st["min"]
            row[f"{ck}_max"] = c_st["max"]

        # Accuracy mode specific metrics
        if mode == "accuracy":
            # Reconstitute NodeScores from success records
            node_scores: list[NodeScore] = []
            for r in successes:
                s = r.get("score")
                if s:
                    node_scores.append(NodeScore(**s))

            if node_scores:
                agg = aggregate_scores(node_scores)
                row["precision_micro"] = agg.precision_micro
                row["recall_micro"] = agg.recall_micro
                row["f1_micro"] = agg.f1_micro
                row["precision_macro"] = agg.precision_macro
                row["recall_macro"] = agg.recall_macro
                row["f1_macro"] = agg.f1_macro
                row["n_precision_defined"] = agg.n_precision_defined
                row["n_recall_defined"] = agg.n_recall_defined
                row["n_f1_defined"] = agg.n_f1_defined
                row["shortlist_recall_micro"] = agg.shortlist_recall_micro
                row["shortlist_recall_macro"] = agg.shortlist_recall_macro
                row["n_shortlist_recall_defined"] = agg.n_shortlist_recall_defined
                row["precision_micro_sensitivity"] = agg.precision_micro_sensitivity
                row["recall_micro_sensitivity"] = agg.recall_micro_sensitivity
                row["f1_micro_sensitivity"] = agg.f1_micro_sensitivity
                row["precision_macro_sensitivity"] = agg.precision_macro_sensitivity
                row["recall_macro_sensitivity"] = agg.recall_macro_sensitivity
                row["f1_macro_sensitivity"] = agg.f1_macro_sensitivity
                row["n_precision_sensitivity_defined"] = agg.n_precision_sensitivity_defined
                row["n_recall_sensitivity_defined"] = agg.n_recall_sensitivity_defined
                row["n_f1_sensitivity_defined"] = agg.n_f1_sensitivity_defined
                row["unjudged_predictions_total"] = agg.excluded_total
            else:
                for metric in (
                    "precision_micro", "recall_micro", "f1_micro",
                    "precision_macro", "recall_macro", "f1_macro",
                    "n_precision_defined", "n_recall_defined", "n_f1_defined",
                    "shortlist_recall_micro", "shortlist_recall_macro",
                    "n_shortlist_recall_defined",
                    "precision_micro_sensitivity", "recall_micro_sensitivity", "f1_micro_sensitivity",
                    "precision_macro_sensitivity", "recall_macro_sensitivity", "f1_macro_sensitivity",
                    "n_precision_sensitivity_defined", "n_recall_sensitivity_defined", "n_f1_sensitivity_defined",
                    "unjudged_predictions_total",
                ):
                    row[metric] = 0.0

        rows.append(row)

    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ===========================================================================
# Dry Run Estimator
# ===========================================================================

def estimate_and_print_plan(
    config: HarnessConfig,
    strategy: NarrowingStrategy,
    *,
    corpora: Optional[dict[str, LoadedCorpus]] = None,
    name_source: Optional[SyntheticNameSource] = None,
) -> dict[str, Any]:
    """Compute and print dry-run execution plan and upper-bound LLM call estimates."""
    plan: dict[str, Any] = {
        "mode": config.mode,
        "strategy": strategy.name,
        "strategy_config": strategy.config(),
        "total_insertions": 0,
        "upper_bound_llm_calls": 0,
        "details": [],
    }

    print("=" * 70)
    print(f"DRY RUN EXECUTION PLAN: {config.mode.upper()} MODE")
    print(f"Strategy: {strategy.name}")
    print(f"Strategy Config: {strategy.config()}")
    print("=" * 70)

    # Estimate max candidate shortlist size per insertion
    # If strategy provides top_k in config, use it; otherwise worst-case is N-1
    top_k_bound = strategy.config().get("top_k", None)

    if config.mode == "accuracy":
        if corpora is None:
            corpora = {
                "DSA_gold_standard_MEKG": load_corpus("DSA"),
                "metacademy_gold_standard_MEKG": load_corpus("metacademy"),
            }

        total_trials = 0
        total_llm = 0

        for corpus_name, loaded_corpus in corpora.items():
            nodes_count = len(loaded_corpus.graph.nodes())
            if "metacademy" in corpus_name.lower():
                sample_k = min(config.metacademy_sample_size, nodes_count)
            else:
                sample_k = nodes_count
            trials = sample_k * config.repeats
            max_cands = min(nodes_count - 1, top_k_bound) if top_k_bound else (nodes_count - 1)
            max_llm = trials * max_cands

            plan["details"].append({
                "corpus": corpus_name,
                "nodes_in_graph": nodes_count,
                "sample_size": sample_k,
                "held_out_trials": trials,
                "max_candidates_per_trial": max_cands,
                "upper_bound_llm_calls": max_llm,
            })
            print(f"Corpus: {corpus_name} | Sample: {sample_k} (of {nodes_count}) | Trials: {trials} | Max LLM: {max_llm}")
            total_trials += trials
            total_llm += max_llm

        plan["total_insertions"] = total_trials
        plan["upper_bound_llm_calls"] = total_llm

    elif config.mode == "sweep":
        if name_source is None:
            raise ValueError("name_source must be provided for sweep dry run.")

        pool_size = len(name_source.names)
        total_trials = 0
        total_llm = 0

        for sz in config.sweep_sizes:
            trials = config.sweep_trials_per_size
            max_cands = min(sz, top_k_bound) if top_k_bound else sz
            max_llm = trials * max_cands
            total_trials += trials
            total_llm += max_llm
            plan["details"].append({
                "size": sz,
                "trials": trials,
                "max_candidates_per_trial": max_cands,
                "upper_bound_llm_calls": max_llm,
            })
            print(f"Size: {sz:4d} | Trials: {trials:2d} | Max Candidates: {max_cands:4d} | Max LLM Calls: {max_llm:6d}")

        plan["total_insertions"] = total_trials
        plan["upper_bound_llm_calls"] = total_llm

    print("-" * 70)
    print(f"TOTAL PLANNED INSERTIONS: {plan['total_insertions']}")
    print(f"ESTIMATED UPPER-BOUND LLM CALLS: {plan['upper_bound_llm_calls']}")
    print("=" * 70)
    return plan


# ===========================================================================
# Accuracy Runner
# ===========================================================================

def run_accuracy_experiment(
    config: HarnessConfig,
    strategy_factory: Callable[[], NarrowingStrategy],
    decision_step: DecisionStep,
    embedder_factory: Callable[[], Embedder],
    *,
    corpora: Optional[dict[str, LoadedCorpus]] = None,
    warmup_fn: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[int, int, int, Optional[int]], None]] = None,
) -> dict[str, Any]:
    """Execute leave-one-out insertion accuracy benchmark across DSA and Metacademy."""
    # Safety checks
    if not config.dry_run and not config.confirm:
        raise RuntimeError(
            "Live experiment runs require explicit confirmation via config.confirm=True "
            "(or CLI flag --confirm) to prevent accidental API consumption."
        )

    output_dir = Path(config.output_dir) if config.output_dir else Path("results") / config.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_jsonl_path = output_dir / "raw.jsonl"
    summary_csv_path = output_dir / "summary.csv"

    # Load corpora if not passed
    if corpora is None:
        corpora = {
            "DSA_gold_standard_MEKG": load_corpus("DSA"),
            "metacademy_gold_standard_MEKG": load_corpus("metacademy"),
        }

    # Inspect fresh strategy for metadata/manifest
    probe_strat = strategy_factory()
    strategy_name = probe_strat.name
    strategy_cfg = probe_strat.config()

    if config.dry_run:
        plan = estimate_and_print_plan(config, probe_strat, corpora=corpora)
        write_manifest(output_dir, config, strategy_cfg, decision_step)
        return plan

    # Write manifest immediately
    write_manifest(output_dir, config, strategy_cfg, decision_step)

    # Optional one-time warmup
    if warmup_fn is not None:
        warmup_fn()

    # Resume handling
    existing_results = load_existing_results(raw_jsonl_path) if config.resume else {}

    llm_meter = _extract_metered_llm(decision_step)
    cumulative_llm_calls = 0

    total_trials = sum(
        (min(config.metacademy_sample_size, len(loaded_corpus.graph.nodes())) if "metacademy" in cname.lower() else len(loaded_corpus.graph.nodes())) * config.repeats
        for cname, loaded_corpus in corpora.items()
    )
    trials_completed = 0

    # Open raw.jsonl in append mode for immediate streaming flush
    with open(raw_jsonl_path, "a", encoding="utf-8") as raw_f:
        for corpus_name, loaded_corpus in corpora.items():
            gold_graph = loaded_corpus.graph
            judgments = loaded_corpus.judgments
            all_nodes = sorted(gold_graph.nodes())

            # Node selection: all 29 nodes for DSA; seeded sample of 30 nodes for Metacademy
            if "metacademy" in corpus_name.lower():
                rng = random.Random(config.seed)
                sample_k = min(config.metacademy_sample_size, len(all_nodes))
                sampled_nodes = sorted(rng.sample(all_nodes, sample_k))
            else:
                sampled_nodes = all_nodes

            for rep in range(config.repeats):
                for h in sampled_nodes:
                    trial_key = f"accuracy:{strategy_name}:{corpus_name}:{h}:r{rep}"

                    # Resume check
                    if trial_key in existing_results:
                        prior = existing_results[trial_key]
                        if prior.get("status") == "success":
                            continue
                        if prior.get("status") == "failed" and not config.retry_failed:
                            continue

                    # LLM call limit safety check
                    # Note: counts successful insertions only, can overshoot by one trial, does not carry across --resume
                    if config.max_llm_calls is not None and cumulative_llm_calls >= config.max_llm_calls:
                        print(f"Safety limit reached: {cumulative_llm_calls} >= {config.max_llm_calls} LLM calls. Aborting cleanly.")
                        generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="accuracy")
                        return {"status": "max_llm_calls_reached", "cumulative_llm_calls": cumulative_llm_calls}

                    # Trial Isolation ([D-31]):
                    # 1. Independent copy of graph without held-out node h
                    # 2. Fresh strategy instance from factory
                    # 3. Fresh raw embedder wrapped in MeteredEmbedder, shared between setup and insert ([D-28])
                    # 4. Explicit gc.collect() prior to timed window
                    g_prime = gold_graph.without_node(h)
                    strategy = strategy_factory()
                    raw_embedder = embedder_factory()
                    metered_embedder = MeteredEmbedder(raw_embedder)

                    try:
                        strategy.setup(g_prime, metered_embedder)
                    except Exception as err:
                        rec = {
                            "key": trial_key,
                            "run_id": config.run_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "failed",
                            "strategy": strategy_name,
                            "mode": "accuracy",
                            "corpus": corpus_name,
                            "node": h,
                            "repeat": rep,
                            "harness_wall_s": 0.0,
                            "retries": 0,
                            "error_type": type(err).__name__,
                            "error_message": str(err),
                        }
                        raw_f.write(json.dumps(rec) + "\n")
                        raw_f.flush()
                        generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="accuracy")
                        raise

                    gc.collect()

                    snap_before = llm_meter.snapshot() if llm_meter is not None else None
                    t0 = time.perf_counter()

                    try:
                        res = insert_node(
                            strategy,
                            g_prime,
                            decision_step,
                            h,
                            metered_embedder=metered_embedder,
                        )
                        harness_wall_s = time.perf_counter() - t0
                        unaccounted_s = harness_wall_s - (res.metrics.total_s + res.metrics.validate_s)

                        snap_after = llm_meter.snapshot() if llm_meter is not None else None
                        snap_delta_dict = None
                        retries_count = 0
                        if snap_before is not None and snap_after is not None:
                            delta = snap_after - snap_before
                            snap_delta_dict = asdict(delta)
                            snap_delta_dict["failed_parses"] = list(delta.failed_parses)
                            retries_count = delta.retries

                        cumulative_llm_calls += res.metrics.llm_calls

                        # Scoring against ground truth ([D-30])
                        score = score_node_insertion(
                            node=h,
                            gold_graph=gold_graph,
                            judgments=judgments,
                            shortlist_candidates=res.shortlist.candidates,
                            decided_edges=res.edges,
                        )

                        rec = {
                            "key": trial_key,
                            "run_id": config.run_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "success",
                            "strategy": strategy_name,
                            "mode": "accuracy",
                            "corpus": corpus_name,
                            "node": h,
                            "repeat": rep,
                            "retries": retries_count,
                            "metrics": asdict(res.metrics),
                            "harness_wall_s": harness_wall_s,
                            "unaccounted_s": unaccounted_s,
                            "llm_snapshot_delta": snap_delta_dict,
                            "score": asdict(score),
                        }
                        raw_f.write(json.dumps(rec) + "\n")
                        raw_f.flush()

                        trials_completed += 1
                        if progress_callback is not None:
                            progress_callback(trials_completed, total_trials, retries_count, None)

                    except LLMTransportError as err:
                        harness_wall_s = time.perf_counter() - t0
                        rec = {
                            "key": trial_key,
                            "run_id": config.run_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "failed",
                            "strategy": strategy_name,
                            "mode": "accuracy",
                            "corpus": corpus_name,
                            "node": h,
                            "repeat": rep,
                            "harness_wall_s": harness_wall_s,
                            "retries": max(0, getattr(err, "attempts", 1) - 1),
                            "error_type": type(err).__name__,
                            "error_message": str(err),
                        }
                        raw_f.write(json.dumps(rec) + "\n")
                        raw_f.flush()

                        trials_completed += 1
                        if progress_callback is not None:
                            progress_callback(trials_completed, total_trials, rec["retries"], None)

                        if config.fail_fast:
                            generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="accuracy")
                            raise
                    except Exception as err:
                        # Non-transport driver contract or unexpected errors abort immediately
                        harness_wall_s = time.perf_counter() - t0
                        rec = {
                            "key": trial_key,
                            "run_id": config.run_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "failed",
                            "strategy": strategy_name,
                            "mode": "accuracy",
                            "corpus": corpus_name,
                            "node": h,
                            "repeat": rep,
                            "harness_wall_s": harness_wall_s,
                            "retries": 0,
                            "error_type": type(err).__name__,
                            "error_message": str(err),
                        }
                        raw_f.write(json.dumps(rec) + "\n")
                        raw_f.flush()

                        trials_completed += 1
                        if progress_callback is not None:
                            progress_callback(trials_completed, total_trials, 0, None)

                        generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="accuracy")
                        raise

    # Generate summary CSV
    generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="accuracy")
    return {"status": "completed", "run_id": config.run_id, "output_dir": str(output_dir)}


# ===========================================================================
# Sweep Runner
# ===========================================================================

def run_sweep_experiment(
    config: HarnessConfig,
    strategy_factory: Callable[[], NarrowingStrategy],
    decision_step: DecisionStep,
    embedder_factory: Callable[[], Embedder],
    name_source: SyntheticNameSource,
    *,
    warmup_fn: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[int, int, int, Optional[int]], None]] = None,
) -> dict[str, Any]:
    """Execute cost sweep scaling benchmark over synthetic concept name sets."""
    # Safety checks
    if not config.dry_run and not config.confirm:
        raise RuntimeError(
            "Live experiment runs require explicit confirmation via config.confirm=True "
            "(or CLI flag --confirm) to prevent accidental API consumption."
        )

    output_dir = Path(config.output_dir) if config.output_dir else Path("results") / config.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_jsonl_path = output_dir / "raw.jsonl"
    summary_csv_path = output_dir / "summary.csv"

    probe_strat = strategy_factory()
    strategy_name = probe_strat.name
    strategy_cfg = probe_strat.config()

    if config.dry_run:
        plan = estimate_and_print_plan(config, probe_strat, name_source=name_source)
        write_manifest(output_dir, config, strategy_cfg, decision_step)
        return plan

    write_manifest(output_dir, config, strategy_cfg, decision_step)

    if warmup_fn is not None:
        warmup_fn()

    existing_results = load_existing_results(raw_jsonl_path) if config.resume else {}

    llm_meter = _extract_metered_llm(decision_step)
    cumulative_llm_calls = 0

    total_trials = len(config.sweep_sizes) * config.sweep_trials_per_size
    trials_completed = 0

    pool_names = list(name_source.names)

    with open(raw_jsonl_path, "a", encoding="utf-8") as raw_f:
        for size_idx, n in enumerate(config.sweep_sizes):
            if len(pool_names) < n + 1:
                raise ValueError(
                    f"SyntheticNameSource has {len(pool_names)} names, but size {n} "
                    f"requires at least {n + 1} unique names."
                )

            for trial_idx in range(config.sweep_trials_per_size):
                trial_key = f"sweep:{strategy_name}:{n}:t{trial_idx}"

                if trial_key in existing_results:
                    prior = existing_results[trial_key]
                    if prior.get("status") == "success":
                        continue
                    if prior.get("status") == "failed" and not config.retry_failed:
                        continue

                # LLM call limit safety check
                # Note: counts successful insertions only, can overshoot by one trial, does not carry across --resume
                if config.max_llm_calls is not None and cumulative_llm_calls >= config.max_llm_calls:
                    print(f"Safety limit reached: {cumulative_llm_calls} >= {config.max_llm_calls} LLM calls. Aborting cleanly.")
                    generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="sweep")
                    return {"status": "max_llm_calls_reached", "cumulative_llm_calls": cumulative_llm_calls}

                # Seeded deterministic sampling for trial directly derived from n
                trial_seed = config.seed + (n * 1000) + trial_idx
                rng = random.Random(trial_seed)
                sampled = rng.sample(pool_names, n + 1)
                existing_concepts = sampled[:n]
                new_name = sampled[n]

                # Names-only graph with pool domain context
                graph = ConceptGraph(domain_context=name_source.domain_context)
                for c in existing_concepts:
                    graph.add_node(c)

                # Isolated strategy and meter
                strategy = strategy_factory()
                raw_embedder = embedder_factory()
                metered_embedder = MeteredEmbedder(raw_embedder)

                try:
                    strategy.setup(graph, metered_embedder)
                except Exception as err:
                    rec = {
                        "key": trial_key,
                        "run_id": config.run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "failed",
                        "strategy": strategy_name,
                        "mode": "sweep",
                        "size": n,
                        "trial": trial_idx,
                        "node": new_name,
                        "harness_wall_s": 0.0,
                        "retries": 0,
                        "error_type": type(err).__name__,
                        "error_message": str(err),
                    }
                    raw_f.write(json.dumps(rec) + "\n")
                    raw_f.flush()
                    generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="sweep")
                    raise

                gc.collect()

                snap_before = llm_meter.snapshot() if llm_meter is not None else None
                t0 = time.perf_counter()

                try:
                    res = insert_node(
                        strategy,
                        graph,
                        decision_step,
                        new_name,
                        metered_embedder=metered_embedder,
                    )
                    harness_wall_s = time.perf_counter() - t0
                    unaccounted_s = harness_wall_s - (res.metrics.total_s + res.metrics.validate_s)

                    snap_after = llm_meter.snapshot() if llm_meter is not None else None
                    snap_delta_dict = None
                    retries_count = 0
                    if snap_before is not None and snap_after is not None:
                        delta = snap_after - snap_before
                        snap_delta_dict = asdict(delta)
                        snap_delta_dict["failed_parses"] = list(delta.failed_parses)
                        retries_count = delta.retries

                    cumulative_llm_calls += res.metrics.llm_calls

                    rec = {
                        "key": trial_key,
                        "run_id": config.run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "success",
                        "strategy": strategy_name,
                        "mode": "sweep",
                        "size": n,
                        "trial": trial_idx,
                        "node": new_name,
                        "retries": retries_count,
                        "metrics": asdict(res.metrics),
                        "harness_wall_s": harness_wall_s,
                        "unaccounted_s": unaccounted_s,
                        "llm_snapshot_delta": snap_delta_dict,
                    }
                    raw_f.write(json.dumps(rec) + "\n")
                    raw_f.flush()

                    trials_completed += 1
                    if progress_callback is not None:
                        progress_callback(trials_completed, total_trials, retries_count, n)

                except LLMTransportError as err:
                    harness_wall_s = time.perf_counter() - t0
                    rec = {
                        "key": trial_key,
                        "run_id": config.run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "failed",
                        "strategy": strategy_name,
                        "mode": "sweep",
                        "size": n,
                        "trial": trial_idx,
                        "node": new_name,
                        "harness_wall_s": harness_wall_s,
                        "retries": max(0, getattr(err, "attempts", 1) - 1),
                        "error_type": type(err).__name__,
                        "error_message": str(err),
                    }
                    raw_f.write(json.dumps(rec) + "\n")
                    raw_f.flush()

                    trials_completed += 1
                    if progress_callback is not None:
                        progress_callback(trials_completed, total_trials, rec["retries"], n)

                    if config.fail_fast:
                        generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="sweep")
                        raise
                except Exception as err:
                    harness_wall_s = time.perf_counter() - t0
                    rec = {
                        "key": trial_key,
                        "run_id": config.run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "failed",
                        "strategy": strategy_name,
                        "mode": "sweep",
                        "size": n,
                        "trial": trial_idx,
                        "node": new_name,
                        "harness_wall_s": harness_wall_s,
                        "retries": 0,
                        "error_type": type(err).__name__,
                        "error_message": str(err),
                    }
                    raw_f.write(json.dumps(rec) + "\n")
                    raw_f.flush()

                    trials_completed += 1
                    if progress_callback is not None:
                        progress_callback(trials_completed, total_trials, 0, n)

                    generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="sweep")
                    raise

    generate_summary_csv(raw_jsonl_path, summary_csv_path, mode="sweep")
    return {"status": "completed", "run_id": config.run_id, "output_dir": str(output_dir)}


# ===========================================================================
# Unified Experiment Runner
# ===========================================================================

def run_experiment(
    config: HarnessConfig,
    strategy_factory: Callable[[], NarrowingStrategy],
    decision_step: DecisionStep,
    embedder_factory: Callable[[], Embedder],
    *,
    corpora: Optional[dict[str, LoadedCorpus]] = None,
    name_source: Optional[SyntheticNameSource] = None,
    warmup_fn: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[int, int, int, Optional[int]], None]] = None,
) -> dict[str, Any]:
    """Unified entry point dispatching to accuracy or sweep runner."""
    if config.mode == "accuracy":
        return run_accuracy_experiment(
            config,
            strategy_factory,
            decision_step,
            embedder_factory,
            corpora=corpora,
            warmup_fn=warmup_fn,
            progress_callback=progress_callback,
        )
    elif config.mode == "sweep":
        if name_source is None:
            raise ValueError("name_source must be provided when running in sweep mode.")
        return run_sweep_experiment(
            config,
            strategy_factory,
            decision_step,
            embedder_factory,
            name_source=name_source,
            warmup_fn=warmup_fn,
            progress_callback=progress_callback,
        )
    else:
        raise ValueError(f"Unknown experiment mode: {config.mode}")
