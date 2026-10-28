# DEMO-001 — Operator Guide

How to run and operate the defense demo (`scripts/demo_trial.py`). The demo is
offline and deterministic: it replays real recorded PILOT-001 answers. No API
key, no network, and no model download are used at demo time.

For the implementation and verification record, see
[`docs/reports/DEMO-001-claude-code-defense-demo-trial.md`](../../reports/DEMO-001-claude-code-defense-demo-trial.md).
For a one-paragraph summary, see the "Defense Demo" section of
[`scripts/README.md`](../../../scripts/README.md).

---

## 1. Before the defense: one-time setup

Run from the repository root.

1. **Use the pinned environment.** The demo needs `sentence-transformers`
   6.1.0, `faiss-cpu` 1.15.1, and the cached `all-MiniLM-L6-v2` model at the
   pinned revision. On this machine that is `.venv-ann/`.
2. **Confirm the pilot cache is present:**
   `results/pilot/20261007_053743Z/raw_calls.jsonl` and `summary.json`.
3. **Confirm the dataset clone is present:**
   `repositories/dataset/EKG-Dataset/` (ignored by git, so it is not in a fresh
   worktree; the main checkout has it).
4. **Run the pre-flight check.** This loads the corpus, validates the cache and
   provenance, checks the node, and loads the embedder. It does not run a trial.

```bash
.venv-ann/bin/python scripts/demo_trial.py --check
```

Expected: five `OK` lines, exit 0. If the embedder line fails, fix the
environment before the defense; the demo never downloads the model.

5. **Rehearse once end-to-end.** Do this while online or offline; the demo sets
   `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.

```bash
.venv-ann/bin/python scripts/demo_trial.py --no-color | less
```

6. **Record the smoke evidence.** Optional but useful:

```bash
.venv-ann/bin/python scripts/demo_trial.py --check
.venv-ann/bin/python scripts/demo_trial.py --no-color --json /tmp/demo.json
```

`--json` refuses to overwrite an existing file and refuses any path under
`results/`.

---

## 2. The default run

```bash
.venv-ann/bin/python scripts/demo_trial.py
```

What it does: one leave-one-out insertion on the DSA corpus. The held-out
concept is `binary_search_tree` by default. The existing graph is 28 concepts
and 47 edges; the full gold graph is 29 concepts and 54 edges.

The transcript has three phases:

| Phase      | What the panel sees                                                                                                                                                                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **BEFORE** | The research question, corpus, hidden gold neighbourhood, the shared decision prompt, the four strategies and the cost formula.                                                                        |
| **WHILE**  | Per strategy: setup time, shortlist size and narrowing, candidate ranking, sampled decision calls with exact prompts, recorded answers, calls, recorded model latency, tokens, cost, and graph update. |
| **AFTER**  | Gold neighbourhood revealed, TP/FP/FN edges, missed-edge causes, precision/recall/F1, shortlist recall, cross-strategy tables, takeaways and limitations.                                              |

Metric tags: `[LIVE]` measured now, `[PILOT]` recorded on 2026-10-07, `[CALC]`
derived from recorded values, `[GOLD]` ground truth shown only in AFTER.

Expected default result (P8, reproduced by the test suite):

| strategy                      | shortlist | calls |   F1 | TP/FP/FN |
| ----------------------------- | --------: | ----: | ---: | -------: |
| S1 brute force                |     28/28 |    28 | .667 |    4/1/3 |
| S2 embedding threshold (θ=.6) |      1/28 |     1 | .250 |    1/0/6 |
| S3 ANN retrieval (k=10)       |     10/28 |    10 | .727 |    4/0/3 |
| S4 bounded bucket (5..10)     |      9/28 |     9 | .250 |    1/0/6 |

Runtime: about 7–10 seconds including model load on this machine; process wall
about 8–11 seconds. Well under 30 seconds.

---

## 3. Flags you are likely to use

```bash
# One strategy or a subset, always printed in S1-S4 order
.venv-ann/bin/python scripts/demo_trial.py --strategies s1,s3

