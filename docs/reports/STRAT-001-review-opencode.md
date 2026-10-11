# STRAT-001-R — Independent Review of Strategy 1 (BruteForceStrategy)

Reviewer task: STRAT-001-R (independent review of STRAT-001).
Reviewer agent: `opencode`.
Written: 2026-10-09.
Read-only review. No source, tests, `decision-log.md`, or `status.md` were modified.
The only file created in the checkout is this report.

## 1. Agent identity

- **Agent:** `opencode`
- **Model label (exactly as my tool displays it):** `big-pickle` (exact model ID `opencode/big-pickle`).
- **I am NOT Gemini.** I did not implement STRAT-001. The implementer report
  (`docs/reports/STRAT-001-gemini-brute-force.md`) is treated below strictly as
  a set of claims to check, not as evidence.

## 2. Verdict

**ACCEPT WITH NOTES.**

The three most important reasons:

1. The implementation matches the Section 2 specification line-for-line: exact
   `name = "brute_force"` class attribute, `uses_embeddings = False`,
   `_embedder` never assigned a non-`None` value, sorted candidates after the
   `!= new_name` filter, plain-float `0.0` scores, no module-level state,
   `max_candidates = max(0, n)` callable before `setup()`, and
   `diagnostics() == {"candidate_count": int}`.
2. All requested behavioural checks reproduce: 22 passed / 1 skipped for the
   new file (the skip is the non-embedding branch of
   `test_embedder_identity_stored_on_strategy`), the offline harness emits
   `llm_calls == shortlist_size == n_before == size`, `embedding_calls == 0`,
   `embed_s == 0.0`, `extra == {"candidate_count": size}`, and the real
   pre-flight guard computes exactly 38,500 for the D-35 matrix.
3. No blocker. The only substantive note is a **test-coverage gap**: a mutated
   strategy that caches graph nodes in a private list and keeps it in sync via
   `on_inserted` **survives** the test file (mutation 8). The contract and
   D-45(4) claim the strategy "reads the live `ConceptGraph` without cached
   copies or indexes"; the tests do not actually enforce that claim. The
   shipped implementation is correct; the guard is what is missing.

## 3. Findings table

| ID | Severity | file:line | Evidence | Suggested change (NOT applied) |
| :-- | :-- | :-- | :-- | :-- |
| F1 | should-fix | `tests/test_brute_force_strategy.py` (whole file); impl at `src/graph_insertion/strategies/brute_force.py:80` | Mutation 8 (private node list kept in sync via `on_inserted`, `shortlist` reads the list instead of the graph) **SURVIVED** the full test file (22 passed, 1 skipped). No test mutates the graph directly after `setup()` to prove `shortlist()` reads it live. | Add a test that builds the strategy, then calls `graph.add_node(...)` directly (without `on_inserted`) and asserts the next `shortlist()` includes the newly-added node; and/or a test that removes a node and asserts it disappears. This directly guards the D-45(4) "stateless, no cached copies" claim. |
| F2 | nit | `tests/test_brute_force_strategy.py:290-296` | The harness smoke test asserts only `status`, `strategy`, `llm_calls`, `shortlist_size`, `embedding_calls`. The null-strategy analogue (`tests/test_null_strategy.py:810-818`) additionally asserts `n_before == size`, `embed_s == 0.0`, and `total_s >= 0.0`. | Mirror the null-strategy assertions (`n_before`, `embed_s`, `embedding_calls_in_update`, `extra == {"candidate_count": n}`). Low value since check F covers this externally, but it is cheap and closes the gap in-repo. |
| F3 | nit | `tests/test_brute_force_strategy.py:99-108` | `test_shortlist_excludes_new_name_even_if_already_in_graph` calls `shortlist("beta")` with `beta` already in the graph. `insert_node` raises `ValueError` when `graph.has_node(new_name)` (`strategy.py:261-262`), so this state is unreachable through the real driver. Harmless defensive coverage, but the test name implies a supported lifecycle state that the driver forbids. | Optionally rename/comment to make clear it exercises the strategy's standalone defensive path, not a reachable driver state. No code change needed. |

