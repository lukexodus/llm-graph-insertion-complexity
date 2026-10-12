#!/usr/bin/env python3
"""
scripts/run_experiment.py — INFRA-004 / INFRA-005 / FIX-008
===========================================================
CLI driver for graph insertion experimental measurement harness:
  - Mode "accuracy": Leave-one-out benchmark across DSA and Metacademy corpora.
  - Mode "sweep": Cost-only scaling sweep over synthetic concept names.

Safety & Guardrails:
  - --dry-run prints insertion plans and estimated upper-bound LLM calls without mutating state.
  - Live execution requires explicit --confirm.
  - Halts cleanly if --max-llm-calls is reached (process-local cap).
  - Supports incremental checkpointing and resuming (--resume, --retry-failed, --fail-fast).
  - DeepSeek peak pricing guard: computed worst-case window estimation; refuses live runs
    during peak windows unless --allow-peak given ([D-37], [D-38], [D-40]).
  - Call-driven progress reporting with 30s heartbeat.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Optional, Sequence

# Ensure src is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_insertion.decision import (
    CALLS_PER_CANDIDATE,
    PROMPT_VERSION,
    PairwiseDecisionStep,
)
from graph_insertion.embedding import Embedder, FakeEmbedder
from graph_insertion.graph_representation import ConceptGraph, embed_text
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    _load_existing_keys,
    accuracy_trial_key,
    run_experiment,
    sample_heldout_nodes,
    sweep_trial_key,
)
from graph_insertion.llm import resolve_model_alias
from graph_insertion.loader import LoadedCorpus, discover_corpora, load_corpus
from graph_insertion.schedule import format_peak_status, window_intersects_peak
from graph_insertion.strategies.null import NullStrategy
from graph_insertion.strategies.registry import (
    PARAM_APPLICABILITY,
    PARAM_CLI_FLAGS,
    STRATEGY_FACTORIES,
    build_strategy_slug,
    check_applicability,
    derive_default_run_id,
    register_stub,
)
from graph_insertion.strategy import (
    DecisionOutcome,
    DecisionStep,
    NarrowingStrategy,
    Shortlist,
    candidate_upper_bound,
)

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


# ===========================================================================
# Local Test Stubs
# ===========================================================================

class StubNarrowingStrategy:
    """Minimal deterministic narrowing strategy for harness testing and dry runs."""

    name: str = "stub_narrowing"
    uses_embeddings: bool = False

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = top_k
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Optional[Embedder] = None

    def setup(self, graph: ConceptGraph, embedder: Any) -> None:
        self._graph = graph
        self._embedder = None

    def shortlist(self, new_name: str) -> Shortlist:
        if not self._graph:
            return Shortlist(candidates=())
        nodes = sorted(self._graph.nodes())
        candidates = tuple(nodes[: self.top_k])
        return Shortlist(candidates=candidates)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        pass

    def config(self) -> dict[str, Any]:
        return {"name": self.name, "top_k": self.top_k}

    def diagnostics(self) -> dict[str, Any]:
        return {}

    def max_candidates(self, n_existing: int) -> int:
        return min(self.top_k, n_existing)


class StubDecisionStep:
    """Minimal decision step stub for testing and dry runs."""

    def __init__(self) -> None:
        self.PROMPT_VERSION = PROMPT_VERSION

    def decide(
        self,
        new_name: str,
        candidates: tuple[str, ...],
        domain_context: Optional[str] = None,
    ) -> DecisionOutcome:
        return DecisionOutcome(
            edges=(),
            llm_calls=len(candidates),
            llm_seconds=0.001 * len(candidates),
        )


# ===========================================================================
# Strategy Registry (INFRA-007)
# ===========================================================================

register_stub(StubNarrowingStrategy)
STRATEGY_REGISTRY: dict[str, Callable[..., NarrowingStrategy]] = STRATEGY_FACTORIES


# ===========================================================================
# Call-Driven Progress Reporter (D1, FIX-008)
# ===========================================================================

class ProgressReporter:
    """Call-driven progress tracker emitting to stderr periodically.

    Parameters
    ----------
    total_calls:
        Total planned upper-bound LLM calls.
    total_trials:
        Total planned trial count.
    strategy_name:
        Name of the narrowing strategy.
    size:
        Current graph size (int) if in sweep mode, or None for accuracy mode.
    interval_s:
        Minimum seconds between progress heartbeat prints (default 30.0).
    stream:
        Output stream (default sys.stderr).
    clock:
        Injectable monotonic clock function (default time.monotonic).
    """

    def __init__(
        self,
        total_calls: int,
        total_trials: int,
        strategy_name: str,
        size: Optional[int] = None,
        *,
        interval_s: float = 30.0,
        stream: Any = sys.stderr,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.total_calls = total_calls
        self.total_trials = total_trials
        self.strategy_name = strategy_name
        self.size = size
        self.interval_s = interval_s
        self.stream = stream
        self.clock = clock

        self.start_time = self.clock()
        self.last_print_time = self.start_time
        self.calls_done = 0
        self.trials_done = 0
        self.retries = 0
        self._hook_active = False

    def on_llm_call(self, calls_done: int, cumulative_retries: int) -> bool:
        """Heartbeat hook invoked on every LLM call completion.

        Emits heartbeat if interval_s has elapsed.
        """
        self._hook_active = True
        self.calls_done = calls_done
        self.retries = cumulative_retries

        now = self.clock()
        if now - self.last_print_time >= self.interval_s:
            self._print_line(now - self.start_time)
            self.last_print_time = now
            return True
        return False

    def update(
        self,
        trials_done: int,
        total_trials: int,
        delta_retries: int = 0,
        size: Optional[int] = None,
        force: bool = False,
    ) -> bool:
        """Trial completion callback from harness.

        Emits progress line on trial completion, interval expiration, or force=True.
        Avoids double-counting retries when on_llm_call hook is active.
        """
        self.trials_done = trials_done
        self.total_trials = total_trials
        if size is not None:
            self.size = size

        if not self._hook_active:
            # When hook is inactive, accumulate per-trial retry deltas from harness
            self.retries += delta_retries

        now = self.clock()
        elapsed = now - self.start_time
        should_print = force or (trials_done == total_trials) or (now - self.last_print_time >= self.interval_s)

        if should_print:
            self._print_line(elapsed)
            self.last_print_time = now
            return True
        return False

    def _print_line(self, elapsed: float) -> None:
        if self.calls_done > 0 and self.calls_done < self.total_calls:
            rate = elapsed / self.calls_done
            eta_s = rate * (self.total_calls - self.calls_done)
            eta_str = f"{eta_s:.1f}s"
        elif self.calls_done >= self.total_calls and self.total_calls > 0:
            eta_str = "0.0s"
        elif self.trials_done > 0 and self.trials_done < self.total_trials:
            # Fallback ETA by trials if no calls reported
            rate = elapsed / self.trials_done
            eta_s = rate * (self.total_trials - self.trials_done)
            eta_str = f"{eta_s:.1f}s"
        else:
            eta_str = "unknown"

        tag = f"{self.strategy_name}" + (f"/n={self.size}" if self.size is not None else "")
        msg = (
            f"[{tag}] {self.calls_done}/{self.total_calls} calls "
            f"(trial {self.trials_done}/{self.total_trials}) "
            f"elapsed={elapsed:.1f}s ETA={eta_str} retries={self.retries}\n"
        )
        self.stream.write(msg)
        self.stream.flush()


# ===========================================================================
# Planned Calls & Pre-Flight Calculation (FIX-008)
# ===========================================================================

class PlannedCallsBound(int):
    """Integer representing the remaining LLM calls upper bound, with metadata on full plan."""

    full_plan_bound: int
    remaining_bound: int
    full_plan_trials: int
    remaining_trials: int

    def __new__(
        cls,
        remaining_bound: int,
        full_plan_bound: int,
        remaining_trials: int = 0,
        full_plan_trials: int = 0,
    ) -> PlannedCallsBound:
        obj = super().__new__(cls, remaining_bound)
        obj.remaining_bound = remaining_bound
        obj.full_plan_bound = full_plan_bound
        obj.remaining_trials = remaining_trials
        obj.full_plan_trials = full_plan_trials
        return obj


def compute_planned_calls_upper_bound(
    config: HarnessConfig,
    corpora: Optional[dict[str, LoadedCorpus]] = None,
    strategy: Optional[Any] = None,
    raw_jsonl_path: Optional[Path] = None,
) -> PlannedCallsBound:
    """Compute worst-case upper bound on total LLM API calls, strategy-aware and resume-aware.

    Instantiates/evaluates bounds per planned trial:
      trial_bound = CALLS_PER_CANDIDATE * candidate_upper_bound(strategy, n_existing_at_trial)
    On --resume, subtracts trials already completed (or skipped if failed and not retry_failed).
    If config.max_llm_calls is set, caps the remaining bound to max_llm_calls.
    """
    skipped_keys: set[str] = set()
    if config.resume and raw_jsonl_path is not None and raw_jsonl_path.exists():
        skipped_keys = _load_existing_keys(raw_jsonl_path, retry_failed=config.retry_failed)

    strategy_name = getattr(strategy, "name", "unknown") if strategy is not None else "unknown"

    full_plan_bound = 0
    remaining_bound = 0
    full_plan_trials = 0
    remaining_trials = 0

    if config.mode == "sweep":
        for n in config.sweep_sizes:
            trial_bound = CALLS_PER_CANDIDATE * candidate_upper_bound(strategy, n)
            for trial_idx in range(config.sweep_trials_per_size):
                trial_key = sweep_trial_key(strategy_name, n, trial_idx)
                full_plan_bound += trial_bound
                full_plan_trials += 1
                if trial_key in skipped_keys:
                    continue
                remaining_bound += trial_bound
                remaining_trials += 1

    elif config.mode == "accuracy":
        if corpora:
            for corpus_name, lc in corpora.items():
                sampled_nodes = sample_heldout_nodes(
                    lc.graph,
                    corpus_name,
                    config.seed,
                    config.metacademy_sample_size,
                )
                n_existing = max(0, len(lc.graph.nodes()) - 1)
                trial_bound = CALLS_PER_CANDIDATE * candidate_upper_bound(strategy, n_existing)

                for rep in range(config.repeats):
                    for h in sampled_nodes:
                        trial_key = accuracy_trial_key(strategy_name, corpus_name, h, rep)
                        full_plan_bound += trial_bound
                        full_plan_trials += 1
                        if trial_key in skipped_keys:
                            continue
                        remaining_bound += trial_bound
                        remaining_trials += 1

    if config.max_llm_calls is not None:
        remaining_bound = min(remaining_bound, config.max_llm_calls)

    return PlannedCallsBound(remaining_bound, full_plan_bound, remaining_trials, full_plan_trials)


def compute_preflight_estimate(
    planned_calls: int,
    est_seconds_per_call: float,
    price_in: float,
    price_out: float,
) -> dict[str, float]:
    """Compute duration and cost estimate based on prompt v2 pilot telemetry."""
    estimated_seconds = planned_calls * est_seconds_per_call
    input_tokens_est = planned_calls * 152.0
    output_tokens_est = planned_calls * 2.5
    estimated_cost_usd = (input_tokens_est * price_in + output_tokens_est * price_out) / 1_000_000.0
    return {
        "planned_calls": planned_calls,
        "estimated_seconds": estimated_seconds,
        "estimated_cost_usd": estimated_cost_usd,
        "input_tokens_est": input_tokens_est,
        "output_tokens_est": output_tokens_est,
    }


def build_live_client(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Any:
    """Construct a live DeepSeekClient instance configured for experimental evaluation.

    Does not perform network I/O upon construction.
    """
    from graph_insertion.llm import DeepSeekClient
    key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError(
            "DEEPSEEK_API_KEY is required for live execution. Set the environment variable or pass api_key."
        )
    return DeepSeekClient(api_key=key, model=model)


# ===========================================================================
# Names File Loading and Validation (C4, FIX-008)
# ===========================================================================

def load_and_validate_names_file(
    path: Path,
    min_required_names: int,
) -> list[str]:
    """Load and validate concept names from a JSON file.

    Accepts:
      - Plain list: ["name1", "name2", ...]
      - Object: {"meta": {...}, "names": ["name1", ...]}

    Validates:
      1. At least min_required_names present.
      2. No duplicates.
      3. Valid snake_case matching ^[a-z][a-z0-9]*(_[a-z0-9]+)*$.
      4. Zero overlap with concepts in the 12 loaded corpora (exact name and embed_text form).
    """
    if not path.exists():
        raise FileNotFoundError(f"Names file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse names file JSON: {e}") from e

    if isinstance(data, list):
        names = data
    elif isinstance(data, dict) and "names" in data:
        names = data["names"]
    else:
        raise ValueError(
            f"Names file must be a JSON array or an object containing a 'names' list. Got: {type(data).__name__}"
        )

    if not isinstance(names, list) or not all(isinstance(x, str) for x in names):
        raise ValueError("Names file must contain a list of strings.")

    if len(names) < min_required_names:
        raise ValueError(
            f"Names file has {len(names)} names, but at least {min_required_names} are required."
        )

    if len(set(names)) != len(names):
        raise ValueError(
            f"Names file contains duplicate names ({len(names) - len(set(names))} duplicates found)."
        )

    for name in names:
        if not _SNAKE_CASE_RE.match(name):
            raise ValueError(
                f"Invalid concept name {name!r}: must match snake_case pattern ^[a-z][a-z0-9]*(_[a-z0-9]+)*$"
            )

    # Validate zero overlap with all corpus nodes (exact name and embed_text form)
    all_corpora = discover_corpora()
    corpus_nodes: set[str] = set()
    corpus_embed_texts: set[str] = set()
    for spec in all_corpora:
        try:
            lc = load_corpus(spec)
            nodes = set(lc.graph.nodes())
            corpus_nodes.update(nodes)
            corpus_embed_texts.update(embed_text(n) for n in nodes)
        except Exception as exc:
            corpus_name = getattr(spec, "name", str(spec))
            raise RuntimeError(
                f"Failed to load benchmark corpus {corpus_name!r} during names validation: {exc}"
            ) from exc

    overlap = set(names) & corpus_nodes
    if overlap:
        sample = sorted(overlap)[:5]
        raise ValueError(
            f"Names file overlaps with corpus concept names ({len(overlap)} overlaps, e.g. {sample}). "
            "Names file concepts must be completely disjoint from all benchmark corpora."
        )

    names_embed_texts = {embed_text(n): n for n in names}
    embed_overlap = set(names_embed_texts.keys()) & corpus_embed_texts
    if embed_overlap:
        sample_names = sorted(names_embed_texts[t] for t in embed_overlap)[:5]
        raise ValueError(
            f"Names file overlaps with corpus concepts in embed_text form ({len(embed_overlap)} overlaps, e.g. {sample_names}). "
            "Concept names when formatted as text payloads must be completely disjoint from benchmark corpora."
        )

    return names


# ===========================================================================
# CLI Parser
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run LLM graph insertion complexity experiments (accuracy or sweep)."
    )
    parser.add_argument(
        "--mode",
        choices=["accuracy", "sweep"],
        default="accuracy",
        help="Experiment mode: 'accuracy' (ground-truth evaluation) or 'sweep' (cost scaling).",
    )
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGY_REGISTRY.keys()),
        default="null",
        help="Narrowing strategy to evaluate (default: 'null').",
    )
    parser.add_argument(
        "-k",
        "--k",
        type=int,
        default=None,
        help="candidate shortlist size k: null, stub and ann_retrieval.",
    )
    parser.add_argument(
        "--theta",
        type=float,
        default=None,
        help="Cosine similarity threshold theta for embedding_threshold (default: 0.6).",
    )
    parser.add_argument(
        "--ef-search",
        type=int,
        default=None,
        help="HNSW efSearch query depth for ann_retrieval (default: 128).",
    )
    parser.add_argument(
        "--s-min",
        type=int,
        default=None,
        help="Minimum segment size s_min for bounded_bucket (default: 5).",
    )
    parser.add_argument(
        "--s-max",
        type=int,
        default=None,
        help="Maximum segment size s_max for bounded_bucket (default: 10).",
    )
    parser.add_argument(
        "--n-bits",
        type=int,
        default=None,
        help="Number of LSH hyperplanes n_bits for bounded_bucket (default: 12).",
    )
    parser.add_argument(
        "--embedder",
        choices=["fake", "minilm"],
        default="fake",
        help="Embedding backend: 'fake' (offline FakeEmbedder) or 'minilm' (pinned sentence-transformers all-MiniLM-L6-v2 on CPU).",
    )
    parser.add_argument(
        "--corpus",
        choices=["DSA", "metacademy", "all"],
        default="all",
        help="Corpus for accuracy mode: 'DSA', 'metacademy', or 'all' (default: all).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save experiment results (defaults to results/<mode>_<strategy>_<slug> or results/<run_id>).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="",
        help="Optional custom run ID string.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling reproducibility (default: 42).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Repeats per held-out node in accuracy mode (default: 1).",
    )
    parser.add_argument(
        "--metacademy-sample-size",
        type=int,
        default=30,
        help="Sample size of held-out nodes for Metacademy (default: 30).",
    )
    parser.add_argument(
        "--sweep-sizes",
        type=int,
        nargs="+",
        default=[50, 100, 200, 500, 1000, 2000],
        help="Concept graph sizes (n) for cost sweep scaling (default: 50 100 200 500 1000 2000).",
    )
    parser.add_argument(
        "--sweep-trials",
        type=int,
        default=10,
        help="Number of trials per size in sweep mode (default: 10).",
    )
    parser.add_argument(
        "--names-file",
        type=str,
        default=None,
        help="Path to JSON file containing synthetic concept names for sweep mode.",
    )
    parser.add_argument(
        "--est-seconds-per-call",
        type=float,
        default=1.0,
        help="Estimated seconds per API call for pre-flight duration calculation (default: 1.0).",
    )
    parser.add_argument(
        "--price-in",
        type=float,
        default=0.15,
        help="Price per 1M input tokens in USD (default: 0.15 off-peak per D-37).",
    )
    parser.add_argument(
        "--price-out",
        type=float,
        default=0.60,
        help="Price per 1M output tokens in USD (default: 0.60 off-peak per D-37).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="DeepSeek model identifier (default 'deepseek-flash', or DEEPSEEK_MODEL env var if set).",
    )
    parser.add_argument(
        "--max-llm-calls",
        type=int,
        default=None,
        help="Safety cap on total LLM API calls executed in the current process only before halting cleanly "
             "(does not carry over or count resumed records from prior runs; counts successful insertions only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned insertions and call estimates without executing.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation required to execute live trials.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip trial keys already successfully completed in raw.jsonl.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-run previously failed trial keys when resuming.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort execution immediately on first trial exception.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute with live DeepSeek API (requires DEEPSEEK_API_KEY environment variable).",
    )
    parser.add_argument(
        "--allow-peak",
        action="store_true",
        help="Allow live run to execute during DeepSeek peak pricing hours (01:00-04:00 or 06:00-10:00 UTC Mon-Fri).",
    )
    return parser


def build_sidecar_payload(
    strategy: NarrowingStrategy,
    embedder_info: dict[str, Any],
    mode: str,
    command_line_params: dict[str, Any],
) -> dict[str, Any]:
    """Construct JSON-serialisable strategy_config.json sidecar dictionary."""
    payload = {
        "strategy": strategy.name,
        "config": strategy.config(),
        "embedder": embedder_info,
        "mode": mode,
        "command_line_params": command_line_params,
    }
    # Verify JSON-safety eagerly
    json.dumps(payload)
    return payload


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Check strategy existence
    strat_factory_fn = STRATEGY_REGISTRY.get(args.strategy)
    if strat_factory_fn is None:
        print(f"Unknown strategy {args.strategy!r}. Choices: {list(STRATEGY_REGISTRY.keys())}", file=sys.stderr)
        return 1

    # Applicability check: reject flags that do not apply to the chosen strategy (exit 2)
    for param_name in ("k", "theta", "ef_search", "s_min", "s_max", "n_bits"):
        val = getattr(args, param_name, None)
        if val is not None and not check_applicability(args.strategy, param_name):
            flag_str = PARAM_CLI_FLAGS.get(param_name, f"--{param_name}")
            parser.error(
                f"argument {flag_str} is not applicable to strategy {args.strategy!r}"
            )

    strategy_params = {
        "theta": args.theta,
        "ef_search": args.ef_search,
        "s_min": args.s_min,
        "s_max": args.s_max,
        "n_bits": args.n_bits,
    }
    strategy_factory = lambda: strat_factory_fn(args.seed, args.k, **strategy_params)

    # Instantiate strategy once via factory without calling setup()
    # Catches out-of-range ValueError and missing-faiss ImportError cleanly (exit 1, no traceback)
    try:
        uninitialized_strategy = strategy_factory()
    except (ValueError, ImportError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    # Gate: --live with an embedding strategy refuses --embedder fake (D-35(4), D-64)
    # Checked BEFORE any client construction, key check, or live dry-run estimate.
    uses_embeddings = bool(getattr(uninitialized_strategy, "uses_embeddings", False))
    if args.live and uses_embeddings and args.embedder == "fake":
        print(
            f"ERROR: Live execution for embedding strategy {uninitialized_strategy.name!r} "
            "requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); "
            "'--embedder fake' is refused for live runs.",
            file=sys.stderr,
        )
        return 1

    # Derive deterministic default run_id and output_dir when neither --output-dir nor --run-id is given
    default_run_id = derive_default_run_id(args.mode, args.strategy, uninitialized_strategy.config())
    if args.output_dir:
        resolved_run_id = args.run_id if args.run_id else default_run_id
        resolved_output_dir = Path(args.output_dir)
    elif args.run_id:
        resolved_run_id = args.run_id
        resolved_output_dir = Path("results") / args.run_id
    else:
        resolved_run_id = default_run_id
        resolved_output_dir = Path("results") / default_run_id

    config = HarnessConfig(
        mode=args.mode,
        run_id=resolved_run_id,
        output_dir=resolved_output_dir,
        seed=args.seed,
        repeats=args.repeats,
        metacademy_sample_size=args.metacademy_sample_size,
        sweep_sizes=tuple(args.sweep_sizes),
        sweep_trials_per_size=args.sweep_trials,
        max_llm_calls=args.max_llm_calls,
        dry_run=args.dry_run,
        confirm=args.confirm,
        resume=args.resume,
        retry_failed=args.retry_failed,
        fail_fast=args.fail_fast,
    )

    output_dir = Path(config.output_dir) if config.output_dir else Path("results") / config.run_id
    raw_jsonl_path = output_dir / "raw.jsonl"
    sidecar_path = output_dir / "strategy_config.json"
    has_existing_raw = raw_jsonl_path.exists()

    # Configuration guard on --resume or any run into an existing directory with raw.jsonl
    if has_existing_raw or (config.resume and sidecar_path.exists()):
        if sidecar_path.exists():
            try:
                stored_sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except Exception as err:
                print(
                    f"ERROR: Failed to parse existing {sidecar_path}: {err}",
                    file=sys.stderr,
                )
                return 1
            stored_strategy = stored_sidecar.get("strategy")
            stored_config = stored_sidecar.get("config")
            current_strategy = uninitialized_strategy.name
            current_config = uninitialized_strategy.config()
            if stored_strategy != current_strategy or stored_config != current_config:
                print(
                    f"ERROR: Strategy configuration mismatch in {output_dir}: "
                    f"stored strategy={stored_strategy!r} config={stored_config} vs "
                    f"current strategy={current_strategy!r} config={current_config}",
                    file=sys.stderr,
                )
                return 1
        elif has_existing_raw:
            print(
                f"WARNING: Existing {raw_jsonl_path} found without {sidecar_path}; "
                "proceeding without sidecar mismatch check and not writing sidecar to non-fresh directory.",
                file=sys.stderr,
            )

    # Corpora selection
    corpora = None
    if config.mode == "accuracy":
        if args.corpus == "DSA":
            corpora = {"DSA_gold_standard_MEKG": load_corpus("DSA")}
        elif args.corpus == "metacademy":
            corpora = {"metacademy_gold_standard_MEKG": load_corpus("metacademy")}
        else:
            corpora = {
                "DSA_gold_standard_MEKG": load_corpus("DSA"),
                "metacademy_gold_standard_MEKG": load_corpus("metacademy"),
            }

    # Gate: live sweep mode requires --names-file (Part B1)
    if args.live and config.mode == "sweep" and not args.names_file:
        print(
            "ERROR: Live execution in sweep mode requires an external names file (--names-file) "
            "generated from the verified DATA-004 concept name pool. Placeholder names are only permitted "
            "for offline/non-live runs.",
            file=sys.stderr,
        )
        return 1

    # Compute planned calls upper bound (strategy-aware, resume-aware)
    planned_calls_bound = compute_planned_calls_upper_bound(
        config=config,
        corpora=corpora,
        strategy=uninitialized_strategy,
        raw_jsonl_path=raw_jsonl_path,
    )
    planned_calls_upper_bound = planned_calls_bound.remaining_bound
    full_plan_bound = planned_calls_bound.full_plan_bound

    # Estimate total trials (remaining trials to execute on --resume)
    total_planned_trials = planned_calls_bound.remaining_trials

    # Decision step wiring & live peak check (FIX-008, FIX-009)
    decision_step: DecisionStep
    metered_client = None

    if args.live:
        from graph_insertion.llm import MeteredLLMClient

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        resolved_model = resolve_model_alias(args.model)
        est = compute_preflight_estimate(
            planned_calls_upper_bound,
            args.est_seconds_per_call,
            args.price_in,
            args.price_out,
        )

        print("=" * 65)
        print("LIVE EXPERIMENT PRE-FLIGHT ESTIMATE")
        print(f"Strategy:                      {uninitialized_strategy.name}")
        print(f"Strategy config:               {uninitialized_strategy.config()}")
        print(f"Embedder:                      {args.embedder}")
        print(f"Output directory:              {output_dir}")
        print(f"Model alias:                   {resolved_model}")
        print(f"Full-plan calls (upper bound): {full_plan_bound}")
        print(f"Remaining calls (upper bound): {est['planned_calls']}")
        print(f"Estimated duration:            {est['estimated_seconds']:.1f}s ({est['estimated_seconds']/60:.1f} min) (assuming {args.est_seconds_per_call:.1f}s/call)")
        print(f"Estimated cost:                ${est['estimated_cost_usd']:.4f} USD")
        print(f"Cost assumptions:              ~152 in, ~2.5 out tokens/call at ${args.price_in:.2f}/M in, ${args.price_out:.2f}/M out")
        print("-" * 65)
        print(format_peak_status(now_utc))
        print("=" * 65)

        would_be_refused = window_intersects_peak(now_utc, est["estimated_seconds"]) and not args.allow_peak
        if would_be_refused:
            end_utc = now_utc + datetime.timedelta(seconds=est["estimated_seconds"])
            refusal_msg = (
                f"Peak check note: Planned execution window [{now_utc.strftime('%H:%M:%S')}, "
                f"{end_utc.strftime('%H:%M:%S')} UTC] intersects DeepSeek peak pricing hours "
                "(01:00-04:00 or 06:00-10:00 UTC Mon-Fri). A real live run would be REFUSED unless '--allow-peak' is passed."
            )
        else:
            refusal_msg = "Peak check note: Planned execution window falls within off-peak pricing hours. A real live run would be PERMITTED."

        print(refusal_msg)

        # --live --dry-run prints estimate and refusal note, exits 0 without key check or client construction
        if args.dry_run:
            print("Dry run complete (live pre-flight estimation only; no API calls or client construction).")
            return 0

        if would_be_refused:
            print(f"ERROR: {refusal_msg}", file=sys.stderr)
            return 1

        if not args.confirm:
            print(
                "ERROR: Live execution requires explicit '--confirm' flag to proceed.",
                file=sys.stderr,
            )
            return 1

        try:
            raw_client = build_live_client(model=args.model)
        except ValueError as err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 1
        metered_client = MeteredLLMClient(raw_client)
        decision_step = PairwiseDecisionStep(metered_client)
    else:
        try:
            from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
            metered_client = MeteredLLMClient(FakeLLMClient())
            decision_step = PairwiseDecisionStep(metered_client)
        except ImportError:
            decision_step = StubDecisionStep()

    # Embedder factory wiring
    embedder_factory: Callable[[], Embedder]
    embedder_info: dict[str, Any]
    if not uses_embeddings or args.embedder == "fake":
        embedder_factory = lambda: FakeEmbedder(dim=32, seed=config.seed)
        embedder_info = {
            "type": "fake",
            "uses_embeddings": uses_embeddings,
            "dim": 32,
            "seed": int(config.seed),
        }
    else:
        from graph_insertion.embedding_minilm import (
            MODEL_DIM,
            MODEL_NAME,
            MODEL_REVISION_PIN,
            SENTENCE_TRANSFORMERS_VERSION_PIN,
            MiniLMEmbedder,
        )

        if config.dry_run:
            embedder_factory = lambda: FakeEmbedder(dim=MODEL_DIM, seed=config.seed)
            embedder_info = {
                "type": "minilm",
                "uses_embeddings": True,
                "model_name": MODEL_NAME,
                "dim": int(MODEL_DIM),
                "revision": MODEL_REVISION_PIN,
                "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
                "device": "cpu",
                "dtype": "float32",
            }
        else:
            try:
                minilm_instance = MiniLMEmbedder()
            except (ImportError, ValueError) as err:
                print(f"ERROR: {err}", file=sys.stderr)
                return 1
            embedder_factory = lambda: minilm_instance
            embedder_info = {
                "type": "minilm",
                "uses_embeddings": True,
                **minilm_instance.identity(),
            }

    # Synthetic name source for sweep (C4, FIX-008)
    name_source = None
    if config.mode == "sweep":
        max_size = max(config.sweep_sizes) if config.sweep_sizes else 2000
        min_names_needed = max_size + 1

        if args.names_file:
            names = load_and_validate_names_file(Path(args.names_file), min_names_needed)
            name_source = SyntheticNameSource(names=names, domain_context="computer science")
        else:
            total_names_needed = max_size + 100
            placeholder_names = [f"synthetic_concept_{i:05d}" for i in range(total_names_needed)]
            name_source = SyntheticNameSource(
                names=placeholder_names,
                domain_context="computer science",
            )

    # Progress reporter setup (call-driven heartbeat)
    progress_reporter = ProgressReporter(
        total_calls=planned_calls_upper_bound,
        total_trials=total_planned_trials,
        strategy_name=getattr(uninitialized_strategy, "name", args.strategy),
        size=config.sweep_sizes[0] if config.sweep_sizes else None,
        interval_s=30.0,
    )

    if metered_client is not None and hasattr(metered_client, "set_on_call"):
        metered_client.set_on_call(progress_reporter.on_llm_call)

    command_line_params = {
        "strategy": args.strategy,
        "k": args.k,
        "theta": args.theta,
        "ef_search": args.ef_search,
        "s_min": args.s_min,
        "s_max": args.s_max,
        "n_bits": args.n_bits,
        "seed": args.seed,
        "embedder": args.embedder,
    }

    try:
        # Write sidecar strategy_config.json BEFORE the first trial on a fresh directory
        if not has_existing_raw and (config.dry_run or config.confirm):
            output_dir.mkdir(parents=True, exist_ok=True)
            sidecar_payload = build_sidecar_payload(
                strategy=uninitialized_strategy,
                embedder_info=embedder_info,
                mode=config.mode,
                command_line_params=command_line_params,
            )
            with open(sidecar_path, "w", encoding="utf-8") as sf:
                json.dump(sidecar_payload, sf, indent=2)

        result = run_experiment(
            config=config,
            strategy_factory=strategy_factory,
            decision_step=decision_step,
            embedder_factory=embedder_factory,
            corpora=corpora,
            name_source=name_source,
            progress_callback=progress_reporter.update,
        )
        if config.dry_run:
            print(f"Default/resolved output directory: {output_dir}")
            print("Dry run complete. Plan recorded in manifest.json.")
        else:
            print(f"Experiment finished: status={result.get('status')} output={result.get('output_dir')}")
        return 0
    except Exception as e:
        print(f"Experiment execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
