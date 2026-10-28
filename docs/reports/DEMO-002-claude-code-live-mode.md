# DEMO-002 — Optional live mode for the defense demo

**Agent:** Claude Code
**Branch:** `task/DEMO-002`
**Base:** `9283a9d` on `master`
**Decision:** [D-100]
**Status:** needs-review

---

## 1. Executive Summary

`scripts/demo_trial.py` now supports an opt-in `--live` mode. It makes real
DeepSeek calls for the same single held-out node and the same four strategies
as the replay demo; it is not a size sweep. The default remains the offline
PILOT-001 replay from DEMO-001.

Live mode requires `--confirm` and `DEEPSEEK_API_KEY`, refuses a DeepSeek peak
window unless `--allow-peak` is passed, switches metric tags from `[PILOT]` to
`[LIVE]`, and writes a new `demo_runs/live-<UTC>/` directory with
`transcript.txt`, `demo.json` and `run_meta.json`. A non-empty output directory
or any path under `results/` is refused. Existing data is never overwritten.

The live transport was exercised with a deterministic fake client; the real
DeepSeek API was not called during this task because no key was supplied. The
real API path is the production `DeepSeekClient` behind the same
`RecordingLLMClient`/`PairwiseDecisionStep`/`insert_node` path.

Tests: 59 demo tests pass; full runnable suite 795 passed, 3 skipped.

---

## 2. Implementation

1. **`RecordingLLMClient`** wraps either `ReplayLLMClient` or `DeepSeekClient`
   and records every `(system, user, LLMResponse)` triple. `run_demo` builds
   `DemoCall`s from that record, not from replay-specific state.
2. **`run_demo(..., live_client=...)`** selects replay or live. It skips
   `load_pilot` in live mode, builds live provenance from the actual responses
   (model, retries, parse failures, transport failures, tokens, latency, cost),
   and marks the report `mode="live"`.
3. **Live banner/tags/limitations.** The banner says `LIVE RUN`, prints the
   endpoint/model/prompt/temperature/thinking and call counts, omits the cache
   SHA, and prints `LIVE_NOTICE`. Answers, latency and tokens use `[LIVE]`.
   The limitations text changes to live wording (fresh calls, no replay
   determinism, one node/one trial).
4. **Output directory.** `_validate_live_output_dir` defaults to
   `demo_runs/live-<UTC>/`, creates it, refuses a non-empty directory, and
   refuses paths under `results/`. `_write_live_outputs` writes the plain
   transcript, the same JSON record as `--json`, and a `run_meta.json`.
   `.gitignore` now ignores `demo_runs/`.
5. **CLI gates.** `--live` requires `--confirm` (exit 2), needs
   `DEEPSEEK_API_KEY` (exit 5), and checks `window_intersects_peak` for a
   120-second window (exit 2 with `--allow-peak` hint). `--check --live` checks
   the key/model without a network call. `--output-dir` without `--live` exits 2.
6. **Guide/README.** The operator guide gains a live-mode section, environment
   and cost notes, live output layout, live limitations, and a symbol cheat
   sheet for every symbol listed in section 8.1. `scripts/README.md` documents
   the live commands and flags.

Production code under `src/` was not modified.

---

## 3. Verification

**Replay regression.** Default replay exits 0; P8 table unchanged:
S1 28 calls F1 .667; S2 1 call F1 .250; S3 10 calls F1 .727; S4 9 calls F1 .250.

**Live orchestration (fake client, no network).**
- `run_demo(..., live_client=FakeLiveClient)` returns `mode="live"`,
  provenance path `(live DeepSeek API)`, 5 calls, 2.50 s accumulated API
  latency, `[LIVE]` tags and no `[PILOT]` text.
- An unparseable live answer raises `DemoError` exit 6.
- Live CLI end-to-end with a monkeypatched client writes
  `transcript.txt`, `demo.json` and `run_meta.json`; transcript contains
  `LIVE RUN`, terminal ends with `LIVE OUTPUT:`.

**Live gates.**
- `--live` without `--confirm` → exit 2.
- `--live --confirm` without `DEEPSEEK_API_KEY` → exit 5.
- `--check --live` without key → exit 5.
- `--output-dir` without `--live` → exit 2.

**Output safety.**
- A non-empty target directory is refused with exit 7 and its contents are
  unchanged.
- `results/` paths are refused by `_validate_live_output_dir`.

**Tests.**
- `tests/test_demo_trial.py`: 59 passed.
- Full runnable suite: 795 passed, 3 skipped. Two analysis modules remain
  excluded because `.venv-ann` lacks matplotlib (pre-existing environment gap).

**Not performed.** No real DeepSeek API call, because no API key was supplied
and spending requires Luke's explicit authorization. The live client itself is
the existing production `DeepSeekClient` used by RUN-001; only the demo-side
recording/output wrapper is new.

---

## 4. Operator Guide Additions

- Section 3A: live mode, `--confirm`, API key, peak guard, expected call count
  and cost, output directory, refusal rules, and live-vs-replay wording.
- Section 8.1a: one-line explanations for every symbol in the file table,
  including live-only `RecordingLLMClient` and `_write_live_outputs`.

---

## 5. Decision D-100

Recorded in `docs/decisions/decision-log.md`: optional live single-trial mode,
`--confirm`/API-key/peak gates, `RecordingLLMClient`, timestamped non-overwriting
output, live vs replay tags, and the explicit statement that this is not a new
empirical result.

---

## 6. Git Diff