No blockers.

## 4. Checks A–J (verbatim command output)

### A. Artifact integrity

```
$ sha256sum src/graph_insertion/strategies/brute_force.py tests/test_brute_force_strategy.py
a0d57c3cbcc95b73f27f8a198bfd74c991a0403cd7ffce9e9a9bfeb128327eee  src/graph_insertion/strategies/brute_force.py
9c687207e144d2220efe6ed20d2773a7ccd6d631ede55576723ea731040a064d  tests/test_brute_force_strategy.py

$ wc -l src/graph_insertion/strategies/brute_force.py tests/test_brute_force_strategy.py
  102 src/graph_insertion/strategies/brute_force.py
  296 tests/test_brute_force_strategy.py
  398 total
```

Both hashes and both line counts **match the patch the APC reviewed exactly**.
The files did not change after that patch.

```
$ git status --short
(empty)

$ git worktree list
/home/lukexodus/projects/llm-graph-insertion-complexity 8418e00 [master]
```

**At the start of this review the working tree was clean and there was a
single worktree.** (During the review, a concurrent thread began modifying
STRAT-002 files — see Section 7.1 — so a re-run of `git status` now shows
`M src/graph_insertion/strategies/embedding_threshold.py` and
`M tests/test_embedding_threshold_strategy.py`; neither is mine and neither
relates to STRAT-001.) The prompt's Section 1 rule 2 ("Two threads share this
checkout; other uncommitted changes (FIX-010, FIX-011, STRAT-002) are expected")
is **stale** — see Section 6.
Because the tree is clean, the "modified by STRAT-001" question is answered
from the STRAT-001 commit itself:

```
$ git show --name-only defd2ed | tail -6
docs/decisions/decision-log.md
docs/reports/STRAT-001-gemini-brute-force.md
docs/tasks/status.md
src/graph_insertion/strategies/brute_force.py
tests/test_brute_force_strategy.py
```

`defd2ed` ("STRAT-001: Strategy 1 brute-force candidate narrowing (D-45)")
touches only the allowed files. Nothing in `harness.py`, `llm.py`,
`__init__.py`, `strategy.py`, `embedding.py`, `graph_representation.py`,
`strategies/null.py`, `scripts/*`, `tests/test_strategy_interface.py`, or
`pyproject.toml` was touched by STRAT-001. FIX-010, FIX-011, and STRAT-002 are
now separate commits (`74ed0ee`, `ccbb3ca`, `6abe13c`) with their own reports
(`FIX-010-gemini-resume-estimate-unification.md`,
`FIX-011-claude-code-command-backend-error-codes.md`,
`STRAT-002-gemini-embedding-threshold.md`).

### B. Code review against Section 2

Read `brute_force.py:1-102` line by line. Every Section 2 requirement holds:

- `name: str = "brute_force"` and `uses_embeddings: bool = False` are **class**
  attributes (`brute_force.py:54-55`).
- `__init__(seed=42)` sets `self.seed`, `self._graph = None`,
  `self._embedder = None`, `self._last_candidate_count = 0`
  (`brute_force.py:57-61`).
- `_embedder` is assigned only `None`, in `__init__` (`:60`) and `setup`
  (`:70`). Grep confirms no other assignment: see below.
- `setup` stores the graph and discards the embedder (`:69-70`).
- `shortlist` raises `RuntimeError` when `self._graph is None` (`:77-78`),
  then `candidates = tuple(sorted(n for n in self._graph.nodes() if n != new_name))`
  (`:80`) — `sorted()` is applied **after** the `!= new_name` filter, on a live
  read of the graph, with no copy or index.
- `scores = tuple(0.0 for _ in candidates)` — plain Python floats (`:81`).
- Empty graph → `Shortlist(candidates=(), scores=())` (`:83`).
- `on_inserted` is a no-op body (`:85-86`).
- `max_candidates(n) = max(0, n_existing)` (`:94`), independent of `setup()`.
- `config() == {"seed": self.seed}` (`:98`); `diagnostics()` returns
  `{"candidate_count": self._last_candidate_count}` (`:102`).
