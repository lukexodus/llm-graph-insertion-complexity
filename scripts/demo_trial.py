"""Defense demo: one concept insertion, four narrowing strategies (PILOT-001 replay).

Offline, deterministic terminal demonstration for thesis panelists.  The
narrowing, graph mutation and scoring paths are the production code.  The only
replaced component is the LLM transport: every answer is looked up by exact
prompt text in the recorded PILOT-001 call cache.

Run:  python scripts/demo_trial.py
Exit codes: 0 ok, 2 usage, 3 pilot cache/provenance, 4 corpus/node,
            5 missing dependency/embedder, 6 internal consistency, 7 output path.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import gc
import hashlib
import json
import os
import re
import sys
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

# Offline HF settings must precede any sentence-transformers import.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from graph_insertion import decision as decision_module  # noqa: E402
from graph_insertion.decision import PairwiseDecisionStep, parse_token  # noqa: E402
from graph_insertion.embedding import FakeEmbedder, MeteredEmbedder  # noqa: E402
from graph_insertion.graph_representation import (  # noqa: E402
    ConceptGraph,
    embed_text,
)
from graph_insertion.llm import LLMResponse, MeteredLLMClient  # noqa: E402
from graph_insertion.loader import load_corpus  # noqa: E402
from graph_insertion.scoring import (  # noqa: E402
    NodeScore,
    compute_gold_incident_edges,
    score_node_insertion,
)
from graph_insertion.strategies.registry import STRATEGY_FACTORIES  # noqa: E402
from graph_insertion.strategy import insert_node  # noqa: E402

import networkx as nx  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PILOT_DIR_DEFAULT = "results/pilot/20261007_053743Z"
PILOT_RAW_CALLS_SHA256 = (
    "879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008"
)
EXPECTED_PROMPT_VERSION = "v2"
EXPECTED_CALLS = 812
EXPECTED_MODEL = "deepseek-flash"
SYSTEM_PROMPT_SHA256 = (
    "32932d476b8cdac7026520cd9e1906a8cca9333d2945ad569fa8a7feb2b3d571"
)
CORPUS_NAME = "DSA"
DEFAULT_NODE = "binary_search_tree"
SEED = 42
WIDTH = 88

PRICE_IN_CACHE_MISS = 0.15
PRICE_IN_CACHE_HIT = 0.003
PRICE_OUT = 0.60

CANONICAL_STRATEGIES = [
    "brute_force",
    "embedding_threshold",
    "ann_retrieval",
    "bounded_bucket",
]
STRATEGY_ALIASES = {
    "s1": "brute_force",
    "s2": "embedding_threshold",
    "s3": "ann_retrieval",
    "s4": "bounded_bucket",
}
STRATEGY_LABELS = {
    "brute_force": "S1 brute_force",
    "embedding_threshold": "S2 embedding_threshold",
    "ann_retrieval": "S3 ann_retrieval",
    "bounded_bucket": "S4 bounded_bucket",
}
DISPLAY_NAMES = {
    "brute_force": "S1",
    "embedding_threshold": "S2",
    "ann_retrieval": "S3",
    "bounded_bucket": "S4",
}

DEMO_PARAMS: dict[str, dict[str, Any]] = {
    "brute_force": {"seed": 42},
    "embedding_threshold": {"theta": 0.6, "seed": 42},
    "ann_retrieval": {
        "k": 10,
        "M": 16,
        "ef_construction": 200,
        "ef_search": 128,
        "seed": 42,
    },
    "bounded_bucket": {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42},
}

DIAGNOSTIC_KEYS = {
    "brute_force": ["candidate_count"],
    "embedding_threshold": ["cosine_comparisons", "max_cosine", "shortlist_size"],
    "ann_retrieval": ["exact_topk_overlap", "shortlist_size", "max_cosine"],
    "bounded_bucket": ["num_segments", "min_segment_size", "max_segment_size"],
}

LIVE_NOTICE = (
    "LIVE NOTICE. This run calls the DeepSeek API now. Every answer below is a "
    "fresh model response produced for exactly the prompt shown, at temperature 0 "
    "with thinking disabled. Narrowing, graph updates, scoring, latency and token "
    "counts are measured live. The run is one held-out node and one trial, not a "
    "new thesis result."
)

REPLAY_NOTICE = (
    "REPLAY NOTICE. The model answers on screen are real. Each one was returned "
    "by deepseek-flash on 2026-10-07 during PILOT-001 for exactly the prompt "
    "shown; this program looks up that stored answer instead of calling the API "
    "again. Nothing is simulated or invented, and a missing record stops the "
    "program. Narrowing, graph updates and scoring run live. Model latency, "
    "token counts and cost are the recorded values, not measurements from this run."
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DemoError(Exception):
    """A demo failure with a stable exit code and actionable hint."""

    def __init__(self, exit_code: int, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.exit_code = int(exit_code)
        self.message = message
        self.hint = hint


# ---------------------------------------------------------------------------
# Replay cache
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayRecord:
    call_index: int
    new_name: str
    candidate: str
    domain_context: str
    user_prompt: str
    response_text: str
    raw_token: str
    latency_s: float
    model: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cache_hit_tokens: int
    cache_miss_tokens: int
    attempts: int
    retry_wait_s: float

    @property
    def token(self) -> str:
        parsed = parse_token(self.response_text)
        if parsed is None:  # validated on load; defensive
            raise DemoError(3, f"invalid recorded response {self.response_text!r}")
        return parsed


@dataclass(frozen=True)
class PilotProvenance:
    path: str
    sha256: str
    recorded_utc: str
    prompt_version: str
    model: str
    n_calls: int
    temperature: float
    thinking_mode: str
    retries: int
    parse_failures: int
    transport_failures: int
    input_tokens: int
    output_tokens: int
    cache_hit_tokens: int
    cache_miss_tokens: int
    estimated_cost_usd: float
    cumulative_latency_s: float
    system_prompt_recorded: bool


_RECORD_FIELDS = {
    "call_index": int,
    "new_name": str,
    "candidate": str,
    "domain_context": str,
    "user_prompt": str,
    "response_text": str,
    "raw_token": str,
    "latency_s": (int, float),
    "model": str,
    "input_tokens": int,
    "output_tokens": int,
    "reasoning_tokens": int,
    "cache_hit_tokens": int,
    "cache_miss_tokens": int,
    "attempts": int,
    "retry_wait_s": (int, float),
}


def _require(condition: bool, message: str, hint: str = "") -> None:
    if not condition:
        raise DemoError(3, message, hint)


def _summary_get(summary: dict[str, Any], path: Sequence[str], default: Any = None) -> Any:
    node: Any = summary
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def load_pilot(
    pilot_dir: Path | str,
    *,
    corpus: Any,
    expected_sha256: Optional[str] = PILOT_RAW_CALLS_SHA256,
) -> tuple[PilotProvenance, dict[str, ReplayRecord]]:
    """Load and fully validate the recorded PILOT-001 call cache.

    Raises DemoError(3) on any defect.  A missing prompt is never fabricated.
    """
    directory = Path(pilot_dir)
    raw_path = directory / "raw_calls.jsonl"
    summary_path = directory / "summary.json"
    _require(raw_path.is_file(), f"pilot cache not found: {raw_path}", "Check --pilot-dir.")
    _require(summary_path.is_file(), f"pilot summary not found: {summary_path}", "Check --pilot-dir.")

    payload = raw_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None:
        _require(
            digest == expected_sha256,
            f"pilot cache SHA-256 mismatch: expected {expected_sha256}, got {digest}",
            "The cache is not the accepted PILOT-001 artifact; restore it before running.",
        )

    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise DemoError(3, f"cannot read pilot summary: {exc}") from exc
    _require(isinstance(summary, dict), "pilot summary is not a JSON object")

    records: list[ReplayRecord] = []
    for line_no, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DemoError(3, f"malformed pilot JSON at line {line_no}: {exc}") from exc
        _require(isinstance(raw, dict), f"pilot line {line_no} is not an object")
        for field_name, expected_type in _RECORD_FIELDS.items():
            _require(
                field_name in raw,
                f"pilot line {line_no} missing field {field_name!r}",
            )
            value = raw[field_name]
            if expected_type is int:
                _require(
                    isinstance(value, int) and not isinstance(value, bool),
                    f"pilot line {line_no} field {field_name!r} must be int, got {type(value).__name__}",
                )
            elif expected_type is float:
                _require(
                    isinstance(value, (int, float)) and not isinstance(value, bool),
                    f"pilot line {line_no} field {field_name!r} must be numeric",
                )
            elif expected_type is str:
                _require(
                    isinstance(value, str),
                    f"pilot line {line_no} field {field_name!r} must be str",
                )
            else:  # tuple of numeric types
                _require(
                    isinstance(value, expected_type) and not isinstance(value, bool),
                    f"pilot line {line_no} field {field_name!r} must be numeric",
                )
        record = ReplayRecord(
            call_index=int(raw["call_index"]),
            new_name=str(raw["new_name"]),
            candidate=str(raw["candidate"]),
            domain_context=str(raw["domain_context"]),
            user_prompt=str(raw["user_prompt"]),
            response_text=str(raw["response_text"]),
            raw_token=str(raw["raw_token"]),
            latency_s=float(raw["latency_s"]),
            model=str(raw["model"]),
            input_tokens=int(raw["input_tokens"]),
            output_tokens=int(raw["output_tokens"]),
            reasoning_tokens=int(raw["reasoning_tokens"]),
            cache_hit_tokens=int(raw["cache_hit_tokens"]),
            cache_miss_tokens=int(raw["cache_miss_tokens"]),
            attempts=int(raw["attempts"]),
            retry_wait_s=float(raw["retry_wait_s"]),
        )
        _require(record.latency_s >= 0, f"pilot line {line_no}: negative latency")
        _require(record.input_tokens >= 0 and record.output_tokens >= 0,
                 f"pilot line {line_no}: negative token count")
        _require(record.reasoning_tokens == 0,
                 f"pilot line {line_no}: nonzero reasoning tokens",
                 "Thinking was disabled in PILOT-001; do not guess how these were billed.")
        _require(record.cache_hit_tokens + record.cache_miss_tokens == record.input_tokens,
                 f"pilot line {line_no}: cache_hit + cache_miss != input_tokens")
        _require(parse_token(record.response_text) is not None,
                 f"pilot line {line_no}: unparseable response {record.response_text!r}")
        records.append(record)

    _require(len(records) == EXPECTED_CALLS,
             f"pilot cache has {len(records)} calls, expected {EXPECTED_CALLS}")
    _require(len(records) == int(_summary_get(summary, ["total_calls"], -1)),
             "pilot cache line count differs from summary total_calls")

    prompts = [r.user_prompt for r in records]
    _require(len(set(prompts)) == len(prompts), "duplicate user_prompt in pilot cache")
    by_pair: dict[tuple[str, str], ReplayRecord] = {}
    for rec in records:
        pair = (rec.new_name, rec.candidate)
        _require(pair not in by_pair, f"duplicate ordered pair in pilot cache: {pair!r}")
        by_pair[pair] = rec

    nodes = set(corpus.graph.nodes())
    expected_pairs = {(a, b) for a in nodes for b in nodes if a != b}
    _require(set(by_pair) == expected_pairs,
             "pilot cache pairs are not exactly all ordered pairs of the corpus",
             "The cache and the loaded corpus disagree; rebuild or restore the accepted artifacts.")

    prompt_version = str(_summary_get(summary, ["prompt_version"], ""))
    _require(prompt_version == EXPECTED_PROMPT_VERSION,
             f"pilot prompt version {prompt_version!r} != {EXPECTED_PROMPT_VERSION!r}")
    model_id = str(_summary_get(summary, ["model_id"], ""))
    _require(model_id == EXPECTED_MODEL,
             f"pilot summary model {model_id!r} != {EXPECTED_MODEL!r}")
    for rec in records:
        _require(rec.model == model_id,
                 f"pilot record model {rec.model!r} differs from summary {model_id!r}")

    input_tokens = sum(r.input_tokens for r in records)
    output_tokens = sum(r.output_tokens for r in records)
    cache_hits = sum(r.cache_hit_tokens for r in records)
    cache_misses = sum(r.cache_miss_tokens for r in records)
    latency = sum(r.latency_s for r in records)
    _require(input_tokens == int(_summary_get(summary, ["token_usage", "input_tokens"], -1)),
             "pilot input-token sum differs from summary")
    _require(output_tokens == int(_summary_get(summary, ["token_usage", "output_tokens"], -1)),
             "pilot output-token sum differs from summary")
    _require(cache_hits == int(_summary_get(summary, ["token_usage", "cache_hit_tokens"], -1)),
             "pilot cache-hit sum differs from summary")
    _require(cache_misses == int(_summary_get(summary, ["token_usage", "cache_miss_tokens"], -1)),
             "pilot cache-miss sum differs from summary")
    summary_latency = float(_summary_get(summary, ["timing_s", "cumulative_latency"], -1.0))
    _require(abs(latency - summary_latency) <= 0.01,
             f"pilot latency sum {latency:.4f}s differs from summary {summary_latency:.4f}s")

    prov = PilotProvenance(
        path=str(raw_path),
        sha256=digest,
        recorded_utc=str(_summary_get(summary, ["timestamp_utc"], "")),
        prompt_version=prompt_version,
        model=model_id,
        n_calls=len(records),
        temperature=float(_summary_get(summary, ["temperature"], -1.0)),
        thinking_mode=str(_summary_get(summary, ["thinking_mode"], "")),
        retries=int(_summary_get(summary, ["retries_and_errors", "retries"], -1)),
        parse_failures=int(_summary_get(summary, ["parse_failure_count"], -1)),
        transport_failures=int(_summary_get(summary, ["transport_failure_count"], -1)),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hit_tokens=cache_hits,
        cache_miss_tokens=cache_misses,
        estimated_cost_usd=float(_summary_get(summary, ["token_usage", "estimated_cost_usd"], -1.0)),
        cumulative_latency_s=latency,
        system_prompt_recorded=any(
            key in summary for key in ("system_prompt", "system_prompt_sha256")
        ),
    )
    return prov, {r.user_prompt: r for r in records}


class ReplayLLMClient:
    """LLMClient that serves recorded PILOT-001 answers by exact prompt text."""

    def __init__(
        self,
        by_prompt: dict[str, ReplayRecord],
        *,
        system_prompt: str = decision_module.SYSTEM_PROMPT,
    ) -> None:
        self._by_prompt = by_prompt
        self._system_prompt = system_prompt
        self.served: list[ReplayRecord] = []

    def complete(self, system: str, user: str) -> LLMResponse:
        if system != self._system_prompt:
            raise DemoError(3, "system prompt differs from the recorded PILOT-001 prompt")
        record = self._by_prompt.get(user)
        if record is None:
            raise DemoError(
                3,
                "no recorded PILOT-001 answer for this prompt; the demo never fabricates a decision",
                "The shortlist reached a pair that PILOT-001 did not query. Restore the accepted cache.",
            )
        self.served.append(record)
        return LLMResponse(
            text=record.response_text,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            reasoning_tokens=record.reasoning_tokens,
            cache_hit_tokens=record.cache_hit_tokens,
            cache_miss_tokens=record.cache_miss_tokens,
            latency_s=record.latency_s,
            model_id=record.model,
            attempts=record.attempts,
            retry_wait_s=record.retry_wait_s,
        )

    def record_parse_failure(self, raw_text: str) -> None:  # parity with metered client
        raise DemoError(3, f"recorded answer failed to parse: {raw_text!r}")


@dataclass(frozen=True)
class IssuedCall:
    """One completion issued during a trial, captured for the transcript."""

    system_prompt: str
    user_prompt: str
    response: LLMResponse


class RecordingLLMClient:
    """Wrap any LLMClient and keep every prompt/response pair in order."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls: list[IssuedCall] = []

    def complete(self, system: str, user: str) -> LLMResponse:
        response = self.inner.complete(system, user)
        self.calls.append(IssuedCall(system, user, response))
        return response

    def record_parse_failure(self, raw_text: str) -> None:
        recorder = getattr(self.inner, "record_parse_failure", None)
        if callable(recorder):
            recorder(raw_text)