```diff
diff --git c/.gitignore i/.gitignore
index 854c63f..016b646 100644
--- c/.gitignore
+++ i/.gitignore
@@ -19,3 +19,4 @@ patch/
 results/
 *.log
 .aider*
+demo_runs/
diff --git c/docs/decisions/decision-log.md i/docs/decisions/decision-log.md
index d5239eb..550d76b 100644
--- c/docs/decisions/decision-log.md
+++ i/docs/decisions/decision-log.md
@@ -980,3 +980,12 @@ Reasoning: records why a second, code-level map exists alongside the decision lo
 (5) In replay a pair's answer is a fixed lookup, so every edge predicted by S2-S4 must be in S1's predicted set; the demo asserts this subset invariant. It need not hold in the official live runs, where each strategy made its own calls, and the transcript's limitations say so.
 (6) Nothing here is an empirical result. The demo is a one-node, one-trial illustration of real recorded PILOT-001 output, not a substitute for the 24-run accuracy/sweep campaign or Chapter 4. V8 found that the pilot replay matches the official accuracy records exactly for S2 and S3 but differs by one predicted edge for S1 and S4; the official runs made their own live calls on 2026-10-18, so replay faithfully reflects the 2026-10-07 pilot, not the later runs.
 Reasoning: gives panelists an honest, reproducible microcosm of the insertion pipeline without spending API budget or depending on the network during a defense, while making every replayed value auditable and refusing to fabricate any missing answer. Affects: `scripts/demo_trial.py`, `tests/test_demo_trial.py`, `scripts/README.md`, `docs/prompts/DEMO-001-PROMPT.md`, `docs/tasks/status.md`, `docs/reports/DEMO-001-claude-code-defense-demo-trial.md`.
+
+**[D-100]** Defense demo: optional live single-trial mode with isolated output (DEMO-002):
+(1) Default behavior is unchanged: `scripts/demo_trial.py` remains the offline PILOT-001 replay demo under [D-99]. A new opt-in `--live` mode makes real DeepSeek API calls for the same single held-out node and the same four strategies; it does not add a size sweep or any new experiment matrix.
+(2) Live mode is guarded: `--live` requires `--confirm`; it requires `DEEPSEEK_API_KEY`; and a live execution window that overlaps DeepSeek peak pricing is refused unless `--allow-peak` is passed ([D-37]). `--check --live` validates the key, model, corpus, node and embedder without making a network call.
+(3) Live transport is wrapped by `RecordingLLMClient`, which preserves every prompt/response pair for the transcript. The decision step, strategies, `insert_node`, meter and scorer remain production code. An unparseable live answer fails closed with exit 6; the demo never invents an edge.
+(4) Live output never overwrites existing data: the default is `demo_runs/live-<UTC>/` (gitignored), with `transcript.txt`, `demo.json` and `run_meta.json`. `--output-dir` overrides the location; a non-empty directory, or any path under `results/`, is refused with exit 7. Replay continues to write only stdout plus an optional `--json` file.
+(5) Metric tags follow the source: live answers, latency and tokens are `[LIVE]`; replay remains `[PILOT]`. Cost is `[CALC]` in both modes. The banner and limitations text switch between the LIVE and REPLAY notices, so a live transcript cannot be confused with a replayed one.
+(6) Nothing here changes the official run plan or Chapter 4 evidence. A live demo is still one node, one trial, and is explicitly not a new result; embeddings remain local and only the LLM transport is live.
+Reasoning: lets Luke demonstrate a genuine model insertion when the network and budget permit, while keeping the default defense path offline and deterministic and preventing live artifacts from colliding with accepted results. Affects: `scripts/demo_trial.py`, `tests/test_demo_trial.py`, `scripts/README.md`, `docs/presentation/information/DEMO-001-OPERATOR-GUIDE.md`, `.gitignore`, `docs/tasks/status.md`, `docs/reports/DEMO-002-claude-code-live-mode.md`.
diff --git c/docs/presentation/information/DEMO-001-OPERATOR-GUIDE.md i/docs/presentation/information/DEMO-001-OPERATOR-GUIDE.md
index ddda849..e00017c 100644
--- c/docs/presentation/information/DEMO-001-OPERATOR-GUIDE.md
+++ i/docs/presentation/information/DEMO-001-OPERATOR-GUIDE.md
@@ -150,6 +150,62 @@ Both are genuine replay results from the same cache, not special cases.
 
 ---
 
+## 3A. Live mode (optional, real API calls)
+
+Default remains replay. Add `--live` to make real DeepSeek calls for the same
+single-node, four-strategy trial. It is still one insertion per strategy, not a
+size sweep.
+
+```bash
+# Pre-flight only: checks key, model, corpus, node, embedder; no network call
+.venv-ann/bin/python scripts/demo_trial.py --check --live
+
+# Real run. --confirm is mandatory.
+export DEEPSEEK_API_KEY=...
+.venv-ann/bin/python scripts/demo_trial.py --live --confirm
+
+# Choose the output directory yourself
+.venv-ann/bin/python scripts/demo_trial.py --live --confirm \
+    --output-dir demo_runs/my-live-run
+
+# Allow peak-priced execution (otherwise a peak window is refused)
+.venv-ann/bin/python scripts/demo_trial.py --live --confirm --allow-peak
+```
+
+What changes in live mode:
+
+- Every answer is a fresh DeepSeek response. The replay cache is not read.
+- Tags switch from `[PILOT]` to `[LIVE]` for answers, latency and tokens.
+- The banner says `LIVE RUN` and prints the endpoint, model, prompt version,
+  temperature, thinking mode and call/retry counts.
+- Default call count is about 48 (S1 28, S2 1, S3 10, S4 9 on the default node);
+  the pre-flight prints a 76-call upper bound and a cost bound. At off-peak
+  prices the default run is on the order of one tenth of a cent.
+- Embeddings are still computed locally with the pinned MiniLM model. Only the
+  LLM transport is live.
+- Peak guard: a live run whose execution window overlaps DeepSeek peak pricing
+  is refused unless `--allow-peak` is passed ([D-37]).
+- Safety: `--confirm` is mandatory, so a stray `--live` cannot spend money.
+
+Output is always written to a new directory, never over an existing one:
+
+```text
+demo_runs/live-<UTC timestamp>/
+  transcript.txt   full no-colour transcript
+  demo.json        same machine-readable record as --json
+  run_meta.json    mode, model, endpoint, argv, node, strategies, wall time
+```
+
+`--output-dir DIR` overrides the location. A non-empty directory is refused
+(exit 7), and so is any path under `results/`. `demo_runs/` is gitignored.
+The terminal still prints the transcript and ends with `LIVE OUTPUT: <dir>`.
+
+Live limitations are printed in the transcript: one node, one trial, no
+scaling claim, and each strategy made its own calls, so strategies may disagree
+on a pair even though they share the decision step.
+
+---
+
 ## 4. What to say, and what not to say
 
 Say:
@@ -163,9 +219,15 @@ Say:
 - "This is one node, one trial. It illustrates the pipeline; the thesis
   evidence is the full runs."
 
+If running `--live`, say instead:
+
+- "This run is making live DeepSeek calls now; every answer is fresh."
+- "Embeddings are still local; only the LLM transport is live."
+- "This is still one node and one trial, not a new empirical result."
+
 Do not say:
 
-- That the demo is making live API calls. It is not.
+- That replay mode is making live API calls. It is not.
 - That the shown latency is this machine's current latency. It is not.
 - That the demo is a new empirical result or part of Chapter 4. It is not.
 - That replay agreement proves the official runs agree. The official accuracy
@@ -182,7 +244,7 @@ Do not say:
 | 2 | Usage error (bad/duplicate/unknown `--strategies`) | Use `s1`–`s4` or the canonical names. |
 | 3 | Pilot cache/provenance failure | Restore the accepted PILOT-001 artifacts; do not edit the cache. The SHA-256 and prompt-version checks are fail-closed. |
 | 4 | Corpus or node problem | Check `repositories/dataset/EKG-Dataset/`; use a node name from the DSA corpus. Close matches are printed. |
-| 5 | Missing dependency or embedder | Use `.venv-ann`; the model must already be cached. The demo never downloads. |
+| 5 | Missing dependency/embedder/API key | Use `.venv-ann`; the model must already be cached. Live mode also needs `DEEPSEEK_API_KEY`. The demo never downloads. |
 | 6 | Internal consistency check failed | A production path, edge rebuild, label sum or subset invariant disagreed. Do not present the run; report it. |
 | 7 | Refused `--json` path | Pick a new path outside `results/` whose parent exists. |
 
@@ -190,6 +252,10 @@ Common fixes:
 
 - **`ModuleNotFoundError: sentence_transformers` or `faiss`** — run with
   `.venv-ann/bin/python`, not system Python.
+- **Live mode exits 5 with `DEEPSEEK_API_KEY`** — export the key or omit
+  `--live`; `--check --live` checks it without making a call.
+- **Live mode exits 2 for peak pricing** — wait for off-peak, or pass
+  `--allow-peak` and accept peak rates.
 - **Model load fails offline** — the cached MiniLM model is missing. Restore the
   cache; do not unset the offline variables to force a download during a
   defense.
@@ -213,7 +279,7 @@ Verified by the test suite and the DEMO-001 report:
 - Deterministic non-volatile JSON across two runs.
 - No writes under `results/`; pilot artifact SHA unchanged.
 - Formatter width <= 88 columns for every DSA node in both Unicode and ASCII.
-- 51 new tests; full runnable suite 787 passed, 3 skipped.
+- 59 new tests; full runnable suite 795 passed, 3 skipped.
 
 Not verified or not claimed:
 
@@ -254,24 +320,120 @@ Use symbol names, not line numbers; line numbers drift. Start in
 
 ### 8.1 Files to open, and what to point at
 
-| File | Symbols to show | What to say |
-|---|---|---|
-| `scripts/demo_trial.py` | `run_demo`, `ReplayLLMClient.complete`, `load_pilot`, `Formatter.while_block` | This is demo-only orchestration. It loads the corpus, loops over strategies, calls production `insert_node`, and formats the transcript. |
-| `src/graph_insertion/strategy.py` | `Shortlist`, `InsertionMetrics`, `insert_node` | The canonical insertion driver. It times narrowing, calls the shared decision step, validates the edges, mutates the graph, updates the strategy, and records metrics. |
-| `src/graph_insertion/decision.py` | `SYSTEM_PROMPT`, `parse_token`, `PairwiseDecisionStep.decide` | The one step shared by all strategies: one model call per candidate, one of three tokens, mapped to a canonical prerequisite edge. |
-| `src/graph_insertion/strategies/brute_force.py` | `BruteForceStrategy.shortlist` | The control: every existing concept is sent to the model. This is why S1 makes exactly `n` calls. |
-| `src/graph_insertion/strategies/embedding_threshold.py` | `EmbeddingThresholdStrategy.setup`, `.shortlist`, `.on_inserted` | S2: cache all embeddings, keep only cosine above theta, append the new vector after insertion. |
-| `src/graph_insertion/strategies/ann_retrieval.py` | `AnnRetrievalStrategy.setup`, `.shortlist`, `.on_inserted` | S3: build an HNSW index, retrieve top-k, add the new vector to the index after insertion. |
-| `src/graph_insertion/strategies/bounded_bucket.py` | `BoundedBucketStrategy.shortlist`, `._locate_home`, `._insert_entry` | S4: hash the new vector, find its home segment, shortlist only that segment, split when it overflows. |
-| `src/graph_insertion/strategies/registry.py` | `STRATEGY_FACTORIES` | One place maps CLI strategy names to classes and default parameters. |
-| `src/graph_insertion/scoring.py` | `score_node_insertion`, `NodeScore` | Turns predicted edges and the shortlist into TP/FP/FN, precision/recall/F1 and shortlist recall. Unjudged DSA pairs are excluded, with a sensitivity variant. |
-| `src/graph_insertion/loader.py` | `load_corpus`, `CORPUS_DOMAIN_CONTEXT_MAP` | Parses the gold triples, applies the verified column orientation, and supplies the domain string for the prompt. |
-| `src/graph_insertion/graph_representation.py` | `ConceptGraph`, `oriented_edge`, `embed_text` | Stores the graph; canonical edge `(prereq, dependent)` always means prereq → dependent; embeddings use bare names with spaces. |
-| `src/graph_insertion/embedding.py` | `MeteredEmbedder` | Counts embedding calls and time. This is how the demo proves S2–S4 embed the new concept once, not repeatedly. |
-| `src/graph_insertion/llm.py` | `LLMResponse`, `MeteredLLMClient` | The transport interface. The demo replaces the client, not the decision step or the meter. |
-| `src/graph_insertion/embedding_minilm.py` | `MiniLMEmbedder` | Pinned model, revision and sentence-transformers version; fail-closed. |
-| `src/graph_insertion/cpu_threads.py` | `pin_cpu_threads` | Pins PyTorch to one thread for comparable embedding latency. |
-| `docs/context/strategy-interface.md` | Strategy lifecycle and timing rules | The written contract; use it if a panelist asks what a strategy is allowed to do. |
+| File                                                    | Symbols to show                                                               | What to say                                                                                                                                                            |
+| ------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
+| `scripts/demo_trial.py`                                 | `run_demo`, `ReplayLLMClient.complete`, `RecordingLLMClient`, `load_pilot`, `Formatter.while_block`, `_write_live_outputs` | This is demo-only orchestration. It loads the corpus, loops over strategies, calls production `insert_node`, and formats the transcript. Live mode wraps the API client with a recorder and writes a run directory. |
+| `src/graph_insertion/strategy.py`                       | `Shortlist`, `InsertionMetrics`, `insert_node`                                | The canonical insertion driver. It times narrowing, calls the shared decision step, validates the edges, mutates the graph, updates the strategy, and records metrics. |
+| `src/graph_insertion/decision.py`                       | `SYSTEM_PROMPT`, `parse_token`, `PairwiseDecisionStep.decide`                 | The one step shared by all strategies: one model call per candidate, one of three tokens, mapped to a canonical prerequisite edge.                                     |
+| `src/graph_insertion/strategies/brute_force.py`         | `BruteForceStrategy.shortlist`                                                | The control: every existing concept is sent to the model. This is why S1 makes exactly `n` calls.                                                                      |
+| `src/graph_insertion/strategies/embedding_threshold.py` | `EmbeddingThresholdStrategy.setup`, `.shortlist`, `.on_inserted`              | S2: cache all embeddings, keep only cosine above theta, append the new vector after insertion.                                                                         |
+| `src/graph_insertion/strategies/ann_retrieval.py`       | `AnnRetrievalStrategy.setup`, `.shortlist`, `.on_inserted`                    | S3: build an HNSW index, retrieve top-k, add the new vector to the index after insertion.                                                                              |
+| `src/graph_insertion/strategies/bounded_bucket.py`      | `BoundedBucketStrategy.shortlist`, `._locate_home`, `._insert_entry`          | S4: hash the new vector, find its home segment, shortlist only that segment, split when it overflows.                                                                  |
+| `src/graph_insertion/strategies/registry.py`            | `STRATEGY_FACTORIES`                                                          | One place maps CLI strategy names to classes and default parameters.                                                                                                   |
+| `src/graph_insertion/scoring.py`                        | `score_node_insertion`, `NodeScore`                                           | Turns predicted edges and the shortlist into TP/FP/FN, precision/recall/F1 and shortlist recall. Unjudged DSA pairs are excluded, with a sensitivity variant.          |
+| `src/graph_insertion/loader.py`                         | `load_corpus`, `CORPUS_DOMAIN_CONTEXT_MAP`                                    | Parses the gold triples, applies the verified column orientation, and supplies the domain string for the prompt.                                                       |
+| `src/graph_insertion/graph_representation.py`           | `ConceptGraph`, `oriented_edge`, `embed_text`                                 | Stores the graph; canonical edge `(prereq, dependent)` always means prereq → dependent; embeddings use bare names with spaces.                                         |
+| `src/graph_insertion/embedding.py`                      | `MeteredEmbedder`                                                             | Counts embedding calls and time. This is how the demo proves S2–S4 embed the new concept once, not repeatedly.                                                         |
+| `src/graph_insertion/llm.py`                            | `LLMResponse`, `MeteredLLMClient`                                             | The transport interface. The demo replaces the client, not the decision step or the meter.                                                                             |
+| `src/graph_insertion/embedding_minilm.py`               | `MiniLMEmbedder`                                                              | Pinned model, revision and sentence-transformers version; fail-closed.                                                                                                 |
+| `src/graph_insertion/cpu_threads.py`                    | `pin_cpu_threads`                                                             | Pins PyTorch to one thread for comparable embedding latency.                                                                                                           |
+| `docs/context/strategy-interface.md`                    | Strategy lifecycle and timing rules                                           | The written contract; use it if a panelist asks what a strategy is allowed to do.                                                                                      |
+
+### 8.1a Symbol cheat sheet
+
+One-line explanations for every symbol in the table above.
+
+**Demo-only (`scripts/demo_trial.py`)**
+
+- `run_demo` — Loads the corpus and either the replay cache or a live client,
+  runs one insertion per selected strategy, and returns the report object used
+  by both the transcript and JSON.
+- `load_pilot` — Validates the recorded cache byte-for-byte (SHA, field types,
+  812 pairs, sums) and returns provenance plus a prompt-to-answer map. Fails
+  closed; no fallback.
+- `ReplayLLMClient.complete` — Looks up the exact `user_prompt` in that map and
+  returns an `LLMResponse`; a missing prompt raises instead of inventing one.
+- `RecordingLLMClient` — Wraps either the replay client or the live DeepSeek
+  client and stores every prompt/response pair in order so the formatter can
+  show calls without changing the decision step.
+- `_write_live_outputs` — Writes `transcript.txt`, `demo.json` and
+  `run_meta.json` into the new live output directory.
+- `Formatter.while_block` — Renders one strategy's WHILE section: setup,
+  shortlist, candidate ranking, sampled calls, answers, calls, latency, tokens,
+  cost and graph update, with `[LIVE]`/`[PILOT]`/`[CALC]` tags.
+
+**Production driver (`src/graph_insertion/strategy.py`)**
+
+- `Shortlist` — The strategy's output: an ordered tuple of candidate names and
+  an optional tuple of matching scores.
+- `InsertionMetrics` — One insertion's counters: graph size, shortlist size,
+  LLM calls, embedding calls and time, shortlist/decision/apply/update/total
+  time, validation time and diagnostics.
+- `insert_node` — The canonical pipeline: validate inputs, time the shortlist,
+  call the shared decision step, validate edges, mutate the graph, call
+  `on_inserted`, and return `InsertionResult` with metrics.
+
+**Shared decision step (`src/graph_insertion/decision.py`)**
+
+- `SYSTEM_PROMPT` — The fixed v2 instruction: prerequisite means direct or
+  indirect, answer with exactly one token, names only.
+- `parse_token` — Normalises a raw completion (strip/uppercase) to
+  `X_PREREQ_Y`, `Y_PREREQ_X`, `NONE`, or `None`.
+- `PairwiseDecisionStep.decide` — Makes one sequential call per candidate and
+  maps the token to a canonical edge or no edge.
+
+**Strategies**
+
+- `BruteForceStrategy.shortlist` — Returns every existing node, alphabetically,
+  with uniform zero scores; S1 therefore makes exactly `n` calls.
+- `EmbeddingThresholdStrategy.setup` — Embeds and L2-normalises all nodes into a
+  matrix; `.shortlist` embeds the new name once and keeps cosine `> theta`;
+  `.on_inserted` appends the cached vector without re-embedding.
+- `AnnRetrievalStrategy.setup` — Builds the HNSW index over normalised vectors;
+  `.shortlist` retrieves top-k; `.on_inserted` adds the cached vector to the
+  index.
+- `BoundedBucketStrategy.shortlist` — Hashes the query, finds its home segment,
+  and scores only that segment's members.
+- `BoundedBucketStrategy._locate_home` — Binary-searches segment boundaries and,
+  when the query falls between segments, chooses the nearer neighbour.
+- `BoundedBucketStrategy._insert_entry` — Inserts the new entry in sorted order
+  and splits the segment at its midpoint if it exceeds `s_max`.
+- `STRATEGY_FACTORIES` — Maps strategy names to factory functions and their
+  default parameters.
+
+**Accuracy (`src/graph_insertion/scoring.py`)**
+
+- `score_node_insertion` — Compares predicted canonical edges and the shortlist
+  with the gold graph and judgments, producing TP/FP/FN, precision, recall, F1,
+  shortlist recall, unjudged-pair exclusion and the sensitivity variant.
+- `NodeScore` — The per-trial dataclass holding those metrics.
+
+**Data (`loader.py`, `graph_representation.py`)**
+
+- `load_corpus` — Discovers and parses a corpus into `ConceptGraph` plus
+  `GoldJudgmentSet`, applying the verified delimiter and column orientation.
+- `CORPUS_DOMAIN_CONTEXT_MAP` — Maps a corpus name to the graph-level subject
+  string placed in the decision prompt.
+- `ConceptGraph` — NetworkX-backed graph wrapper; nodes are bare names, an edge
+  `(u, v)` means u is a prerequisite of v, and `without_node` makes the
+  leave-one-out copy.
+- `oriented_edge` — Converts a file row into canonical `(prereq, dependent)`;
+  gold files use `(col2, col1)`, example MEKG files use `(col1, col2)`.
+- `embed_text` — Converts a concept name to its embedding text by replacing
+  underscores with spaces; no domain context is added.
+
+**Embedding and transport (`embedding.py`, `llm.py`, `embedding_minilm.py`, `cpu_threads.py`)**
+
+- `MeteredEmbedder` — Counts embedding calls, texts and seconds; the demo uses
+  it to prove the new concept is embedded once.
+- `LLMResponse` — The transport result: text, token counts, latency, model ID
+  and attempts.
+- `MeteredLLMClient` — Wraps any client to count calls, retries, tokens, latency
+  and parse failures.
+- `MiniLMEmbedder` — The pinned all-MiniLM-L6-v2 backend: 384-dimensional,
+  CPU, float32, version and revision checked at construction.
+- `pin_cpu_threads` — Sets and verifies PyTorch intra-op threads to one so
+  embedding latency is comparable across strategies.
 
 ### 8.2 Five-minute code path
 
@@ -346,3 +508,4 @@ Then add the demo-specific sentence:
 | `docs/decisions/decision-log.md` | D-99: replay-only, fail-closed, tag semantics. |
 | `docs/tasks/status.md` | DEMO-001 status row. |
 | `results/pilot/20261007_053743Z/` | Recorded PILOT-001 cache and summary. |
+| `demo_runs/live-<UTC>/` | Generated live output (`transcript.txt`, `demo.json`, `run_meta.json`); gitignored. |
diff --git c/docs/tasks/status.md i/docs/tasks/status.md
index 1addc81..21df456 100644
--- c/docs/tasks/status.md
+++ i/docs/tasks/status.md
@@ -99,6 +99,7 @@ Status: **in-progress**
 | PRES-001 | Consolidate the source material, requirements, style reference, and asset pack for the APC to plan a separate background-concepts HTML presentation for defense panelists (first-principles teaching; no Chapter 4 results). | **needs-review** | Completed by Claude Code; branch `task/PRES-001`, worktree `../llm-graph-insertion-complexity-PRES-001`. Materials in `docs/presentation/background-deck/` (`BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, logos). See report [`docs/reports/PRES-001-claude-code-background-deck-materials.md`](docs/reports/PRES-001-claude-code-background-deck-materials.md). |
 | PRES-002 | Build the single-file, offline background-concepts HTML deck (26 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval, efSearch, and configuration/mode/run/trial scene follow-ups. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md), [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md), [`docs/reports/PRES-002-claude-code-efsearch-scene.md`](docs/reports/PRES-002-claude-code-efsearch-scene.md) and [`docs/reports/PRES-002-claude-code-configuration-mode-scenes.md`](docs/reports/PRES-002-claude-code-configuration-mode-scenes.md). |
 | DEMO-001 | Build an offline, deterministic terminal demonstration for defense panelists: one DSA leave-one-out insertion through all four strategies, with every LLM decision replayed by exact prompt from the recorded PILOT-001 cache and staged BEFORE/WHILE/AFTER output. | **needs-review** | Completed by Claude Code; branch `task/DEMO-001`, worktree `../llm-graph-insertion-complexity-DEMO-001`. 51 new tests; full suite 787 passed, 3 skipped (two analysis modules excluded because `.venv-ann` lacks matplotlib). See report [`docs/reports/DEMO-001-claude-code-defense-demo-trial.md`](docs/reports/DEMO-001-claude-code-defense-demo-trial.md). |