- No module-level state: the only module-level statements are the docstring,
  `from __future__ import annotations`, `from typing import ...`, two
  `graph_insertion` imports, and the class (`grep -n "^[^ #\"'\t]"` output
  below).
- No embeddings, no LLM calls, no randomness, no graph mutation, no I/O.

```
$ grep -n "_embedder" src/graph_insertion/strategies/brute_force.py
20:            _embedder stays None, zero embedding activity during setup, shortlist,
60:        self._embedder: Any = None
67:        self._embedder remains None so insert_node's identity check is bypassed.
70:        self._embedder = None

$ grep -n "^[^ #\"'\t]" src/graph_insertion/strategies/brute_force.py
2:strategies/brute_force.py — STRAT-001
3:=====================================
4:BruteForceStrategy: brute-force candidate-narrowing strategy.
6:Purpose:
13:Decisions:
26:Implementation Details:
33:from __future__ import annotations
35:from typing import Any, Optional
37:from graph_insertion.graph_representation import ConceptGraph
38:from graph_insertion.strategy import Shortlist
41:class BruteForceStrategy:
```

### C. Run the tests

```
$ python -m pytest -q tests/test_brute_force_strategy.py | tail -3
tests/test_brute_force_strategy.py .......s...............               [100%]

======================== 22 passed, 1 skipped in 2.90s =========================
```

This **matches** the implementer's reported `22 passed, 1 skipped`. The skip:

```
$ python -m pytest -q tests/test_brute_force_strategy.py -rs | tail -3
SKIPPED [1] tests/test_strategy_interface.py:397: Non-embedding strategy: _embedder is None by design
======================== 22 passed, 1 skipped in 2.55s =========================
```

The skipped test is `StrategyConformanceSuite::test_embedder_identity_stored_on_strategy`
(`test_strategy_interface.py:384-415`), skipped at line 397 because
`uses_embeddings = False`. This is the expected non-embedding bypass.

```
$ python -m pytest -q | tail -3
.....                                                                    [100%]

================== 365 passed, 3 skipped in 80.10s (0:01:20) ===================
```

The full-suite count **differs** from the implementer's `322 passed, 3 skipped`
because STRAT-002 (`6abe13c`) and DATA-006 (`8418e00`) added test modules after
STRAT-001 (`defd2ed`). No failures, no errors: I caused none.

### D. Mutation check

Copied `src/`, `tests/`, and `pyproject.toml` to `/tmp/strat001-mut` and
mutated the copy's `brute_force.py` one mutation at a time, running
`python -m pytest -q tests/test_brute_force_strategy.py` in the copy
(`PYTHONPATH`/pytest `pythonpath=src` resolves to the copy; verified
`graph_insertion.__file__` == `/tmp/strat001-mut/src/graph_insertion/__init__.py`).
Baseline in the copy: 22 passed, 1 skipped.

```
=== summary ===
M1_delete_sorted	KILLED	20 passed, 1 skipped; 2 failed
M2_drop_filter	KILLED	21 passed, 1 skipped; 1 failed
M3_max_candidates_n_minus_1	KILLED	15 passed, 1 skipped; 7 failed
M4_setup_stores_embedder	KILLED	21 passed, 1 skipped; 1 failed
M5_no_raise_before_setup	KILLED	21 passed, 1 skipped; 1 failed
M6_scores_none	KILLED	17 passed, 1 skipped; 5 failed
M7_diagnostics_zero	KILLED	21 passed, 1 skipped; 1 failed
M8_private_list_instead_of_graph	SURVIVED	(22 passed, 1 skipped)
```

See Section 5 for the failing test names.