# A different held-out node (must exist in DSA)
.venv-ann/bin/python scripts/demo_trial.py --node graph

# Show every decision call (brute force has 28)
.venv-ann/bin/python scripts/demo_trial.py --show-all-calls

# Plain ASCII (useful if the projector/font lacks box-drawing glyphs)
.venv-ann/bin/python scripts/demo_trial.py --ascii

# Wait for Enter between BEFORE, WHILE and AFTER
.venv-ann/bin/python scripts/demo_trial.py --pause

# Disable colour explicitly, or set NO_COLOR
.venv-ann/bin/python scripts/demo_trial.py --no-color

# Use a different pilot directory (resolved against the repo root)
.venv-ann/bin/python scripts/demo_trial.py --pilot-dir results/pilot/20261007_053743Z

# Machine-readable report (must be outside results/ and must not already exist)
.venv-ann/bin/python scripts/demo_trial.py --json /tmp/demo.json

# Show a Python traceback on failure (debugging only)
.venv-ann/bin/python scripts/demo_trial.py --traceback
```

Colour appears only when stdout is a TTY and neither `--no-color` nor
`NO_COLOR` is set. Piped output is plain automatically.

### Suggested defense presentation

1. Run `--check` first, on screen, so the panel sees the provenance and cache
   fingerprint pass.
2. Run the default command with `--pause` if you want to talk between phases.
3. During WHILE, point at the shortlist size and call count; do not read every
   call. `--show-all-calls` is for Q&A, not the main run.
4. During AFTER, point at shortlist recall first, then F1. The story is
   two-stage: narrowing decides what the model is allowed to see; the shared
   decision step decides the edges.
5. Use `--strategies s1,s3` if time is short; it keeps the strongest contrast.

### Useful Q&A counter-nodes

The default node is favourable to narrowing (`binary_search_tree` ranks 5th of
29 by `F1(S3) - F1(S1)`). If a panelist asks for a counterexample:

```bash
# Brute force clearly beats S3: S1 F1 1.000 vs S3 F1 0.000
.venv-ann/bin/python scripts/demo_trial.py --node bellman_ford_algorithm --strategies s1,s3

# S2 returns an empty shortlist: no calls, no edges
.venv-ann/bin/python scripts/demo_trial.py --node graph --strategies s2
```

Both are genuine replay results from the same cache, not special cases.

---

## 3A. Live mode (optional, real API calls)

Default remains replay. Add `--live` to make real DeepSeek calls for the same
single-node, four-strategy trial. It is still one insertion per strategy, not a
size sweep.

```bash
# Pre-flight only: checks key, model, corpus, node, embedder; no network call
.venv-ann/bin/python scripts/demo_trial.py --check --live

# Real run. --confirm is mandatory.
export DEEPSEEK_API_KEY=...
.venv-ann/bin/python scripts/demo_trial.py --live --confirm

# Choose the output directory yourself
.venv-ann/bin/python scripts/demo_trial.py --live --confirm \
    --output-dir demo_runs/my-live-run

# Allow peak-priced execution (otherwise a peak window is refused)
.venv-ann/bin/python scripts/demo_trial.py --live --confirm --allow-peak
```

What changes in live mode:

- Every answer is a fresh DeepSeek response. The replay cache is not read.
- Tags switch from `[PILOT]` to `[LIVE]` for answers, latency and tokens.
- The banner says `LIVE RUN` and prints the endpoint, model, prompt version,
  temperature, thinking mode and call/retry counts.
- Default call count is about 48 (S1 28, S2 1, S3 10, S4 9 on the default node);
  the pre-flight prints a 76-call upper bound and a cost bound. At off-peak
  prices the default run is on the order of one tenth of a cent.
- Embeddings are still computed locally with the pinned MiniLM model. Only the
  LLM transport is live.
- Peak guard: a live run whose execution window overlaps DeepSeek peak pricing
  is refused unless `--allow-peak` is passed ([D-37]).
- Safety: `--confirm` is mandatory, so a stray `--live` cannot spend money.

Output is always written to a new directory, never over an existing one:

```text
demo_runs/live-<UTC timestamp>/
  transcript.txt   full no-colour transcript
  demo.json        same machine-readable record as --json
  run_meta.json    mode, model, endpoint, argv, node, strategies, wall time