+| DEMO-002 | Add optional `--live` mode to the defense demo: same single-node/four-strategy trial with real DeepSeek calls, `--confirm` and API-key gates, peak protection, `[LIVE]` tags, and a timestamped `demo_runs/live-<UTC>/` output directory that never overwrites existing data. | **needs-review** | Completed by Claude Code; branch `task/DEMO-002`. 59 demo tests; full suite 795 passed, 3 skipped (two analysis modules excluded because `.venv-ann` lacks matplotlib). See report [`docs/reports/DEMO-002-claude-code-live-mode.md`](docs/reports/DEMO-002-claude-code-live-mode.md). |
 
 ## Housekeeping
 
diff --git c/scripts/README.md i/scripts/README.md
index 3ec8a31..a8deb65 100644
--- c/scripts/README.md
+++ i/scripts/README.md
@@ -312,33 +312,43 @@ the production code; only the LLM transport is replaced by a replay client that
 looks up each answer by exact prompt text in the recorded PILOT-001 cache.
 
 ```bash
-# Full demo (all four strategies, default node)
+# Full replay demo (default)
 .venv-ann/bin/python scripts/demo_trial.py
 
 # One strategy / a different node / plain ASCII / pauses between phases
 .venv-ann/bin/python scripts/demo_trial.py --strategies s1,s3 --node graph --ascii --pause
 
-# Offline pre-flight: provenance, corpus, node, embedder (no trial)
+# Replay pre-flight: provenance, corpus, node, embedder (no trial)
 .venv-ann/bin/python scripts/demo_trial.py --check
 
-# Save the machine-readable report outside results/
+# Save the replay machine-readable report outside results/
 .venv-ann/bin/python scripts/demo_trial.py --json /tmp/demo.json
+
+# Live: real DeepSeek calls for the same single trial; --confirm is mandatory
+.venv-ann/bin/python scripts/demo_trial.py --live --confirm
+.venv-ann/bin/python scripts/demo_trial.py --check --live
+.venv-ann/bin/python scripts/demo_trial.py --live --confirm --output-dir demo_runs/my-run
 ```
 
 Options: `--node NAME`, `--strategies LIST` (`s1`–`s4` or canonical names),
 `--pilot-dir DIR`, `--no-color`, `--ascii`, `--pause`, `--show-all-calls`,