**Mutation 1 note.** `ConceptGraph.nodes()` returns `self._g.nodes()`
(`graph_representation.py:166-168`), i.e. a NetworkX `NodeView` iterated in
**insertion order** (Python dict order), not sorted and not hash-order.
Mutation 1 (delete `sorted(...)`) is therefore **KILLED**, by
`test_shortlist_order_independent_of_graph_insertion_order` and
`test_shortlist_all_nodes_sorted_ascending_and_scores_zero`. This means the
`sorted()` call is genuinely load-bearing: the module docstring
(`brute_force.py:27-28`) and D-45(2) claim it guarantees determinism
"independent of graph node insertion order and `PYTHONHASHSEED`", and the test
suite substantiates that claim. (Deleting `sorted()` does not survive because
two graphs with different insertion orders produce different candidate tuples.)

### E. Contract faithfulness of the test doubles

- `FakeDecisionStep` (`test_strategy_interface.py:109-140`) implements the
  `DecisionStep` protocol signature `decide(new_name, candidates, domain_context=None)`
  and returns `llm_calls=len(candidates)` — the same accounting the real step
  returns. It makes zero real LLM calls, but `insert_node` reads only
  `outcome.llm_calls`, so the driver tests are faithful at the metric level.
- The harness smoke test does **not** use `FakeDecisionStep`. It uses
  `make_fake_decision_step()` (`test_brute_force_strategy.py:52-55`) =
  `PairwiseDecisionStep(MeteredLLMClient(FakeLLMClient()))`, i.e. the **real**
  `PairwiseDecisionStep`.
- Faithfulness confirmed from `decision.py`: `decide()` loops over every
  candidate and calls `self.llm_client.complete(...)` once per candidate
  (`decision.py:128-130`) and returns `llm_calls=len(candidates)`
  (`decision.py:155`). `MeteredLLMClient.complete` increments `self.calls` once
  per real call (`llm.py:212`).
- The check is therefore real, not a fake artifact. Independent confirmation
  from my end-to-end run (F): the size-200 record's
  `llm_snapshot_delta.calls == 200`, matching `metrics.llm_calls == 200`.

No stub contradicts the real contract. The FIX-009/FIX-002 failure mode
(tests passing against a stub that disagrees with the real contract) was not
found here.

### F. End-to-end through the real harness

Scratch script `/tmp/strat001_e2e.py`, `run_sweep_experiment` offline,
`BruteForceStrategy`, placeholder names, sizes `(50, 100, 200)`, 2 trials each
(mirroring `tests/test_null_strategy.py::TestNullStrategySweepFullMatrix`):

```
run result: {'status': 'completed', 'run_id': 'strat001_e2e', 'output_dir': '/tmp/strat001-e2e-out'}
record count: 6
problems: NONE
numpy types in metrics: NONE
files: ['manifest.json', 'raw.jsonl', 'summary.csv']
ALL CHECKS PASSED
```

Every one of the 6 records satisfied `status == "success"`,
`strategy == "brute_force"`,
`metrics.llm_calls == metrics.shortlist_size == metrics.n_before == size`,
`metrics.embedding_calls == 0`, `metrics.embed_s == 0.0`, and
`metrics.extra == {"candidate_count": size}`. `json.dumps(rec)` succeeded for
every record and no value in `metrics` is a `numpy.generic`; the written
`raw.jsonl`/`summary.csv` serialise cleanly.

Representative record (size 200):

```json
{"key": "sweep:brute_force:200:t0", "run_id": "strat001_e2e", "status": "success",
 "strategy": "brute_force", "size": 200, "trial": 0,
 "metrics": {"n_before": 200, "shortlist_size": 200, "llm_calls": 200,
   "embedding_calls": 0, "embed_s": 0.0,
   "embedding_calls_in_update": 0, "embed_in_update_s": 0.0,
   "extra": {"candidate_count": 200}},
 "llm_snapshot_delta": {"calls": 200, "attempts": 200, "retries": 0, "parse_failures": 0}}
```

### G. The 38,500 bound through the real guard

