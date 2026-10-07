#!/usr/bin/env python3
"""
scripts/run_experiment.py — INFRA-004
=====================================
CLI driver for graph insertion experimental measurement harness:
  - Mode "accuracy": Leave-one-out benchmark across DSA and Metacademy corpora.
  - Mode "sweep": Cost-only scaling sweep over synthetic concept names.

Safety & Guardrails:
  - --dry-run prints insertion plans and estimated upper-bound LLM calls without mutating state.
  - Live execution requires explicit --confirm.
  - Halts cleanly if --max-llm-calls is reached.
  - Supports incremental checkpointing and resuming (--resume, --retry-failed, --fail-fast).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure src is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_insertion.decision import PROMPT_VERSION
from graph_insertion.embedding import Embedder, FakeEmbedder
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    run_experiment,
)
from graph_insertion.loader import load_corpus
from graph_insertion.strategy import (
    DecisionOutcome,
    DecisionStep,
    NarrowingStrategy,
    Shortlist,
)


# ===========================================================================
# Local Test Stubs
# ===========================================================================

class StubNarrowingStrategy:
    """Minimal deterministic narrowing strategy for harness testing and dry runs."""

    def __init__(self, top_k: int = 5) -> None:
        self.name = "stub_narrowing"
        self.top_k = top_k
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Optional[Embedder] = None

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        self._graph = graph
        self._embedder = embedder

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
        "--max-llm-calls",
        type=int,
        default=None,
        help="Safety cap on total LLM API calls before halting cleanly.",
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

    # Strategy and decision step factories
    strategy_factory = lambda: StubNarrowingStrategy(top_k=5)
    embedder_factory = lambda: FakeEmbedder(dim=32, seed=config.seed)

    # Decision step wiring
    decision_step: DecisionStep
    try:
        from graph_insertion.decision import PairwiseDecisionStep
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

    # Synthetic name source for sweep
    name_source = None
    if config.mode == "sweep":
        max_size = max(config.sweep_sizes) if config.sweep_sizes else 2000
        total_names_needed = max_size + 100
        placeholder_names = [f"synthetic_concept_{i:05d}" for i in range(total_names_needed)]
        name_source = SyntheticNameSource(
            names=placeholder_names,
            domain_context="computer science",
        )

    try:
        result = run_experiment(
            config=config,
            strategy_factory=strategy_factory,
            decision_step=decision_step,
            embedder_factory=embedder_factory,
            corpora=corpora,
            name_source=name_source,
        )
        if config.dry_run:
            print(f"Dry run complete. Plan recorded in manifest.json.")
        else:
            print(f"Experiment finished: status={result.get('status')} output={result.get('output_dir')}")
        return 0
    except Exception as e:
        print(f"Experiment execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