```

`--output-dir DIR` overrides the location. A non-empty directory is refused
(exit 7), and so is any path under `results/`. `demo_runs/` is gitignored.
The terminal still prints the transcript and ends with `LIVE OUTPUT: <dir>`.

Live limitations are printed in the transcript: one node, one trial, no
scaling claim, and each strategy made its own calls, so strategies may disagree
on a pair even though they share the decision step.

---

## 4. What to say, and what not to say

Say:

- "The answers on screen are real recorded DeepSeek answers from PILOT-001 on
  2026-10-07, for exactly these prompts. The program looks them up instead of
  calling the API."
- "Narrowing, graph update, the decision step and scoring run live."
- "Latency, tokens and cost shown here are the recorded values, not
  measurements from this run."
- "This is one node, one trial. It illustrates the pipeline; the thesis
  evidence is the full runs."

If running `--live`, say instead:

- "This run is making live DeepSeek calls now; every answer is fresh."
- "Embeddings are still local; only the LLM transport is live."
- "This is still one node and one trial, not a new empirical result."

Do not say:

- That replay mode is making live API calls. It is not.
- That the shown latency is this machine's current latency. It is not.
- That the demo is a new empirical result or part of Chapter 4. It is not.
- That replay agreement proves the official runs agree. The official accuracy
  runs made their own live calls. Replay matches S2 and S3 exactly; S1 and S4
  each differ by one predicted edge from the 2026-10-18 accuracy records.

---

## 5. Exit codes and troubleshooting

| Exit | Meaning | What to do |
|---:|---|---|
| 0 | Success | Continue. |
| 2 | Usage error (bad/duplicate/unknown `--strategies`) | Use `s1`–`s4` or the canonical names. |
| 3 | Pilot cache/provenance failure | Restore the accepted PILOT-001 artifacts; do not edit the cache. The SHA-256 and prompt-version checks are fail-closed. |
| 4 | Corpus or node problem | Check `repositories/dataset/EKG-Dataset/`; use a node name from the DSA corpus. Close matches are printed. |
| 5 | Missing dependency/embedder/API key | Use `.venv-ann`; the model must already be cached. Live mode also needs `DEEPSEEK_API_KEY`. The demo never downloads. |
| 6 | Internal consistency check failed | A production path, edge rebuild, label sum or subset invariant disagreed. Do not present the run; report it. |
| 7 | Refused `--json` path | Pick a new path outside `results/` whose parent exists. |

Common fixes:

- **`ModuleNotFoundError: sentence_transformers` or `faiss`** — run with
  `.venv-ann/bin/python`, not system Python.
- **Live mode exits 5 with `DEEPSEEK_API_KEY`** — export the key or omit
  `--live`; `--check --live` checks it without making a call.
- **Live mode exits 2 for peak pricing** — wait for off-peak, or pass
  `--allow-peak` and accept peak rates.
- **Model load fails offline** — the cached MiniLM model is missing. Restore the
  cache; do not unset the offline variables to force a download during a
  defense.
- **Dataset not found** — the ignored `repositories/` clone is absent (common in
  a fresh worktree). Run from the main checkout or restore the clone.
- **`node ... is not in the DSA corpus`** — the hint lists close matches.
- **Output looks garbled on the projector** — add `--ascii`; if colour is
  distracting, add `--no-color`.
- **Output is too long for one screen** — use `--strategies s1,s3`, or page it:
  `... | less -R`.

---

## 6. What is verified, and what is not

Verified by the test suite and the DEMO-001 report:

- 812/812 prompts reproduce byte-exactly; cache SHA-256 is pinned.
- Default P8 table reproduced exactly.
- Offline run under `unshare -rn`; no API key read.
- Deterministic non-volatile JSON across two runs.
- No writes under `results/`; pilot artifact SHA unchanged.
- Formatter width <= 88 columns for every DSA node in both Unicode and ASCII.
- 59 new tests; full runnable suite 795 passed, 3 skipped.

Not verified or not claimed:

- The official accuracy-run decisions for S1/S4 are not identical to the pilot
  replay (one edge each). The demo is faithful to PILOT-001, not to the later
  live runs.
- The demo is not a re-run of the 24-run campaign, not a Chapter 4 result, and
  not evidence about amortised cost.
- It does not test a second corpus or a second held-out node simultaneously.

---

## 7. If the cache or prompt ever changes

The demo is deliberately fail-closed. If the PILOT-001 cache is re-recorded or
`decision.SYSTEM_PROMPT` changes, the run exits 3. Do not loosen the checks for
a defense. The correct path is:

1. Re-record and re-accept the pilot under a new task.
2. Update `PILOT_RAW_CALLS_SHA256` and `SYSTEM_PROMPT_SHA256` in
   `scripts/demo_trial.py`.
3. Update the regression values in `tests/test_demo_trial.py`.
4. Record a new decision entry; do not edit D-99 silently.

The current pins are:

- Cache SHA-256:
  `879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008`
- System prompt SHA-256:
  `32932d476b8cdac7026520cd9e1906a8cca9333d2945ad569fa8a7feb2b3d571`

---

## 8. Source-code walkthrough for panelists

Use symbol names, not line numbers; line numbers drift. Start in
`scripts/demo_trial.py`, then follow the production call path.

### 8.1 Files to open, and what to point at

| File                                                    | Symbols to show                                                               | What to say                                                                                                                                                            |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/demo_trial.py`                                 | `run_demo`, `ReplayLLMClient.complete`, `RecordingLLMClient`, `load_pilot`, `Formatter.while_block`, `_write_live_outputs` | This is demo-only orchestration. It loads the corpus, loops over strategies, calls production `insert_node`, and formats the transcript. Live mode wraps the API client with a recorder and writes a run directory. |
| `src/graph_insertion/strategy.py`                       | `Shortlist`, `InsertionMetrics`, `insert_node`                                | The canonical insertion driver. It times narrowing, calls the shared decision step, validates the edges, mutates the graph, updates the strategy, and records metrics. |
| `src/graph_insertion/decision.py`                       | `SYSTEM_PROMPT`, `parse_token`, `PairwiseDecisionStep.decide`                 | The one step shared by all strategies: one model call per candidate, one of three tokens, mapped to a canonical prerequisite edge.                                     |
| `src/graph_insertion/strategies/brute_force.py`         | `BruteForceStrategy.shortlist`                                                | The control: every existing concept is sent to the model. This is why S1 makes exactly `n` calls.                                                                      |
| `src/graph_insertion/strategies/embedding_threshold.py` | `EmbeddingThresholdStrategy.setup`, `.shortlist`, `.on_inserted`              | S2: cache all embeddings, keep only cosine above theta, append the new vector after insertion.                                                                         |
| `src/graph_insertion/strategies/ann_retrieval.py`       | `AnnRetrievalStrategy.setup`, `.shortlist`, `.on_inserted`                    | S3: build an HNSW index, retrieve top-k, add the new vector to the index after insertion.                                                                              |
| `src/graph_insertion/strategies/bounded_bucket.py`      | `BoundedBucketStrategy.shortlist`, `._locate_home`, `._insert_entry`          | S4: hash the new vector, find its home segment, shortlist only that segment, split when it overflows.                                                                  |
| `src/graph_insertion/strategies/registry.py`            | `STRATEGY_FACTORIES`                                                          | One place maps CLI strategy names to classes and default parameters.                                                                                                   |
| `src/graph_insertion/scoring.py`                        | `score_node_insertion`, `NodeScore`                                           | Turns predicted edges and the shortlist into TP/FP/FN, precision/recall/F1 and shortlist recall. Unjudged DSA pairs are excluded, with a sensitivity variant.          |
| `src/graph_insertion/loader.py`                         | `load_corpus`, `CORPUS_DOMAIN_CONTEXT_MAP`                                    | Parses the gold triples, applies the verified column orientation, and supplies the domain string for the prompt.                                                       |
| `src/graph_insertion/graph_representation.py`           | `ConceptGraph`, `oriented_edge`, `embed_text`                                 | Stores the graph; canonical edge `(prereq, dependent)` always means prereq → dependent; embeddings use bare names with spaces.                                         |
| `src/graph_insertion/embedding.py`                      | `MeteredEmbedder`                                                             | Counts embedding calls and time. This is how the demo proves S2–S4 embed the new concept once, not repeatedly.                                                         |
| `src/graph_insertion/llm.py`                            | `LLMResponse`, `MeteredLLMClient`                                             | The transport interface. The demo replaces the client, not the decision step or the meter.                                                                             |
| `src/graph_insertion/embedding_minilm.py`               | `MiniLMEmbedder`                                                              | Pinned model, revision and sentence-transformers version; fail-closed.                                                                                                 |
| `src/graph_insertion/cpu_threads.py`                    | `pin_cpu_threads`                                                             | Pins PyTorch to one thread for comparable embedding latency.                                                                                                           |
| `docs/context/strategy-interface.md`                    | Strategy lifecycle and timing rules                                           | The written contract; use it if a panelist asks what a strategy is allowed to do.                                                                                      |