def estimated_cost_usd(
    cache_miss_tokens: int,
    cache_hit_tokens: int,
    output_tokens: int,
) -> float:
    """Off-peak PILOT-001 price formula ([D-36]), USD per 1M tokens."""
    return (
        cache_miss_tokens * PRICE_IN_CACHE_MISS
        + cache_hit_tokens * PRICE_IN_CACHE_HIT
        + output_tokens * PRICE_OUT
    ) / 1_000_000.0


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


@dataclass
class DemoCall:
    x: str
    y: str
    token: str
    edge: Optional[tuple[str, str]]
    latency_s: float
    input_tokens: int
    output_tokens: int
    user_prompt: str


@dataclass
class EdgeLabel:
    edge: tuple[str, str]
    label: str
    gold_path: Optional[list[str]] = None


@dataclass
class MissedEdge:
    edge: tuple[str, str]
    cause: str


@dataclass
class StrategyReport:
    name: str
    display: str
    config: dict[str, Any]
    setup_s_live: float
    setup_embedding_calls: int
    shortlist_candidates: tuple[str, ...]
    shortlist_scores: Optional[tuple[float, ...]]
    shortlist_s_live: float
    embed_s_live: float
    update_s_live: float
    replay_wall_s_live: float
    calls: list[DemoCall]
    recorded_latency_s: float
    recorded_input_tokens: int
    recorded_output_tokens: int
    recorded_cache_hit_tokens: int
    recorded_cache_miss_tokens: int
    cost_usd: float
    calls_vs_s1_pct: float
    kept_pct: float
    applied_nodes_added: int
    applied_edges_added: int
    score: NodeScore
    labelled_edges: list[EdgeLabel]
    missed: list[MissedEdge]
    lost_narrowing: int
    lost_decision: int
    recall_given_shortlist: Optional[float]
    diagnostics: dict[str, Any]
    retries: int = 0
    parse_failures: int = 0
    transport_failures: int = 0


@dataclass
class DemoReport:
    started_utc: str
    wall_s_live: float
    argv: list[str]
    provenance: PilotProvenance
    pilot_dir: str
    corpus_name: str
    domain_context: Optional[str]
    node: str
    full_nodes: int
    full_edges: int
    n_before: int
    e_before: int
    gold_prerequisites: list[str]
    gold_dependents: list[str]
    gold_incident: int
    prompt_version: str
    system_prompt_sha256: str
    prices: dict[str, float]
    strategies: list[StrategyReport]
    selected: list[str]
    subset_of_s1: Optional[bool]
    embedder_identity: Optional[dict[str, Any]]
    cpu_threads: Optional[dict[str, Any]]
    mode: str = "replay"
    live_base_url: Optional[str] = None
    output_dir: Optional[str] = None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def resolve_pilot_dir(pilot_dir: str | Path) -> Path:
    path = Path(pilot_dir)
    return path if path.is_absolute() else REPO_ROOT / path


