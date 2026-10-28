# DEMO-001 — Defense demo: one insertion, four strategies (PILOT-001 replay)

Standalone implementation prompt for the local coding agent (Claude Code).
Archive as `docs/prompts/DEMO-001-PROMPT.md`. Written by the APC AI on
2026-10-29 against bundle `apc-bundle-core-20261029-0038` (commit `7dec5e9`).

- **TASK-ID:** `DEMO-001`
- **Reserved decision ID:** `D-99` (see pre-flight P2; if it is already used, STOP and report, do not renumber)
- **Suggested follow-up IDs (not part of this task):** `DEMO-001-R` (independent review, Gemini), `TOOL-002` (bundle-script path defect)
- **Status row:** add under "Presentation track" in `docs/tasks/status.md`, final status `needs-review`

You have no memory of any earlier conversation. This repo is the source of
truth. Where this prompt says something you can check and the repo disagrees,
trust the repo and say so in your report.

---

## 0. Read first, in this order

1. `AGENTS.md` (all of it, especially "Parallel work and worktrees" and the four deliverables)
2. `docs/context/complete-context.md`
3. `docs/context/strategy-interface.md` and `docs/context/data-formats.md`
4. `docs/context/codebase-map.md` — the sections on `strategy.insert_node`, the accuracy-stage trial loop (`run_accuracy_experiment`), `MiniLMEmbedder`, `pin_cpu_threads`, and the invariants list
5. `docs/decisions/decision-log.md` entries D-21, D-23, D-24, D-25, D-28, D-29, D-30, D-33, D-35, D-36, D-37, D-64, D-67, D-72, D-73, D-78
6. `src/graph_insertion/{strategy,decision,llm,scoring,loader,graph_representation,embedding,embedding_minilm,cpu_threads}.py` and `strategies/{registry,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}.py`
7. `scripts/run_experiment.py` (how the harness builds the embedder, the warm-up, the held-out graph, and the metered clients) and `scripts/pilot_dsa_zero_shot.py` (cost formula, pilot artifact layout)

## 1. Goal

Build `scripts/demo_trial.py` (+ `tests/test_demo_trial.py`): an offline,
deterministic terminal demonstration for thesis panelists. It performs ONE real
concept-insertion trial on the DSA corpus (one held-out concept, default
`binary_search_tree`) through all four narrowing strategies, using the
production code paths, and prints staged BEFORE / WHILE / AFTER output.

The LLM decision for every (new concept, candidate) pair is REPLAYED from the
real recorded PILOT-001 call cache. The decision step, graph update and scoring
are the production code. Only the transport is replaced.

### Non-goals (hard)

- No new empirical result. No writes under `results/`. No change to any official artifact.
- No API call, no network access, no API key read, no model download at demo time.
- No HTML, no new deck, no sweep mode, no multi-corpus support, no parameter tuning flags.
- No change to anything under `src/` unless you can show it is unavoidable (then stop and ask Luke; do not just do it).
- Do not fold in the `scripts/apc-bundle.sh` path defect (see §9).

## 2. Pre-flight (do all of these, report each result even when it confirms the assumption)

**P1. Worktree.** The main checkout is expected to be dirty: an uncommitted
exploratory prototype exists, and `docs/context/repo-tree.txt` is modified (a
side effect of the bundle script). Therefore do NOT work in the main checkout.
Run `git worktree list` and `git status --short`, then
`git worktree add ../llm-graph-insertion-complexity-DEMO-001 -b task/DEMO-001`.
Locate the prototype, read it as a reference only, and do not commit it as-is.
Do not stage or revert `docs/context/repo-tree.txt`. Report the prototype's
path and what you did with it.

**P2. Decision ID.** Run `./scripts/manage-decisions.py --next`, and grep
`docs/decisions/decision-log.md` for `D-99`. The APC could not see the log; it
reserved D-99 because D-98 is the highest ID visible in `status.md` and the
context docs. If D-99 is already present, stop and report the conflict.

**P3. Pilot cache facts.** Inspect `results/pilot/20261007_053743Z/raw_calls.jsonl`
and its sibling `summary.json`. Verify and report: line count 812; required
fields on every line (`call_index, new_name, candidate, domain_context,
user_prompt, response_text, raw_token, latency_s, model, input_tokens,
output_tokens, reasoning_tokens, cache_hit_tokens, cache_miss_tokens, attempts,
retry_wait_s`); exactly the 29 x 28 ordered pairs of the DSA corpus, each once;
`user_prompt` unique; every `response_text` parses with `decision.parse_token`;
sums of input tokens (123,872), output tokens (2,035), latency (676.80 s),
cache-hit tokens (0); `summary.json` prompt version `v2`, model
`deepseek-flash`, temperature 0, thinking disabled, 0 retries, 0 parse
failures, 0 transport failures, estimated cost $0.019802. Record the SHA-256 of
`raw_calls.jsonl`. State whether `summary.json` records the system prompt or a
hash of it.