### 8.1a Symbol cheat sheet

One-line explanations for every symbol in the table above.

**Demo-only (`scripts/demo_trial.py`)**

- `run_demo` — Loads the corpus and either the replay cache or a live client,
  runs one insertion per selected strategy, and returns the report object used
  by both the transcript and JSON.
- `load_pilot` — Validates the recorded cache byte-for-byte (SHA, field types,
  812 pairs, sums) and returns provenance plus a prompt-to-answer map. Fails
  closed; no fallback.
- `ReplayLLMClient.complete` — Looks up the exact `user_prompt` in that map and
  returns an `LLMResponse`; a missing prompt raises instead of inventing one.
- `RecordingLLMClient` — Wraps either the replay client or the live DeepSeek
  client and stores every prompt/response pair in order so the formatter can
  show calls without changing the decision step.
- `_write_live_outputs` — Writes `transcript.txt`, `demo.json` and
  `run_meta.json` into the new live output directory.
- `Formatter.while_block` — Renders one strategy's WHILE section: setup,
  shortlist, candidate ranking, sampled calls, answers, calls, latency, tokens,
  cost and graph update, with `[LIVE]`/`[PILOT]`/`[CALC]` tags.

**Production driver (`src/graph_insertion/strategy.py`)**

- `Shortlist` — The strategy's output: an ordered tuple of candidate names and
  an optional tuple of matching scores.