def _check_strategy_config(name: str, config: dict[str, Any]) -> None:
    expected = DEMO_PARAMS[name]
    for key, value in expected.items():
        if key not in config:
            raise DemoError(6, f"{name} config missing {key!r}: {config!r}")
        actual = config[key]
        if isinstance(value, float):
            if abs(float(actual) - value) > 1e-12:
                raise DemoError(6, f"{name} config {key}={actual!r}, expected {value!r}")
        elif actual != value:
            raise DemoError(6, f"{name} config {key}={actual!r}, expected {value!r}")


def parse_strategies(text: Optional[str]) -> list[str]:
    if text is None:
        return list(CANONICAL_STRATEGIES)
    raw = [part.strip() for part in text.split(",") if part.strip()]
    if not raw:
        raise DemoError(2, "--strategies requires at least one name")
    selected: set[str] = set()
    for part in raw:
        key = part.lower()
        name = STRATEGY_ALIASES.get(key, key)
        if name not in CANONICAL_STRATEGIES:
            raise DemoError(
                2,
                f"unknown strategy {part!r}",
                "Use s1/s2/s3/s4 or the canonical names.",
            )
        if name in selected:
            raise DemoError(2, f"duplicate strategy {part!r}")
        selected.add(name)
    return [name for name in CANONICAL_STRATEGIES if name in selected]