`compute_planned_calls_upper_bound` lives in `scripts/run_experiment.py:287`.
It is callable without the `STRATEGY_REGISTRY` (it takes the strategy instance
directly), so no CLI/registry edit was needed. Scratch script
`/tmp/strat001_bound.py`:

```
CALLS_PER_CANDIDATE = 1
PlannedCallsBound: 38500
full_plan_bound: 38500
remaining_bound: 38500
full_plan_trials: 60
remaining_trials: 60
manual candidate_upper_bound sum: 38500
BOUND CHECK PASSED: 38500
```

The D-35 matrix drive (`sweep_sizes=(50,100,200,500,1000,2000)`,
`sweep_trials_per_size=10`) yields exactly **38,500**, both through
`compute_planned_calls_upper_bound` and through direct
`candidate_upper_bound(strategy, n)`. `CALLS_PER_CANDIDATE == 1` is locked in
`decision.py:28`.

### H. Cost sanity (report only)

`/tmp/strat001_timing.py`, `shortlist()` on a 2000-node graph, 200 calls:

```
n_calls=200 n_nodes=2000
median_us=457.31
min_us=431.71 max_us=1126.47
mean_us=516.29
p95_us=752.86
median_ms=0.4573
```

Median **~0.46 ms** (457 µs), well under a millisecond, consistent with an
O(n log n) sort per call at n=2000. No assertion added to the repo.

### I. Bookkeeping

```
$ git diff -- docs/decisions/decision-log.md docs/tasks/status.md
(empty)
```

The diff is empty because the working tree is clean (everything is committed).
Using the commit instead:

```
$ git show defd2ed -- docs/decisions/decision-log.md docs/tasks/status.md
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index ab414ec..00b949f 100644
...
@@ -363,3 +363,11 @@ ...
+**[D-45]** Strategy 1 brute-force candidate narrowing implementation and bound (STRAT-001):
+(1) ... (5) ...
+Reasoning: ... Affects: ...
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index e57ad04..b82a7bc 100644
...
-| STRAT-001 | Implement Strategy 1 (brute-force)         | open   | —  ...
+| STRAT-001 | Implement Strategy 1 (brute-force)         | **needs-review** | ...  ...
```

This is a clean **append of D-45 at the end of the log** and a change to the
**STRAT-001 row only**. D-44 is not in this commit (it was committed earlier in
`ccbb3ca`, FIX-011), and the FIX-011 status row is likewise in `ccbb3ca`, not
here — so both belong to the other thread, as the prompt said.

Every factual statement in D-45 was checked against the code:

- (1) `name = "brute_force"`, `uses_embeddings = False`, embedder discarded,
  `_embedder` remains `None` — **correct** (`brute_force.py:54-70`).
- (2) `RuntimeError` before `setup()`; all existing nodes minus `new_name`;
  ascending sort; uniform `0.0` scores; empty tuples on an empty graph —
  **correct** (`brute_force.py:77-83`); the determinism claim is substantiated
  by mutation 1 being KILLED.
- (3) `max_candidates = max(0, n_existing)`, callable before `setup()`, exact
  bound, total 38,500 over the D-35 matrix — **correct** (verified in G).
- (4) stateless live read, `on_inserted` no-op, `config() == {"seed": self.seed}`,
  `diagnostics() == {"candidate_count": int}` with 0 before any shortlist —
  **correct** (`brute_force.py:85-102`); note the *tests do not pin the live-read
  part* (F1), but the code does satisfy it.
- (5) "all assumptions in the task prompt were verified (no contradictions
  found)" — the implementer's Part 0 findings (a–h) are internally consistent
  with what I could re-verify (exports, `HarnessConfig` defaults, conformance
  non-embedding branches, `Shortlist.scores` consumers). I found no
  contradiction in those assumptions.

### J. Report integrity

- Agent identity: report says `gemini` / model `Gemini 3.8 Flash (High)`
  (`STRAT-001-gemini-brute-force.md:5-6`). I **cannot verify** a model label;
  the string is plausible but Luke should confirm it against what his tool
  displayed. Flagged.