- `InsertionMetrics` — One insertion's counters: graph size, shortlist size,
  LLM calls, embedding calls and time, shortlist/decision/apply/update/total
  time, validation time and diagnostics.
- `insert_node` — The canonical pipeline: validate inputs, time the shortlist,
  call the shared decision step, validate edges, mutate the graph, call
  `on_inserted`, and return `InsertionResult` with metrics.

**Shared decision step (`src/graph_insertion/decision.py`)**

- `SYSTEM_PROMPT` — The fixed v2 instruction: prerequisite means direct or
  indirect, answer with exactly one token, names only.
- `parse_token` — Normalises a raw completion (strip/uppercase) to
  `X_PREREQ_Y`, `Y_PREREQ_X`, `NONE`, or `None`.
- `PairwiseDecisionStep.decide` — Makes one sequential call per candidate and
  maps the token to a canonical edge or no edge.

**Strategies**

- `BruteForceStrategy.shortlist` — Returns every existing node, alphabetically,
  with uniform zero scores; S1 therefore makes exactly `n` calls.
- `EmbeddingThresholdStrategy.setup` — Embeds and L2-normalises all nodes into a
  matrix; `.shortlist` embeds the new name once and keeps cosine `> theta`;
  `.on_inserted` appends the cached vector without re-embedding.