def _build_embedder(selected: Sequence[str]) -> tuple[Any, Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Return (raw_embedder, identity, cpu_pin) or FakeEmbedder for S1-only."""
    needs_embeddings = any(name != "brute_force" for name in selected)
    if not needs_embeddings:
        return FakeEmbedder(dim=32, seed=SEED), None, None

    if "ann_retrieval" in selected:
        # D-73: import faiss (via the strategy module) before torch/MiniLM.
        import graph_insertion.strategies.ann_retrieval  # noqa: F401

    try:
        from graph_insertion.cpu_threads import CPU_THREAD_PIN, pin_cpu_threads
        from graph_insertion.embedding_minilm import MiniLMEmbedder

        embedder = MiniLMEmbedder()
        pin = pin_cpu_threads(CPU_THREAD_PIN)
        # Warm-up outside every timed window, so the first shortlist is not
        # inflated by lazy model initialisation (the official harness relies on
        # setup() for first-touch; this demo keeps that effect out of its timers).
        embedder.embed("demo warm up")
        identity = embedder.identity()
        cpu = {"requested": int(pin["requested"]), "torch_threads": int(pin["torch_threads"])}
        return embedder, identity, cpu
    except DemoError:
        raise
    except Exception as exc:
        raise DemoError(
            5,
            f"embedding backend unavailable: {type(exc).__name__}: {exc}",
            "Use the pinned .venv-ann environment with the cached MiniLM model; no download is attempted.",
        ) from exc


def _gold_path(gold_graph: ConceptGraph, prereq: str, dependent: str) -> Optional[list[str]]:
    nxg = gold_graph.nx_graph
    if not nxg.has_node(prereq) or not nxg.has_node(dependent):
        return None
    if not nx.has_path(nxg, prereq, dependent):
        return None
    return list(nx.shortest_path(nxg, prereq, dependent))


def run_demo(
    *,
    node: str = DEFAULT_NODE,
    selected: Optional[Sequence[str]] = None,
    pilot_dir: str | Path = PILOT_DIR_DEFAULT,
    corpus: Any = None,
    replay: Optional[ReplayLLMClient] = None,
    provenance: Optional[PilotProvenance] = None,
    raw_embedder: Any = None,
    live_client: Any = None,
    argv: Optional[Sequence[str]] = None,
) -> DemoReport:
    """Execute one insertion trial for each selected strategy and return the report.

    Pass *replay* for the offline PILOT-001 demo, or *live_client* (an
    ``LLMClient``) for one real API-backed trial. Never both.
    """
    started = datetime.now(timezone.utc)
    t_start = time.perf_counter()
    selected_names = list(selected) if selected is not None else list(CANONICAL_STRATEGIES)
    is_live = live_client is not None
    if is_live and replay is not None:
        raise DemoError(2, "choose either replay or live mode, not both")

    if corpus is None:
        try:
            corpus = load_corpus(CORPUS_NAME)
        except Exception as exc:
            raise DemoError(4, f"cannot load DSA corpus: {type(exc).__name__}: {exc}") from exc

    prompt_sha = hashlib.sha256(decision_module.SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    if prompt_sha != SYSTEM_PROMPT_SHA256:
        raise DemoError(
            3,
            "decision.SYSTEM_PROMPT changed since PILOT-001; replay would not match the recorded answers",
            "Restore the v2 prompt or re-record the pilot before running this demo.",
        )

    nodes = sorted(corpus.graph.nodes())
    if node not in nodes:
        suggestions = difflib.get_close_matches(node, nodes, n=5, cutoff=0.3)
        hint = f"Close matches: {', '.join(suggestions)}" if suggestions else "No close matches."
        raise DemoError(4, f"node {node!r} is not in the DSA corpus", hint)

    if is_live:
        resolved_pilot = Path("(live DeepSeek API)")
        client: Any = live_client
    else:
        resolved_pilot = resolve_pilot_dir(pilot_dir)
        if replay is None:
            provenance, by_prompt = load_pilot(resolved_pilot, corpus=corpus)
            replay = ReplayLLMClient(by_prompt)
        elif provenance is None:
            raise DemoError(6, "synthetic replay requires explicit provenance")
        client = replay

    for name in selected_names:
        if name not in CANONICAL_STRATEGIES:
            raise DemoError(2, f"unknown strategy {name!r}")

    configs: dict[str, dict[str, Any]] = {}
    for name in selected_names:
        try:
            probe = STRATEGY_FACTORIES[name](**DEMO_PARAMS[name])
        except DemoError:
            raise
        except Exception as exc:
            raise DemoError(5, f"cannot construct {name}: {type(exc).__name__}: {exc}") from exc
        configs[name] = dict(probe.config())
        _check_strategy_config(name, configs[name])

    if raw_embedder is None:
        raw_embedder, embedder_identity, cpu_threads = _build_embedder(selected_names)
    else:
        embedder_identity = None
        cpu_threads = None

    gold_graph = corpus.graph
    gold_incident = compute_gold_incident_edges(gold_graph, node)
    report_strategies: list[StrategyReport] = []
    edges_by_strategy: dict[str, set[tuple[str, str]]] = {}

    for name in selected_names:
        g = gold_graph.without_node(node)
        n_before = g.num_nodes()
        e_before = g.num_edges()

        strategy = STRATEGY_FACTORIES[name](**DEMO_PARAMS[name])
        _check_strategy_config(name, dict(strategy.config()))
        meter = MeteredEmbedder(raw_embedder)
        setup_calls_before = meter.calls
        t0 = time.perf_counter()
        strategy.setup(g, meter)
        setup_s = time.perf_counter() - t0
        setup_embedding_calls = meter.calls - setup_calls_before
        gc.collect()

        recorder = RecordingLLMClient(client)
        llm_meter = MeteredLLMClient(recorder)
        step = PairwiseDecisionStep(llm_meter)
        try:
            t1 = time.perf_counter()
            result = insert_node(strategy, g, step, node, metered_embedder=meter)
            replay_wall = time.perf_counter() - t1
        except DemoError:
            raise
        except Exception as exc:
            raise DemoError(6, f"{name} insertion failed: {type(exc).__name__}: {exc}") from exc

        prompt_to_candidate = {
            step.build_user_prompt(node, candidate, corpus.domain_context): candidate
            for candidate in result.shortlist.candidates
        }
        calls: list[DemoCall] = []
        for issued in recorder.calls:
            candidate = prompt_to_candidate.get(issued.user_prompt)
            if candidate is None:
                raise DemoError(
                    6,
                    f"{name}: issued a prompt outside the strategy shortlist",
                )
            token = parse_token(issued.response.text)
            if token is None:
                raise DemoError(
                    6,
                    f"{name}: unparseable live response {issued.response.text!r}",
                    "The demo refuses to invent an edge for an unparseable answer.",
                )
            if token == "X_PREREQ_Y":
                edge: Optional[tuple[str, str]] = (node, candidate)
            elif token == "Y_PREREQ_X":
                edge = (candidate, node)
            else:
                edge = None
            calls.append(
                DemoCall(
                    x=node,
                    y=candidate,
                    token=token,
                    edge=edge,
                    latency_s=issued.response.latency_s,
                    input_tokens=issued.response.input_tokens,
                    output_tokens=issued.response.output_tokens,
                    user_prompt=issued.user_prompt,
                )
            )

        rebuilt = {c.edge for c in calls if c.edge is not None}
        if rebuilt != set(result.edges):
            raise DemoError(
                6,
                f"{name}: edges rebuilt from recorded tokens differ from production insert_node edges",
            )

        score = score_node_insertion(
            node=node,
            gold_graph=gold_graph,
            judgments=corpus.judgments,
            shortlist_candidates=result.shortlist.candidates,
            decided_edges=result.edges,
        )

        shortlist_set = set(result.shortlist.candidates)
        predicted = set(result.edges)
        labels: list[EdgeLabel] = []
        tp = fp = excluded = 0
        for edge in result.edges:
            single = score_node_insertion(
                node=node,
                gold_graph=gold_graph,
                judgments=corpus.judgments,
                shortlist_candidates=result.shortlist.candidates,
                decided_edges=[edge],
            )
            tp += single.tp
            fp += single.fp
            excluded += single.excluded_predictions
            if single.tp:
                label = "TP"
            elif single.excluded_predictions:
                label = "UNJUDGED"
            else:
                label = "FP"
            path = None
            if label == "FP":
                path = _gold_path(gold_graph, edge[0], edge[1])
            labels.append(EdgeLabel(edge=edge, label=label, gold_path=path))
        if (tp, fp, excluded) != (score.tp, score.fp, score.excluded_predictions):
            raise DemoError(6, f"{name}: per-edge labels do not sum to the NodeScore counts")

        missed: list[MissedEdge] = []
        for edge in sorted(gold_incident - predicted):
            prereq, dependent = edge
            other = dependent if prereq == node else prereq
            if other not in shortlist_set:
                cause = "not shortlisted"
            elif (dependent, prereq) in predicted:
                cause = "direction reversed"
            else:
                cause = "judged NONE"
            missed.append(MissedEdge(edge=edge, cause=cause))
        if len(missed) != score.fn:
            raise DemoError(6, f"{name}: missed-edge list length differs from FN")

        lost_narrowing = sum(1 for m in missed if m.cause == "not shortlisted")
        lost_decision = len(missed) - lost_narrowing

        latency = sum(c.latency_s for c in calls)
        input_tokens = sum(c.input_tokens for c in calls)
        output_tokens = sum(c.output_tokens for c in calls)
        cache_hits = sum(call_cache for call_cache in (
            issued.response.cache_hit_tokens for issued in recorder.calls
        ))
        cache_misses = sum(call_cache for call_cache in (
            issued.response.cache_miss_tokens for issued in recorder.calls
        ))
        cost = estimated_cost_usd(cache_misses, cache_hits, output_tokens)

        recall_given = None
        if score.shortlist_recall and score.recall is not None and score.shortlist_recall > 0:
            recall_given = score.recall / score.shortlist_recall

        diagnostics = {
            key: result.metrics.extra.get(key)
            for key in DIAGNOSTIC_KEYS.get(name, [])
            if key in result.metrics.extra
        }

        report_strategies.append(
            StrategyReport(
                name=name,
                display=DISPLAY_NAMES[name],
                config=configs[name],
                setup_s_live=setup_s,
                setup_embedding_calls=setup_embedding_calls,
                shortlist_candidates=result.shortlist.candidates,
                shortlist_scores=result.shortlist.scores,
                shortlist_s_live=result.metrics.shortlist_s,
                embed_s_live=result.metrics.embed_s,
                update_s_live=result.metrics.update_s,
                replay_wall_s_live=replay_wall,
                calls=calls,
                recorded_latency_s=latency,
                recorded_input_tokens=input_tokens,
                recorded_output_tokens=output_tokens,
                recorded_cache_hit_tokens=cache_hits,
                recorded_cache_miss_tokens=cache_misses,
                cost_usd=cost,
                calls_vs_s1_pct=100.0 * (1.0 - len(calls) / n_before) if n_before else 0.0,
                kept_pct=100.0 * len(result.shortlist.candidates) / n_before if n_before else 0.0,
                applied_nodes_added=1,
                applied_edges_added=len(result.edges),
                score=score,
                labelled_edges=labels,
                missed=missed,
                lost_narrowing=lost_narrowing,
                lost_decision=lost_decision,
                recall_given_shortlist=recall_given,
                diagnostics=diagnostics,
                retries=llm_meter.retries,
                parse_failures=llm_meter.parse_failures,
                transport_failures=len(llm_meter.failed_calls),
            )
        )
        edges_by_strategy[name] = predicted

    if is_live:
        total_input = sum(s.recorded_input_tokens for s in report_strategies)
        total_output = sum(s.recorded_output_tokens for s in report_strategies)
        total_hits = sum(s.recorded_cache_hit_tokens for s in report_strategies)
        total_misses = sum(s.recorded_cache_miss_tokens for s in report_strategies)
        total_latency = sum(s.recorded_latency_s for s in report_strategies)
        total_cost = sum(s.cost_usd for s in report_strategies)
        provenance = PilotProvenance(
            path="(live DeepSeek API)",
            sha256="",
            recorded_utc=started.isoformat(),
            prompt_version=decision_module.PROMPT_VERSION,
            model=str(getattr(live_client, "model", "")),
            n_calls=sum(len(s.calls) for s in report_strategies),
            temperature=float(getattr(live_client, "temperature", 0.0)),
            thinking_mode=str(getattr(live_client, "thinking_mode", "disabled")),
            retries=sum(s.retries for s in report_strategies),
            parse_failures=sum(s.parse_failures for s in report_strategies),
            transport_failures=sum(s.transport_failures for s in report_strategies),
            input_tokens=total_input,
            output_tokens=total_output,
            cache_hit_tokens=total_hits,
            cache_miss_tokens=total_misses,
            estimated_cost_usd=total_cost,
            cumulative_latency_s=total_latency,
            system_prompt_recorded=False,
        )
    elif provenance is None:
        raise DemoError(6, "replay report is missing provenance")

    subset_of_s1: Optional[bool] = None
    if "brute_force" in edges_by_strategy:
        base = edges_by_strategy["brute_force"]
        subset_of_s1 = all(edges <= base for edges in edges_by_strategy.values())
        if not subset_of_s1:
            raise DemoError(6, "subset invariant violated: a narrowing strategy predicted an edge S1 did not")

    return DemoReport(
        started_utc=started.isoformat(),
        wall_s_live=time.perf_counter() - t_start,
        argv=list(argv) if argv is not None else list(sys.argv[1:]),
        provenance=provenance,
        pilot_dir=str(resolved_pilot),
        corpus_name=str(corpus.name),
        domain_context=corpus.domain_context,
        node=node,
        full_nodes=gold_graph.num_nodes(),
        full_edges=gold_graph.num_edges(),
        n_before=gold_graph.num_nodes() - 1,
        e_before=gold_graph.num_edges() - len(gold_incident),
        gold_prerequisites=sorted(gold_graph.prerequisites_of(node)),
        gold_dependents=sorted(gold_graph.dependents_of(node)),
        gold_incident=len(gold_incident),
        prompt_version=decision_module.PROMPT_VERSION,
        system_prompt_sha256=hashlib.sha256(
            decision_module.SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        prices={
            "cache_miss_in_per_m": PRICE_IN_CACHE_MISS,
            "cache_hit_in_per_m": PRICE_IN_CACHE_HIT,
            "output_per_m": PRICE_OUT,
        },
        strategies=report_strategies,
        selected=selected_names,
        subset_of_s1=subset_of_s1,
        embedder_identity=embedder_identity,
        cpu_threads=cpu_threads,
        mode="live" if is_live else "replay",
        live_base_url=str(getattr(live_client, "base_url", "")) if is_live else None,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


class Palette:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\x1b[{code}m{text}\x1b[0m"

    def tag_live(self, text: str = "[LIVE]") -> str:
        return self.paint(text, "36")

    def tag_pilot(self, text: str = "[PILOT]") -> str:
        return self.paint(text, "35")

    def tag_calc(self, text: str = "[CALC]") -> str:
        return self.paint(text, "33")

    def tag_gold(self, text: str = "[GOLD]") -> str:
        return self.paint(text, "34")

    def tp(self, text: str = "TP") -> str:
        return self.paint(text, "32")

    def fp(self, text: str = "FP") -> str:
        return self.paint(text, "31")

    def fn(self, text: str = "FN") -> str:
        return self.paint(text, "33")


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plural(count: int, singular: str, plural: Optional[str] = None) -> str:
    word = singular if count == 1 else (plural or singular + "s")
    return f"{count} {word}"


def visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def _pilot_start(provenance: PilotProvenance) -> str:
    stem = Path(provenance.path).parent.name
    try:
        dt = datetime.strptime(stem, "%Y%m%d_%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%SZ")
    except ValueError:
        return _short_ts(provenance.recorded_utc)


def _short_ts(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except (ValueError, TypeError):
        return value[:19]


def _display_path(path_text: str) -> str:
    try:
        return str(Path(path_text).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path_text)


@dataclass
class FormatOptions:
    color: bool = False
    ascii: bool = False
    show_all_calls: bool = False


class Formatter:
    def __init__(self, report: DemoReport, options: FormatOptions) -> None:
        self.report = report
        self.options = options
        self.palette = Palette(options.color)
        self.lines: list[str] = []
        self._first_call_printed = False

    # -- glyphs ---------------------------------------------------------
    @property
    def heavy(self) -> str:
        return "=" if self.options.ascii else "═"

    @property
    def light(self) -> str:
        return "-" if self.options.ascii else "─"

    @property
    def arrow(self) -> str:
        return "->" if self.options.ascii else "→"

    @property
    def dot(self) -> str:
        return "." if self.options.ascii else "·"

    # -- primitives -----------------------------------------------------
    def add(self, text: str = "") -> None:
        self.lines.append(text)

    def add_wrapped(self, text: str, *, indent: str = "  ", width: int = WIDTH) -> None:
        for line in textwrap.wrap(
            text,
            width=width,
            initial_indent=indent,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [indent.rstrip()]:
            self.add(line)

    def rule(self, char: Optional[str] = None) -> None:
        self.add((char or self.heavy) * WIDTH)

    def phase(self, title: str) -> None:
        self.rule(self.light)
        self.add(f" {title}")
        self.rule(self.light)

    @staticmethod
    def fmt_metric(value: Optional[float], digits: int = 3) -> str:
        if value is None:
            return "n/a"
        return f"{value:.{digits}f}"

    @staticmethod
    def fmt_s(seconds: float) -> str:
        return f"{seconds:.2f} s"

    @staticmethod
    def fmt_ms(seconds: float) -> str:
        return f"{seconds * 1000.0:.1f} ms"

    def add_edge(self, marker: str, paint, edge_text: str, suffix: str = "") -> None:
        prefix = f"      {marker:<10s} "
        wrapped = textwrap.wrap(
            prefix + edge_text + suffix,
            width=WIDTH,
            subsequent_indent=" " * len(prefix),
            break_long_words=False,
            break_on_hyphens=False,
        ) or [prefix + edge_text + suffix]
        for index, line in enumerate(wrapped):
            if index == 0 and self.palette.enabled:
                line = line[:6] + paint(marker) + line[6 + len(marker):]
            self.add(line)

    # -- phases ---------------------------------------------------------
    def source_tag(self, text: Optional[str] = None) -> str:
        if self.report.mode == "live":
            return self.palette.tag_live(text or "[LIVE]")
        return self.palette.tag_pilot(text or "[PILOT]")

    def banner(self) -> None:
        p = self.palette
        r = self.report
        prov = r.provenance
        live = r.mode == "live"
        suffix = "LIVE RUN" if live else "PILOT-001 replay"
        self.rule()
        self.add(
            " DEFENSE DEMO  ·  one concept insertion, four narrowing strategies"
            f"   {suffix}".replace("·", self.dot)
        )
        self.rule()
        self.add(" PROVENANCE")
        if live:
            self.add("   LLM decisions  LIVE calls to the DeepSeek API (not replayed)")
            self.add(f"   Endpoint       {r.live_base_url or '(unknown)'}")
            self.add(
                f"   Model         {prov.model} {self.dot} prompt {prov.prompt_version}"
                f" {self.dot} temperature {prov.temperature:g} {self.dot} thinking {prov.thinking_mode}"
            )
            self.add(
                f"                 {prov.n_calls} calls {self.dot} {prov.retries} retries"
                f" {self.dot} {prov.parse_failures} parse failures"
                f" {self.dot} {prov.transport_failures} transport failures"
            )
            self.add("   Network / API  live API used · key read from DEEPSEEK_API_KEY")
        else:
            self.add("   LLM decisions  REPLAYED from recorded PILOT-001 calls")
            self.add("                  (not re-requested, not simulated)")
            self.add(f"   Cache file     {_display_path(prov.path)}")
            self.add(
                f"                  {prov.n_calls} calls {self.dot} sha256 {prov.sha256[:12]}"
                f"{'...' if self.options.ascii else '…'} {self.dot} recorded {_pilot_start(prov)}"
            )
            self.add(
                f"   Recorded with  {prov.model} {self.dot} prompt {prov.prompt_version}"
                f" {self.dot} temperature {prov.temperature:g} {self.dot} thinking {prov.thinking_mode}"
            )
            self.add(
                f"                  {prov.retries} retries {self.dot} {prov.parse_failures} parse failures"
                f" {self.dot} {prov.transport_failures} transport failures"
            )
            self.add("   Network / API  none used · no API key read".replace("·", self.dot))
        self.add("   Run live here  corpus load, narrowing, graph update, scoring, timers [LIVE]")
        if r.embedder_identity:
            identity = r.embedder_identity
            self.add(
                f"   Embedder       {identity['model_name']} rev {str(identity['revision'])[:7]}"
                f" {self.dot} CPU {self.dot} 1 thread"
            )
            self.add(
                f"                  sentence-transformers"
                f" {identity['sentence_transformers_version']}"
            )
        else:
            self.add("   Embedder       not loaded (brute_force needs none)")
        if live:
            self.add(
                " TAGS  " + p.tag_live() + " measured now   "
                + p.tag_calc() + " computed"
            )
            self.add(
                "       " + p.tag_gold() + " ground truth (revealed after)"
            )
        else:
            self.add(
                " TAGS  " + p.tag_live() + " measured now   "
                + p.tag_pilot() + " recorded 2026-10-07"
            )
            self.add(
                "       " + p.tag_calc() + " computed       "
                + p.tag_gold() + " ground truth (revealed after)"
            )
        self.add("")
        self.add_wrapped(LIVE_NOTICE if live else REPLAY_NOTICE)
        self.add("")

    def before(self) -> None:
        r = self.report
        self.phase("PHASE 1 · BEFORE".replace("·", self.dot))
        self.add_wrapped(
            "The thesis measures how the cost (LLM calls, time) and the accuracy of "
            "inserting one new concept into an existing LLM-built prerequisite graph "
            "depend on how candidates are narrowed. Only the narrowing differs; the "
            "LLM decision step is identical for every strategy."
        )
        self.add("")
        self.add(f"  Corpus            {r.corpus_name}")
        self.add(f"  Domain context    {r.domain_context!r}")
        self.add(f"  Full graph        {r.full_nodes} concepts, {r.full_edges} prerequisite edges")
        self.add(f"  NEW concept       {r.node}")
        self.add(f"  Existing graph    {r.n_before} concepts, {r.e_before} edges")
        self.add("  Gold neighbourhood: HIDDEN until AFTER. Nothing before AFTER is marked with it.")
        self.add("")
        self.add("  THE SHARED DECISION STEP (identical for every strategy)")
        for raw_line in decision_module.SYSTEM_PROMPT.splitlines():
            if not raw_line.strip():
                self.add("    ")
                continue
            for line in textwrap.wrap(
                raw_line,
                width=WIDTH - 4,
                initial_indent="    ",
                subsequent_indent="    ",
            ):
                self.add(line)
        self.add("    User prompt template:")
        self.add("      Subject area: <domain>")
        self.add("      Concept X: <new concept, spaces instead of underscores>")
        self.add("      Concept Y: <candidate, spaces instead of underscores>")
        self.add("    Answers: X_PREREQ_Y | Y_PREREQ_X | NONE")
        self.add(
            "    One call per shortlisted candidate; X_PREREQ_Y -> edge (new -> cand);"
        )
        self.add(
            "    Y_PREREQ_X -> edge (cand -> new); canonical direction prerequisite -> dependent."
        )
        self.add("    Only names are shown to the model.")
        self.add("")
        self.add("  STRATEGIES SELECTED")
        for s in r.strategies:
            if s.name == "brute_force":
                desc = "nothing; every existing concept is judged"
            elif s.name == "embedding_threshold":
                desc = (
                    f"cosine(new, node) > {s.config.get('theta')} (strict), "
                    "MiniLM embeddings"
                )
            elif s.name == "ann_retrieval":
                desc = (
                    f"top-{s.config.get('k')} by cosine through HNSW "
                    f"(M={s.config.get('M')}, efConstruction={s.config.get('ef_construction')}, "
                    f"efSearch={s.config.get('ef_search')})"
                )
            else:
                desc = (
                    f"one size-bounded home bucket ({s.config.get('s_min')}.."
                    f"{s.config.get('s_max')}, {s.config.get('n_bits')} hash bits)"
                )
            self.add(f"    {s.display:2s} {s.name}")
            for line in textwrap.wrap(
                desc,
                width=WIDTH - 6,
                initial_indent="       ",
                subsequent_indent="       ",
                break_long_words=False,
                break_on_hyphens=False,
            ):
                self.add(line)
        self.add("")
        self.add(
            "  cost = (cache-miss in x $0.15 + cache-hit in x $0.003 + out x $0.60) / 1M"
        )
        self.add("         (off-peak prices, D-36)")
        self.add("")

    def _visible_call_indices(self, calls: list[DemoCall]) -> tuple[list[int], int]:
        n = len(calls)
        if self.options.show_all_calls or n <= 10:
            return list(range(n)), 0
        keep: set[int] = {0, 1, 2}
        for idx, call in enumerate(calls):
            if call.token != "NONE":
                keep.add(idx)
        first_none = next((i for i, c in enumerate(calls) if c.token == "NONE"), None)
        if first_none is not None:
            keep.add(first_none)
        ordered = sorted(i for i in keep if i < n)
        hidden = [i for i in range(n) if i not in set(ordered)]
        hidden_none = sum(1 for i in hidden if calls[i].token == "NONE")
        return ordered, hidden_none

    def while_block(self, index: int, total: int, s: StrategyReport) -> None:
        p = self.palette
        shortlist_n = len(s.shortlist_candidates)
        self.phase(
            f"PHASE 2 · WHILE   strategy {index} of {total}:  {s.display}  {s.name}"
        )
        self.add(
            f"  setup     index build over {self.report.n_before} concepts"
            f"   {self.fmt_ms(s.setup_s_live)} {p.tag_live()}  excluded from official timer"
        )
        if shortlist_n == 0:
            self.add(
                f"  shortlist 0 of {self.report.n_before} kept (0.0%), narrowed away 100.0%"
            )
            self.add(f"            time {self.fmt_ms(s.shortlist_s_live)} {p.tag_live()}")
            self.add("  no LLM calls, no edges")
            latency_word = "API latency" if self.report.mode == "live" else "recorded latency"
            self.add(f"  LLM        0 calls · 0.00 s {latency_word} {self.source_tag()}")
            self.add(f"             0 in / 0 out tokens {self.source_tag()}")
            self.add(f"             cost $0.000000 {p.tag_calc()}")
            self.add(f"             calls vs S1: 100% {p.tag_calc()}")
            self.add(
                f"  applied    +1 concept, +0 edges  ->  graph"
                f" {self.report.full_nodes} concepts, {self.report.e_before} edges"
                f" {p.tag_calc()}"
            )
            self.add(f"             update {self.fmt_ms(s.update_s_live)} {p.tag_live()}")
            self.add(
                f"             replay wall time {self.fmt_ms(s.replay_wall_s_live)}"
                f" {p.tag_live()}"
            )
            self.add("")
            return
        self.add(
            f"  shortlist {shortlist_n} of {self.report.n_before} kept"
            f" ({s.kept_pct:.1f}%), narrowed away {100.0 - s.kept_pct:.1f}%"
        )
        self.add(
            f"            time {self.fmt_ms(s.shortlist_s_live)} {p.tag_live()}"
            f"  (embedding the new name: {self.fmt_ms(s.embed_s_live)})"
        )

        scores = s.shortlist_scores
        if s.name == "brute_force":
            self.add(
                f"  all {shortlist_n} existing concepts, alphabetical, no ranking"
            )
        elif scores is not None and len(scores) == shortlist_n and len(set(scores)) > 1:
            self.add(f"  top candidates by cosine {p.tag_live()}")
            shown = 0
            for rank, (score, name) in enumerate(zip(scores, s.shortlist_candidates), 1):
                if rank > 10:
                    break
                self.add(f"    {rank:3d}  {score:.3f}  {name}")
                shown += 1
            if shortlist_n > shown:
                self.add(f"    ... and {shortlist_n - shown} more")
        else:
            self.add(f"  candidates: {', '.join(s.shortlist_candidates)}")

        if s.diagnostics:
            parts = []
            for key, value in s.diagnostics.items():
                if isinstance(value, float):
                    parts.append(f"{key}={value:.3f}")
                else:
                    parts.append(f"{key}={value}")
            self.add(f"  diagnostics  {(' ' + self.dot + ' ').join(parts)}  {p.tag_live()}")
            self.add("")

        visible, hidden_none = self._visible_call_indices(s.calls)
        if self.options.show_all_calls:
            label = f"{len(s.calls)} calls, all shown"
        elif len(visible) == len(s.calls):
            label = f"{len(s.calls)} calls, all shown"
        else:
            label = f"{len(s.calls)} calls, {len(visible)} shown"
        label = label.replace(" calls", " call" if len(s.calls) == 1 else " calls")
        self.add(f"  decisions  {label} {self.source_tag()}")

        total_calls = len(s.calls)
        for pos in visible:
            call = s.calls[pos]
            x_text = embed_text(call.x)
            y_text = embed_text(call.y)
            self.add(f"   call {pos + 1:2d}/{total_calls:<2d}  X = {x_text}   Y = {y_text}")
            if not self._first_call_printed:
                self._first_call_printed = True
                prompt_label = (
                    "exact prompt sent in this run"
                    if self.report.mode == "live"
                    else "exact prompt sent in PILOT-001"
                )
                self.add(f"             {prompt_label} {self.source_tag()}")
                for line in call.user_prompt.splitlines():
                    self.add(f"             | {line}")
            answer = call.token
            self.add(
                f"             answer {answer:<12s} {self.fmt_s(call.latency_s):>7s}"
                f"  {call.input_tokens} in / {call.output_tokens} out"
            )
            if call.edge is None:
                self.add("             -> no edge")
            else:
                self.add_wrapped(
                    f"-> edge  {call.edge[0]} {self.arrow} {call.edge[1]}"
                    "   (prerequisite -> dependent)",
                    indent=" " * 13,
                )
        if hidden_none > 0:
            self.add(
                f"   ... {hidden_none} NONE decisions not printed (use --show-all-calls)"
            )

        counts: dict[str, int] = {"NONE": 0, "X_PREREQ_Y": 0, "Y_PREREQ_X": 0}
        for call in s.calls:
            counts[call.token] = counts.get(call.token, 0) + 1
        self.add(
            f"  answers    NONE {counts['NONE']} · X_PREREQ_Y {counts['X_PREREQ_Y']}"
            f" · Y_PREREQ_X {counts['Y_PREREQ_X']}          {self.source_tag()}"
        )
        latency_word = "API latency" if self.report.mode == "live" else "recorded latency"
        self.add(
            f"  LLM        {len(s.calls)} calls · {self.fmt_s(s.recorded_latency_s)} {latency_word}"
            f" {self.source_tag()}"
        )
        self.add(
            f"             {s.recorded_input_tokens:,} in / {s.recorded_output_tokens:,} out tokens"
            f" {self.source_tag()}"
        )
        self.add(f"             cost ${s.cost_usd:.6f} {p.tag_calc()}")
        self.add(f"             calls vs S1: {s.calls_vs_s1_pct:.0f}% {p.tag_calc()}")
        self.add(
            f"  applied    +1 concept, +{_plural(s.applied_edges_added, 'edge')}  ->  graph"
            f" {self.report.full_nodes} concepts,"
            f" {self.report.e_before + s.applied_edges_added} edges {p.tag_calc()}"
        )
        self.add(f"             update {self.fmt_ms(s.update_s_live)} {p.tag_live()}")
        self.add(
            f"             replay wall time {self.fmt_ms(s.replay_wall_s_live)} {p.tag_live()}"
        )
        self.add("")

    def after(self) -> None:
        p = self.palette
        r = self.report
        self.phase("PHASE 3 · AFTER".replace("·", self.dot))
        def gold_names(label: str, names: list[str]) -> None:
            prefix = f"  {p.tag_gold()} {label}: "
            if not names:
                self.add(prefix + "(none)")
                return
            for line in textwrap.wrap(
                ", ".join(names),
                width=WIDTH,
                initial_indent=prefix,
                subsequent_indent="      ",
                break_long_words=False,
                break_on_hyphens=False,
            ):
                self.add(line)

        gold_names(f"prerequisites of {r.node}", r.gold_prerequisites)
        gold_names(f"dependents of {r.node}", r.gold_dependents)
        self.add(f"  {p.tag_gold()} {r.gold_incident} gold incident edges")
        self.add("")

        for s in r.strategies:
            score = s.score
            self.add(f"  {s.display} {s.name}")
            self.add(
                f"    shortlist captured {score.shortlist_hits}/{score.gold_neighbours}"
                f" gold neighbours (shortlist recall {self.fmt_metric(score.shortlist_recall)})"
            )
            if s.labelled_edges:
                self.add("    predicted edges")
                for item in s.labelled_edges:
                    edge = f"{item.edge[0]} {self.arrow} {item.edge[1]}"
                    if item.label == "TP":
                        paint = p.tp
                    elif item.label == "FP":
                        paint = p.fp
                    else:
                        paint = p.tag_gold
                    self.add_edge(item.label, paint, edge)
                    if item.gold_path:
                        path = f" {self.arrow} ".join(item.gold_path)
                        self.add_wrapped(
                            f"(gold path exists: {path})",
                            indent=" " * 17,
                        )
            else:
                self.add("    predicted edges: none")
            if s.missed:
                self.add("    missed gold edges")
                for item in s.missed:
                    edge = f"{item.edge[0]} {self.arrow} {item.edge[1]}"
                    self.add_edge("FN", p.fn, edge, f"  ({item.cause})")
            else:
                self.add("    missed gold edges: none")
            self.add(
                f"    lost at narrowing {s.lost_narrowing} {self.dot} lost at decision"
                f" {s.lost_decision} {p.tag_calc()}"
            )
            self.add(
                f"    metrics  P {self.fmt_metric(score.precision)}"
                f"  R {self.fmt_metric(score.recall)}"
                f"  F1 {self.fmt_metric(score.f1)}"
                f"   TP {score.tp} FP {score.fp} FN {score.fn} {p.tag_calc()}"
            )
            if score.excluded_predictions:
                self.add(
                    f"    unjudged predictions excluded: {score.excluded_predictions}"
                    f"  (sensitivity F1 {self.fmt_metric(score.f1_sensitivity)})"
                )
            if s.recall_given_shortlist is not None:
                self.add(
                    f"    recall decomposition: shortlist {self.fmt_metric(score.shortlist_recall)}"
                    f" x given-shortlist {self.fmt_metric(s.recall_given_shortlist)}"
                    f" = {self.fmt_metric(score.recall)} {p.tag_calc()}"
                )
            self.add("")

        if r.subset_of_s1 is not None:
            status = "OK" if r.subset_of_s1 else "FAILED"
            self.add(
                f"  INVARIANT  every edge from a narrowing strategy is in S1's predicted set: {status}"
            )
        else:
            self.add("  INVARIANT  subset check not run (S1 not selected)")
        self.add("")

        self.comparison_tables()
        self.takeaways()
        self.limitations()

    def comparison_tables(self) -> None:
        r = self.report
        self.add(
            f"  {'WORK':<22} {'kept':>7} {'calls':>5} {'vsS1':>5}"
            f" {'LLM lat':>8} {'tokens in/out':>13} {'cost':>9} {'shortlist':>8}"
        )
        source_label = "[LIVE]" if self.report.mode == "live" else "[PILOT]"
        self.add(
            f"  (LLM latency and tokens are {source_label}; cost is [CALC];"
            " shortlist time is [LIVE].)"
        )
        for s in r.strategies:
            shortlist_n = len(s.shortlist_candidates)
            kept = f"{shortlist_n}/{r.n_before}"
            tokens = f"{s.recorded_input_tokens:,} / {s.recorded_output_tokens:,}"
            label = f"{s.display} {s.name}"
            self.add(
                f"  {label:<22} {kept:>7} {len(s.calls):>5} {s.calls_vs_s1_pct:>4.0f}%"
                f" {self.fmt_s(s.recorded_latency_s):>8}"
                f" {tokens:>13} {('$' + format(s.cost_usd, '.6f')):>9}"
                f" {self.fmt_ms(s.shortlist_s_live):>8}"
            )
        self.add("")
        self.add(
            f"  {'ACCURACY':<22} {'sl.recall':>9} {'P':>6} {'R':>6} {'F1':>6}"
            f" {'TP/FP/FN':>10} {'lost n/d':>9}"
        )
        for s in r.strategies:
            score = s.score
            self.add(
                f"  {s.display + ' ' + s.name:<22} {self.fmt_metric(score.shortlist_recall):>9}"
                f" {self.fmt_metric(score.precision):>6}"
                f" {self.fmt_metric(score.recall):>6}"
                f" {self.fmt_metric(score.f1):>6}"
                f" {(str(score.tp) + '/' + str(score.fp) + '/' + str(score.fn)):>10}"
                f" {(str(s.lost_narrowing) + '/' + str(s.lost_decision)):>9}"
            )
        self.add("")

    def takeaways(self) -> None:
        r = self.report
        self.add("  TAKEAWAYS")

        def bullet(text: str) -> None:
            for line in textwrap.wrap(
                text,
                width=WIDTH - 4,
                initial_indent="    - ",
                subsequent_indent="      ",
                break_long_words=False,
                break_on_hyphens=False,
            ):
                self.add(line)

        narrowing = [s for s in r.strategies if s.name != "brute_force"]
        if narrowing:
            for s in narrowing:
                bullet(
                    f"{s.display} made {len(s.calls)} calls, {s.calls_vs_s1_pct:.0f}% fewer"
                    f" than S1's {r.n_before}."
                )
        if r.subset_of_s1 and "brute_force" in r.selected and len(r.strategies) > 1:
            bullet(
                "Every edge from S2-S4 was also predicted by S1: the decision step is"
                " identical, so differences come only from which pairs were sent to the model."
            )
        if narrowing:
            parts = []
            for s in narrowing:
                parts.append(
                    f"{s.display} kept {self.fmt_metric(s.score.shortlist_recall)} of gold"
                    f" neighbours and lost {s.lost_narrowing} edge(s) before the model saw them"
                )
            bullet("Narrowing's price: " + "; ".join(parts) + ".")
        if "brute_force" in r.selected and narrowing:
            s1 = next(s for s in r.strategies if s.name == "brute_force")
            better = [
                s for s in narrowing
                if s.score.f1 is not None and s1.score.f1 is not None and s.score.f1 > s1.score.f1
            ]
            if better:
                best = max(better, key=lambda s: s.score.f1 or 0.0)
                bullet(
                    f"{best.display} has a higher F1 than S1 because it never judged"
                    f" {s1.score.fp} pair(s) that S1 turned into false positives."
                )
            else:
                bullet("On this node no narrowing strategy beat brute-force F1.")
        bullet(
            "One node is an illustration. The thesis evidence is the full runs (RQ1-RQ3),"
            " not this transcript."
        )
        self.add("")

    def limitations(self) -> None:
        self.add("  LIMITATIONS — WHAT THIS DOES NOT PROVE")
        if self.report.mode == "live":
            self.add_wrapped(
                "Decisions are live DeepSeek API calls made during this run, not replayed"
                " recordings. The answers are what the model returned now."
            )
        else:
            self.add_wrapped(
                "Decisions are replayed from PILOT-001 recordings, not re-requested. This is real"
                " model output for exactly these prompts, recorded on 2026-10-07."
            )
        self.add_wrapped(
            "One held-out node, one trial, one repeat. This is an illustration, not a new"
            " result, and it is not part of Chapter 4."
        )
        if self.report.mode == "live":
            self.add_wrapped(
                "Latency, tokens and cost are measured live by this run. Only this single"
                " insertion is measured; it says nothing about scaling with graph size."
            )
        else:
            self.add_wrapped(
                "Latency, tokens and cost are recorded values. Only setup, shortlist, update and"
                " replay times are measured now; replay wall time says nothing about model latency."
            )
        if self.report.mode == "live":
            self.add_wrapped(
                "In this live run each strategy made its own API calls, so strategies may"
                " disagree on a pair even though they share the same decision step."
            )
        else:
            self.add_wrapped(
                "In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a"
                " pair. In the official runs each strategy made its own live calls, so agreement"
                " on a pair is not guaranteed there."
            )
        if self.report.subset_of_s1 is not None:
            self.add_wrapped(
                "DSA gold is not transitively reduced, so some false positives may be"
                " defensible by transitive closure; metrics are computed against the gold as"
                " given."
            )
        self.add_wrapped(
            "Strategy parameters are the pre-fixed defaults (D-64); nothing was tuned on this node."
        )
        self.add("")

    def footer(self) -> None:
        p = self.palette
        if self.report.output_dir:
            self.add_wrapped(
                f"demo wall time {self.report.wall_s_live:.1f} s [LIVE]   "
                f"{self.dot} output {self.report.output_dir}",
                indent="  ",
            )
        else:
            self.add(
                f"  demo wall time {self.report.wall_s_live:.1f} s {p.tag_live()}   "
                f"{self.dot} no files written to results/"
            )
        self.rule()

    def render(self) -> list[str]:
        self.banner()
        self.before()
        for idx, strategy in enumerate(self.report.strategies, 1):
            self.while_block(idx, len(self.report.strategies), strategy)
        self.after()
        self.footer()
        for line in self.lines:
            if visible_len(line) > WIDTH:
                raise DemoError(
                    6,
                    f"formatter produced a {visible_len(line)}-column line (limit {WIDTH}): {line!r}",
                )
        return self.lines


def format_report(report: DemoReport, options: FormatOptions) -> list[str]:
    return Formatter(report, options).render()


# ---------------------------------------------------------------------------
# JSON record
# ---------------------------------------------------------------------------


def report_to_json(report: DemoReport) -> dict[str, Any]:
    prov = dataclasses.asdict(report.provenance)
    strategies: list[dict[str, Any]] = []
    for s in report.strategies:
        strategies.append(
            {
                "name": s.name,
                "display": s.display,
                "config": dict(s.config),
                "setup_s_live": s.setup_s_live,
                "setup_embedding_calls": s.setup_embedding_calls,
                "shortlist": {
                    "candidates": list(s.shortlist_candidates),
                    "scores": list(s.shortlist_scores) if s.shortlist_scores is not None else None,
                    "shortlist_s_live": s.shortlist_s_live,
                    "embed_s_live": s.embed_s_live,
                    "kept_pct": s.kept_pct,
                },
                "calls": [
                    {
                        "x": c.x,
                        "y": c.y,
                        "token": c.token,
                        "edge": list(c.edge) if c.edge else None,
                        "latency_s": c.latency_s,
                        "input_tokens": c.input_tokens,
                        "output_tokens": c.output_tokens,
                    }
                    for c in s.calls
                ],
                "recorded": {
                    "llm_calls": len(s.calls),
                    "latency_s": s.recorded_latency_s,
                    "input_tokens": s.recorded_input_tokens,
                    "output_tokens": s.recorded_output_tokens,
                },
                "calc": {
                    "cost_usd": s.cost_usd,
                    "calls_vs_s1_pct": s.calls_vs_s1_pct,
                    "kept_pct": s.kept_pct,
                },
                "applied": {
                    "nodes_added": s.applied_nodes_added,
                    "edges_added": s.applied_edges_added,
                    "update_s_live": s.update_s_live,
                },
                "score": dataclasses.asdict(s.score),
                "labelled_edges": [
                    {
                        "edge": list(item.edge),
                        "label": item.label,
                        "gold_path": item.gold_path,
                    }
                    for item in s.labelled_edges
                ],
                "missed": [
                    {"edge": list(item.edge), "cause": item.cause} for item in s.missed
                ],
                "lost_narrowing": s.lost_narrowing,
                "lost_decision": s.lost_decision,
                "recall_given_shortlist": s.recall_given_shortlist,
                "diagnostics": dict(s.diagnostics),
                "replay_wall_s_live": s.replay_wall_s_live,
            }
        )
    return {
        "schema": "demo-trial-1",
        "mode": report.mode,
        "live_base_url": report.live_base_url,
        "run": {
            "started_utc": report.started_utc,
            "wall_s_live": report.wall_s_live,
            "argv": list(report.argv),
            "output_dir": report.output_dir,
        },
        "provenance": {
            **prov,
            "embedder": report.embedder_identity,
            "cpu_threads": report.cpu_threads,
        },
        "trial": {
            "corpus": report.corpus_name,
            "node": report.node,
            "domain_context": report.domain_context,
            "n_before": report.n_before,
            "e_before": report.e_before,
            "full_nodes": report.full_nodes,
            "full_edges": report.full_edges,
            "gold": {
                "prerequisites": report.gold_prerequisites,
                "dependents": report.gold_dependents,
                "incident_edges": report.gold_incident,
            },
        },
        "decision_step": {
            "prompt_version": report.prompt_version,
            "system_prompt_sha256": report.system_prompt_sha256,
            "price_per_m": report.prices,
        },
        "strategies": strategies,
        "comparison": {
            s.name: {
                "shortlist_size": len(s.shortlist_candidates),
                "llm_calls": len(s.calls),
                "recorded_latency_s": s.recorded_latency_s,
                "cost_usd": s.cost_usd,
                "shortlist_recall": s.score.shortlist_recall,
                "precision": s.score.precision,
                "recall": s.score.recall,
                "f1": s.score.f1,
            }
            for s in report.strategies
        },
        "invariants": {"subset_of_s1": report.subset_of_s1},
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay or live demo: one insertion, four strategies."
    )
    parser.add_argument("--node", default=DEFAULT_NODE)
    parser.add_argument("--strategies", default=None)
    parser.add_argument("--pilot-dir", default=PILOT_DIR_DEFAULT)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--ascii", action="store_true")
    parser.add_argument("--pause", action="store_true")
    parser.add_argument("--show-all-calls", action="store_true")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--live", action="store_true", help="Make real DeepSeek API calls instead of replay.")
    parser.add_argument("--confirm", action="store_true", help="Required with --live.")
    parser.add_argument("--allow-peak", action="store_true", help="Allow a live run inside DeepSeek peak hours.")
    parser.add_argument("--output-dir", default=None, help="Live run output directory (default: demo_runs/live-<UTC>).")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--traceback", dest="show_traceback", action="store_true")
    return parser


def _validate_json_path(path_text: str) -> Path:
    path = Path(path_text)
    resolved = path.resolve()
    if path.exists():
        raise DemoError(7, f"refusing to overwrite existing --json file: {path}", "Choose a new path.")
    results_dir = (REPO_ROOT / "results").resolve()
    if resolved == results_dir or results_dir in resolved.parents:
        raise DemoError(7, f"refusing to write under results/: {path}", "Write outside the official results tree.")
    if not resolved.parent.is_dir():
        raise DemoError(7, f"parent directory does not exist for --json: {path}", "Create the directory first.")
    return resolved


def _validate_live_output_dir(path_text: Optional[str]) -> Path:
    if path_text:
        candidate = Path(path_text)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
        candidate = REPO_ROOT / "demo_runs" / f"live-{stamp}"
    resolved = candidate.resolve()
    results_dir = (REPO_ROOT / "results").resolve()
    if resolved == results_dir or results_dir in resolved.parents:
        raise DemoError(7, f"refusing to write live output under results/: {candidate}",
                        "Choose a directory outside the official results tree.")
    if resolved.exists():
        if not resolved.is_dir():
            raise DemoError(7, f"output path is not a directory: {candidate}")
        if any(resolved.iterdir()):
            raise DemoError(7, f"refusing to overwrite non-empty output directory: {candidate}",
                            "Pass a new --output-dir or remove the old demo directory.")
    else:
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DemoError(7, f"cannot create output directory {candidate}: {exc}") from exc
    return resolved


def _build_live_client() -> Any:
    from graph_insertion.llm import DeepSeekClient

    try:
        return DeepSeekClient()
    except ValueError as exc:
        raise DemoError(5, f"cannot start live run: {exc}",
                        "Set DEEPSEEK_API_KEY, or omit --live to use the offline replay.") from exc


def _live_preflight(selected: Sequence[str], corpus: Any) -> int:
    from graph_insertion.strategy import candidate_upper_bound

    n_existing = corpus.graph.num_nodes() - 1
    max_calls = 0
    for name in selected:
        probe = STRATEGY_FACTORIES[name](**DEMO_PARAMS[name])
        max_calls += candidate_upper_bound(probe, n_existing)
    estimated = max_calls * ((220 * PRICE_IN_CACHE_MISS + 16 * PRICE_OUT) / 1_000_000.0)
    print("LIVE RUN PRE-FLIGHT")
    print(f"  corpus      {corpus.name}  ({n_existing} existing concepts)")
    print(f"  strategies  {', '.join(selected)}")
    print(f"  max calls   {max_calls}  (upper bound; actual depends on shortlists)")
    print(f"  cost bound  ${estimated:.4f}  (off-peak prices, D-36)")
    return max_calls


def _write_live_outputs(
    report: DemoReport,
    output_dir: Path,
    *,
    ascii_mode: bool,
    show_all_calls: bool,
    argv: Sequence[str],
) -> None:
    plain = format_report(
        report,
        FormatOptions(color=False, ascii=ascii_mode, show_all_calls=show_all_calls),
    )
    (output_dir / "transcript.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")
    (output_dir / "demo.json").write_text(
        json.dumps(report_to_json(report), indent=2) + "\n",
        encoding="utf-8",
    )
    meta = {
        "schema": "demo-trial-live-meta-1",
        "mode": "live",
        "started_utc": report.started_utc,
        "wall_s_live": report.wall_s_live,
        "argv": list(argv),
        "node": report.node,
        "strategies": report.selected,
        "model": report.provenance.model,
        "base_url": report.live_base_url,
        "output_dir": str(output_dir),
        "files": ["transcript.txt", "demo.json", "run_meta.json"],
    }
    (output_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _color_enabled(no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


def _print_check(ok: bool, label: str, detail: str) -> None:
    print(f"{'OK  ' if ok else 'FAIL'} {label}: {detail}")


def run_checks(
    node: str,
    selected: Sequence[str],
    pilot_dir: str | Path,
    *,
    live: bool = False,
) -> int:
    failures = 0
    try:
        corpus = load_corpus(CORPUS_NAME)
        _print_check(True, "corpus", f"{corpus.name}: {corpus.graph.num_nodes()} nodes, "
                                 f"{corpus.graph.num_edges()} edges, domain={corpus.domain_context!r}")
    except Exception as exc:
        _print_check(False, "corpus", f"{type(exc).__name__}: {exc}")
        return 4

    if live:
        try:
            client = _build_live_client()
            _print_check(True, "live API", f"model={client.model}, base_url={client.base_url} "
                                           f"(no network call made)")
            _print_check(True, "live key", "DEEPSEEK_API_KEY present")
        except DemoError as exc:
            _print_check(False, "live API", exc.message)
            return 5
    else:
        try:
            prov, by_prompt = load_pilot(resolve_pilot_dir(pilot_dir), corpus=corpus)
            _print_check(True, "pilot cache", f"{prov.n_calls} calls, sha256 {prov.sha256[:12]}")
            _print_check(True, "pilot provenance", f"prompt {prov.prompt_version}, model {prov.model}, "
                                                  f"cost ${prov.estimated_cost_usd:.6f}")
        except DemoError as exc:
            _print_check(False, "pilot cache", exc.message)
            return 3

    nodes = sorted(corpus.graph.nodes())
    if node in nodes:
        _print_check(True, "node", node)
    else:
        suggestions = difflib.get_close_matches(node, nodes, n=5, cutoff=0.3)
        _print_check(False, "node", f"{node!r} not in corpus; close matches: {suggestions}")
        return 4

    if any(name != "brute_force" for name in selected):
        try:
            _, identity, cpu = _build_embedder(selected)
            _print_check(True, "embedder", f"{identity['model_name']} rev {str(identity['revision'])[:7]}, "
                                          f"torch threads {cpu['torch_threads']}")
        except DemoError as exc:
            _print_check(False, "embedder", exc.message)
            return 5
    else:
        _print_check(True, "embedder", "not required for the selected strategies")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        selected = parse_strategies(args.strategies)
        if args.check:
            return run_checks(args.node, selected, args.pilot_dir, live=args.live)

        live = bool(args.live)
        if live and args.output_dir is None:
            pass  # default is created below
        if not live and args.output_dir:
            raise DemoError(2, "--output-dir requires --live",
                            "Omit --output-dir for replay, or add --live.")
        if live and not args.confirm:
            raise DemoError(2, "live run requires --confirm",
                            "Add --confirm after checking the pre-flight estimate.")

        output_dir: Optional[Path] = None
        live_client: Any = None
        corpus: Any = None
        if live:
            from graph_insertion.schedule import format_peak_status, window_intersects_peak

            now_utc = datetime.now(timezone.utc)
            if window_intersects_peak(now_utc, 120) and not args.allow_peak:
                raise DemoError(
                    2,
                    "live run refused: the execution window overlaps DeepSeek peak pricing",
                    format_peak_status(now_utc) + "\nUse --allow-peak only if you accept peak prices.",
                )
            live_client = _build_live_client()
            try:
                corpus = load_corpus(CORPUS_NAME)
            except Exception as exc:
                raise DemoError(4, f"cannot load DSA corpus: {type(exc).__name__}: {exc}") from exc
            output_dir = _validate_live_output_dir(args.output_dir)
            try:
                _live_preflight(selected, corpus)
            except DemoError:
                raise
            except Exception as exc:
                raise DemoError(5, f"cannot prepare live strategies: {type(exc).__name__}: {exc}") from exc
            print(f"  peak check  {format_peak_status(now_utc).splitlines()[-1]}")
            print(f"  output dir  {output_dir}")
            print("")

        json_path = _validate_json_path(args.json_path) if args.json_path else None
        report = run_demo(
            node=args.node,
            selected=selected,
            pilot_dir=args.pilot_dir,
            corpus=corpus,
            live_client=live_client,
            argv=list(argv) if argv is not None else sys.argv[1:],
        )
        if output_dir is not None:
            report.output_dir = str(output_dir)

        options = FormatOptions(
            color=_color_enabled(args.no_color),
            ascii=args.ascii,
            show_all_calls=args.show_all_calls,
        )
        lines = format_report(report, options)
        seen_phase = False
        for line in lines:
            if args.pause and line.startswith(" PHASE ") and seen_phase:
                if sys.stdin.isatty() and sys.stdout.isatty():
                    try:
                        input("  [Enter for next phase] ")
                    except EOFError:
                        pass
            print(line)
            if line.startswith(" PHASE "):
                seen_phase = True
        if output_dir is not None:
            _write_live_outputs(
                report,
                output_dir,
                ascii_mode=args.ascii,
                show_all_calls=args.show_all_calls,
                argv=list(argv) if argv is not None else sys.argv[1:],
            )
        if json_path is not None:
            json_path.write_text(
                json.dumps(report_to_json(report), indent=2) + "\n",
                encoding="utf-8",
            )
        if output_dir is not None:
            print(f"\nLIVE OUTPUT: {output_dir}")
            print("  transcript.txt  demo.json  run_meta.json")
        return 0
    except DemoError as exc:
        if args.show_traceback:
            import traceback

            traceback.print_exc()
        print(f"ERROR: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"HINT: {exc.hint}", file=sys.stderr)
        return exc.exit_code
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        if args.show_traceback:
            import traceback

            traceback.print_exc()
        print(f"ERROR: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main())