- New-file test count: report `22 passed, 1 skipped` — **matches** my run.
- Line counts: report 102 / 296 — **matches** my `wc -l`.
- Full-suite count: report `322 passed, 3 skipped` — **not reproducible now**
  (I get 365 passed, 3 skipped) because STRAT-002 and DATA-006 added tests
  after the commit; the report's number was presumably accurate at `defd2ed`.
  I did not check out `defd2ed` to confirm (hard rule 2 forbids checkout).
- "Found but not changed" section: **exists** (`STRAT-001-gemini-brute-force.md:195-200`).
- Report's `git diff` index line `80f5244..00b949f` differs from the committed
  `defd2ed` line `ab414ec..00b949f`. Explanation: at report time D-44 was still
  uncommitted in the working tree (hence the combined D-44+D-45 hunk the report
  shows); once FIX-011 committed D-44 (`ccbb3ca`), the STRAT-001 commit's base
  became `ab414ec`. Not a report error; just a snapshot-timing artifact.

## 5. Mutation table (check D)

| # | Mutation | Result | Failing test(s) when KILLED |
| :-- | :-- | :-- | :-- |
| M1 | delete `sorted(...)` (iterate `graph.nodes()` order) | **KILLED** | `TestBruteForceUnit::test_shortlist_all_nodes_sorted_ascending_and_scores_zero`; `TestBruteForceUnit::test_shortlist_order_independent_of_graph_insertion_order` |
| M2 | drop the `if n != new_name` filter | **KILLED** | `TestBruteForceUnit::test_shortlist_excludes_new_name_even_if_already_in_graph` |
| M3 | `max_candidates` returns `max(0, n_existing - 1)` | **KILLED** | `TestBruteForceConformance::test_shortlist_is_subset_and_excludes_new_node`; `::test_shortlist_does_not_mutate_graph`; `::test_same_seed_gives_same_shortlist`; `::test_repeated_inserts_see_previous_nodes`; `::test_max_candidates_bound_if_defined`; `TestBruteForceUnit::test_max_candidates_unsetup_instance`; `::test_full_matrix_bound_d35` |
| M4 | `setup` stores the embedder (`self._embedder = embedder`) | **KILLED** | `TestBruteForceUnit::test_embedder_remains_none_after_setup` |
| M5 | `shortlist` returns empty instead of raising before `setup()` | **KILLED** | `TestBruteForceUnit::test_shortlist_before_setup_raises_runtime_error` |
| M6 | scores become `None` | **KILLED** | `TestBruteForceUnit::test_shortlist_all_nodes_sorted_ascending_and_scores_zero`; `::test_shortlist_excludes_new_name_even_if_already_in_graph`; `::test_shortlist_empty_graph`; `::test_shortlist_order_independent_of_graph_insertion_order`; `TestBruteForceScaleSanity::test_scale_sanity_2000_nodes` |
| M7 | `diagnostics()` always reports `0` | **KILLED** | `TestBruteForceUnit::test_config_and_diagnostics_json_serializable` |
| M8 | `on_inserted` appends to a private list; `shortlist` uses it instead of the graph | **SURVIVED** | — (see F1) |

Mutation 1's result (KILLED) means the module docstring / D-45(2) determinism
claim is real and test-guarded. Mutation 8's survival is the one gap: the test
suite never forces a graph mutation that bypasses `on_inserted`, so a
cache-instead-of-live-read implementation would pass. The shipped code does read
the graph live, so this is a missing guard, not a defect.

## 6. Prompt corrections

Statements in the review prompt checked against the repo:

