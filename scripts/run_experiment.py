#!/usr/bin/env python3
"""
scripts/run_experiment.py — INFRA-004 / INFRA-005
=================================================
CLI driver for graph insertion experimental measurement harness:
  - Mode "accuracy": Leave-one-out benchmark across DSA and Metacademy corpora.
  - Mode "sweep": Cost-only scaling sweep over synthetic concept names.

Safety & Guardrails:
  - --dry-run prints insertion plans and estimated upper-bound LLM calls without mutating state.
  - Live execution requires explicit --confirm.
  - Halts cleanly if --max-llm-calls is reached.
  - Supports incremental checkpointing and resuming (--resume, --retry-failed, --fail-fast).
  - DeepSeek peak pricing guard: refuses to start live runs during peak windows unless --allow-peak given ([D-37], [D-38]).
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

from graph_insertion.decision import PROMPT_VERSION, PairwiseDecisionStep
from graph_insertion.embedding import Embedder, FakeEmbedder
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    run_experiment,
)
from graph_insertion.loader import discover_corpora, load_corpus
from graph_insertion.strategies.null import NullStrategy
from graph_insertion.strategy import (
    DecisionOutcome,
    DecisionStep,
    NarrowingStrategy,
    Shortlist,
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
# Strategy Registry
# ===========================================================================

STRATEGY_REGISTRY: dict[str, Callable[[int, int], NarrowingStrategy]] = {
    "null": lambda seed, k: NullStrategy(seed=seed, k=k),
    "stub": lambda seed, k: StubNarrowingStrategy(top_k=k),
}


# ===========================================================================
# Progress Reporter (D1)
# ===========================================================================

class ProgressReporter:
    """Plain-text progress tracker emitting to stderr periodically.

    Parameters
    ----------
    total:
        Total planned insertions.
    strategy_name:
        Name of the narrowing strategy.
    size:
        Current graph size (int) if in sweep mode, or None for accuracy mode.
    interval_s:
        Minimum seconds between progress line prints (default 30.0).
    interval_n:
        Minimum number of insertions between progress line prints (default 10).
    stream:
        Output stream (default sys.stderr).
    clock:
        Injectable monotonic clock function (default time.monotonic).
    """

    def __init__(
        self,
        total: int,
        strategy_name: str,
        size: Optional[int] = None,
        *,
        interval_s: float = 30.0,
        interval_n: int = 10,
        stream: Any = sys.stderr,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.total = total
        self.strategy_name = strategy_name
        self.size = size
        self.interval_s = interval_s
        self.interval_n = interval_n
        self.stream = stream
        self.clock = clock

        self.start_time = self.clock()
        self.last_print_time = self.start_time
        self.last_print_n = 0
        self.done = 0
        self.retries = 0

    def update(
        self,
        done: int,
        total: int,
        retries: int = 0,
        size: Optional[int] = None,
        force: bool = False,
    ) -> bool:
        """Record progress. Emits progress line if intervals elapsed or force=True.

        Returns True if a line was emitted, False otherwise.
        """
        self.done = done
        self.total = total
        self.retries += retries
        if size is not None:
            self.size = size

        now = self.clock()
        elapsed = now - self.start_time
        time_since_last = now - self.last_print_time
        n_since_last = self.done - self.last_print_n

        should_print = (
            force
            or self.done == self.total
            or (time_since_last >= self.interval_s and n_since_last > 0)
            or (self.interval_n > 0 and n_since_last >= self.interval_n)
        )

        if should_print:
            self._print_line(elapsed)
            self.last_print_time = now
            self.last_print_n = self.done
            return True
        return False

    def _print_line(self, elapsed: float) -> None:
        if self.done > 0 and self.done < self.total:
            rate = elapsed / self.done
            eta_s = rate * (self.total - self.done)
            eta_str = f"{eta_s:.1f}s"
        elif self.done >= self.total:
            eta_str = "0.0s"
        else:
            eta_str = "unknown"

        tag = f"{self.strategy_name}" + (f"/n={self.size}" if self.size is not None else "")
        msg = (
            f"[{tag}] {self.done}/{self.total} insertions "
            f"elapsed={elapsed:.1f}s ETA={eta_str} retries={self.retries}\n"
        )
        self.stream.write(msg)
        self.stream.flush()


# ===========================================================================
# Names File Loading and Validation (C4)
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
      4. Zero overlap with concepts in the 12 loaded corpora.
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

    # Validate zero overlap with all corpus nodes
    all_corpora = discover_corpora()
    corpus_nodes: set[str] = set()
    for spec in all_corpora:
        try:
            lc = load_corpus(spec)
            corpus_nodes.update(lc.graph.nodes())
        except Exception:
            pass

    overlap = set(names) & corpus_nodes
    if overlap:
        sample = sorted(overlap)[:5]
        raise ValueError(
            f"Names file overlaps with corpus concept names ({len(overlap)} overlaps, e.g. {sample}). "
            "Names file concepts must be completely disjoint from all benchmark corpora."
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
        default=1,
        help="Candidate shortlist size k for null strategy (default: 1).",
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
        help="Directory to save experiment results (defaults to results/<run_id>).",
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = HarnessConfig(
        mode=args.mode,
        run_id=args.run_id,
        output_dir=Path(args.output_dir) if args.output_dir else None,
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

    # Strategy factory from registry
    strat_factory_fn = STRATEGY_REGISTRY.get(args.strategy)
    if strat_factory_fn is None:
        print(f"Unknown strategy {args.strategy!r}. Choices: {list(STRATEGY_REGISTRY.keys())}", file=sys.stderr)
        return 1

    strategy_factory = lambda: strat_factory_fn(config.seed, args.k)
    embedder_factory = lambda: FakeEmbedder(dim=32, seed=config.seed)

    # Decision step wiring & live peak check (D2)
    decision_step: DecisionStep
    if args.live:
        from graph_insertion.llm import DeepSeekClient, MeteredLLMClient
        from graph_insertion.schedule import format_peak_status, window_intersects_peak

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        print("--- DeepSeek Schedule Status ---")
        print(format_peak_status(now_utc))
        print("--------------------------------")

        # Estimate duration
        estimated_duration_s = 600.0  # default estimate
        if window_intersects_peak(now_utc, estimated_duration_s) and not args.allow_peak:
            print(
                "ERROR: Execution window intersects DeepSeek peak pricing hours (01:00-04:00 or 06:00-10:00 UTC Mon-Fri).\n"
                "To run anyway at peak rates, pass '--allow-peak'.",
                file=sys.stderr,
            )
            return 1

        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("ERROR: DEEPSEEK_API_KEY environment variable is required for --live runs.", file=sys.stderr)
            return 1
        raw_client = DeepSeekClient(api_key=api_key)
        decision_step = PairwiseDecisionStep(MeteredLLMClient(raw_client))
    else:
        try:
            from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
            decision_step = PairwiseDecisionStep(MeteredLLMClient(FakeLLMClient()))
        except ImportError:
            decision_step = StubDecisionStep()

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

    # Synthetic name source for sweep (C4)
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

    # Progress reporter setup (D1)
    # Estimate total trials
    if config.mode == "accuracy":
        total_planned = 0
        if corpora:
            for cname, lc in corpora.items():
                k_sample = min(config.metacademy_sample_size, len(lc.graph.nodes())) if "metacademy" in cname.lower() else len(lc.graph.nodes())
                total_planned += k_sample * config.repeats
    else:
        total_planned = len(config.sweep_sizes) * config.sweep_trials_per_size

    progress_reporter = ProgressReporter(
        total=total_planned,
        strategy_name=args.strategy,
        size=config.sweep_sizes[0] if config.sweep_sizes else None,
        interval_s=30.0,
        interval_n=10,
    )

    try:
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
            print("Dry run complete. Plan recorded in manifest.json.")
        else:
            print(f"Experiment finished: status={result.get('status')} output={result.get('output_dir')}")
        return 0
    except Exception as e:
        print(f"Experiment execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