- `AnnRetrievalStrategy.setup` — Builds the HNSW index over normalised vectors;
  `.shortlist` retrieves top-k; `.on_inserted` adds the cached vector to the
  index.
- `BoundedBucketStrategy.shortlist` — Hashes the query, finds its home segment,
  and scores only that segment's members.
- `BoundedBucketStrategy._locate_home` — Binary-searches segment boundaries and,
  when the query falls between segments, chooses the nearer neighbour.
- `BoundedBucketStrategy._insert_entry` — Inserts the new entry in sorted order
  and splits the segment at its midpoint if it exceeds `s_max`.
- `STRATEGY_FACTORIES` — Maps strategy names to factory functions and their
  default parameters.

**Accuracy (`src/graph_insertion/scoring.py`)**

- `score_node_insertion` — Compares predicted canonical edges and the shortlist
  with the gold graph and judgments, producing TP/FP/FN, precision, recall, F1,
  shortlist recall, unjudged-pair exclusion and the sensitivity variant.
- `NodeScore` — The per-trial dataclass holding those metrics.

**Data (`loader.py`, `graph_representation.py`)**

- `load_corpus` — Discovers and parses a corpus into `ConceptGraph` plus
  `GoldJudgmentSet`, applying the verified delimiter and column orientation.
- `CORPUS_DOMAIN_CONTEXT_MAP` — Maps a corpus name to the graph-level subject
  string placed in the decision prompt.
- `ConceptGraph` — NetworkX-backed graph wrapper; nodes are bare names, an edge
  `(u, v)` means u is a prerequisite of v, and `without_node` makes the
  leave-one-out copy.
- `oriented_edge` — Converts a file row into canonical `(prereq, dependent)`;
  gold files use `(col2, col1)`, example MEKG files use `(col1, col2)`.
- `embed_text` — Converts a concept name to its embedding text by replacing
  underscores with spaces; no domain context is added.

**Embedding and transport (`embedding.py`, `llm.py`, `embedding_minilm.py`, `cpu_threads.py`)**

- `MeteredEmbedder` — Counts embedding calls, texts and seconds; the demo uses
  it to prove the new concept is embedded once.
- `LLMResponse` — The transport result: text, token counts, latency, model ID
  and attempts.
- `MeteredLLMClient` — Wraps any client to count calls, retries, tokens, latency
  and parse failures.
- `MiniLMEmbedder` — The pinned all-MiniLM-L6-v2 backend: 384-dimensional,
  CPU, float32, version and revision checked at construction.
- `pin_cpu_threads` — Sets and verifies PyTorch intra-op threads to one so
  embedding latency is comparable across strategies.

### 8.2 Five-minute code path

Open these in order and keep each stop short:

1. **`scripts/demo_trial.py` → `run_demo`.** Point at
   `gold_graph.without_node(node)`, the per-strategy loop, the fresh
   `MeteredEmbedder`, and the call to `insert_node`.
2. **`src/graph_insertion/strategy.py` → `insert_node`.** Point at the sequence:
   `strategy.shortlist()`, then `decision_step.decide()`, then edge validation,
   then `graph.add_node` / `add_prereq_edge`, then
   `strategy.on_inserted()`, then `InsertionMetrics`.
3. **`src/graph_insertion/decision.py` → `PairwiseDecisionStep.decide`.**
   Point at the single call per candidate and the three-token mapping:
   `X_PREREQ_Y` → `(new, cand)`, `Y_PREREQ_X` → `(cand, new)`, `NONE` → no
   edge. Point at `SYSTEM_PROMPT`: direct or indirect prerequisite, one token
   only, names only.
4. **One strategy's `shortlist`.** Use `brute_force.py` for the simplest
   contrast; use `ann_retrieval.py` or `bounded_bucket.py` if asked how
   narrowing actually works.