- Section 0 ("`BruteForceStrategy` and `tests/test_brute_force_strategy.py` plus
  D-45 and the STRAT-001 row") — **correct**.
- Section 0 ("The patch the APC reviewed had [two sha256 hashes]") — **correct**;
  hashes match byte-for-byte.
- Section 1 rule 2 ("Two threads share this checkout; other uncommitted changes
  (FIX-010, FIX-011, STRAT-002) are expected and are not yours") — **WRONG
  (stale)**. All three are now committed (`74ed0ee`, `ccbb3ca`, `6abe13c`),
  `HEAD` is `8418e00`, `git status --short` is empty, and `git worktree list`
  shows one worktree. The repo wins; I reviewed the committed state.
- Section 2 spec items (class attrs, `setup` discards embedder, sorted-after-filter,
  float scores, `max_candidates`, `config`/`diagnostics`, no embeddings/LLM/
  randomness/mutation/I-O, 38,500) — all **correct** against the code.
- Section 2 ("Files the implementer was allowed to touch ...") — **correct**;
  `defd2ed` touches only those files.
- Section 3.C ("reported `22 passed, 1 skipped`; confirm the skip") — **correct**
  for the new file; the skip is `test_embedder_identity_stored_on_strategy`.
- Section 3.D mutation-1 note ("check what `nodes()` returns") — **correct and
  important**: `nodes()` is insertion-ordered, and mutation 1 is KILLED.
- Section 3.G ("`brute_force` is not in `STRATEGY_REGISTRY`; if the function
  cannot be called without the registry, say so") — the function **can** be
  called directly with a strategy instance; bound verified at 38,500.
- Section 3.E ("confirm from `decision.py` that `llm_calls == len(candidates)`
  for the real step") — **correct** (`decision.py:128-130, 155`).
- Section 3.I ("The D-44 hunk and the FIX-011 row belong to another thread") —
  **correct**; both are in `ccbb3ca` (FIX-011), not in `defd2ed`.
- Section 3.A ("other threads' files will show in `git status`") — **wrong now**;
  the tree is clean (see the stale-state note above).

## 7. Found but not changed

1. **Repository state moved on from the prompt.** STRAT-001 (`defd2ed`),
   STRAT-002 (`6abe13c`), FIX-011 (`ccbb3ca`), and DATA-006 (`8418e00`) are all
   committed and the tree was clean at review start. **During the review a
   concurrent thread started modifying STRAT-002 files**
   (`src/graph_insertion/strategies/embedding_threshold.py` and
   `tests/test_embedding_threshold_strategy.py`, both `M` in `git status` at
   report time); those edits are not mine and do not touch STRAT-001. `/tmp`
   scratch copies were used for mutation testing, so nothing was written into
   the checkout except this report.
2. **Untracked/ignored files present but untouched**: `.env` (deliberately never
   read/printed, per hard rule 3), `apc-bundle-*.tar.gz`, `patch/`,
   `repositories/`, `results/`, `docs/foundations_.../syllabus.*`, and
   `__pycache__` dirs. None were opened or modified.
3. **Mutation 8 survivor / test-coverage gap (F1).** Not fixed, per the
   read-only rule. This is the highest-value follow-up.
4. **Implementer's model label is unverifiable** ("Gemini 3.8 Flash (High)").
   Luke should confirm it against his tool display.
5. **Full-suite count in the implementer report is not reproducible at current
   HEAD** (365 vs 322) because later commits added tests; not checked out to
   confirm the historical number.
6. **Test double faithfulness (E) is sound** — recorded so a future agent does
   not re-derive it: the harness smoke test uses the real
   `PairwiseDecisionStep`, and `llm_snapshot_delta.calls == n` independently
   confirms one real client call per candidate.

## 8. Open questions

1. Should F1's missing live-read test be added under STRAT-001-R as a follow-up
   (needs a fix task, since this review is read-only)? It is the only mutation
   survivor and directly guards a claim D-45(4) makes.
2. Is Luke's tool's actual Gemini model label "Gemini 3.8 Flash (High)"? I
   cannot verify a model label from the repo.
3. The prompt expected a dirty tree and enumerated other threads' uncommitted
   files; since everything been committed, should future STRAT reviews be
   written against `HEAD` (as here) rather than a working tree? Recorded so the
   APC can update the review-prompt template if it still assumes uncommitted
   work.
