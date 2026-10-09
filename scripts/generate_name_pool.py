#!/usr/bin/env python3
"""scripts/generate_name_pool.py — Synthetic CS concept-name pool generator.

Generates a large-n pool of synthetic computer-science concept names with
zero overlap with any of the 12 evaluation corpora, formatted as:
    {"meta": {...}, "names": [...]}
compatible with scripts/run_experiment.py:load_and_validate_names_file.

Modes:
  --offline-fake : Deterministic synthetic generator for offline testing/verification.
                   Refuses to write the default tracked path (requires explicit --output).
  --dry-run      : Prints call plan, estimated cost, and peak schedule status (no calls/files).
  --live         : Real DeepSeek generation. Requires --live, --confirm, and DEEPSEEK_API_KEY.
  --build-only   : Rebuild pool from an existing raw_responses.jsonl cache without LLM calls.
  --verify       : Validates pool hashes, corpus disjunction, formatting, and provenance.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shlex
import signal
import subprocess
import sys
import time
from typing import Any, Optional, Sequence

# Ensure src/ and repo root are on path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from graph_insertion.graph_representation import embed_text
from graph_insertion.llm import (
    DeepSeekClient,
    LLMResponse,
    MeteredLLMClient,
    resolve_model_alias,
)
from graph_insertion.loader import discover_corpora, load_corpus
from graph_insertion.schedule import format_peak_status, window_intersects_peak

# ===========================================================================
# Constants and Schema Definitions
# ===========================================================================

DEFAULT_TRACKED_OUTPUT = Path("data/synthetic/cs_concept_names.json")
NAME_POOL_PROMPT_VERSION = "np1"
NAME_POOL_PROMPT_VERSION_COMMAND = "np1w"
SCHEMA_VERSION = "1.0"
DOMAIN = "computer science"
DEFAULT_SEED = 42
TARGET_NAMES_DEFAULT = 2600
MIN_REQUIRED_NAMES_FOR_VALIDATION = 2001
MAX_CALLS_DEFAULT = 400

# Estimated token consumption per generation call
EST_INPUT_TOKENS_PER_CALL = 250
EST_OUTPUT_TOKENS_PER_CALL = 450

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

# 80 distinct, curated computer science subfields covering foundational,
# systems, theory, AI/ML, security, and applied domains.
SUBFIELDS: tuple[str, ...] = (
    "algorithms",
    "data_structures",
    "computational_complexity",
    "graph_theory",
    "automata_theory",
    "formal_languages",
    "computational_geometry",
    "combinatorial_optimization",
    "algorithmic_game_theory",
    "cryptography",
    "computer_security",
    "network_security",
    "hardware_security",
    "information_theory",
    "coding_theory",
    "quantum_computing",
    "computer_architecture",
    "microarchitecture",
    "instruction_set_architecture",
    "digital_logic_design",
    "operating_systems",
    "file_systems",
    "memory_management",
    "virtualization",
    "concurrency_and_multithreading",
    "distributed_systems",
    "distributed_consensus",
    "fault_tolerant_computing",
    "cloud_computing",
    "parallel_computing",
    "high_performance_computing",
    "computer_networks",
    "wireless_networking",
    "software_defined_networking",
    "routing_protocols",
    "transport_layer_protocols",
    "database_systems",
    "relational_databases",
    "query_optimization",
    "transaction_processing",
    "nosql_databases",
    "distributed_databases",
    "data_warehousing",
    "stream_processing",
    "compilers",
    "programming_language_theory",
    "type_theory",
    "program_analysis",
    "formal_methods",
    "model_checking",
    "software_engineering",
    "software_testing",
    "software_architecture",
    "design_patterns",
    "requirements_engineering",
    "devops_and_ci_cd",
    "site_reliability_engineering",
    "artificial_intelligence",
    "machine_learning",
    "deep_learning",
    "neural_networks",
    "reinforcement_learning",
    "natural_language_processing",
    "computer_vision",
    "speech_processing",
    "information_retrieval",
    "recommender_systems",
    "knowledge_representation",
    "semantic_web",
    "robotics",
    "motion_planning",
    "human_computer_interaction",
    "user_interface_design",
    "computer_graphics",
    "rendering_techniques",
    "geometric_modeling",
    "image_processing",
    "bioinformatics",
    "computational_biology",
    "numerical_analysis",
)

SYSTEM_PROMPT = (
    "You are a computer science curriculum expert. "
    "When prompted with a computer science subfield, generate a JSON array of core concept names "
    "taught in undergraduate and graduate courses in that subfield.\n"
    "Rules:\n"
    "1. Return ONLY a valid JSON array of strings: [\"concept_one\", \"concept_two\", ...].\n"
    "2. No conversational text, no Markdown code fences, no descriptions, and no numbers.\n"
    "3. Each concept name must be lowercase snake_case (e.g. 'binary_search_tree', 'page_table').\n"
    "4. Each concept name must be 1 to 4 words long.\n"
    "5. Do NOT include file extensions (never end in '.txt').\n"
    "6. Focus on distinct, canonical foundational concepts."
)


# ===========================================================================
# Prompt Construction
# ===========================================================================

def build_system_prompt() -> str:
    """Return the pinned system prompt for concept name generation."""
    return SYSTEM_PROMPT


def build_user_prompt(subfield: str, round_num: int, previous_names: list[str]) -> str:
    """Build the user prompt for a given subfield and round.

    In round 2 and later, lists names already collected for this subfield (capped at 100)
    and explicitly instructs the model not to repeat them.
    """
    human_subfield = subfield.replace("_", " ")
    if round_num == 1 or not previous_names:
        return (
            f"List 40 distinct, specific core concept names taught in a computer science curriculum for the subfield '{human_subfield}'.\n"
            f"Output must be a valid JSON array of 40 lowercase snake_case strings (1-4 words each, no file extensions, concept names only)."
        )

    capped = previous_names[-100:] if len(previous_names) > 100 else previous_names
    prev_json = json.dumps(capped)
    return (
        f"List 40 distinct, specific core concept names taught in a computer science curriculum for the subfield '{human_subfield}'.\n"
        f"Do NOT repeat any of the following {len(capped)} concepts already collected for this subfield:\n"
        f"{prev_json}\n"
        f"Generate 40 NEW, distinct concept names not listed above.\n"
        f"Output must be a valid JSON array of 40 lowercase snake_case strings (1-4 words each, no file extensions, concept names only)."
    )


def build_command_prompt(subfield: str, round_num: int, previous_names: list[str]) -> str:
    """Build single combined prompt for command backend (np1w).

    Combines SYSTEM_PROMPT and user prompt with exactly two newlines.
    """
    user_prompt = build_user_prompt(subfield, round_num, previous_names)
    return f"{SYSTEM_PROMPT}\n\n{user_prompt}"


# ===========================================================================
# Response Parsing & JSON Array Extraction
# ===========================================================================

def parse_json_array_response(raw_text: str) -> list[str]:
    """Parse raw LLM response text into a list of concept name strings.

    Tries strict parsing first. If strict parsing fails with a JSON decode error,
    falls back to extracting the outermost [...] array from the surrounding prose.
    Raises ValueError if response does not parse as a JSON array.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except Exception as exc:
        # Fallback: extract outermost [...] if prose surrounds the array
        start = raw_text.find("[")
        end = raw_text.rfind("]")
        if start != -1 and end != -1 and start < end:
            try:
                candidate = json.loads(raw_text[start : end + 1])
                if isinstance(candidate, list):
                    data = candidate
                else:
                    raise ValueError(f"Failed to parse response as JSON: {exc}") from exc
            except Exception:
                raise ValueError(f"Failed to parse response as JSON: {exc}") from exc
        else:
            raise ValueError(f"Failed to parse response as JSON: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    names: list[str] = []
    for item in data:
        if isinstance(item, str):
            names.append(item.strip())
        elif isinstance(item, dict) and "name" in item and isinstance(item["name"], str):
            names.append(item["name"].strip())
    return names


# ===========================================================================
# Cache Management (raw_responses.jsonl)
# ===========================================================================

@dataclass
class CacheEntry:
    round: int
    subfield: str
    subfield_idx: int
    request_system: str
    request_user: str
    response_text: str
    model_id: str
    token_usage: dict[str, int]
    timestamp_utc: str
    retries: int
    latency_s: float
    parsed_names: list[str]
    backend: str = "deepseek"
    prompt_version: str = "np1"
    backend_meta: Optional[dict[str, Any]] = None


def load_completed_cache(cache_path: Path) -> dict[tuple[int, str], CacheEntry]:
    """Load cached responses from raw_responses.jsonl.

    Tolerates old records without 'backend' or 'prompt_version' by defaulting
    them to 'deepseek' and 'np1'.
    REFUSES a cache mixing backends or prompt versions by raising ValueError.

    A (round, subfield) is complete once a cached response parses as a JSON array;
    otherwise it is skipped and re-requested on rerun.
    """
    completed: dict[tuple[int, str], CacheEntry] = {}
    if not cache_path.exists():
        return completed

    first_backend: Optional[str] = None
    first_prompt_version: Optional[str] = None

    with open(cache_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
            except Exception:
                continue

            r = record.get("round")
            sf = record.get("subfield")
            resp_text = record.get("response_text", "")
            if r is None or sf is None:
                continue

            backend_val = str(record.get("backend") or "deepseek")
            prompt_version_val = str(record.get("prompt_version") or "np1")

            # Validate cache consistency across all records
            if first_backend is None:
                first_backend = backend_val
                first_prompt_version = prompt_version_val
            else:
                if backend_val != first_backend:
                    raise ValueError(
                        f"Cache {cache_path} contains mixed backends: found '{backend_val}' "
                        f"and '{first_backend}' (line {line_no})."
                    )
                if prompt_version_val != first_prompt_version:
                    raise ValueError(
                        f"Cache {cache_path} contains mixed prompt versions: found '{prompt_version_val}' "
                        f"and '{first_prompt_version}' (line {line_no})."
                    )

            try:
                parsed = parse_json_array_response(resp_text)
            except ValueError:
                # Incomplete/unparseable response; re-request on rerun
                continue

            entry = CacheEntry(
                round=int(r),
                subfield=str(sf),
                subfield_idx=int(record.get("subfield_idx", 0)),
                request_system=str(record.get("request_system", "")),
                request_user=str(record.get("request_user", "")),
                response_text=resp_text,
                model_id=str(record.get("model_id", "")),
                token_usage=record.get("token_usage", {}),
                timestamp_utc=str(record.get("timestamp_utc", "")),
                retries=int(record.get("retries", 0)),
                latency_s=float(record.get("latency_s", 0.0)),
                parsed_names=parsed,
                backend=backend_val,
                prompt_version=prompt_version_val,
                backend_meta=record.get("backend_meta"),
            )
            completed[(int(r), str(sf))] = entry
    return completed


def append_cache_record(cache_path: Path, entry: CacheEntry) -> None:
    """Append a raw generation response record to raw_responses.jsonl."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "round": entry.round,
        "subfield": entry.subfield,
        "subfield_idx": entry.subfield_idx,
        "request_system": entry.request_system,
        "request_user": entry.request_user,
        "response_text": entry.response_text,
        "model_id": entry.model_id,
        "token_usage": entry.token_usage,
        "timestamp_utc": entry.timestamp_utc,
        "retries": entry.retries,
        "latency_s": entry.latency_s,
        "backend": entry.backend,
        "prompt_version": entry.prompt_version,
    }
    if entry.backend_meta is not None:
        record["backend_meta"] = entry.backend_meta
    with open(cache_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ===========================================================================
# Benchmark Corpora Discovery & Overlap Check
# ===========================================================================

def load_benchmark_corpus_concepts() -> tuple[set[str], set[str], list[str]]:
    """Discover all benchmark corpora and collect concept names and embed_text forms.

    Does not swallow exceptions during corpus discovery/loading.
    """
    specs = discover_corpora()
    nodes: set[str] = set()
    embed_texts: set[str] = set()
    corpora_names: list[str] = []

    for spec in specs:
        corpus_name = getattr(spec, "name", str(spec))
        corpora_names.append(corpus_name)
        try:
            lc = load_corpus(spec)
            for n in lc.graph.nodes():
                nodes.add(n)
                embed_texts.add(embed_text(n))
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load benchmark corpus {corpus_name!r} during names validation: {exc}"
            ) from exc

    return nodes, embed_texts, sorted(corpora_names)


# ===========================================================================
# Candidate Validation, Deduplication, and Drops
# ===========================================================================

def validate_and_dedupe_candidates(
    entries: list[CacheEntry],
    corpus_nodes: set[str],
    corpus_embed_texts: set[str],
) -> tuple[list[str], int, dict[str, int]]:
    """Deterministically filter, deduplicate, and assemble concept names.

    Evaluates candidates in fixed order: (round, subfield_idx, position in response).
    Tracks drop counts by reason:
      - ends_with_txt
      - invalid_snake_case
      - invalid_length
      - invalid_word_count
      - corpus_overlap_exact
      - corpus_overlap_embed
      - duplicate_exact
      - duplicate_embed
      - plural_pair
    """
    # Sort entries deterministically
    sorted_entries = sorted(entries, key=lambda e: (e.round, e.subfield_idx))

    drop_counts: dict[str, int] = {
        "ends_with_txt": 0,
        "invalid_snake_case": 0,
        "invalid_length": 0,
        "invalid_word_count": 0,
        "corpus_overlap_exact": 0,
        "corpus_overlap_embed": 0,
        "duplicate_exact": 0,
        "duplicate_embed": 0,
        "plural_pair": 0,
    }

    n_raw = 0
    seen_exact: set[str] = set()
    seen_embed: set[str] = set()
    preliminary_names: list[str] = []

    for entry in sorted_entries:
        for candidate in entry.parsed_names:
            n_raw += 1
            cand = candidate.strip()

            if cand.endswith(".txt") or ".txt" in cand:
                drop_counts["ends_with_txt"] += 1
                continue

            if not _SNAKE_CASE_RE.match(cand):
                drop_counts["invalid_snake_case"] += 1
                continue

            if not (3 <= len(cand) <= 50):
                drop_counts["invalid_length"] += 1
                continue

            word_count = len(cand.split("_"))
            if not (1 <= word_count <= 5):
                drop_counts["invalid_word_count"] += 1
                continue

            if cand in corpus_nodes:
                drop_counts["corpus_overlap_exact"] += 1
                continue

            cand_embed = embed_text(cand)
            if cand_embed in corpus_embed_texts:
                drop_counts["corpus_overlap_embed"] += 1
                continue

            if cand in seen_exact:
                drop_counts["duplicate_exact"] += 1
                continue

            if cand_embed in seen_embed:
                drop_counts["duplicate_embed"] += 1
                continue

            seen_exact.add(cand)
            seen_embed.add(cand_embed)
            preliminary_names.append(cand)

    # Filter near-duplicate plural pairs:
    # If X and X+"s" or X+"es" both exist, drop the plural form.
    pool_set = set(preliminary_names)
    filtered_names: list[str] = []
    for name in preliminary_names:
        is_plural = False
        if name.endswith("s") and len(name) > 1 and name[:-1] in pool_set:
            is_plural = True
        elif name.endswith("es") and len(name) > 2 and name[:-2] in pool_set:
            is_plural = True

        if is_plural:
            drop_counts["plural_pair"] += 1
        else:
            filtered_names.append(name)

    return filtered_names, n_raw, drop_counts


# ===========================================================================
# Deterministic Pool Construction
# ===========================================================================

def build_pool_from_cache(
    cache_path: Path,
    output_path: Path,
    *,
    generator_kind: str,
    configured_model: str,
    seed: int = DEFAULT_SEED,
    run_ids: Optional[list[str]] = None,
    allow_fake: bool = False,
) -> dict[str, Any]:
    """Build the final name pool deterministically from raw_responses.jsonl cache."""
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")

    cache = load_completed_cache(cache_path)
    if not cache:
        raise ValueError(f"No valid parsed responses found in cache: {cache_path}")

    corpus_nodes, corpus_embeds, corpora_names = load_benchmark_corpus_concepts()
    valid_names, n_raw, drop_counts = validate_and_dedupe_candidates(
        list(cache.values()), corpus_nodes, corpus_embeds
    )

    # Deterministic seeded shuffle (random.Random(42))
    shuffled_names = list(valid_names)
    rng = random.Random(seed)
    rng.shuffle(shuffled_names)

    # Hashes
    sha256_names = hashlib.sha256("\n".join(shuffled_names).encode("utf-8")).hexdigest()
    raw_bytes = cache_path.read_bytes()
    sha256_raw = hashlib.sha256(raw_bytes).hexdigest()

    # Model IDs and timestamps
    model_ids_seen = sorted({e.model_id for e in cache.values() if e.model_id})
    timestamps = [e.timestamp_utc for e in cache.values() if e.timestamp_utc]
    first_ts = min(timestamps) if timestamps else datetime.now(timezone.utc).isoformat()
    last_ts = max(timestamps) if timestamps else datetime.now(timezone.utc).isoformat()

    all_run_ids = list(run_ids or [cache_path.parent.name])

    sample_entry = next(iter(cache.values()))
    is_command_backend = (sample_entry.backend == "command") or (
        generator_kind == "claude-web-ui-via-prompt-adapter"
    )

    if is_command_backend:
        observed_counts: dict[str, int] = {}
        tier_counts: dict[str, int] = {}
        adapter_vers: set[str] = set()

        req_model: Optional[str] = None
        req_effort: Optional[str] = None
        req_memory = False
        req_web_search = False

        for e in cache.values():
            if e.backend_meta:
                bm = e.backend_meta
                if req_model is None and "model_requested" in bm:
                    req_model = str(bm["model_requested"])
                if req_effort is None and "effort_requested" in bm:
                    req_effort = str(bm["effort_requested"])
                if "memory_requested" in bm:
                    req_memory = bool(bm["memory_requested"])
                if "web_search_requested" in bm:
                    req_web_search = bool(bm["web_search_requested"])

                obs = bm.get("model_observed") or e.model_id
                if obs:
                    observed_counts[str(obs)] = observed_counts.get(str(obs), 0) + 1

                tier = bm.get("tier")
                if tier is not None:
                    t_str = str(tier)
                    tier_counts[t_str] = tier_counts.get(t_str, 0) + 1

                ad = bm.get("adapter")
                if isinstance(ad, dict) and "version" in ad:
                    adapter_vers.add(str(ad["version"]))

        meta: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "domain": DOMAIN,
            "generator": "claude-web-ui-via-prompt-adapter",
            "prompt_version": NAME_POOL_PROMPT_VERSION_COMMAND,
            "requested_model": req_model or configured_model,
            "requested_effort": req_effort or "low",
            "requested_memory": req_memory,
            "requested_web_search": req_web_search,
            "observed_models": observed_counts,
            "tier_histogram": tier_counts,
            "adapter_versions": sorted(adapter_vers),
            "temperature": None,
            "max_tokens": None,
            "parameter_note": "Web UI does not expose temperature or max_tokens controls",
            "run_ids": all_run_ids,
            "first_utc_timestamp": first_ts,
            "last_utc_timestamp": last_ts,
            "n_raw": n_raw,
            "n_valid": len(shuffled_names),
            "drop_counts": drop_counts,
            "seed": seed,
            "sha256_names": sha256_names,
            "sha256_raw_responses": sha256_raw,
            "corpora_checked": corpora_names,
        }
    else:
        meta = {
            "schema_version": SCHEMA_VERSION,
            "domain": DOMAIN,
            "generator": generator_kind,
            "configured_model_alias": configured_model,
            "response_reported_model_ids": model_ids_seen,
            "temperature": 0.7,
            "max_tokens": 1500,
            "prompt_version": NAME_POOL_PROMPT_VERSION,
            "run_ids": all_run_ids,
            "first_utc_timestamp": first_ts,
            "last_utc_timestamp": last_ts,
            "n_raw": n_raw,
            "n_valid": len(shuffled_names),
            "drop_counts": drop_counts,
            "seed": seed,
            "sha256_names": sha256_names,
            "sha256_raw_responses": sha256_raw,
            "corpora_checked": corpora_names,
        }

    result = {
        "meta": meta,
        "names": shuffled_names,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return result


# ===========================================================================
# Offline-Fake Generator
# ===========================================================================

def generate_offline_fake_response(
    subfield: str,
    round_num: int,
) -> tuple[str, LLMResponse]:
    """Deterministically generate 40 synthetic concept names for offline testing."""
    offset = (round_num - 1) * 40
    fake_names = [f"synth_{subfield}_{offset + i:03d}" for i in range(1, 41)]
    resp_text = json.dumps(fake_names)
    resp = LLMResponse(
        text=resp_text,
        input_tokens=EST_INPUT_TOKENS_PER_CALL,
        output_tokens=EST_OUTPUT_TOKENS_PER_CALL,
        latency_s=0.01,
        model_id="fake-deepseek-flash",
        attempts=1,
    )
    return resp_text, resp


# ===========================================================================
# Verification Mode
# ===========================================================================

def verify_pool(
    pool_path: Path,
    cache_path: Optional[Path] = None,
    allow_fake: bool = False,
) -> None:
    """Verify integrity, hashes, provenance, and corpus disjunction of a name pool file.

    Exits 1 on any discrepancy.
    """
    if not pool_path.exists():
        print(f"ERROR: Pool file does not exist: {pool_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(pool_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"ERROR: Failed to parse pool JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, dict) or "names" not in data or "meta" not in data:
        print("ERROR: Pool JSON must contain 'meta' and 'names' keys.", file=sys.stderr)
        sys.exit(1)

    meta = data["meta"]
    names = data["names"]

    if meta.get("generator") == "offline-fake" and not allow_fake:
        print(
            "ERROR: Pool was generated by 'offline-fake' (pass --allow-fake to bypass for tests).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Verify SHA256 of names
    computed_names_sha = hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
    expected_names_sha = meta.get("sha256_names")
    if computed_names_sha != expected_names_sha:
        print(
            f"ERROR: Names SHA256 mismatch! Expected {expected_names_sha}, computed {computed_names_sha}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Verify cache SHA256 if cache exists
    target_cache = cache_path
    if target_cache is None and meta.get("run_ids"):
        candidate = Path("results/datagen") / meta["run_ids"][0] / "raw_responses.jsonl"
        if candidate.exists():
            target_cache = candidate

    if target_cache is not None and target_cache.exists():
        computed_raw_sha = hashlib.sha256(target_cache.read_bytes()).hexdigest()
        expected_raw_sha = meta.get("sha256_raw_responses")
        if computed_raw_sha != expected_raw_sha:
            print(
                f"ERROR: Cache SHA256 mismatch! Expected {expected_raw_sha}, computed {computed_raw_sha}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Check minimum names length
    if len(names) < MIN_REQUIRED_NAMES_FOR_VALIDATION:
        print(
            f"ERROR: Pool contains {len(names)} names, but at least {MIN_REQUIRED_NAMES_FOR_VALIDATION} are required.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check snake_case and formatting
    for idx, name in enumerate(names):
        if not _SNAKE_CASE_RE.match(name):
            print(f"ERROR: Name at index {idx} ({name!r}) is not valid snake_case.", file=sys.stderr)
            sys.exit(1)
        if not (3 <= len(name) <= 50):
            print(f"ERROR: Name at index {idx} ({name!r}) length {len(name)} not in [3, 50].", file=sys.stderr)
            sys.exit(1)
        if ".txt" in name:
            print(f"ERROR: Name at index {idx} ({name!r}) contains '.txt'.", file=sys.stderr)
            sys.exit(1)

    # Check uniqueness
    if len(set(names)) != len(names):
        print("ERROR: Pool contains duplicate names.", file=sys.stderr)
        sys.exit(1)

    # Check plural pairs
    names_set = set(names)
    for name in names:
        if name.endswith("s") and len(name) > 1 and name[:-1] in names_set:
            print(f"ERROR: Plural pair detected in verified pool: ({name[:-1]}, {name})", file=sys.stderr)
            sys.exit(1)
        if name.endswith("es") and len(name) > 2 and name[:-2] in names_set:
            print(f"ERROR: Plural pair detected in verified pool: ({name[:-2]}, {name})", file=sys.stderr)
            sys.exit(1)

    # Check corpus disjunction
    corpus_nodes, corpus_embeds, _ = load_benchmark_corpus_concepts()
    overlap_exact = set(names) & corpus_nodes
    if overlap_exact:
        print(f"ERROR: Pool overlaps with benchmark corpus nodes: {sorted(overlap_exact)[:5]}", file=sys.stderr)
        sys.exit(1)

    names_embeds = {embed_text(n): n for n in names}
    overlap_embed = set(names_embeds.keys()) & corpus_embeds
    if overlap_embed:
        print(f"ERROR: Pool overlaps with benchmark corpus nodes in embed_text form: {sorted(overlap_embed)[:5]}", file=sys.stderr)
        sys.exit(1)

    print(f"Pool verification PASSED: {len(names)} valid names verified against {len(corpus_nodes)} corpus concepts.")


# ===========================================================================
# Backend Seam Abstraction
# ===========================================================================

@dataclass
class GenerationResult:
    text: str
    model_id: str
    token_usage: dict[str, int]
    latency_s: float
    retries: int
    backend_meta: Optional[dict[str, Any]] = None
    ok: bool = True
    error_code: int = 0
    error_message: str = ""
    reset_time: Optional[str] = None


class GenerationBackend:
    def complete(
        self,
        *,
        subfield: str,
        round_num: int,
        previous_names: list[str],
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:
        raise NotImplementedError


class DeepSeekGenerationBackend(GenerationBackend):
    def __init__(self, metered_client: MeteredLLMClient) -> None:
        self.metered_client = metered_client

    def complete(
        self,
        *,
        subfield: str,
        round_num: int,
        previous_names: list[str],
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:
        resp = self.metered_client.complete(system=system_prompt, user=user_prompt)
        return GenerationResult(
            text=resp.text,
            model_id=resp.model_id,
            token_usage={
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "reasoning_tokens": resp.reasoning_tokens,
                "cache_hit_tokens": resp.cache_hit_tokens,
                "cache_miss_tokens": resp.cache_miss_tokens,
            },
            latency_s=resp.latency_s,
            retries=resp.attempts - 1,
            ok=True,
        )


ADAPTER_ERROR_STRING_TO_CODE: dict[str, int] = {
    "bad_request": 2,
    "rate_limit": 10,
    "login_required": 11,
    "timeout": 12,
    "refusal": 13,
    "model_mismatch": 14,
    "other": 1,
}
CONTRACT_ERROR_CODES: set[int] = {1, 2, 10, 11, 12, 13, 14}


def parse_adapter_error(raw_err: Any, proc_returncode: int) -> int:
    """Parse adapter error string or int into contract code, with process exit fallback.

    bad_request -> 2
    rate_limit -> 10
    login_required -> 11
    timeout -> 12
    refusal -> 13
    model_mismatch -> 14
    other or unknown -> 1
    If stdout has no usable "error", fall back to the process exit code when it is
    one of the contract codes ({1, 2, 10, 11, 12, 13, 14}), else 1.
    """
    if isinstance(raw_err, str):
        cleaned = raw_err.strip().lower()
        if not cleaned:
            if proc_returncode in CONTRACT_ERROR_CODES:
                return proc_returncode
            return 1
        if cleaned in ADAPTER_ERROR_STRING_TO_CODE:
            return ADAPTER_ERROR_STRING_TO_CODE[cleaned]
        return 1

    if isinstance(raw_err, (int, float)) and not isinstance(raw_err, bool):
        val = int(raw_err)
        if val in CONTRACT_ERROR_CODES:
            return val
        return 1

    if proc_returncode in CONTRACT_ERROR_CODES:
        return proc_returncode
    return 1


class CommandGenerationBackend(GenerationBackend):
    def __init__(
        self,
        *,
        command: str,
        profile: str,
        model: str = "sonnet",
        effort: Optional[str] = "low",
        timeout_s: int = 300,
        sigterm_wait_s: float = 10.0,
    ) -> None:
        self.command = command
        self.profile = profile
        self.model = model
        self.effort = effort
        self.timeout_s = timeout_s
        self.sigterm_wait_s = sigterm_wait_s

    def complete(
        self,
        *,
        subfield: str,
        round_num: int,
        previous_names: list[str],
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:
        prompt_text = build_command_prompt(subfield, round_num, previous_names)
        payload = {
            "prompt": prompt_text,
            "profile": self.profile,
            "model": self.model,
            "effort": self.effort,
            "thinking": None,
            "web_search": False,
            "memory": False,
            "headless": False,
            "timeout_s": self.timeout_s,
        }
        cmd_args = shlex.split(self.command)
        timeout_limit = self.timeout_s + 60

        try:
            proc = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except Exception as exc:
            return GenerationResult(
                text="",
                model_id=self.model,
                token_usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 0,
                },
                latency_s=0.0,
                retries=0,
                ok=False,
                error_code=1,
                error_message=f"Failed to execute command: {exc}",
                reset_time=None,
            )

        try:
            stdout_text, stderr_text = proc.communicate(
                input=json.dumps(payload),
                timeout=timeout_limit,
            )
        except subprocess.TimeoutExpired:
            pgid = proc.pid
            try:
                os.killpg(pgid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass

            try:
                proc.wait(timeout=self.sigterm_wait_s)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                proc.wait()

            return GenerationResult(
                text="",
                model_id=self.model,
                token_usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 0,
                },
                latency_s=float(timeout_limit),
                retries=0,
                ok=False,
                error_code=12,
                error_message=f"Subprocess timed out after {timeout_limit} seconds",
                reset_time=None,
            )

        stdout_text = stdout_text.strip()
        try:
            resp_json = json.loads(stdout_text)
            if not isinstance(resp_json, dict):
                raise ValueError("Output is not a JSON object")
        except Exception as exc:
            err_code = parse_adapter_error(None, proc.returncode)
            return GenerationResult(
                text="",
                model_id=self.model,
                token_usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 0,
                },
                latency_s=0.0,
                retries=0,
                ok=False,
                error_code=err_code,
                error_message=f"Invalid adapter stdout (not a valid JSON object): {exc}",
                reset_time=None,
            )

        is_ok = bool(resp_json.get("ok")) and (proc.returncode == 0)
        if is_ok:
            model_obs = resp_json.get("model_observed")
            model_req = resp_json.get("model_requested", self.model)
            model_id = str(model_obs or model_req or self.model)
            elapsed = float(resp_json.get("elapsed_s", 0.0))
            backend_meta = {k: v for k, v in resp_json.items() if k != "text"}
            return GenerationResult(
                text=str(resp_json.get("text", "")),
                model_id=model_id,
                token_usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 0,
                },
                latency_s=elapsed,
                retries=0,
                backend_meta=backend_meta,
                ok=True,
            )
        else:
            raw_err = resp_json.get("error")
            err_code = parse_adapter_error(raw_err, proc.returncode)
            err_msg = str(resp_json.get("message", "Adapter reported error"))
            reset_time = resp_json.get("reset_time")
            if reset_time is not None:
                reset_time = str(reset_time)
            return GenerationResult(
                text="",
                model_id=self.model,
                token_usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 0,
                },
                latency_s=float(resp_json.get("elapsed_s", 0.0)),
                retries=0,
                ok=False,
                error_code=err_code,
                error_message=err_msg,
                reset_time=reset_time,
            )


# ===========================================================================
# Generation Loop
# ===========================================================================

def run_generation_loop(
    *,
    mode: str,  # "live" or "offline-fake"
    backend: str = "deepseek",  # "deepseek" or "command"
    output_path: Path,
    cache_path: Path,
    run_id: str,
    target_names: int = TARGET_NAMES_DEFAULT,
    max_calls: int = MAX_CALLS_DEFAULT,
    price_in: float = 0.15,
    price_out: float = 0.60,
    est_seconds_per_call: float = 1.0,
    allow_peak: bool = False,
    model: Optional[str] = None,
    command: Optional[str] = None,
    adapter_profile: Optional[str] = None,
    adapter_model: str = "sonnet",
    adapter_effort: Optional[str] = "low",
    adapter_timeout: int = 300,
    pause_s: float = 3.0,
) -> int:
    """Execute iterative generation across subfields until target_names is reached."""
    configured_model = resolve_model_alias(model) if backend != "command" else adapter_model

    # Check offline-fake output path restriction
    if mode == "offline-fake":
        if output_path.resolve() == DEFAULT_TRACKED_OUTPUT.resolve():
            print(
                f"ERROR: --offline-fake cannot write to default tracked path '{DEFAULT_TRACKED_OUTPUT}'. "
                "Specify an explicit alternate path via --output.",
                file=sys.stderr,
            )
            return 1

    cache = load_completed_cache(cache_path)
    corpus_nodes, corpus_embeds, _ = load_benchmark_corpus_concepts()

    # Pre-flight check on existing cache
    valid_names, _, _ = validate_and_dedupe_candidates(
        list(cache.values()), corpus_nodes, corpus_embeds
    )
    if len(valid_names) >= target_names:
        print(f"Cache already contains {len(valid_names)} valid names (target: {target_names}). Building pool.")
        gen_kind = (
            "offline-fake"
            if mode == "offline-fake"
            else ("claude-web-ui-via-prompt-adapter" if backend == "command" else "deepseek")
        )
        build_pool_from_cache(
            cache_path=cache_path,
            output_path=output_path,
            generator_kind=gen_kind,
            configured_model=configured_model,
            seed=DEFAULT_SEED,
            run_ids=[run_id],
            allow_fake=(mode == "offline-fake"),
        )
        return 0

    # Backend initialization
    gen_backend: Optional[GenerationBackend] = None
    if mode == "live":
        if backend == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                print("ERROR: DEEPSEEK_API_KEY environment variable is required for live generation.", file=sys.stderr)
                return 1
            raw_client = DeepSeekClient(
                api_key=api_key,
                model=configured_model,
                temperature=0.7,
                max_tokens=1500,
            )
            gen_backend = DeepSeekGenerationBackend(MeteredLLMClient(raw_client))
        elif backend == "command":
            if not command:
                print("ERROR: --command is required for command backend live generation.", file=sys.stderr)
                return 1
            if not adapter_profile:
                print("ERROR: --adapter-profile is required for command backend live generation.", file=sys.stderr)
                return 1
            gen_backend = CommandGenerationBackend(
                command=command,
                profile=adapter_profile,
                model=adapter_model,
                effort=adapter_effort,
                timeout_s=adapter_timeout,
            )

    calls_made = 0
    round_num = 1
    consecutive_failures = 0
    system_prompt = build_system_prompt()

    # Track collected names per subfield to pass to round 2+ prompts
    subfield_collected: dict[str, list[str]] = {sf: [] for sf in SUBFIELDS}
    for entry in cache.values():
        subfield_collected[entry.subfield].extend(entry.parsed_names)

    while calls_made < max_calls:
        # Check planned calls for this round
        needed_in_round: list[tuple[int, str]] = []
        for sf_idx, sf in enumerate(SUBFIELDS):
            if (round_num, sf) not in cache:
                needed_in_round.append((sf_idx, sf))

        if not needed_in_round:
            round_num += 1
            continue

        planned_calls_this_round = min(len(needed_in_round), max_calls - calls_made)
        now_utc = datetime.now(timezone.utc)

        if backend == "command" and mode == "live":
            est_seconds = planned_calls_this_round * 20.0
            print(f"\n--- Round {round_num} Pre-Flight (Command Backend) ---")
            print(f"Planned calls:         {planned_calls_this_round}")
            print(f"Estimated duration:    {est_seconds:.1f} s (@ 20s/call)")
            print("Reminder:              'Generate memory from chats' must be OFF on target Claude account.")
        else:
            est_seconds = planned_calls_this_round * est_seconds_per_call
            est_cost = (
                planned_calls_this_round
                * (EST_INPUT_TOKENS_PER_CALL * price_in + EST_OUTPUT_TOKENS_PER_CALL * price_out)
                / 1_000_000
            )
            peak_status_str = format_peak_status(now_utc)
            print(f"\n--- Round {round_num} Pre-Flight ---")
            print(f"Planned calls:         {planned_calls_this_round}")
            print(f"Estimated duration:    {est_seconds:.1f} s")
            print(f"Estimated cost:        ${est_cost:.4f} USD")
            print(f"Peak status:           {peak_status_str}")

            if mode == "live" and backend == "deepseek":
                intersects = window_intersects_peak(now_utc, est_seconds)
                if intersects and not allow_peak:
                    print(
                        "ERROR: Execution window intersects DeepSeek peak pricing hours. "
                        "Schedule during off-peak window or pass '--allow-peak'.",
                        file=sys.stderr,
                    )
                    return 1

        for sf_idx, sf in needed_in_round:
            if calls_made >= max_calls:
                print(f"Reached --max-calls limit ({max_calls}). Stopping generation.")
                break

            user_prompt = build_user_prompt(sf, round_num, subfield_collected[sf])

            if mode == "live":
                assert gen_backend is not None
                if backend == "command":
                    res = gen_backend.complete(
                        subfield=sf,
                        round_num=round_num,
                        previous_names=subfield_collected[sf],
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    )
                    calls_made += 1
                    if not res.ok:
                        if res.error_code == 10:
                            print(f"Rate limit reached (error 10): {res.error_message}", file=sys.stderr)
                            if res.reset_time:
                                print(f"Reset time: {res.reset_time}", file=sys.stderr)
                            return 3
                        elif res.error_code == 11:
                            print(f"Login/challenge required (error 11): {res.error_message}", file=sys.stderr)
                            print(
                                f"Please log in or clear the challenge in profile '{adapter_profile}' and rerun.",
                                file=sys.stderr,
                            )
                            return 4
                        elif res.error_code == 14:
                            print(f"Model mismatch (error 14): {res.error_message}", file=sys.stderr)
                            return 5
                        elif res.error_code == 2:
                            print(f"Bad request (error 2): {res.error_message}", file=sys.stderr)
                            return 1
                        else:
                            # Error codes 12, 13, 1
                            print(
                                f"Warning: Adapter call failed for ({round_num}, {sf}) [error {res.error_code}]: {res.error_message}",
                                file=sys.stderr,
                            )
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                print("ERROR: 3 consecutive failures encountered. Stopping generation.", file=sys.stderr)
                                return 6
                            if pause_s > 0:
                                time.sleep(pause_s)
                            continue
                else:
                    try:
                        res = gen_backend.complete(
                            subfield=sf,
                            round_num=round_num,
                            previous_names=subfield_collected[sf],
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                        )
                    except Exception as exc:
                        print(f"Warning: LLM call failed for ({round_num}, {sf}): {exc}", file=sys.stderr)
                        calls_made += 1
                        continue
                    calls_made += 1
            else:
                resp_text, fake_resp = generate_offline_fake_response(sf, round_num)
                calls_made += 1
                res = GenerationResult(
                    text=resp_text,
                    model_id=fake_resp.model_id,
                    token_usage={
                        "input_tokens": fake_resp.input_tokens,
                        "output_tokens": fake_resp.output_tokens,
                        "reasoning_tokens": fake_resp.reasoning_tokens,
                        "cache_hit_tokens": fake_resp.cache_hit_tokens,
                        "cache_miss_tokens": fake_resp.cache_miss_tokens,
                    },
                    latency_s=fake_resp.latency_s,
                    retries=fake_resp.attempts - 1,
                    ok=True,
                )

            try:
                parsed = parse_json_array_response(res.text)
            except ValueError as err:
                print(f"Warning: Failed to parse JSON array from ({round_num}, {sf}): {err}", file=sys.stderr)
                parsed = []
                if backend == "command" and mode == "live":
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        print("ERROR: 3 consecutive failures encountered. Stopping generation.", file=sys.stderr)
                        return 6

            if parsed:
                consecutive_failures = 0

            rec_backend = "deepseek" if mode == "offline-fake" else backend
            rec_prompt_version = (
                NAME_POOL_PROMPT_VERSION_COMMAND if rec_backend == "command" else NAME_POOL_PROMPT_VERSION
            )

            entry = CacheEntry(
                round=round_num,
                subfield=sf,
                subfield_idx=sf_idx,
                request_system=system_prompt if rec_backend != "command" else "",
                request_user=user_prompt
                if rec_backend != "command"
                else build_command_prompt(sf, round_num, subfield_collected[sf]),
                response_text=res.text,
                model_id=res.model_id,
                token_usage=res.token_usage,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                retries=res.retries,
                latency_s=res.latency_s,
                parsed_names=parsed,
                backend=rec_backend,
                prompt_version=rec_prompt_version,
                backend_meta=res.backend_meta,
            )

            append_cache_record(cache_path, entry)
            if parsed:
                cache[(round_num, sf)] = entry
                subfield_collected[sf].extend(parsed)

            # Check valid names accumulated
            valid_names, _, _ = validate_and_dedupe_candidates(
                list(cache.values()), corpus_nodes, corpus_embeds
            )
            if len(valid_names) >= target_names:
                print(f"Reached target {target_names} valid names ({len(valid_names)} collected).")
                break

            if backend == "command" and mode == "live" and pause_s > 0:
                time.sleep(pause_s)

        # Check stopping condition after round
        valid_names, _, _ = validate_and_dedupe_candidates(
            list(cache.values()), corpus_nodes, corpus_embeds
        )
        if len(valid_names) >= target_names:
            break
        round_num += 1

    print(f"\nGeneration complete. Building final pool into {output_path}...")
    gen_kind = (
        "offline-fake"
        if mode == "offline-fake"
        else ("claude-web-ui-via-prompt-adapter" if backend == "command" else "deepseek")
    )
    build_pool_from_cache(
        cache_path=cache_path,
        output_path=output_path,
        generator_kind=gen_kind,
        configured_model=configured_model,
        seed=DEFAULT_SEED,
        run_ids=[run_id],
        allow_fake=(mode == "offline-fake"),
    )
    return 0


# ===========================================================================
# CLI Parser
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic CS concept-name pool for large-n complexity sweeps."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--offline-fake",
        action="store_true",
        help="Run offline simulation producing synthetic names (requires explicit non-default --output).",
    )
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Run live generation via DeepSeek API (requires --confirm and DEEPSEEK_API_KEY).",
    )
    mode_group.add_argument(
        "--build-only",
        action="store_true",
        help="Rebuild pool from existing cache without making generator calls.",
    )
    mode_group.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing pool file's hashes, format, and corpus disjunction.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan, estimated calls, cost, and peak status; make no calls and create no files.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation required to execute live DeepSeek API generation.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_TRACKED_OUTPUT),
        help=f"Path to output JSON pool (default: {DEFAULT_TRACKED_OUTPUT}).",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=None,
        help="Path to raw_responses.jsonl cache (default: results/datagen/<run_id>/raw_responses.jsonl).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run identifier string (defaults to current UTC timestamp).",
    )
    parser.add_argument(
        "--target-names",
        type=int,
        default=TARGET_NAMES_DEFAULT,
        help=f"Target number of valid names to collect (default: {TARGET_NAMES_DEFAULT}).",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=MAX_CALLS_DEFAULT,
        help=f"Maximum LLM calls across generation session (default: {MAX_CALLS_DEFAULT}).",
    )
    parser.add_argument(
        "--price-in",
        type=float,
        default=0.15,
        help="Input token price in USD per 1M tokens (default: 0.15).",
    )
    parser.add_argument(
        "--price-out",
        type=float,
        default=0.60,
        help="Output token price in USD per 1M tokens (default: 0.60).",
    )
    parser.add_argument(
        "--est-seconds-per-call",
        type=float,
        default=1.0,
        help="Estimated seconds per call for peak window calculation (default: 1.0).",
    )
    parser.add_argument(
        "--allow-peak",
        action="store_true",
        help="Bypass peak-hour execution refusal.",
    )
    parser.add_argument(
        "--allow-fake",
        action="store_true",
        help="Allow verification of an offline-fake generated pool file.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="DeepSeek model alias (defaults to DEEPSEEK_MODEL or 'deepseek-flash').",
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=["deepseek", "command"],
        default="deepseek",
        help="Generation backend: 'deepseek' (default) or 'command' (claude-automator prompt-adapter).",
    )
    parser.add_argument(
        "--command",
        type=str,
        default=None,
        help="Command string for command backend (shlex-split, executed without shell).",
    )
    parser.add_argument(
        "--adapter-profile",
        type=str,
        default=None,
        help="Browser profile name for claude-automator prompt-adapter (required for live command runs).",
    )
    parser.add_argument(
        "--adapter-model",
        type=str,
        default="sonnet",
        help="Model identifier requested for command adapter (default: sonnet).",
    )
    parser.add_argument(
        "--adapter-effort",
        type=str,
        default="low",
        help="Effort tier for command adapter: low, medium, high, extra, max (default: low).",
    )
    parser.add_argument(
        "--adapter-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for adapter conversation (default: 300).",
    )
    parser.add_argument(
        "--pause-s",
        type=float,
        default=3.0,
        help="Pause in seconds between command backend calls (default: 3.0).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    output_path = Path(args.output)
    cache_path = Path(args.cache_file) if args.cache_file else Path(f"results/datagen/{run_id}/raw_responses.jsonl")

    # Verification mode
    if args.verify:
        verify_pool(
            pool_path=output_path,
            cache_path=cache_path if args.cache_file else None,
            allow_fake=args.allow_fake,
        )
        return 0

    # Build-only mode
    if args.build_only:
        cache = load_completed_cache(cache_path)
        sample = next(iter(cache.values())) if cache else None
        backend_kind = sample.backend if sample else args.backend
        gen_kind = (
            "claude-web-ui-via-prompt-adapter"
            if backend_kind == "command"
            else "deepseek"
        )
        configured_model = (
            resolve_model_alias(args.model)
            if backend_kind != "command"
            else args.adapter_model
        )
        print(f"Rebuilding pool from cache: {cache_path} -> {output_path}")
        built = build_pool_from_cache(
            cache_path=cache_path,
            output_path=output_path,
            generator_kind=gen_kind,
            configured_model=configured_model,
            seed=DEFAULT_SEED,
            run_ids=[run_id],
            allow_fake=True,
        )
        from scripts.run_experiment import load_and_validate_names_file

        loaded = load_and_validate_names_file(
            output_path, min_required_names=MIN_REQUIRED_NAMES_FOR_VALIDATION
        )
        assert loaded == built["names"], "Loaded names did not match built names UNCHANGED"
        print(
            f"Pool rebuilt successfully at {output_path} ({len(loaded)} valid names verified UNCHANGED)."
        )
        return 0

    # Dry-run mode
    if args.dry_run:
        now_utc = datetime.now(timezone.utc)
        if args.backend == "command":
            planned = min(len(SUBFIELDS), args.max_calls)
            est_duration = planned * 20.0
            print("=== DATA-005 Concept Name Pool Generator Plan (Dry Run - Command Backend) ===")
            print(f"Subfields count:       {len(SUBFIELDS)}")
            print(f"Target valid names:    {args.target_names}")
            print(f"Max calls cap:         {args.max_calls}")
            print(f"Output path:           {output_path}")
            print(f"Cache file:            {cache_path}")
            print(f"Current UTC time:      {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"Command string:        {args.command or '[not set]'}")
            print(f"Adapter profile:       {args.adapter_profile or '[not set]'}")
            print(f"Adapter model:         {args.adapter_model}")
            print(f"Estimated duration:    {est_duration:.1f} s (@ 20s/call)")
            print("Reminder:              'Generate memory from chats' must be OFF on target Claude account.")
        else:
            est_cost = (
                min(len(SUBFIELDS), args.max_calls)
                * (EST_INPUT_TOKENS_PER_CALL * args.price_in + EST_OUTPUT_TOKENS_PER_CALL * args.price_out)
                / 1_000_000
            )
            print("=== DATA-004 Concept Name Pool Generator Plan (Dry Run) ===")
            print(f"Subfields count:       {len(SUBFIELDS)}")
            print(f"Target valid names:    {args.target_names}")
            print(f"Max calls cap:         {args.max_calls}")
            print(f"Output path:           {output_path}")
            print(f"Cache file:            {cache_path}")
            print(f"Current UTC time:      {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"Peak status:           {format_peak_status(now_utc)}")
            print(f"Estimated round 1 cost: ${est_cost:.4f} USD")
        print("Dry run complete (no API calls made, no files created).")
        return 0

    # Live or offline-fake generation
    if not args.live and not args.offline_fake:
        parser.print_help()
        print("\nERROR: Please specify --offline-fake, --live, --build-only, or --verify.", file=sys.stderr)
        return 1

    if args.live:
        if not args.confirm:
            print("ERROR: Live generation requires explicit '--confirm' flag to proceed.", file=sys.stderr)
            return 1
        if args.backend == "command":
            if not args.command:
                print("ERROR: --command is required for command backend live generation.", file=sys.stderr)
                return 1
            if not args.adapter_profile:
                print("ERROR: --adapter-profile is required for command backend live generation.", file=sys.stderr)
                return 1

    mode = "live" if args.live else "offline-fake"
    return run_generation_loop(
        mode=mode,
        backend=args.backend,
        output_path=output_path,
        cache_path=cache_path,
        run_id=run_id,
        target_names=args.target_names,
        max_calls=args.max_calls,
        price_in=args.price_in,
        price_out=args.price_out,
        est_seconds_per_call=args.est_seconds_per_call,
        allow_peak=args.allow_peak,
        model=args.model,
        command=args.command,
        adapter_profile=args.adapter_profile,
        adapter_model=args.adapter_model,
        adapter_effort=args.adapter_effort,
        adapter_timeout=args.adapter_timeout,
        pause_s=args.pause_s,
    )


if __name__ == "__main__":
    sys.exit(main())