5. **`src/graph_insertion/scoring.py` → `score_node_insertion`.** Point at
   `shortlist_recall` (did narrowing keep the true neighbours?) and
   `tp`/`fp`/`fn` (did the shared decision step get the edges right?).
6. **`scripts/demo_trial.py` → `ReplayLLMClient.complete`.** This is the only
   replacement: exact `user_prompt` lookup in the accepted cache, no answer
   fabricated, SHA-pinned cache.

Optional: **`Formatter.while_block`** if asked where the `[LIVE]`, `[PILOT]`,
`[CALC]` and `[GOLD]` tags come from.

### 8.3 The explanation in one breath

> A strategy only chooses whom the model is allowed to see. The shared decision
> step asks the same question for each candidate and returns the same three
> possible answers. The driver applies the edges and records the cost. Scoring
> compares the result with the gold graph at two points: did narrowing keep the
> right neighbours, and did the model get the edges right?

Then add the demo-specific sentence:

> This program replaces only the HTTP transport with a lookup into the real
> recorded PILOT-001 answers. The strategy classes, the decision step, the
> graph update, the meter and the scorer are the production code; `src/` was
> not modified for the demo.

### 8.4 Quick answers if a panelist probes

| Question | Answer |
|---|---|
| "Is the shortlist hardcoded?" | No. It is computed live by the strategy from the held-out graph and the pinned MiniLM embeddings. |
| "Are the model answers hardcoded?" | They are recorded, not invented: every answer is looked up by exact prompt text from the accepted PILOT-001 cache. A missing prompt stops the run; it never guesses. |
| "Did you change the experiment code to make the demo?" | No changes under `src/`. `scripts/demo_trial.py` imports the production classes; only the LLM client is swapped. |
| "Where is the actual LLM call in the official run?" | `PairwiseDecisionStep.decide` calls the injected client once per candidate. In the official run that client is `DeepSeekClient`; in the demo it is `ReplayLLMClient`. |
| "How is the comparison fair?" | The decision prompt, model, token vocabulary, embedder and scorer are identical across S1–S4. Only the shortlist mechanism differs. |
| "How do you know narrowing caused the difference?" | In replay the answer for a pair is fixed, so any edge difference can only come from which pairs reached the decision step. The demo asserts the S1 superset invariant and prints it. |
| "How is cost measured?" | `InsertionMetrics` records shortlist time, decision time, apply time, update time, embedding calls and LLM calls. The demo adds recorded pilot latency and tokens separately and labels them `[PILOT]`. |
| "How is accuracy computed?" | `score_node_insertion` compares predicted canonical edges with the gold graph and `GoldJudgmentSet`: TP/FP/FN, precision/recall/F1, plus shortlist recall. |
| "What is the edge direction?" | Canonical `(prereq, dependent)` means prereq → dependent; `oriented_edge` converts the file's column order once at load time. |
| "Why can S2 return nothing?" | The threshold is strict `cosine > theta`; if no existing concept passes, the shortlist is empty, so the decision step makes zero calls and adds no edges. That is a valid outcome, not an error. |

---

## 9. Files involved

| File | Role |
|---|---|
| `scripts/demo_trial.py` | Demo implementation and CLI. |
| `tests/test_demo_trial.py` | 51 regression tests. |
| `docs/prompts/DEMO-001-PROMPT.md` | Original task prompt (archived). |
| `docs/reports/DEMO-001-claude-code-defense-demo-trial.md` | Full verification and evidence record. |
| `scripts/README.md` | One-paragraph command reference. |
| `docs/decisions/decision-log.md` | D-99: replay-only, fail-closed, tag semantics. |
| `docs/tasks/status.md` | DEMO-001 status row. |
| `results/pilot/20261007_053743Z/` | Recorded PILOT-001 cache and summary. |
| `demo_runs/live-<UTC>/` | Generated live output (`transcript.txt`, `demo.json`, `run_meta.json`); gitignored. |