**P4. Prompt reproduction (all 812, not a sample).** For every record, confirm
`PairwiseDecisionStep.build_user_prompt(new_name, candidate, domain_context)`
reproduces `user_prompt` byte for byte, with `domain_context` taken from the
loaded DSA corpus. Also confirm `decision.SYSTEM_PROMPT` is unchanged since the
pilot (for example `git log --format='%h %ad' --since=2026-10-07 -- src/graph_insertion/decision.py`
plus a look at the diff of any hit). The cache stores the user prompt only, so
the system prompt is verified through prompt version v2 and this history check.

**P5. Baseline tests.** Run the full suite before changing anything. Record
the pass/skip counts.

**P6. Offline model load.** With the network unavailable (or
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` set), confirm
`MiniLMEmbedder()` loads from the local cache under the pinned revision and
that `pin_cpu_threads(1)` succeeds. Report how you disabled the network (for
example `unshare -rn`), or say it could not be verified.

**P7. Repo facts to confirm.** DSA corpus: 29 nodes, 54 prerequisite edges,
domain context `"data structures and algorithms"`; whether the DSA gold graph
is transitively reduced (compute with `networkx.transitive_reduction`; the
limitation text in §6.9 assumes it is NOT); how `run_experiment.py` builds its
warm-up and in what order it imports faiss and constructs the embedder
(D-73); which tests already import from `scripts/` and how (reuse that pattern).

**P8. Regenerate the prototype table.** Reproduce the preliminary numbers
below with your implementation (exact match expected for the discrete
quantities; latencies and tokens are recorded values and must match exactly).
Any mismatch is a finding, not something to paper over.

| strategy | shortlist | calls | recorded latency | tokens in/out | cost | shortlist recall | P | R | F1 | TP/FP/FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| brute_force | 28/28 | 28 | 28.39 s | 4291/71 | $0.000686 | 1.000 | .800 | .571 | .667 | 4/1/3 |
| embedding_threshold θ=.6 | 1/28 | 1 | 1.37 s | 153/5 | $0.000026 | .143 | 1.000 | .143 | .250 | 1/0/6 |
| ann_retrieval k=10 ef=128 | 10/28 | 10 | 10.11 s | 1534/32 | $0.000249 | .714 | 1.000 | .571 | .727 | 4/0/3 |
| bounded_bucket 5..10 | 9/28 | 9 | 8.85 s | 1380/21 | $0.000220 | .429 | 1.000 | .143 | .250 | 1/0/6 |

This table is exploratory, not a thesis result. Gold neighbourhood of
`binary_search_tree`: prerequisites recursion, binary_search, tree; dependents
red_black_tree, avl_tree, b_tree, trie (7 incident edges; 28 existing nodes
after removal; 47 remaining edges).

## 3. Design decisions already made (do not reopen; flag only if you find a defect)

1. One held-out node per run. Default `binary_search_tree`. `--node` takes exactly one name.
2. All four strategies run by default, in the fixed order S1, S2, S3, S4. The WHILE block is identical in structure for all four; the narration emphasis (S1 vs S3) is the presenter's choice, not the program's.
3. Call-printing rule (exact): let N be the shortlist size. If N <= 10, print every call, in shortlist order. If N > 10, print the union of (a) the first 3 calls, (b) every call whose token is not `NONE`, (c) the first `NONE` call if one exists, all in shortlist order, then one line `... K NONE decisions not printed (use --show-all-calls)`. `--show-all-calls` prints everything.
4. Tokens and cost are shown per strategy and in the comparison table, with the cost formula shown once.
5. A closing LIMITATIONS box is mandatory and is the "what this does not prove" section.
6. Replay wording is fixed in §6.2.
7. `--json PATH` is included (§7).
8. No pacing sleeps. Never `time.sleep` to imitate model latency.

## 4. Command-line interface

```
python scripts/demo_trial.py [--node NAME] [--strategies LIST] [--pilot-dir DIR]
                             [--no-color] [--ascii] [--pause] [--show-all-calls]
                             [--json PATH] [--check] [--traceback]
```

- `--node NAME` (default `binary_search_tree`): must be a node of the DSA corpus. On a miss, exit 4 and print up to 5 `difflib` close matches.
- `--strategies LIST`: comma-separated subset of `brute_force,embedding_threshold,ann_retrieval,bounded_bucket` (aliases `s1,s2,s3,s4`). Always executed and printed in canonical order. Duplicates or unknown names: exit 2.
- `--pilot-dir DIR` (default `results/pilot/20261007_053743Z`, resolved against the repo root, not the CWD).
- `--no-color`: also honour the `NO_COLOR` environment variable. Colour is used only when stdout is a TTY and neither is set.
- `--ascii`: replace box-drawing characters and arrows with ASCII (`+ - |`, `->`).
- `--pause`: wait for Enter between phases, only when stdin and stdout are both TTYs; otherwise silently ignored.
- `--show-all-calls`: print every decision call.
- `--json PATH`: also write the machine-readable record (§7). Refuse (exit 7) if PATH exists, or if its resolved path is inside `<repo>/results/`, or if its parent directory does not exist.
- `--check`: run provenance + corpus + node + (if needed) embedder-load checks, print one `OK`/`FAIL` line per check, run no trial, exit 0/nonzero.
- `--traceback`: show Python tracebacks on error (off by default).
- No flags for theta, k, ef, s_min, s_max, seeds, repeats or corpus. Parameters are the D-64 defaults, hard-coded, and asserted against `strategy.config()` (§5.4).

Exit codes: 0 ok; 2 usage; 3 pilot cache / provenance failure; 4 corpus or node problem; 5 missing dependency or embedder; 6 internal consistency check failed; 7 refused output path.

## 5. Architecture and behaviour

One file, `scripts/demo_trial.py`, in this order of sections. Pure logic is
importable (guard `main()` with `if __name__ == "__main__"`), because the tests
load it through the same mechanism the repo's other script tests use.

### 5.1 Constants

```python
PILOT_DIR_DEFAULT = "results/pilot/20261007_053743Z"
PILOT_RAW_CALLS_SHA256 = "<fill after P3>"        # fail closed on mismatch
EXPECTED_PROMPT_VERSION = decision.PROMPT_VERSION  # must be "v2"
EXPECTED_CALLS = 812
CORPUS_NAME = "DSA"
DEFAULT_NODE = "binary_search_tree"
SEED = 42
DEMO_PARAMS = {  # D-64 / D-35 / D-55 defaults, asserted against strategy.config()
    "brute_force": {"seed": 42},
    "embedding_threshold": {"theta": 0.6, "seed": 42},
    "ann_retrieval": {"k": 10, "ef_search": 128, ...},   # read the real config() keys
    "bounded_bucket": {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42},
}
# Off-peak prices, USD per 1M tokens ([D-36])
PRICE_IN_CACHE_MISS = 0.15
PRICE_IN_CACHE_HIT  = 0.003
PRICE_OUT           = 0.60
WIDTH = 88
```

Cost formula (show it in the transcript and in the report):

```
cost_usd = (cache_miss_tokens * 0.15 + cache_hit_tokens * 0.003 + output_tokens * 0.60) / 1_000_000
```

PILOT-001 had zero cache hits, so this equals `(input * 0.15 + output * 0.60) / 1e6`,
which is what `pilot_dsa_zero_shot.py` used. Check sanity: S1's 4291 in / 71 out
gives $0.000686. Assert `cache_hit + cache_miss == input_tokens` per record.
Reasoning tokens are 0 (thinking disabled); if any record has nonzero
reasoning tokens, fail closed (exit 3) rather than guess how they were billed.

### 5.2 Replay (fail closed)

```python
class DemoError(Exception):              # carries .exit_code and a one-line .hint
@dataclass(frozen=True) class ReplayRecord: ...        # one per jsonl line, validated types
@dataclass(frozen=True) class PilotProvenance: ...     # path, sha256, recorded_utc, model, prompt_version,
                                                       # n_calls, temperature, thinking, retries, parse_failures,
                                                       # transport_failures, input_tokens, output_tokens,
                                                       # est_cost_usd, cumulative_latency_s
def load_pilot(pilot_dir, *, corpus) -> tuple[PilotProvenance, dict[str, ReplayRecord]]
class ReplayLLMClient:                                 # implements llm.LLMClient
    def complete(self, system: str, user: str) -> LLMResponse
    served: list[ReplayRecord]                         # in call order, for the transcript
```

`load_pilot` must raise `DemoError(exit_code=3)` on ANY of: missing file or
`summary.json`; SHA-256 differs from `PILOT_RAW_CALLS_SHA256`; line count != 812
or != summary `calls`; unparsable JSON line; missing or wrong-typed field;
negative latency or token counts; `cache_hit + cache_miss != input_tokens`;
nonzero reasoning tokens; duplicate `user_prompt`; duplicate `(new_name,
candidate)`; the pair set is not exactly all ordered pairs of the corpus nodes;
`response_text` not accepted by `parse_token`; summary prompt version !=
`EXPECTED_PROMPT_VERSION`; summary model != the per-record model; summary totals
(input/output tokens, cumulative latency to 0.01 s) differ from the recomputed
sums. Every `DemoError` message states what failed and what Luke should do.

`ReplayLLMClient.complete(system, user)` must: (1) require `system ==
decision.SYSTEM_PROMPT`, else `DemoError(3)`; (2) look up `user` by exact string
in the dict, a miss is `DemoError(3)` ("no recorded PILOT-001 answer for this
prompt; the demo never fabricates a decision"); (3) return `LLMResponse(text=
record.response_text, input_tokens, output_tokens, reasoning_tokens,
cache_hit_tokens, cache_miss_tokens, latency_s=record.latency_s,
model_id=record.model, attempts=record.attempts, retry_wait_s=record.retry_wait_s)`;
(4) append the record to `served`. It must never construct `FakeLLMClient` or
`DeepSeekClient`, never import `httpx` for requests, and never read
`DEEPSEEK_API_KEY`. The demo must run with that variable unset and with no network.

### 5.3 Environment preparation (before any heavy import)

- `os.environ.setdefault("HF_HUB_OFFLINE", "1")` and `("TRANSFORMERS_OFFLINE", "1")` before importing `sentence_transformers`, so a missing cache fails fast instead of hanging on a network probe. Do not change `embedding_minilm.py` for this.
- If `ann_retrieval` is selected, import `graph_insertion.strategies.ann_retrieval` (which imports faiss) BEFORE constructing `MiniLMEmbedder` (D-73 import order). If it is not selected, do not import faiss.
- Construct `MiniLMEmbedder()` only when a selected strategy needs it (S2, S3, S4). S1 alone must run with no sentence-transformers and no faiss installed. Then `pin_cpu_threads(1)` (D-72) and record `embedder.identity()` and the pin read-back for the banner.
- Missing package, missing cache, or version/revision pin mismatch: catch, re-raise as `DemoError(5)` naming the missing piece. Never download.
- One warm-up embed of a fixed dummy string before the first timed strategy, mirroring what `run_experiment.py` does (read it and copy the intent), so the first embedding strategy's measured shortlist time is not inflated by lazy initialisation.

### 5.4 One strategy trial (mirror the accuracy-stage loop in `run_experiment.py`)

For each selected strategy name, in canonical order:

1. `G = corpus.graph.without_node(node)` (fresh copy; the gold graph is never mutated). Record `n_before = G.num_nodes()` and `e_before = G.num_edges()`.
2. `strategy = STRATEGY_FACTORIES[name](seed=SEED, **params)`; assert `strategy.config()` contains the `DEMO_PARAMS[name]` values, else `DemoError(6)`.
3. `meter = MeteredEmbedder(shared_raw_embedder)` (a fresh meter over the shared, already-loaded model; fresh strategy per trial). S1 discards the embedder; pass the meter anyway, as the harness does.
4. Time `strategy.setup(G, meter)` with `perf_counter` ([LIVE], excluded from the official trial timer per D-25). Record setup embedding calls from the meter.
5. `gc.collect()`.
6. `llm_meter = MeteredLLMClient(replay)`; `step = PairwiseDecisionStep(llm_meter)`; `snap0 = llm_meter.snapshot()`.
7. `res = insert_node(strategy, G, step, node, metered_embedder=meter)`; `delta = llm_meter.snapshot() - snap0`.
8. `score = score_node_insertion(node=node, gold_graph=corpus.graph, judgments=corpus.judgments, shortlist_candidates=res.shortlist.candidates, decided_edges=res.edges)`.
9. Slice `replay.served` for this strategy's calls. Rebuild the canonical edges from the recorded tokens (`X_PREREQ_Y` -> `(node, cand)`, `Y_PREREQ_X` -> `(cand, node)`) and assert the set equals `res.edges` (`DemoError(6)` otherwise).
10. Collect `strategy.diagnostics()` (already called inside `insert_node`; read `res.metrics.extra`). Print only a short whitelist per strategy (at most 3 keys, chosen from what the module really emits; e.g. S2 `cosine_comparisons`, `max_cosine`; S3 `exact_topk_overlap`; S4 the segment-size fields). Missing keys are skipped silently.

Reuse production code for everything above. Do not reimplement narrowing,
decision interpretation or scoring. The only logic written here is orchestration,
analysis annotations (§5.5) and formatting.

### 5.5 Analysis annotations (demo-side, clearly labelled as annotations, never altering a metric)

- **Edge labels.** Label each predicted edge TP / FP / UNJUDGED by calling `score_node_insertion` on that single edge (`decided_edges=[edge]`) and reading `tp`, `fp`, `excluded_predictions`. Assert the per-edge counts sum to the strategy's full `NodeScore` counts (`DemoError(6)` otherwise). This reuses the production rule instead of copying it.
- **Missed gold edges (FN) with cause.** For each gold incident edge not predicted, with `o` the other endpoint: `not shortlisted` if `o` is not in the shortlist; else `direction reversed` if the reverse edge was predicted; else `judged NONE`. Report the split "lost at narrowing / lost at decision". Assert `len(FN list) == score.fn`.
- **Transitive-closure note for FPs.** For each FP, if the full gold graph (`corpus.graph.nx_graph()`, which contains the held-out node) has a directed path prereq -> dependent, append `(gold path exists: a -> ... -> b)`. This is a note only; it never changes precision. The PROMPT_VERSION v2 system prompt defines "prerequisite" as direct OR indirect, so a transitive prediction is consistent with the prompt even where the sparse gold graph lacks the direct edge.
- **Subset invariant.** If S1 ran: every edge predicted by S2/S3/S4 must be in S1's predicted set, because in replay a pair's decision is a fixed lookup and narrowing only removes pairs. Print `OK` or fail with `DemoError(6)`. This is by construction in replay; in the official live runs each strategy made its own calls, so it need not hold there (say so in the limitations).
- **Two-stage recall decomposition** per strategy: `recall = shortlist_recall x recall_given_shortlist` (print both factors when defined).

### 5.6 Measured vs recorded vs computed tags

Every metric line carries exactly one tag, and the legend appears in the banner:

| tag | meaning |
|---|---|
| `[LIVE]` | measured by this process now: setup time, shortlist time (and its embedding part), update time, replay wall time, total demo wall time |
| `[PILOT]` | recorded in PILOT-001: each answer, per-call latency, tokens, model |
| `[CALC]` | computed from recorded values: cost, totals, percentages of calls |
| `[GOLD]` | ground truth from the corpus, shown only in AFTER |

Never present replay wall time as model latency. "Recorded model latency" is the sum of the PILOT-001 per-call `latency_s` for the calls the strategy made (this is `DecisionOutcome.llm_seconds`).

## 6. Exact output specification

Width is fixed at 88 columns; no line may exceed it (tests enforce this in both
Unicode and `--ascii` mode). Use only single-width glyphs. Colour: tags and
TP/FP/FN words only. The layout below is illustrative; every number is
regenerated at run time. Placeholders in `<angle brackets>`.

### 6.1 Banner and provenance

```
════════════════════════════════════════════════════════════════════════════════════════
 DEFENSE DEMO  ·  one concept insertion, four narrowing strategies        PILOT-001 replay
════════════════════════════════════════════════════════════════════════════════════════
 PROVENANCE
   LLM decisions  REPLAYED from recorded PILOT-001 calls (not re-requested, not simulated)
   Cache file     results/pilot/20261007_053743Z/raw_calls.jsonl
                  812 calls · sha256 <first 12 hex>… · recorded 2026-10-07 05:37:43Z
   Recorded with  deepseek-flash · prompt v2 · temperature 0 · thinking disabled
                  0 retries · 0 parse failures · 0 transport failures
   Run live here  corpus load, narrowing, graph update, scoring, timers tagged [LIVE]
   Embedder       all-MiniLM-L6-v2 rev <first 7 hex> · sentence-transformers 6.1.0 · CPU · 1 thread
   Network / API  none used · no API key read
 TAGS  [LIVE] measured now   [PILOT] recorded 2026-10-07   [CALC] computed   [GOLD] ground truth
```

If S1 only is selected, the Embedder line reads `not loaded (brute_force needs none)`.

### 6.2 Replay notice (exact wording, printed once in the banner block, wrapped to width)

> REPLAY NOTICE. The model answers on screen are real. Each one was returned by deepseek-flash on 2026-10-07 during PILOT-001 for exactly the prompt shown; this program looks up that stored answer instead of calling the API again. Nothing is simulated or invented, and a missing record stops the program. Narrowing, graph updates and scoring run live. Model latency, token counts and cost are the recorded values, not measurements from this run.

### 6.3 PHASE 1 · BEFORE

Content, in this order:

1. **What the thesis measures** (two sentences): how the cost (LLM calls, time) and the accuracy of inserting one new concept into an existing LLM-built prerequisite graph depend on how candidates are narrowed; only the narrowing differs, the LLM decision step is identical.
2. **The trial**: corpus `DSA`; domain context string; full graph `<29> concepts, <54> prerequisite edges`; the held-out NEW concept; existing graph `<28> concepts, <47> edges`; and the line `Gold neighbourhood: HIDDEN until AFTER. Nothing printed before AFTER is marked with it.`
3. **The decision step (identical for every strategy)**: print `decision.SYSTEM_PROMPT` (wrapped), the user-prompt template with `Subject area / Concept X (new) / Concept Y (candidate)`, the three answer tokens, the rule "one call per shortlisted candidate; X_PREREQ_Y -> edge (new -> cand); Y_PREREQ_X -> edge (cand -> new); canonical direction prerequisite -> dependent", and "only names are shown to the model".
4. **The four strategies** with what each narrows by, taking parameter values from `strategy.config()` (build the configs first, without running them):
   - S1 `brute_force`: nothing; every existing concept is judged
   - S2 `embedding_threshold`: keep nodes with cosine(new, node) > theta (strict), names embedded with MiniLM
   - S3 `ann_retrieval`: top-k nearest by cosine through an HNSW index (k, M, efConstruction, efSearch from config)
   - S4 `bounded_bucket`: one size-bounded home bucket of hyperplane-hash codes (s_min..s_max, n_bits from config)
5. **Cost formula** line: `cost = (cache-miss in x $0.15 + cache-hit in x $0.003 + out x $0.60) / 1M  (off-peak, D-36)`.

### 6.4 PHASE 2 · WHILE (one block per strategy)

```
────────────────────────────────────────────────────────────────────────────────────────
 PHASE 2 · WHILE   strategy 3 of 4:  S3  ann_retrieval  (k=10, efSearch=128)
────────────────────────────────────────────────────────────────────────────────────────
  setup     index build over 28 concepts          <41.2 ms> [LIVE]  excluded from official timer
  shortlist <10> of <28> kept (<35.7%>), narrowed away <64.3%>
            time <3.1 ms> [LIVE]  (embedding the new name: <2.9 ms>)
  top candidates by cosine [LIVE]
     1  <0.712>  <candidate>
     ...                                              (all shown when N <= 10, else top 10)
  diagnostics  <exact_topk_overlap = ...>  [LIVE]
  decisions  <10> calls, all shown [PILOT]
   call  1/10  X = <new>   Y = <cand>
               answer <NONE>                         <1.02 s>  <153> in / <5> out
               -> no edge
   call  2/10  X = <new>   Y = <cand>
               answer <Y_PREREQ_X>                   ...
               -> edge  <cand> -> <new>   (prerequisite -> dependent)
   ...
  answers    NONE <6> · X_PREREQ_Y <2> · Y_PREREQ_X <2>          [PILOT]
  LLM        <10> calls · <10.11 s> recorded latency [PILOT] · <1,534> in / <32> out tokens [PILOT]
             cost <$0.000249> [CALC]  ·  calls vs S1: <-64%> [CALC]
  applied    +1 concept, +<4> edges  ->  graph <29> concepts, <51> edges
             update <0.05 ms> [LIVE] · replay wall time <2 ms> [LIVE]
```

Rules:

- The first call printed in the whole transcript also prints the exact `user_prompt` text (3 lines, indented) with the line `exact prompt sent in PILOT-001 [PILOT]`.
- Candidate preview: when `scores` are exposed and not all equal (S2, S3, S4), print rank, cosine to 3 decimals, name; top 10 only, followed by `... and <K> more` when N > 10 (S2 can exceed 10 in principle). S1 prints `all <28> existing concepts, alphabetical, no ranking` (its scores are a uniform 0.0 and must not be shown as similarities) and prints no preview table.
- Empty shortlist (possible for S2): print `shortlist  0 of 28 kept ... no LLM calls, no edges` and skip the decisions/answers lines; LLM line shows `0 calls`.
- Percentages: kept% = size / n_before; narrowed% = 100 - kept%; calls vs S1 = `1 - calls / n_before` (S1 makes exactly n_before calls by construction, so this needs no S1 run). One decimal for kept%/narrowed%, zero decimals for calls vs S1.
- **No gold information anywhere in BEFORE or WHILE**: no `[GOLD]` tag, no hit/miss markers on candidates.
- Names print in their canonical form (underscores) in edges and tables and in the `embed_text` form (spaces) in the `X = ... Y = ...` call lines, because that is what the model saw.

### 6.5 PHASE 3 · AFTER

1. **Reveal** `[GOLD]`: prerequisites of the held-out node and dependents, as names. Also `7 gold incident edges`.
2. **Per strategy**, in order: shortlist captured `<h>/<g>` gold neighbours (`shortlist recall`); predicted edges each labelled `TP` / `FP` / `UNJUDGED` with the §5.5 gold-path note on FPs; missed gold edges `FN` each with its cause; the line `lost at narrowing <a> · lost at decision <b>`; metrics `P <..> R <..> F1 <..>  TP <..> FP <..> FN <..>`; `unjudged predictions excluded: <n>` (when n > 0 also print the sensitivity F1 from `NodeScore.f1_sensitivity`, D-30). Undefined metrics print `n/a` (never 0, never an exception).
3. **Subset invariant** line (§5.5) when S1 ran.
4. **Cross-strategy comparison**, two tables so each fits 88 columns:

```
  WORK                kept   narrowed  calls  vs S1   LLM latency   tokens in/out    cost       shortlist
                                                      [PILOT]       [PILOT]          [CALC]     [LIVE]
  S1 brute_force      28/28     0.0%     28    0%      28.39 s       4,291 / 71     $0.000686      <x> ms
  ...
  ACCURACY            shortlist recall    P      R      F1     TP/FP/FN   lost narrow/decide
  S1 brute_force           1.000        .800   .571   .667     4/1/3          0 / 3
  ...
```

5. **Takeaways (3 to 5)**: generated from computed values by templates with guard conditions, never hard-coded prose about a particular node. Required templates:
   - T1 cost: calls and percentage reduction of each selected narrowing strategy against S1's `n_before` calls.
   - T2 only the shortlist differs: if the subset invariant held, say that every edge S2-S4 predicted was also predicted by brute force because the decision step is identical, so any difference comes from which pairs were sent to the model.
   - T3 narrowing's price: shortlist recall per strategy and how many gold edges were lost before the model saw them.
   - T4 (only if some narrowing strategy has F1 > S1's F1 and S1 ran): name that strategy and say its F1 is higher because it never judged <m> pairs that S1 turned into false positives; else print `On this node no narrowing strategy beat brute-force F1.`
   - T5 (static): `One node is an illustration. The thesis evidence is the full runs (RQ1-RQ3), not this transcript.`
6. **LIMITATIONS box** (always last, never omitted, includes `--strategies` subsets):
   - Decisions are replayed from PILOT-001 recordings, not re-requested; this is real model output for exactly these prompts, from 2026-10-07.
   - One held-out node, one trial, one repeat. This is an illustration, not a new result, and it is not part of Chapter 4.
   - Latency, tokens and cost are recorded values; only setup, shortlist, update and replay times are measured now, and replay wall time says nothing about model latency.
   - In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a pair. In the official runs each strategy made its own live calls, so agreement on a pair is not guaranteed there.
   - DSA gold is not transitively reduced (confirm in P7; reword if false), so some false positives may be defensible by transitive closure; metrics are computed against the gold as given.
   - Strategy parameters are the pre-fixed defaults (D-64); nothing was tuned on this node.
7. Footer: `demo wall time <x.x s> [LIVE]` and `no files written to results/`.

### 6.6 Terminal behaviour

Plain/piped output must work: no ANSI when not a TTY or when `--no-color` / `NO_COLOR`; `--ascii` swaps glyphs. A broken pipe (`| head`) must not print a traceback. Runtime target: total under about 30 s including model load, ideally under 15 s on Luke's machine; report the measured time.

## 7. `--json PATH` record

Written once at the end, from the same in-memory `DemoReport` the formatter uses
(so the transcript and JSON cannot diverge). UTF-8, `indent=2`, sorted keys off
(stable insertion order). Top level:

```
{ "schema": "demo-trial-1",
  "run": {"started_utc": ..., "wall_s_live": ..., "argv": [...]},          # volatile block
  "provenance": {pilot fields, sha256, embedder identity, cpu_threads},
  "trial": {"corpus", "node", "domain_context", "n_before", "e_before", "gold": {...}},
  "decision_step": {"prompt_version", "system_prompt_sha256", "price_per_m": {...}},
  "strategies": [ { "name", "config", "setup_s_live", "shortlist": {...,"shortlist_s_live","embed_s_live"},
                    "calls": [ {"x","y","token","edge","latency_s_pilot","input_tokens","output_tokens"} ],
                    "recorded": {"llm_calls","latency_s","input_tokens","output_tokens"},
                    "calc": {"cost_usd","calls_vs_s1_pct","kept_pct"},
                    "applied": {"nodes_added","edges_added","update_s_live"},
                    "score": {NodeScore fields}, "labelled_edges": [...], "missed": [...] } ],
  "comparison": {...}, "invariants": {"subset_of_s1": true|false|null} }
```

Everything under `run` and every key ending `_live` is volatile; everything else must be byte-identical across repeated runs (this is what the determinism acceptance test diffs).

## 8. Tests (`tests/test_demo_trial.py`)

No network, no API key. Replay-client and formatter tests must not import MiniLM or faiss. Use the repo's existing pattern for importing from `scripts/`.

Required groups:

1. **Replay loader/client** on a tiny synthetic cache written to `tmp_path` (with a `summary.json`): happy path; recorded latency/tokens/text returned verbatim; miss raises `DemoError(3)` with no fallback; wrong system prompt; wrong prompt version; line count vs summary mismatch; malformed JSON line; missing field; wrong type; negative latency; hit+miss != input; nonzero reasoning tokens; duplicate `user_prompt`; duplicate pair; pair set not equal to all ordered pairs; invalid `response_text`; tampered SHA-256 (use a patched pin); summary totals mismatch. Also: `FakeLLMClient` and `DeepSeekClient` are never constructed (monkeypatch both to raise), `socket` is blocked (monkeypatch), and the test runs with `DEEPSEEK_API_KEY` removed.
2. **Cost**: formula with and without cache hits; S1 example 4291/71 -> $0.000686 (to 6 dp).
3. **Orchestration with `FakeEmbedder`** (deterministic, no MiniLM): build a synthetic cache on the fly keyed by `PairwiseDecisionStep.build_user_prompt` over a small synthetic corpus, run all four strategies, and assert: production `insert_node` and `score_node_insertion` were used (spy), canonical edges rebuilt from tokens equal `res.edges`, the gold graph object is unchanged, the subset invariant holds, edge-label sums equal `NodeScore`, FN causes sum to `score.fn`. A test that deliberately breaks an edge (monkeypatched) makes `DemoError(6)` fire.
4. **Formatter** on a hand-built `DemoReport`: every line <= 88 columns in Unicode and `--ascii`; no `\x1b` when colour is off; the call-printing rule for N = 28, 10, 11, 1, 0 (exact counts and the `K NONE decisions not printed` line); `--show-all-calls`; empty shortlist wording; S1 prints no similarity table; percentages; `n/a` for undefined metrics; every metric line has exactly one tag; takeaway guards (T4 present only when its condition holds; T2 absent when the invariant is false or S1 did not run); the banner contains the PILOT-001 path, 812, `v2`, the model, and the replay notice verbatim; **gold-leak test**: nothing before the AFTER header contains the `[GOLD]` tag or any hit/miss marker.
5. **CLI**: `--strategies` parsing, ordering, duplicates and unknown names -> exit 2; unknown `--node` -> exit 4 with suggestions; `--json` to an existing file or under `results/` -> exit 7 and nothing written; `--check` runs no trial; broken pipe handling.
6. **MiniLM integration** (skip with a clear reason when sentence-transformers, faiss, the cached model or `results/pilot/...` is absent): run `binary_search_tree` for all four strategies and assert shortlist sizes 28/1/10/9, LLM calls 28/1/10/9, TP/FP/FN `4/1/3`, `1/0/6`, `4/0/3`, `1/0/6` (only if P8 reproduced them), and that two consecutive runs give identical non-volatile JSON.
7. **Real-cache provenance** (skip when the file is absent): the actual PILOT-001 cache passes `load_pilot` and covers all 812 pairs.

## 9. Out of scope, flagged

`scripts/apc-bundle.sh` profiles `presentation` and `full` exit 1 because they
reference `docs/presentation/script/Defense_Script_and_Background_Guide.md` (and
a comprehensive version) that do not exist; the real files are under
`docs/presentation/information/`. Do not fix it here. Confirm the defect in one
line of your report (command and exit code) and leave it for a separate `TOOL-002`.

## 10. Verification steps after the build (report all)

V1. Full test suite: before/after counts, new tests only add.
V2. Acceptance run: `python scripts/demo_trial.py` on a TTY and piped to a file; wall time (cold and warm), transcript attached or excerpted.
V3. Network-off run (§P6 method) of the full demo.
V4. Determinism: run twice with `--json`, diff the non-volatile fields.
V5. Official artifacts untouched: `sha256sum results/pilot/20261007_053743Z/raw_calls.jsonl` before and after; `git status --short results/` clean; no new files under `results/`.
V6. P8 table reproduced (or each discrepancy listed).
V7. **Survey (verification only, not part of the deliverable script, no sweep mode added):** with a shell loop over all 29 DSA nodes, run the finished script with `--json` into a directory OUTSIDE the repo (for example `$TMPDIR`), then tabulate per node: gold degree, calls, shortlist recall and F1 for each strategy. Report where `binary_search_tree` sits (rank of F1(S3) - F1(S1)), and name (a) a node where brute force clearly beats S3 and (b) a node where S2 returns an empty shortlist. These are for Luke's choice of a Q&A "counter-node"; nothing from the survey is committed.
V8. **Cross-check against the accuracy stage (read-only):** for the held-out node and each strategy, compare the replayed TP/FP/FN, `llm_calls` and shortlist hits with the matching record in `results/accuracy_<strategy...>/raw.jsonl` when one exists (those files hold scores, not edges). Report matches and mismatches; a mismatch is informative (the official runs made their own live calls) and must be explained, not hidden.

V9. Confirm the transitive-reduction fact (P7) and the real `diagnostics()` keys you whitelisted.

## 11. Deliverables (AGENTS.md "After finishing any task")

1. Commit on `task/DEMO-001`: `feat(DEMO-001): offline PILOT-001 replay defense demo`. Commit only files you created/edited for this task (never `docs/context/repo-tree.txt`, never the prototype). List any untracked file in the report.
2. Patch: `mkdir -p patch && git diff HEAD~1 > patch/DEMO-001-claude-code-defense-demo-trial.patch`.
3. Report: `docs/reports/DEMO-001-claude-code-defense-demo-trial.md`, using the outline in §12. Diffs pasted from `git diff` in the worktree with index lines, never retyped.
4. `docs/tasks/status.md`: add the DEMO-001 row under "Presentation track", status `needs-review`, with the report link (re-read the file immediately before editing; edit only your row).
5. `docs/decisions/decision-log.md`: append **D-99** (re-read the file first). Content: the demo is replay-only and fail-closed; the cache SHA-256 pin; the tag semantics (`[LIVE]/[PILOT]/[CALC]/[GOLD]`); the HF offline environment settings; the subset invariant and why it holds only in replay; that nothing here is an empirical result; the files added. Use the format of neighbouring entries.
6. Validate: `./scripts/validate-report.py docs/reports/DEMO-001-claude-code-defense-demo-trial.md --require-patch` must pass.
7. Do not merge, rebase, or delete the worktree. State the branch name and worktree path in the report.
8. Update `scripts/README.md` with a short "Defense demo" section (command, flags, exit codes). No other doc edits unless a discrepancy forces one (then say so).
9. Build a fresh bundle only if Luke asks; the new files are not in any bundle profile.

## 12. Report outline (this is what Luke will hand back to the APC)

1. Executive summary (3 to 6 lines: what exists, how to run it, runtime, whether P8 reproduced).
2. Pre-flight results P1-P8 (one line each, with the actual numbers).
3. Implementation summary (module sections, how production code is reused, what is new).
4. Output transcript (full, `--no-color`) for the default run.
5. Verification V1-V9 with evidence.
6. Discrepancies and findings (anything the prompt or the bundle got wrong; the prototype's fate; the bundle-script defect confirmation).
7. Decision D-99 text.
8. Test list and counts.
9. Unified diff and patch file reference.
10. Items for the APC: suggested counter-node, anything Luke must decide, follow-ups (`DEMO-001-R`, `TOOL-002`).

## 13. Acceptance criteria

- AC1 Default command runs offline, no API key, no network, exit 0, under about 30 s.
- AC2 All 812 prompts reproduced byte-exact; cache validated and SHA-pinned; any defect fails closed with the right exit code.
- AC3 Production code paths used for load, strategies, `insert_node`, `PairwiseDecisionStep`, `MeteredLLMClient`, scoring; no narrowing or scoring logic reimplemented.
- AC4 The §6 layout is implemented: all three phases, the tags, the fixed replay notice, the LIMITATIONS box; no gold information before AFTER.
- AC5 Call-printing rule, percentages, cost formula, `n/a` handling and empty-shortlist handling exactly as specified.
- AC6 P8 table reproduced or discrepancies explained.
- AC7 Deterministic non-volatile JSON across two runs.
- AC8 No writes under `results/`; official artifacts byte-identical before/after.
- AC9 New tests pass without network; MiniLM/faiss tests skip cleanly when unavailable; the full suite has no new failures.
- AC10 All four AGENTS.md deliverables plus D-99, status row, report validation, and a README section.

## 14. Stop conditions (stop and report instead of improvising)

D-99 already used; the cache does not match P3/P4; `SYSTEM_PROMPT` changed since the pilot; a production change in `src/` seems unavoidable; MiniLM cannot load offline; P8 numbers differ materially; the worktree cannot be created cleanly.