-`--json PATH`, `--check`, `--traceback`. Colour is used only on a TTY unless
-`--no-color` or `NO_COLOR` is set. The demo sets `HF_HUB_OFFLINE=1` and
-`TRANSFORMERS_OFFLINE=1`; it never calls the API, reads `DEEPSEEK_API_KEY`, or
-writes under `results/`.
+`--json PATH`, `--live`, `--confirm`, `--allow-peak`, `--output-dir DIR`,
+`--check`, `--traceback`. Colour is used only on a TTY unless `--no-color` or
+`NO_COLOR` is set. Replay sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`
+and never calls the API. Live mode requires `DEEPSEEK_API_KEY`, refuses a peak
+pricing window unless `--allow-peak` is passed, and writes a new
+`demo_runs/live-<UTC>/` directory containing `transcript.txt`, `demo.json` and
+`run_meta.json`; a non-empty output directory is refused, as is any path under
+`results/`. Embeddings remain local in both modes.
 
 Exit codes: `0` ok, `2` usage, `3` pilot cache/provenance failure, `4` corpus or
-node problem, `5` missing dependency/embedder, `6` internal consistency check,
-`7` refused output path.
+node problem, `5` missing dependency/embedder/API key, `6` internal consistency
+check, `7` refused output path.
 
-The demo is an illustration, not a new result. Decisions are real recorded
-PILOT-001 answers (2026-10-07, prompt v2, `deepseek-flash`); latency, tokens and
-cost are recorded values, not measurements from the demo run.
+The demo is an illustration, not a new result. Replay decisions are real
+recorded PILOT-001 answers (2026-10-07, prompt v2, `deepseek-flash`); live
+answers are fresh API responses. Latency, tokens and cost are shown with
+`[PILOT]` in replay and `[LIVE]` in live mode.
 
 Operator guide, including defense-day flow, flags, troubleshooting, exit codes
 and suggested counter-nodes:
diff --git c/scripts/demo_trial.py i/scripts/demo_trial.py
old mode 100644
new mode 100755
index ce2d934..ee2f011
--- c/scripts/demo_trial.py
+++ i/scripts/demo_trial.py
@@ -127,6 +127,14 @@ DIAGNOSTIC_KEYS = {
     "bounded_bucket": ["num_segments", "min_segment_size", "max_segment_size"],
 }
 
+LIVE_NOTICE = (
+    "LIVE NOTICE. This run calls the DeepSeek API now. Every answer below is a "
+    "fresh model response produced for exactly the prompt shown, at temperature 0 "
+    "with thinking disabled. Narrowing, graph updates, scoring, latency and token "
+    "counts are measured live. The run is one held-out node and one trial, not a "
+    "new thesis result."
+)
+
 REPLAY_NOTICE = (
     "REPLAY NOTICE. The model answers on screen are real. Each one was returned "
     "by deepseek-flash on 2026-10-07 during PILOT-001 for exactly the prompt "
@@ -448,6 +456,33 @@ class ReplayLLMClient:
         raise DemoError(3, f"recorded answer failed to parse: {raw_text!r}")
 
 
+@dataclass(frozen=True)
+class IssuedCall:
+    """One completion issued during a trial, captured for the transcript."""
+
+    system_prompt: str
+    user_prompt: str
+    response: LLMResponse
+
+
+class RecordingLLMClient:
+    """Wrap any LLMClient and keep every prompt/response pair in order."""
+
+    def __init__(self, inner: Any) -> None:
+        self.inner = inner
+        self.calls: list[IssuedCall] = []
+
+    def complete(self, system: str, user: str) -> LLMResponse:
+        response = self.inner.complete(system, user)
+        self.calls.append(IssuedCall(system, user, response))
+        return response
+
+    def record_parse_failure(self, raw_text: str) -> None:
+        recorder = getattr(self.inner, "record_parse_failure", None)
+        if callable(recorder):
+            recorder(raw_text)
+
+
 def estimated_cost_usd(
     cache_miss_tokens: int,
     cache_hit_tokens: int,
@@ -472,7 +507,7 @@ class DemoCall:
     y: str
     token: str
     edge: Optional[tuple[str, str]]
-    latency_s_pilot: float
+    latency_s: float
     input_tokens: int
     output_tokens: int
     user_prompt: str
@@ -522,6 +557,9 @@ class StrategyReport:
     lost_decision: int
     recall_given_shortlist: Optional[float]
     diagnostics: dict[str, Any]
+    retries: int = 0
+    parse_failures: int = 0
+    transport_failures: int = 0
 
 
 @dataclass
@@ -549,6 +587,9 @@ class DemoReport:
     subset_of_s1: Optional[bool]
     embedder_identity: Optional[dict[str, Any]]
     cpu_threads: Optional[dict[str, Any]]
+    mode: str = "replay"
+    live_base_url: Optional[str] = None
+    output_dir: Optional[str] = None
 
 
 # ---------------------------------------------------------------------------
@@ -647,12 +688,20 @@ def run_demo(
     replay: Optional[ReplayLLMClient] = None,
     provenance: Optional[PilotProvenance] = None,
     raw_embedder: Any = None,
+    live_client: Any = None,
     argv: Optional[Sequence[str]] = None,
 ) -> DemoReport:
-    """Execute one insertion trial for each selected strategy and return the report."""
+    """Execute one insertion trial for each selected strategy and return the report.
+
+    Pass *replay* for the offline PILOT-001 demo, or *live_client* (an
+    ``LLMClient``) for one real API-backed trial. Never both.
+    """
     started = datetime.now(timezone.utc)
     t_start = time.perf_counter()
     selected_names = list(selected) if selected is not None else list(CANONICAL_STRATEGIES)
+    is_live = live_client is not None
+    if is_live and replay is not None:
+        raise DemoError(2, "choose either replay or live mode, not both")
 
     if corpus is None:
         try:
@@ -674,12 +723,17 @@ def run_demo(
         hint = f"Close matches: {', '.join(suggestions)}" if suggestions else "No close matches."
         raise DemoError(4, f"node {node!r} is not in the DSA corpus", hint)
 
-    resolved_pilot = resolve_pilot_dir(pilot_dir)
-    if replay is None:
-        provenance, by_prompt = load_pilot(resolved_pilot, corpus=corpus)
-        replay = ReplayLLMClient(by_prompt)
-    elif provenance is None:
-        raise DemoError(6, "synthetic replay requires explicit provenance")
+    if is_live:
+        resolved_pilot = Path("(live DeepSeek API)")
+        client: Any = live_client
+    else:
+        resolved_pilot = resolve_pilot_dir(pilot_dir)
+        if replay is None:
+            provenance, by_prompt = load_pilot(resolved_pilot, corpus=corpus)
+            replay = ReplayLLMClient(by_prompt)
+        elif provenance is None:
+            raise DemoError(6, "synthetic replay requires explicit provenance")
+        client = replay
 
     for name in selected_names:
         if name not in CANONICAL_STRATEGIES:
@@ -722,8 +776,8 @@ def run_demo(
         setup_embedding_calls = meter.calls - setup_calls_before
         gc.collect()
 
-        served_before = len(replay.served)
-        llm_meter = MeteredLLMClient(replay)
+        recorder = RecordingLLMClient(client)
+        llm_meter = MeteredLLMClient(recorder)
         step = PairwiseDecisionStep(llm_meter)
         try:
             t1 = time.perf_counter()
@@ -734,26 +788,41 @@ def run_demo(
         except Exception as exc:
             raise DemoError(6, f"{name} insertion failed: {type(exc).__name__}: {exc}") from exc
 
-        served = replay.served[served_before:]
+        prompt_to_candidate = {
+            step.build_user_prompt(node, candidate, corpus.domain_context): candidate
+            for candidate in result.shortlist.candidates
+        }
         calls: list[DemoCall] = []
-        for rec in served:
-            token = rec.token
+        for issued in recorder.calls:
+            candidate = prompt_to_candidate.get(issued.user_prompt)
+            if candidate is None:
+                raise DemoError(
+                    6,
+                    f"{name}: issued a prompt outside the strategy shortlist",
+                )
+            token = parse_token(issued.response.text)
+            if token is None:
+                raise DemoError(
+                    6,
+                    f"{name}: unparseable live response {issued.response.text!r}",
+                    "The demo refuses to invent an edge for an unparseable answer.",
+                )
             if token == "X_PREREQ_Y":
-                edge: Optional[tuple[str, str]] = (node, rec.candidate)
+                edge: Optional[tuple[str, str]] = (node, candidate)
             elif token == "Y_PREREQ_X":
-                edge = (rec.candidate, node)
+                edge = (candidate, node)
             else:
                 edge = None
             calls.append(
                 DemoCall(
                     x=node,
-                    y=rec.candidate,
+                    y=candidate,
                     token=token,
                     edge=edge,
-                    latency_s_pilot=rec.latency_s,
-                    input_tokens=rec.input_tokens,
-                    output_tokens=rec.output_tokens,
-                    user_prompt=rec.user_prompt,
+                    latency_s=issued.response.latency_s,
+                    input_tokens=issued.response.input_tokens,
+                    output_tokens=issued.response.output_tokens,
+                    user_prompt=issued.user_prompt,
                 )
             )
 
@@ -817,15 +886,15 @@ def run_demo(
         lost_narrowing = sum(1 for m in missed if m.cause == "not shortlisted")
         lost_decision = len(missed) - lost_narrowing
 
-        latency = sum(c.latency_s_pilot for c in calls)
+        latency = sum(c.latency_s for c in calls)
         input_tokens = sum(c.input_tokens for c in calls)
         output_tokens = sum(c.output_tokens for c in calls)
-        cache_hits = sum(
-            rec.cache_hit_tokens for rec in served
-        )
-        cache_misses = sum(
-            rec.cache_miss_tokens for rec in served
-        )
+        cache_hits = sum(call_cache for call_cache in (
+            issued.response.cache_hit_tokens for issued in recorder.calls
+        ))
+        cache_misses = sum(call_cache for call_cache in (
+            issued.response.cache_miss_tokens for issued in recorder.calls
+        ))
         cost = estimated_cost_usd(cache_misses, cache_hits, output_tokens)
 
         recall_given = None
@@ -869,10 +938,43 @@ def run_demo(
                 lost_decision=lost_decision,
                 recall_given_shortlist=recall_given,
                 diagnostics=diagnostics,
+                retries=llm_meter.retries,
+                parse_failures=llm_meter.parse_failures,
+                transport_failures=len(llm_meter.failed_calls),
             )
         )
         edges_by_strategy[name] = predicted
 
+    if is_live:
+        total_input = sum(s.recorded_input_tokens for s in report_strategies)
+        total_output = sum(s.recorded_output_tokens for s in report_strategies)
+        total_hits = sum(s.recorded_cache_hit_tokens for s in report_strategies)
+        total_misses = sum(s.recorded_cache_miss_tokens for s in report_strategies)
+        total_latency = sum(s.recorded_latency_s for s in report_strategies)
+        total_cost = sum(s.cost_usd for s in report_strategies)
+        provenance = PilotProvenance(
+            path="(live DeepSeek API)",
+            sha256="",
+            recorded_utc=started.isoformat(),
+            prompt_version=decision_module.PROMPT_VERSION,
+            model=str(getattr(live_client, "model", "")),
+            n_calls=sum(len(s.calls) for s in report_strategies),
+            temperature=float(getattr(live_client, "temperature", 0.0)),
+            thinking_mode=str(getattr(live_client, "thinking_mode", "disabled")),
+            retries=sum(s.retries for s in report_strategies),
+            parse_failures=sum(s.parse_failures for s in report_strategies),
+            transport_failures=sum(s.transport_failures for s in report_strategies),
+            input_tokens=total_input,
+            output_tokens=total_output,
+            cache_hit_tokens=total_hits,
+            cache_miss_tokens=total_misses,
+            estimated_cost_usd=total_cost,
+            cumulative_latency_s=total_latency,
+            system_prompt_recorded=False,
+        )
+    elif provenance is None:
+        raise DemoError(6, "replay report is missing provenance")
+
     subset_of_s1: Optional[bool] = None
     if "brute_force" in edges_by_strategy:
         base = edges_by_strategy["brute_force"]
@@ -910,6 +1012,8 @@ def run_demo(
         subset_of_s1=subset_of_s1,
         embedder_identity=embedder_identity,
         cpu_threads=cpu_threads,
+        mode="live" if is_live else "replay",
+        live_base_url=str(getattr(live_client, "base_url", "")) if is_live else None,
     )
 
 
@@ -1069,30 +1173,54 @@ class Formatter:
             self.add(line)
 
     # -- phases ---------------------------------------------------------
+    def source_tag(self, text: Optional[str] = None) -> str:
+        if self.report.mode == "live":
+            return self.palette.tag_live(text or "[LIVE]")
+        return self.palette.tag_pilot(text or "[PILOT]")
+
     def banner(self) -> None:
         p = self.palette
         r = self.report
         prov = r.provenance
+        live = r.mode == "live"
+        suffix = "LIVE RUN" if live else "PILOT-001 replay"
         self.rule()
-        self.add(" DEFENSE DEMO  ·  one concept insertion, four narrowing strategies   PILOT-001 replay"
-                 .replace("·", self.dot))
+        self.add(
+            " DEFENSE DEMO  ·  one concept insertion, four narrowing strategies"
+            f"   {suffix}".replace("·", self.dot)
+        )
         self.rule()
         self.add(" PROVENANCE")
-        self.add("   LLM decisions  REPLAYED from recorded PILOT-001 calls")
-        self.add("                  (not re-requested, not simulated)")
-        self.add(f"   Cache file     {_display_path(prov.path)}")
-        self.add(
-            f"                  {prov.n_calls} calls {self.dot} sha256 {prov.sha256[:12]}"
-            f"{'...' if self.options.ascii else '…'} {self.dot} recorded {_pilot_start(prov)}"
-        )
-        self.add(
-            f"   Recorded with  {prov.model} {self.dot} prompt {prov.prompt_version}"
-            f" {self.dot} temperature {prov.temperature:g} {self.dot} thinking {prov.thinking_mode}"
-        )
-        self.add(
-            f"                  {prov.retries} retries {self.dot} {prov.parse_failures} parse failures"
-            f" {self.dot} {prov.transport_failures} transport failures"
-        )
+        if live:
+            self.add("   LLM decisions  LIVE calls to the DeepSeek API (not replayed)")
+            self.add(f"   Endpoint       {r.live_base_url or '(unknown)'}")
+            self.add(
+                f"   Model         {prov.model} {self.dot} prompt {prov.prompt_version}"
+                f" {self.dot} temperature {prov.temperature:g} {self.dot} thinking {prov.thinking_mode}"
+            )
+            self.add(
+                f"                 {prov.n_calls} calls {self.dot} {prov.retries} retries"
+                f" {self.dot} {prov.parse_failures} parse failures"
+                f" {self.dot} {prov.transport_failures} transport failures"
+            )
+            self.add("   Network / API  live API used · key read from DEEPSEEK_API_KEY")
+        else:
+            self.add("   LLM decisions  REPLAYED from recorded PILOT-001 calls")
+            self.add("                  (not re-requested, not simulated)")
+            self.add(f"   Cache file     {_display_path(prov.path)}")
+            self.add(
+                f"                  {prov.n_calls} calls {self.dot} sha256 {prov.sha256[:12]}"
+                f"{'...' if self.options.ascii else '…'} {self.dot} recorded {_pilot_start(prov)}"
+            )
+            self.add(
+                f"   Recorded with  {prov.model} {self.dot} prompt {prov.prompt_version}"
+                f" {self.dot} temperature {prov.temperature:g} {self.dot} thinking {prov.thinking_mode}"
+            )
+            self.add(
+                f"                  {prov.retries} retries {self.dot} {prov.parse_failures} parse failures"
+                f" {self.dot} {prov.transport_failures} transport failures"
+            )
+            self.add("   Network / API  none used · no API key read".replace("·", self.dot))
         self.add("   Run live here  corpus load, narrowing, graph update, scoring, timers [LIVE]")
         if r.embedder_identity:
             identity = r.embedder_identity
@@ -1106,17 +1234,25 @@ class Formatter:
             )
         else:
             self.add("   Embedder       not loaded (brute_force needs none)")
-        self.add("   Network / API  none used · no API key read".replace("·", self.dot))
-        self.add(
-            " TAGS  " + p.tag_live() + " measured now   "
-            + p.tag_pilot() + " recorded 2026-10-07"
-        )
-        self.add(
-            "       " + p.tag_calc() + " computed       "
-            + p.tag_gold() + " ground truth (revealed after)"
-        )
+        if live:
+            self.add(
+                " TAGS  " + p.tag_live() + " measured now   "
+                + p.tag_calc() + " computed"
+            )
+            self.add(
+                "       " + p.tag_gold() + " ground truth (revealed after)"
+            )
+        else:
+            self.add(
+                " TAGS  " + p.tag_live() + " measured now   "
+                + p.tag_pilot() + " recorded 2026-10-07"
+            )
+            self.add(
+                "       " + p.tag_calc() + " computed       "
+                + p.tag_gold() + " ground truth (revealed after)"
+            )
         self.add("")
-        self.add_wrapped(REPLAY_NOTICE)
+        self.add_wrapped(LIVE_NOTICE if live else REPLAY_NOTICE)
         self.add("")
 
     def before(self) -> None:
@@ -1230,8 +1366,9 @@ class Formatter:
             )
             self.add(f"            time {self.fmt_ms(s.shortlist_s_live)} {p.tag_live()}")
             self.add("  no LLM calls, no edges")
-            self.add(f"  LLM        0 calls · 0.00 s recorded latency {p.tag_pilot()}")
-            self.add(f"             0 in / 0 out tokens {p.tag_pilot()}")
+            latency_word = "API latency" if self.report.mode == "live" else "recorded latency"
+            self.add(f"  LLM        0 calls · 0.00 s {latency_word} {self.source_tag()}")
+            self.add(f"             0 in / 0 out tokens {self.source_tag()}")
             self.add(f"             cost $0.000000 {p.tag_calc()}")
             self.add(f"             calls vs S1: 100% {p.tag_calc()}")
             self.add(
@@ -1291,7 +1428,7 @@ class Formatter:
         else:
             label = f"{len(s.calls)} calls, {len(visible)} shown"
         label = label.replace(" calls", " call" if len(s.calls) == 1 else " calls")
-        self.add(f"  decisions  {label} {p.tag_pilot()}")
+        self.add(f"  decisions  {label} {self.source_tag()}")
 
         total_calls = len(s.calls)
         for pos in visible:
@@ -1301,12 +1438,17 @@ class Formatter:
             self.add(f"   call {pos + 1:2d}/{total_calls:<2d}  X = {x_text}   Y = {y_text}")
             if not self._first_call_printed:
                 self._first_call_printed = True
-                self.add("             exact prompt sent in PILOT-001 [PILOT]")
+                prompt_label = (
+                    "exact prompt sent in this run"
+                    if self.report.mode == "live"
+                    else "exact prompt sent in PILOT-001"
+                )
+                self.add(f"             {prompt_label} {self.source_tag()}")
                 for line in call.user_prompt.splitlines():
                     self.add(f"             | {line}")
             answer = call.token
             self.add(
-                f"             answer {answer:<12s} {self.fmt_s(call.latency_s_pilot):>7s}"
+                f"             answer {answer:<12s} {self.fmt_s(call.latency_s):>7s}"
                 f"  {call.input_tokens} in / {call.output_tokens} out"
             )
             if call.edge is None:
@@ -1327,15 +1469,16 @@ class Formatter:
             counts[call.token] = counts.get(call.token, 0) + 1
         self.add(
             f"  answers    NONE {counts['NONE']} · X_PREREQ_Y {counts['X_PREREQ_Y']}"
-            f" · Y_PREREQ_X {counts['Y_PREREQ_X']}          {p.tag_pilot()}"
+            f" · Y_PREREQ_X {counts['Y_PREREQ_X']}          {self.source_tag()}"
         )
+        latency_word = "API latency" if self.report.mode == "live" else "recorded latency"
         self.add(
-            f"  LLM        {len(s.calls)} calls · {self.fmt_s(s.recorded_latency_s)} recorded latency"
-            f" {p.tag_pilot()}"
+            f"  LLM        {len(s.calls)} calls · {self.fmt_s(s.recorded_latency_s)} {latency_word}"
+            f" {self.source_tag()}"
         )
         self.add(
             f"             {s.recorded_input_tokens:,} in / {s.recorded_output_tokens:,} out tokens"
-            f" {p.tag_pilot()}"
+            f" {self.source_tag()}"
         )
         self.add(f"             cost ${s.cost_usd:.6f} {p.tag_calc()}")
         self.add(f"             calls vs S1: {s.calls_vs_s1_pct:.0f}% {p.tag_calc()}")
@@ -1449,8 +1592,10 @@ class Formatter:
             f"  {'WORK':<22} {'kept':>7} {'calls':>5} {'vsS1':>5}"
             f" {'LLM lat':>8} {'tokens in/out':>13} {'cost':>9} {'shortlist':>8}"
         )
+        source_label = "[LIVE]" if self.report.mode == "live" else "[PILOT]"
         self.add(
-            "  (LLM latency and tokens are [PILOT]; cost is [CALC]; shortlist time is [LIVE].)"
+            f"  (LLM latency and tokens are {source_label}; cost is [CALC];"
+            " shortlist time is [LIVE].)"
         )
         for s in r.strategies:
             shortlist_n = len(s.shortlist_candidates)
@@ -1537,23 +1682,41 @@ class Formatter:
 
     def limitations(self) -> None:
         self.add("  LIMITATIONS — WHAT THIS DOES NOT PROVE")
-        self.add_wrapped(
-            "Decisions are replayed from PILOT-001 recordings, not re-requested. This is real"
-            " model output for exactly these prompts, recorded on 2026-10-07."
-        )
+        if self.report.mode == "live":
+            self.add_wrapped(
+                "Decisions are live DeepSeek API calls made during this run, not replayed"
+                " recordings. The answers are what the model returned now."
+            )
+        else:
+            self.add_wrapped(
+                "Decisions are replayed from PILOT-001 recordings, not re-requested. This is real"
+                " model output for exactly these prompts, recorded on 2026-10-07."
+            )
         self.add_wrapped(
             "One held-out node, one trial, one repeat. This is an illustration, not a new"
             " result, and it is not part of Chapter 4."
         )
-        self.add_wrapped(
-            "Latency, tokens and cost are recorded values. Only setup, shortlist, update and"
-            " replay times are measured now; replay wall time says nothing about model latency."
-        )
-        self.add_wrapped(
-            "In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a"
-            " pair. In the official runs each strategy made its own live calls, so agreement"
-            " on a pair is not guaranteed there."
-        )
+        if self.report.mode == "live":
+            self.add_wrapped(
+                "Latency, tokens and cost are measured live by this run. Only this single"
+                " insertion is measured; it says nothing about scaling with graph size."
+            )
+        else:
+            self.add_wrapped(
+                "Latency, tokens and cost are recorded values. Only setup, shortlist, update and"
+                " replay times are measured now; replay wall time says nothing about model latency."
+            )
+        if self.report.mode == "live":
+            self.add_wrapped(
+                "In this live run each strategy made its own API calls, so strategies may"
+                " disagree on a pair even though they share the same decision step."
+            )
+        else:
+            self.add_wrapped(
+                "In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a"
+                " pair. In the official runs each strategy made its own live calls, so agreement"
+                " on a pair is not guaranteed there."
+            )
         if self.report.subset_of_s1 is not None:
             self.add_wrapped(
                 "DSA gold is not transitively reduced, so some false positives may be"
@@ -1567,10 +1730,17 @@ class Formatter:
 
     def footer(self) -> None:
         p = self.palette
-        self.add(
-            f"  demo wall time {self.report.wall_s_live:.1f} s {p.tag_live()}   "
-            f"{self.dot} no files written to results/"
-        )
+        if self.report.output_dir:
+            self.add_wrapped(
+                f"demo wall time {self.report.wall_s_live:.1f} s [LIVE]   "
+                f"{self.dot} output {self.report.output_dir}",
+                indent="  ",
+            )
+        else:
+            self.add(
+                f"  demo wall time {self.report.wall_s_live:.1f} s {p.tag_live()}   "
+                f"{self.dot} no files written to results/"
+            )
         self.rule()
 
     def render(self) -> list[str]:
@@ -1622,7 +1792,7 @@ def report_to_json(report: DemoReport) -> dict[str, Any]:
                         "y": c.y,
                         "token": c.token,
                         "edge": list(c.edge) if c.edge else None,
-                        "latency_s_pilot": c.latency_s_pilot,
+                        "latency_s": c.latency_s,
                         "input_tokens": c.input_tokens,
                         "output_tokens": c.output_tokens,
                     }
@@ -1665,10 +1835,13 @@ def report_to_json(report: DemoReport) -> dict[str, Any]:
         )
     return {
         "schema": "demo-trial-1",
+        "mode": report.mode,
+        "live_base_url": report.live_base_url,
         "run": {
             "started_utc": report.started_utc,
             "wall_s_live": report.wall_s_live,
             "argv": list(report.argv),
+            "output_dir": report.output_dir,
         },
         "provenance": {
             **prov,
@@ -1719,7 +1892,7 @@ def report_to_json(report: DemoReport) -> dict[str, Any]:
 
 def build_parser() -> argparse.ArgumentParser:
     parser = argparse.ArgumentParser(
-        description="Offline PILOT-001 replay demo: one insertion, four strategies."
+        description="Replay or live demo: one insertion, four strategies."
     )
     parser.add_argument("--node", default=DEFAULT_NODE)
     parser.add_argument("--strategies", default=None)
@@ -1729,6 +1902,10 @@ def build_parser() -> argparse.ArgumentParser:
     parser.add_argument("--pause", action="store_true")
     parser.add_argument("--show-all-calls", action="store_true")
     parser.add_argument("--json", dest="json_path", default=None)
+    parser.add_argument("--live", action="store_true", help="Make real DeepSeek API calls instead of replay.")
+    parser.add_argument("--confirm", action="store_true", help="Required with --live.")
+    parser.add_argument("--allow-peak", action="store_true", help="Allow a live run inside DeepSeek peak hours.")
+    parser.add_argument("--output-dir", default=None, help="Live run output directory (default: demo_runs/live-<UTC>).")
     parser.add_argument("--check", action="store_true")
     parser.add_argument("--traceback", dest="show_traceback", action="store_true")
     return parser
@@ -1747,6 +1924,93 @@ def _validate_json_path(path_text: str) -> Path:
     return resolved
 
 
+def _validate_live_output_dir(path_text: Optional[str]) -> Path:
+    if path_text:
+        candidate = Path(path_text)
+        if not candidate.is_absolute():
+            candidate = REPO_ROOT / candidate
+    else:
+        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
+        candidate = REPO_ROOT / "demo_runs" / f"live-{stamp}"
+    resolved = candidate.resolve()
+    results_dir = (REPO_ROOT / "results").resolve()
+    if resolved == results_dir or results_dir in resolved.parents:
+        raise DemoError(7, f"refusing to write live output under results/: {candidate}",
+                        "Choose a directory outside the official results tree.")
+    if resolved.exists():
+        if not resolved.is_dir():
+            raise DemoError(7, f"output path is not a directory: {candidate}")
+        if any(resolved.iterdir()):
+            raise DemoError(7, f"refusing to overwrite non-empty output directory: {candidate}",
+                            "Pass a new --output-dir or remove the old demo directory.")
+    else:
+        try:
+            resolved.mkdir(parents=True, exist_ok=True)
+        except OSError as exc:
+            raise DemoError(7, f"cannot create output directory {candidate}: {exc}") from exc
+    return resolved
+
+
+def _build_live_client() -> Any:
+    from graph_insertion.llm import DeepSeekClient
+
+    try:
+        return DeepSeekClient()
+    except ValueError as exc:
+        raise DemoError(5, f"cannot start live run: {exc}",
+                        "Set DEEPSEEK_API_KEY, or omit --live to use the offline replay.") from exc
+
+
+def _live_preflight(selected: Sequence[str], corpus: Any) -> int:
+    from graph_insertion.strategy import candidate_upper_bound
+
+    n_existing = corpus.graph.num_nodes() - 1
+    max_calls = 0
+    for name in selected:
+        probe = STRATEGY_FACTORIES[name](**DEMO_PARAMS[name])
+        max_calls += candidate_upper_bound(probe, n_existing)
+    estimated = max_calls * ((220 * PRICE_IN_CACHE_MISS + 16 * PRICE_OUT) / 1_000_000.0)
+    print("LIVE RUN PRE-FLIGHT")
+    print(f"  corpus      {corpus.name}  ({n_existing} existing concepts)")
+    print(f"  strategies  {', '.join(selected)}")
+    print(f"  max calls   {max_calls}  (upper bound; actual depends on shortlists)")
+    print(f"  cost bound  ${estimated:.4f}  (off-peak prices, D-36)")
+    return max_calls
+
+
+def _write_live_outputs(
+    report: DemoReport,
+    output_dir: Path,
+    *,
+    ascii_mode: bool,
+    show_all_calls: bool,
+    argv: Sequence[str],
+) -> None:
+    plain = format_report(
+        report,
+        FormatOptions(color=False, ascii=ascii_mode, show_all_calls=show_all_calls),
+    )
+    (output_dir / "transcript.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")
+    (output_dir / "demo.json").write_text(
+        json.dumps(report_to_json(report), indent=2) + "\n",
+        encoding="utf-8",
+    )
+    meta = {
+        "schema": "demo-trial-live-meta-1",
+        "mode": "live",
+        "started_utc": report.started_utc,
+        "wall_s_live": report.wall_s_live,
+        "argv": list(argv),
+        "node": report.node,
+        "strategies": report.selected,
+        "model": report.provenance.model,
+        "base_url": report.live_base_url,
+        "output_dir": str(output_dir),
+        "files": ["transcript.txt", "demo.json", "run_meta.json"],
+    }
+    (output_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
+
+
 def _color_enabled(no_color: bool) -> bool:
     if no_color or os.environ.get("NO_COLOR") is not None:
         return False
@@ -1757,7 +2021,13 @@ def _print_check(ok: bool, label: str, detail: str) -> None:
     print(f"{'OK  ' if ok else 'FAIL'} {label}: {detail}")
 
 
-def run_checks(node: str, selected: Sequence[str], pilot_dir: str | Path) -> int:
+def run_checks(
+    node: str,
+    selected: Sequence[str],
+    pilot_dir: str | Path,
+    *,
+    live: bool = False,
+) -> int:
     failures = 0
     try:
         corpus = load_corpus(CORPUS_NAME)
@@ -1767,14 +2037,24 @@ def run_checks(node: str, selected: Sequence[str], pilot_dir: str | Path) -> int
         _print_check(False, "corpus", f"{type(exc).__name__}: {exc}")
         return 4
 
-    try:
-        prov, by_prompt = load_pilot(resolve_pilot_dir(pilot_dir), corpus=corpus)
-        _print_check(True, "pilot cache", f"{prov.n_calls} calls, sha256 {prov.sha256[:12]}")
-        _print_check(True, "pilot provenance", f"prompt {prov.prompt_version}, model {prov.model}, "
-                                              f"cost ${prov.estimated_cost_usd:.6f}")
-    except DemoError as exc:
-        _print_check(False, "pilot cache", exc.message)
-        return 3
+    if live:
+        try:
+            client = _build_live_client()
+            _print_check(True, "live API", f"model={client.model}, base_url={client.base_url} "
+                                           f"(no network call made)")
+            _print_check(True, "live key", "DEEPSEEK_API_KEY present")
+        except DemoError as exc:
+            _print_check(False, "live API", exc.message)
+            return 5
+    else:
+        try:
+            prov, by_prompt = load_pilot(resolve_pilot_dir(pilot_dir), corpus=corpus)
+            _print_check(True, "pilot cache", f"{prov.n_calls} calls, sha256 {prov.sha256[:12]}")
+            _print_check(True, "pilot provenance", f"prompt {prov.prompt_version}, model {prov.model}, "
+                                                  f"cost ${prov.estimated_cost_usd:.6f}")
+        except DemoError as exc:
+            _print_check(False, "pilot cache", exc.message)
+            return 3
 
     nodes = sorted(corpus.graph.nodes())
     if node in nodes:
@@ -1803,15 +2083,59 @@ def main(argv: Optional[Sequence[str]] = None) -> int:
     try:
         selected = parse_strategies(args.strategies)
         if args.check:
-            return run_checks(args.node, selected, args.pilot_dir)
+            return run_checks(args.node, selected, args.pilot_dir, live=args.live)
+
+        live = bool(args.live)
+        if live and args.output_dir is None:
+            pass  # default is created below
+        if not live and args.output_dir:
+            raise DemoError(2, "--output-dir requires --live",
+                            "Omit --output-dir for replay, or add --live.")
+        if live and not args.confirm:
+            raise DemoError(2, "live run requires --confirm",
+                            "Add --confirm after checking the pre-flight estimate.")
+
+        output_dir: Optional[Path] = None
+        live_client: Any = None
+        corpus: Any = None
+        if live:
+            from graph_insertion.schedule import format_peak_status, window_intersects_peak
+
+            now_utc = datetime.now(timezone.utc)
+            if window_intersects_peak(now_utc, 120) and not args.allow_peak:
+                raise DemoError(
+                    2,
+                    "live run refused: the execution window overlaps DeepSeek peak pricing",
+                    format_peak_status(now_utc) + "\nUse --allow-peak only if you accept peak prices.",
+                )
+            live_client = _build_live_client()
+            try:
+                corpus = load_corpus(CORPUS_NAME)
+            except Exception as exc:
+                raise DemoError(4, f"cannot load DSA corpus: {type(exc).__name__}: {exc}") from exc
+            output_dir = _validate_live_output_dir(args.output_dir)
+            try:
+                _live_preflight(selected, corpus)
+            except DemoError:
+                raise
+            except Exception as exc:
+                raise DemoError(5, f"cannot prepare live strategies: {type(exc).__name__}: {exc}") from exc
+            print(f"  peak check  {format_peak_status(now_utc).splitlines()[-1]}")
+            print(f"  output dir  {output_dir}")
+            print("")
 
         json_path = _validate_json_path(args.json_path) if args.json_path else None
         report = run_demo(
             node=args.node,
             selected=selected,
             pilot_dir=args.pilot_dir,
+            corpus=corpus,
+            live_client=live_client,
             argv=list(argv) if argv is not None else sys.argv[1:],
         )
+        if output_dir is not None:
+            report.output_dir = str(output_dir)
+
         options = FormatOptions(
             color=_color_enabled(args.no_color),
             ascii=args.ascii,
@@ -1829,11 +2153,22 @@ def main(argv: Optional[Sequence[str]] = None) -> int:
             print(line)
             if line.startswith(" PHASE "):
                 seen_phase = True
+        if output_dir is not None:
+            _write_live_outputs(
+                report,
+                output_dir,
+                ascii_mode=args.ascii,
+                show_all_calls=args.show_all_calls,
+                argv=list(argv) if argv is not None else sys.argv[1:],
+            )
         if json_path is not None:
             json_path.write_text(
                 json.dumps(report_to_json(report), indent=2) + "\n",
                 encoding="utf-8",
             )
+        if output_dir is not None:
+            print(f"\nLIVE OUTPUT: {output_dir}")
+            print("  transcript.txt  demo.json  run_meta.json")
         return 0
     except DemoError as exc:
         if args.show_traceback:
diff --git c/tests/test_demo_trial.py i/tests/test_demo_trial.py
index 5ad42c6..886c2e8 100644
--- c/tests/test_demo_trial.py
+++ i/tests/test_demo_trial.py
@@ -28,6 +28,7 @@ from graph_insertion.graph_representation import (
     GoldJudgmentSet,
     SourceKind,
 )
+from graph_insertion.llm import LLMResponse
 from graph_insertion.scoring import NodeScore
 
 
@@ -516,7 +517,7 @@ def make_strategy(
             y=f"c{i}",
             token=tokens[i],
             edge=(("n2", f"c{i}") if tokens[i] == "X_PREREQ_Y" else None),
-            latency_s_pilot=1.0,
+            latency_s=1.0,
             input_tokens=153,
             output_tokens=5,
             user_prompt=f"prompt {i}",
@@ -795,6 +796,142 @@ class TestCLI:
         assert "Traceback" not in result.stderr
 
 
+# ---------------------------------------------------------------------------
+# Live mode (fake client; no network)
+# ---------------------------------------------------------------------------
+
+
+class FakeLiveClient:
+    model = "deepseek-flash"
+    base_url = "https://api.deepseek.com"
+    temperature = 0.0
+    thinking_mode = "disabled"
+
+    def __init__(self, token_override=None):
+        self.token_override = token_override
+
+    def complete(self, system: str, user: str) -> LLMResponse:
+        x = y = None
+        for line in user.splitlines():
+            if line.startswith("Concept X: "):
+                x = line[11:].replace(" ", "_")
+            elif line.startswith("Concept Y: "):
+                y = line[11:].replace(" ", "_")
+        token = self.token_override or response_for(x, y)
+        return LLMResponse(
+            text=token,
+            input_tokens=150,
+            output_tokens=5,
+            latency_s=0.5,
+            model_id="deepseek-flash",
+        )
+
+    def record_parse_failure(self, text: str) -> None:
+        pass
+
+
+class TestLiveMode:
+    def test_live_orchestration_marks_live_and_uses_replay_free_path(self, tmp_path):
+        corpus = make_toy_corpus()
+        report = demo.run_demo(
+            node="n2",
+            selected=["brute_force"],
+            corpus=corpus,
+            live_client=FakeLiveClient(),
+            raw_embedder=FakeEmbedder(dim=32, seed=42),
+            argv=["--live"],
+        )
+        assert report.mode == "live"
+        assert report.provenance.path == "(live DeepSeek API)"
+        assert report.provenance.model == "deepseek-flash"
+        assert report.provenance.n_calls == 5
+        assert report.provenance.cumulative_latency_s == pytest.approx(2.5)
+        lines = demo.format_report(report, demo.FormatOptions(color=False))
+        text = "\n".join(lines)
+        assert "LIVE RUN" in text
+        assert demo.LIVE_NOTICE in text.replace("\n  ", " ").replace("\n", " ")
+        assert "[PILOT]" not in text
+        assert "5 calls · 2.50 s API latency [LIVE]" in text
+
+    def test_live_unparseable_response_fails_closed(self):
+        corpus = make_toy_corpus()
+        with pytest.raises(demo.DemoError) as exc:
+            demo.run_demo(
+                node="n2",
+                selected=["brute_force"],
+                corpus=corpus,
+                live_client=FakeLiveClient(token_override="MAYBE"),
+                raw_embedder=FakeEmbedder(dim=32, seed=42),
+                argv=["--live"],
+            )
+        assert exc.value.exit_code == 6
+
+    def test_live_output_dir_refuses_nonempty(self, tmp_path):
+        target = tmp_path / "out"
+        target.mkdir()
+        (target / "keep.txt").write_text("keep", encoding="utf-8")
+        with pytest.raises(demo.DemoError) as exc:
+            demo._validate_live_output_dir(str(target))
+        assert exc.value.exit_code == 7
+        assert (target / "keep.txt").read_text(encoding="utf-8") == "keep"
+
+    def test_live_outputs_written(self, tmp_path):
+        corpus = make_toy_corpus()
+        report = demo.run_demo(
+            node="n2",
+            selected=["brute_force"],
+            corpus=corpus,
+            live_client=FakeLiveClient(),
+            raw_embedder=FakeEmbedder(dim=32, seed=42),
+            argv=["--live"],
+        )
+        output_dir = demo._validate_live_output_dir(str(tmp_path / "live"))
+        report.output_dir = str(output_dir)
+        demo._write_live_outputs(
+            report, output_dir, ascii_mode=False, show_all_calls=False, argv=["--live"]
+        )
+        assert (output_dir / "transcript.txt").is_file()
+        assert (output_dir / "demo.json").is_file()
+        assert (output_dir / "run_meta.json").is_file()
+        meta = json.loads((output_dir / "run_meta.json").read_text(encoding="utf-8"))
+        assert meta["mode"] == "live"
+        assert meta["model"] == "deepseek-flash"
+
+    def test_live_cli_requires_confirm(self, capsys):
+        assert demo.main(["--live", "--strategies", "s1"]) == 2
+        assert "--confirm" in capsys.readouterr().err
+
+    def test_live_cli_missing_key_exit_5(self, monkeypatch, capsys):
+        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
+        monkeypatch.setattr(
+            "graph_insertion.schedule.window_intersects_peak", lambda *args: False
+        )
+        assert demo.main(["--live", "--confirm", "--strategies", "s1"]) == 5
+        assert "DEEPSEEK_API_KEY" in capsys.readouterr().err
+
+    def test_check_live_missing_key_exit_5(self, monkeypatch):
+        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
+        assert demo.main(["--check", "--live", "--strategies", "s1"]) == 5
+
+    def test_live_cli_end_to_end_with_fake_client(self, tmp_path, monkeypatch, capsys):
+        monkeypatch.setattr(demo, "_build_live_client", lambda: FakeLiveClient())
+        monkeypatch.setattr(
+            "graph_insertion.schedule.window_intersects_peak", lambda *args: False
+        )
+        output_dir = tmp_path / "live-run"
+        code = demo.main([
+            "--live", "--confirm", "--strategies", "s1",
+            "--output-dir", str(output_dir), "--no-color",
+        ])
+        assert code == 0
+        assert (output_dir / "transcript.txt").is_file()
+        assert (output_dir / "demo.json").is_file()
+        assert (output_dir / "run_meta.json").is_file()
+        transcript = (output_dir / "transcript.txt").read_text(encoding="utf-8")
+        assert "LIVE RUN" in transcript
+        assert "LIVE OUTPUT:" in capsys.readouterr().out
+
+
 # ---------------------------------------------------------------------------
 # Group 6 — MiniLM integration
 # ---------------------------------------------------------------------------
```

---

## 7. Items for Luke

1. To exercise the real API, set `DEEPSEEK_API_KEY` and run
   `--check --live`, then `--live --confirm`; the default output lands under
   `demo_runs/live-<UTC>/`.
2. Live mode costs roughly one tenth of a cent for the default 48-call trial at
   off-peak prices; the pre-flight prints a 76-call upper bound.
3. Branch `task/DEMO-002` is ready to merge; no merge was performed before this
   report was written.
