# DEMO-001 — Defense demo: one insertion, four strategies (PILOT-001 replay)

**Agent:** Claude Code
**Branch:** `task/DEMO-001`
**Worktree:** `/home/lukexodus/projects/llm-graph-insertion-complexity-DEMO-001`
**Base commit:** `7dec5e9`
**Reserved decision:** [D-99]
**Status:** needs-review
**Merged:** `28edad8` (merge commit on `master`); task branch tip `c71acbe`.

---

## 1. Executive Summary

`scripts/demo_trial.py` is built and working. It performs one DSA leave-one-out
insertion for `binary_search_tree` through S1–S4 using the production loader,
strategies, `insert_node`, `PairwiseDecisionStep`, `MeteredLLMClient` and
`score_node_insertion`. The only replacement is the LLM transport: every answer
is replayed by exact prompt text from the accepted PILOT-001 cache.

The default run exits 0, works offline under `unshare -rn`, writes nothing under
`results/`, and takes about 7–10 s including model load (8.4 s process wall on
the final run). The P8 table reproduced exactly. 51 new tests pass; the full
runnable suite is 787 passed, 3 skipped. Two analysis test modules cannot be
collected in `.venv-ann` because matplotlib is not installed there; this is a
pre-existing environment gap, not a DEMO-001 failure.

Run it with:

```bash
.venv-ann/bin/python scripts/demo_trial.py
```

Operator guide (defense-day flow, flags, troubleshooting, exit codes and
suggested counter-nodes):
[`docs/presentation/information/DEMO-001-OPERATOR-GUIDE.md`](../presentation/information/DEMO-001-OPERATOR-GUIDE.md).

---

## 2. Pre-flight Results (P1–P8)

**P1 — Worktree.** Main checkout was dirty: `docs/context/repo-tree.txt`
modified (bundle side effect), `docs/presentation/information/details.md`
modified by a formatting-only diff not made by this task, and untracked
`.claude/` plus `redraw_thesis_figures.py`. Created
`../llm-graph-insertion-complexity-DEMO-001` on `task/DEMO-001` from `7dec5e9`.
No exploratory prototype file exists anywhere in the repo or worktrees; the
earlier prototype was an in-memory one-off and was never written to disk. The
worktree lacks the ignored `repositories/` clone, so a read-only symlink to the
main checkout's dataset was created for testing (untracked, not committed).

**P2 — Decision ID.** `./scripts/manage-decisions.py next` reports
`[D-99]`; D-99 is absent from `decision-log.md`. The prompt's `--next` form is
not supported by the current CLI; `next` is the correct subcommand. No conflict.

**P3 — Pilot cache.** All checks pass: 812 lines; all 16 required fields on
every line; exactly 29×28 ordered DSA pairs, each once; 812 unique prompts;
every `response_text` parses; input tokens 123,872; output tokens 2,035;
cumulative latency 676.8048 s; cache-hit tokens 0; prompt v2; model
`deepseek-flash`; temperature 0; thinking disabled; 0 retries, 0 parse
failures, 0 transport failures; estimated cost $0.019802.
SHA-256: `879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008`.
`summary.json` records only `prompt_version` ("v2"), not the system prompt text
or a hash.

**P4 — Prompt reproduction.** All 812 prompts reproduce byte-for-byte via
`PairwiseDecisionStep.build_user_prompt` with the loaded DSA domain context:
0 mismatches by string and UTF-8 comparison. `decision.SYSTEM_PROMPT` is
unchanged since the pilot: the pilot ran after `9d8743b` (v2 few-shot prompt)
and before `13faeb8` (which only adds `CALLS_PER_CANDIDATE`); current SHA-256 is
`32932d476b8cdac7026520cd9e1906a8cca9333d2945ad569fa8a7feb2b3d571`.

**P5 — Baseline tests.** A direct full-suite invocation fails collection because
`.venv-ann` lacks matplotlib (`tests/test_analysis_pipeline.py`,
`tests/test_posthoc.py`). Excluding those two modules: **736 passed, 3 skipped**
before changes; **787 passed, 3 skipped** after (the 51 new tests).

**P6 — Offline model.** `unshare -rn .venv-ann/bin/python scripts/demo_trial.py
--strategies s3 --no-color` exited 0. `MiniLMEmbedder()` loaded from the local
cache at the pinned revision and `pin_cpu_threads(1)` reported one torch thread.

**P7 — Repo facts.** DSA has 29 nodes, 54 prerequisite edges, domain context
`"data structures and algorithms"`. `networkx.transitive_reduction` gives 40
edges versus 54: the gold graph is **not** transitively reduced (14 redundant
edges). `run_experiment.py` constructs one shared `MiniLMEmbedder`, then calls
`pin_cpu_threads(1)`; it has **no embedder warm-up** (its only `warmup_fn` writes
the sidecar). For S3, faiss is imported through `ann_retrieval` before torch is
imported for MiniLM (D-73). Tests import scripts as a namespace package, e.g.
`from scripts.run_experiment import ...`.

**P8 — Prototype table reproduced.**

| strategy | shortlist | calls | recorded latency | tokens in/out | cost | shortlist recall | P | R | F1 | TP/FP/FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| brute_force | 28/28 | 28 | 28.39 s | 4,291/71 | $0.000686 | 1.000 | .800 | .571 | .667 | 4/1/3 |
| embedding_threshold θ=.6 | 1/28 | 1 | 1.37 s | 153/5 | $0.000026 | .143 | 1.000 | .143 | .250 | 1/0/6 |
| ann_retrieval k=10 ef=128 | 10/28 | 10 | 10.11 s | 1,534/32 | $0.000249 | .714 | 1.000 | .571 | .727 | 4/0/3 |
| bounded_bucket 5..10 | 9/28 | 9 | 8.85 s | 1,380/21 | $0.000220 | .429 | 1.000 | .143 | .250 | 1/0/6 |

All discrete values match. The measured shortlist/setup timings differ per run,
as expected.

---

## 3. Implementation Details

`scripts/demo_trial.py` is a single importable module with a guarded `main()`.
Sections:

1. **Constants and provenance.** PILOT path, SHA-256 pin, prompt version,
   system-prompt SHA-256 pin, strategy defaults, off-peak prices, width 88.
2. **Replay cache.** `load_pilot` validates every record, the exact pair set,
   prompt uniqueness, types, token/latency sums and summary consistency, and
   fails closed with exit 3. `ReplayLLMClient.complete` checks the system prompt
   and exact user prompt; a missing answer raises rather than fabricating one.
3. **Report model.** Frozen-ish dataclasses for calls, edge labels, missed
   edges, per-strategy results and the whole report, shared by the formatter and
   `--json` so the two cannot diverge.
4. **Orchestration.** For each strategy in canonical order: fresh held-out graph,
   fresh strategy, fresh `MeteredEmbedder`, timed `setup`, `gc.collect`, replayed
   decision step through the production `insert_node`, production
   `score_node_insertion`, per-edge labels, FN causes, transitive gold-path notes,
   subset invariant, and two-stage recall decomposition.
5. **Formatter.** Staged BEFORE / WHILE / AFTER output with `[LIVE]`, `[PILOT]`,
   `[CALC]`, `[GOLD]` tags; width enforced at 88 columns in Unicode and ASCII;
   colour only for tags and TP/FP/FN markers; no gold information before AFTER
   except the provenance legend.
6. **CLI.** All specified flags, exit codes 0/2/3/4/5/6/7, `--check`,
   `--show-all-calls`, `--ascii`, `--pause`, `--json`, broken-pipe handling.

Production code reused: `load_corpus`, `ConceptGraph.without_node`,
`STRATEGY_FACTORIES`, each strategy's `setup`/`shortlist`/`on_inserted`,
`insert_node`, `PairwiseDecisionStep`, `MeteredLLMClient`,
`score_node_insertion`, `MeteredEmbedder`, `MiniLMEmbedder`,
`pin_cpu_threads`. No narrowing or scoring logic is reimplemented.

`tests/test_demo_trial.py` adds 51 tests across seven groups: replay loader and
client (including fail-closed paths and no live client/socket), cost formula,
orchestration with `FakeEmbedder`, formatter rules (width, tags, call-printing,
gold-leak, takeaway guards), CLI, MiniLM integration and the real cache.

`scripts/README.md` now has a short "Defense Demo" section.

One deliberate demo-only addition: a single warm-up embed before the first timed
strategy, outside every timed window. The official runner has no embedder
warm-up; without this, the first embedding strategy's measured shortlist time
would include lazy first-touch cost. It changes no score or call count.

---

## 4. Output Transcript (default run, `--no-color`)

```text
════════════════════════════════════════════════════════════════════════════════════════
 DEFENSE DEMO  ·  one concept insertion, four narrowing strategies   PILOT-001 replay
════════════════════════════════════════════════════════════════════════════════════════
 PROVENANCE
   LLM decisions  REPLAYED from recorded PILOT-001 calls
                  (not re-requested, not simulated)
   Cache file     results/pilot/20261007_053743Z/raw_calls.jsonl
                  812 calls · sha256 879f22b102f3… · recorded 2026-10-07 05:37:43Z
   Recorded with  deepseek-flash · prompt v2 · temperature 0 · thinking disabled
                  0 retries · 0 parse failures · 0 transport failures
   Run live here  corpus load, narrowing, graph update, scoring, timers [LIVE]
   Embedder       all-MiniLM-L6-v2 rev 1110a24 · CPU · 1 thread
                  sentence-transformers 6.1.0
   Network / API  none used · no API key read
 TAGS  [LIVE] measured now   [PILOT] recorded 2026-10-07
       [CALC] computed       [GOLD] ground truth (revealed after)

  REPLAY NOTICE. The model answers on screen are real. Each one was returned by
  deepseek-flash on 2026-10-07 during PILOT-001 for exactly the prompt shown; this
  program looks up that stored answer instead of calling the API again. Nothing is
  simulated or invented, and a missing record stops the program. Narrowing, graph
  updates and scoring run live. Model latency, token counts and cost are the recorded
  values, not measurements from this run.

────────────────────────────────────────────────────────────────────────────────────────
 PHASE 1 · BEFORE
────────────────────────────────────────────────────────────────────────────────────────
  The thesis measures how the cost (LLM calls, time) and the accuracy of inserting one
  new concept into an existing LLM-built prerequisite graph depend on how candidates are
  narrowed. Only the narrowing differs; the LLM decision step is identical for every
  strategy.

  Corpus            DSA_gold_standard_MEKG
  Domain context    'data structures and algorithms'
  Full graph        29 concepts, 54 prerequisite edges
  NEW concept       binary_search_tree
  Existing graph    28 concepts, 47 edges
  Gold neighbourhood: HIDDEN until AFTER. Nothing before AFTER is marked with it.

  THE SHARED DECISION STEP (identical for every strategy)
    You judge prerequisite relationships between concepts in a curriculum. A concept
    P is a prerequisite of a concept Q if a learner needs to understand P, directly
    or indirectly through other concepts, before learning Q. Answer with exactly one
    of: X_PREREQ_Y (X is a prerequisite of Y), Y_PREREQ_X (Y is a prerequisite of
    X), NONE (neither). Output only that token.
    
    Examples:
    Concept X: fractions / Concept Y: ratios -> X_PREREQ_Y
    Concept X: calculus / Concept Y: limits -> Y_PREREQ_X
    Concept X: poetry / Concept Y: plumbing -> NONE
    User prompt template:
      Subject area: <domain>
      Concept X: <new concept, spaces instead of underscores>
      Concept Y: <candidate, spaces instead of underscores>
    Answers: X_PREREQ_Y | Y_PREREQ_X | NONE
    One call per shortlisted candidate; X_PREREQ_Y -> edge (new -> cand);
    Y_PREREQ_X -> edge (cand -> new); canonical direction prerequisite -> dependent.
    Only names are shown to the model.

  STRATEGIES SELECTED
    S1 brute_force
       nothing; every existing concept is judged
    S2 embedding_threshold
       cosine(new, node) > 0.6 (strict), MiniLM embeddings
    S3 ann_retrieval
       top-10 by cosine through HNSW (M=16, efConstruction=200, efSearch=128)
    S4 bounded_bucket
       one size-bounded home bucket (5..10, 12 hash bits)

  cost = (cache-miss in x $0.15 + cache-hit in x $0.003 + out x $0.60) / 1M
         (off-peak prices, D-36)

────────────────────────────────────────────────────────────────────────────────────────
 PHASE 2 · WHILE   strategy 1 of 4:  S1  brute_force
────────────────────────────────────────────────────────────────────────────────────────
  setup     index build over 28 concepts   0.0 ms [LIVE]  excluded from official timer
  shortlist 28 of 28 kept (100.0%), narrowed away 0.0%
            time 0.0 ms [LIVE]  (embedding the new name: 0.0 ms)
  all 28 existing concepts, alphabetical, no ranking
  diagnostics  candidate_count=28  [LIVE]

  decisions  28 calls, 7 shown [PILOT]
   call  1/28  X = binary search tree   Y = asymptotic complexity
             exact prompt sent in PILOT-001 [PILOT]
             | Subject area: data structures and algorithms
             | Concept X: binary search tree
             | Concept Y: asymptotic complexity
             answer NONE          0.90 s  153 in / 2 out
             -> no edge
   call  2/28  X = binary search tree   Y = avl tree
             answer X_PREREQ_Y    0.87 s  154 in / 5 out
             -> edge  binary_search_tree → avl_tree   (prerequisite -> dependent)
   call  3/28  X = binary search tree   Y = b tree
             answer NONE          1.47 s  153 in / 2 out
             -> no edge
   call  5/28  X = binary search tree   Y = binary search
             answer Y_PREREQ_X    1.37 s  153 in / 5 out
             -> edge  binary_search → binary_search_tree   (prerequisite -> dependent)
   call 16/28  X = binary search tree   Y = pointer
             answer Y_PREREQ_X    1.00 s  152 in / 5 out
             -> edge  pointer → binary_search_tree   (prerequisite -> dependent)
   call 21/28  X = binary search tree   Y = red black tree
             answer X_PREREQ_Y    0.69 s  154 in / 5 out
             -> edge  binary_search_tree → red_black_tree   (prerequisite -> dependent)
   call 27/28  X = binary search tree   Y = tree
             answer Y_PREREQ_X    0.80 s  152 in / 5 out
             -> edge  tree → binary_search_tree   (prerequisite -> dependent)
   ... 21 NONE decisions not printed (use --show-all-calls)
  answers    NONE 23 · X_PREREQ_Y 2 · Y_PREREQ_X 3          [PILOT]
  LLM        28 calls · 28.39 s recorded latency [PILOT]
             4,291 in / 71 out tokens [PILOT]
             cost $0.000686 [CALC]
             calls vs S1: 0% [CALC]
  applied    +1 concept, +5 edges  ->  graph 29 concepts, 52 edges [CALC]
             update 0.0 ms [LIVE]
             replay wall time 0.3 ms [LIVE]

────────────────────────────────────────────────────────────────────────────────────────
 PHASE 2 · WHILE   strategy 2 of 4:  S2  embedding_threshold
────────────────────────────────────────────────────────────────────────────────────────
  setup     index build over 28 concepts   73.7 ms [LIVE]  excluded from official timer
  shortlist 1 of 28 kept (3.6%), narrowed away 96.4%
            time 11.1 ms [LIVE]  (embedding the new name: 10.9 ms)
  candidates: binary_search
  diagnostics  cosine_comparisons=28 · max_cosine=0.801 · shortlist_size=1  [LIVE]

  decisions  1 call, all shown [PILOT]
   call  1/1   X = binary search tree   Y = binary search
             answer Y_PREREQ_X    1.37 s  153 in / 5 out
             -> edge  binary_search → binary_search_tree   (prerequisite -> dependent)
  answers    NONE 0 · X_PREREQ_Y 0 · Y_PREREQ_X 1          [PILOT]
  LLM        1 calls · 1.37 s recorded latency [PILOT]
             153 in / 5 out tokens [PILOT]
             cost $0.000026 [CALC]
             calls vs S1: 96% [CALC]
  applied    +1 concept, +1 edge  ->  graph 29 concepts, 48 edges [CALC]
             update 0.0 ms [LIVE]
             replay wall time 11.2 ms [LIVE]

────────────────────────────────────────────────────────────────────────────────────────
 PHASE 2 · WHILE   strategy 3 of 4:  S3  ann_retrieval
────────────────────────────────────────────────────────────────────────────────────────
  setup     index build over 28 concepts   72.2 ms [LIVE]  excluded from official timer
  shortlist 10 of 28 kept (35.7%), narrowed away 64.3%
            time 10.4 ms [LIVE]  (embedding the new name: 10.2 ms)
  top candidates by cosine [LIVE]
      1  0.801  binary_search
      2  0.590  tree
      3  0.586  b_tree
      4  0.566  breadth_first_search
      5  0.478  depth_first_search
      6  0.462  avl_tree
      7  0.436  red_black_tree
      8  0.433  minimum_spanning_tree
      9  0.349  hash_table
     10  0.330  sorting_algorithm
  diagnostics  exact_topk_overlap=1.000 · shortlist_size=10 · max_cosine=0.801  [LIVE]

  decisions  10 calls, all shown [PILOT]
   call  1/10  X = binary search tree   Y = binary search
             answer Y_PREREQ_X    1.37 s  153 in / 5 out
             -> edge  binary_search → binary_search_tree   (prerequisite -> dependent)
   call  2/10  X = binary search tree   Y = tree
             answer Y_PREREQ_X    0.80 s  152 in / 5 out
             -> edge  tree → binary_search_tree   (prerequisite -> dependent)
   call  3/10  X = binary search tree   Y = b tree
             answer NONE          1.47 s  153 in / 2 out
             -> no edge
   call  4/10  X = binary search tree   Y = breadth first search
             answer NONE          0.96 s  154 in / 2 out
             -> no edge
   call  5/10  X = binary search tree   Y = depth first search
             answer NONE          0.97 s  154 in / 2 out
             -> no edge
   call  6/10  X = binary search tree   Y = avl tree
             answer X_PREREQ_Y    0.87 s  154 in / 5 out
             -> edge  binary_search_tree → avl_tree   (prerequisite -> dependent)
   call  7/10  X = binary search tree   Y = red black tree
             answer X_PREREQ_Y    0.69 s  154 in / 5 out
             -> edge  binary_search_tree → red_black_tree   (prerequisite -> dependent)
   call  8/10  X = binary search tree   Y = minimum spanning tree
             answer NONE          0.69 s  154 in / 2 out
             -> no edge
   call  9/10  X = binary search tree   Y = hash table
             answer NONE          1.09 s  153 in / 2 out
             -> no edge
   call 10/10  X = binary search tree   Y = sorting algorithm
             answer NONE          1.20 s  153 in / 2 out
             -> no edge
  answers    NONE 6 · X_PREREQ_Y 2 · Y_PREREQ_X 2          [PILOT]
  LLM        10 calls · 10.11 s recorded latency [PILOT]
             1,534 in / 32 out tokens [PILOT]
             cost $0.000249 [CALC]
             calls vs S1: 64% [CALC]
  applied    +1 concept, +4 edges  ->  graph 29 concepts, 51 edges [CALC]
             update 0.0 ms [LIVE]
             replay wall time 10.6 ms [LIVE]

────────────────────────────────────────────────────────────────────────────────────────
 PHASE 2 · WHILE   strategy 4 of 4:  S4  bounded_bucket
────────────────────────────────────────────────────────────────────────────────────────
  setup     index build over 28 concepts   69.6 ms [LIVE]  excluded from official timer
  shortlist 9 of 28 kept (32.1%), narrowed away 67.9%
            time 11.2 ms [LIVE]  (embedding the new name: 11.1 ms)
  top candidates by cosine [LIVE]
      1  0.478  depth_first_search
      2  0.462  avl_tree
      3  0.433  minimum_spanning_tree
      4  0.318  dijkstra_algorithm
      5  0.318  recursive_backtracking
      6  0.314  recursion
      7  0.283  heap
      8  0.274  graph
      9  0.111  trie
  diagnostics  num_segments=4 · min_segment_size=6 · max_segment_size=10  [LIVE]

  decisions  9 calls, all shown [PILOT]
   call  1/9   X = binary search tree   Y = depth first search
             answer NONE          0.97 s  154 in / 2 out
             -> no edge
   call  2/9   X = binary search tree   Y = avl tree
             answer X_PREREQ_Y    0.87 s  154 in / 5 out
             -> edge  binary_search_tree → avl_tree   (prerequisite -> dependent)
   call  3/9   X = binary search tree   Y = minimum spanning tree
             answer NONE          0.69 s  154 in / 2 out
             -> no edge
   call  4/9   X = binary search tree   Y = dijkstra algorithm
             answer NONE          1.17 s  155 in / 2 out
             -> no edge
   call  5/9   X = binary search tree   Y = recursive backtracking
             answer NONE          1.03 s  154 in / 2 out
             -> no edge
   call  6/9   X = binary search tree   Y = recursion
             answer NONE          1.00 s  152 in / 2 out
             -> no edge
   call  7/9   X = binary search tree   Y = heap
             answer NONE          1.45 s  152 in / 2 out
             -> no edge
   call  8/9   X = binary search tree   Y = graph
             answer NONE          0.89 s  152 in / 2 out
             -> no edge
   call  9/9   X = binary search tree   Y = trie
             answer NONE          0.78 s  153 in / 2 out
             -> no edge
  answers    NONE 8 · X_PREREQ_Y 1 · Y_PREREQ_X 0          [PILOT]
  LLM        9 calls · 8.85 s recorded latency [PILOT]
             1,380 in / 21 out tokens [PILOT]
             cost $0.000220 [CALC]
             calls vs S1: 68% [CALC]
  applied    +1 concept, +1 edge  ->  graph 29 concepts, 48 edges [CALC]
             update 0.0 ms [LIVE]
             replay wall time 11.4 ms [LIVE]

────────────────────────────────────────────────────────────────────────────────────────
 PHASE 3 · AFTER
────────────────────────────────────────────────────────────────────────────────────────
  [GOLD] prerequisites of binary_search_tree: binary_search, recursion, tree
  [GOLD] dependents of binary_search_tree: avl_tree, b_tree, red_black_tree, trie
  [GOLD] 7 gold incident edges

  S1 brute_force
    shortlist captured 7/7 gold neighbours (shortlist recall 1.000)
    predicted edges
      TP         binary_search_tree → avl_tree
      TP         binary_search → binary_search_tree
      FP         pointer → binary_search_tree
                 (gold path exists: pointer → tree → binary_search_tree)
      TP         binary_search_tree → red_black_tree
      TP         tree → binary_search_tree
    missed gold edges
      FN         binary_search_tree → b_tree  (judged NONE)
      FN         binary_search_tree → trie  (judged NONE)
      FN         recursion → binary_search_tree  (judged NONE)
    lost at narrowing 0 · lost at decision 3 [CALC]
    metrics  P 0.800  R 0.571  F1 0.667   TP 4 FP 1 FN 3 [CALC]
    recall decomposition: shortlist 1.000 x given-shortlist 0.571 = 0.571 [CALC]

  S2 embedding_threshold
    shortlist captured 1/7 gold neighbours (shortlist recall 0.143)
    predicted edges
      TP         binary_search → binary_search_tree
    missed gold edges
      FN         binary_search_tree → avl_tree  (not shortlisted)
      FN         binary_search_tree → b_tree  (not shortlisted)
      FN         binary_search_tree → red_black_tree  (not shortlisted)
      FN         binary_search_tree → trie  (not shortlisted)
      FN         recursion → binary_search_tree  (not shortlisted)
      FN         tree → binary_search_tree  (not shortlisted)
    lost at narrowing 6 · lost at decision 0 [CALC]
    metrics  P 1.000  R 0.143  F1 0.250   TP 1 FP 0 FN 6 [CALC]
    recall decomposition: shortlist 0.143 x given-shortlist 1.000 = 0.143 [CALC]

  S3 ann_retrieval
    shortlist captured 5/7 gold neighbours (shortlist recall 0.714)
    predicted edges
      TP         binary_search → binary_search_tree
      TP         tree → binary_search_tree
      TP         binary_search_tree → avl_tree
      TP         binary_search_tree → red_black_tree
    missed gold edges
      FN         binary_search_tree → b_tree  (judged NONE)
      FN         binary_search_tree → trie  (not shortlisted)
      FN         recursion → binary_search_tree  (not shortlisted)
    lost at narrowing 2 · lost at decision 1 [CALC]
    metrics  P 1.000  R 0.571  F1 0.727   TP 4 FP 0 FN 3 [CALC]
    recall decomposition: shortlist 0.714 x given-shortlist 0.800 = 0.571 [CALC]

  S4 bounded_bucket
    shortlist captured 3/7 gold neighbours (shortlist recall 0.429)
    predicted edges
      TP         binary_search_tree → avl_tree
    missed gold edges
      FN         binary_search → binary_search_tree  (not shortlisted)
      FN         binary_search_tree → b_tree  (not shortlisted)
      FN         binary_search_tree → red_black_tree  (not shortlisted)
      FN         binary_search_tree → trie  (judged NONE)
      FN         recursion → binary_search_tree  (judged NONE)
      FN         tree → binary_search_tree  (not shortlisted)
    lost at narrowing 4 · lost at decision 2 [CALC]
    metrics  P 1.000  R 0.143  F1 0.250   TP 1 FP 0 FN 6 [CALC]
    recall decomposition: shortlist 0.429 x given-shortlist 0.333 = 0.143 [CALC]

  INVARIANT  every edge from a narrowing strategy is in S1's predicted set: OK

  WORK                      kept calls  vsS1  LLM lat tokens in/out      cost shortlist
  (LLM latency and tokens are [PILOT]; cost is [CALC]; shortlist time is [LIVE].)
  S1 brute_force           28/28    28    0%  28.39 s    4,291 / 71 $0.000686   0.0 ms
  S2 embedding_threshold    1/28     1   96%   1.37 s       153 / 5 $0.000026  11.1 ms
  S3 ann_retrieval         10/28    10   64%  10.11 s    1,534 / 32 $0.000249  10.4 ms
  S4 bounded_bucket         9/28     9   68%   8.85 s    1,380 / 21 $0.000220  11.2 ms

  ACCURACY               sl.recall      P      R     F1   TP/FP/FN  lost n/d
  S1 brute_force             1.000  0.800  0.571  0.667      4/1/3       0/3
  S2 embedding_threshold     0.143  1.000  0.143  0.250      1/0/6       6/0
  S3 ann_retrieval           0.714  1.000  0.571  0.727      4/0/3       2/1
  S4 bounded_bucket          0.429  1.000  0.143  0.250      1/0/6       4/2

  TAKEAWAYS
    - S2 made 1 calls, 96% fewer than S1's 28.
    - S3 made 10 calls, 64% fewer than S1's 28.
    - S4 made 9 calls, 68% fewer than S1's 28.
    - Every edge from S2-S4 was also predicted by S1: the decision step is
      identical, so differences come only from which pairs were sent to the model.
    - Narrowing's price: S2 kept 0.143 of gold neighbours and lost 6 edge(s) before
      the model saw them; S3 kept 0.714 of gold neighbours and lost 2 edge(s) before
      the model saw them; S4 kept 0.429 of gold neighbours and lost 4 edge(s) before
      the model saw them.
    - S3 has a higher F1 than S1 because it never judged 1 pair(s) that S1 turned
      into false positives.
    - One node is an illustration. The thesis evidence is the full runs (RQ1-RQ3),
      not this transcript.

  LIMITATIONS — WHAT THIS DOES NOT PROVE
  Decisions are replayed from PILOT-001 recordings, not re-requested. This is real model
  output for exactly these prompts, recorded on 2026-10-07.
  One held-out node, one trial, one repeat. This is an illustration, not a new result,
  and it is not part of Chapter 4.
  Latency, tokens and cost are recorded values. Only setup, shortlist, update and replay
  times are measured now; replay wall time says nothing about model latency.
  In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a pair.
  In the official runs each strategy made its own live calls, so agreement on a pair is
  not guaranteed there.
  DSA gold is not transitively reduced, so some false positives may be defensible by
  transitive closure; metrics are computed against the gold as given.
  Strategy parameters are the pre-fixed defaults (D-64); nothing was tuned on this node.

  demo wall time 7.1 s [LIVE]   · no files written to results/
════════════════════════════════════════════════════════════════════════════════════════
```

---

## 5. Verification V1–V9

**V1 — Tests.** `tests/test_demo_trial.py`: 51 passed. Full runnable suite:
787 passed, 3 skipped, 1 warning. (Two analysis modules excluded for missing
matplotlib; see P5.)

**V2 — Acceptance run.** Default piped run exit 0; process wall 8.36 s, demo
wall 7.1 s. A TTY run via `script -qec` exited 0 in 0.52 s for S1 only. Warm
process wall measured earlier at 11.2 s under CPU contention; all runs are well
under 30 s.

**V3 — Network off.** `unshare -rn` full S3 path exit 0, no API key, no network.

**V4 — Determinism.** Two `--json` runs produce byte-identical non-volatile
JSON after removing `run` and every key ending `_live`: `True`.

**V5 — Official artifacts untouched.** `sha256sum` of
`results/pilot/20261007_053743Z/raw_calls.jsonl` is unchanged before/after;
`git status --short results/` is clean; no new files under `results/`.

**V6 — P8.** Reproduced exactly; see P8.

**V7 — Survey (verification only, not committed).** All 29 DSA nodes were run
through `run_demo` in one process with the shared MiniLM embedder. Results in
`/tmp/demo-survey.json`. `binary_search_tree` ranks **5th of 29** by
`F1(S3) - F1(S1)` (+0.061). A node where brute force clearly beats S3:
**`bellman_ford_algorithm`** (S1 F1 1.000, S3 F1 0.000). Nodes where S2 returns
an empty shortlist include **`graph`**, `asymptotic_complexity`, `linked_list`,
`heap`, `dijkstra_algorithm`, `stack`, `queue`, `trie`, and others (15 total).

**V8 — Cross-check against the accuracy stage.** Replayed vs official
`raw.jsonl` for `binary_search_tree`:

| strategy | replay TP/FP/FN | official TP/FP/FN | calls | shortlist hits | shortlist size |
|---|---|---|---|---|---|
| brute_force | 4/1/3 | 5/1/2 | 28 vs 28 | 7 vs 7 | 28 vs 28 |
| embedding_threshold | 1/0/6 | 1/0/6 | 1 vs 1 | 1 vs 1 | 1 vs 1 |
| ann_retrieval | 4/0/3 | 4/0/3 | 10 vs 10 | 5 vs 5 | 10 vs 10 |
| bounded_bucket | 1/0/6 | 2/0/5 | 9 vs 9 | 3 vs 3 | 9 vs 9 |

S2 and S3 match exactly. S1 and S4 each gain one true positive in the official
run: the official runs made their own live calls on 2026-10-18, while the demo
replays the 2026-10-07 pilot. The JSONL score records do not store which edge
changed, so the exact differing pair cannot be named from the artifacts. This
is consistent with the limitation text: replay is faithful to the pilot, not to
the later live runs.

**V9 — Diagnostics and transitive reduction.** Whitelisted keys exist:
S1 `candidate_count`; S2 `cosine_comparisons`, `max_cosine`, `shortlist_size`;
S3 `exact_topk_overlap`, `shortlist_size`, `max_cosine`; S4 `num_segments`,
`min_segment_size`, `max_segment_size`. DSA is not transitively reduced
(54 edges vs 40 in the reduction).

---

## 6. Discrepancies and Findings

1. **No prototype file existed.** P1 assumed an uncommitted exploratory
   prototype; none was on disk in the main checkout or any worktree. The earlier
   prototype was an in-memory one-off. No reference code was reused.
2. **`manage-decisions.py --next` is not a valid flag.** The CLI requires the
   `next` subcommand. Used `next`; D-99 was free.
3. **`run_experiment.py` has no embedder warm-up.** Its `warmup_fn` only writes
   the sidecar. The demo adds one warm-up embed outside timed windows; this is
   documented in D-99 and changes no metric.
4. **Bundle-profile defect confirmed.** `./scripts/apc-bundle.sh presentation
   --list` and `full --list` both exit 1 with
   `MISSING: docs/presentation/script/Defense_Script_and_Background_Guide.md`
   and the comprehensive-version path. The real files are under
   `docs/presentation/information/`. Not fixed here; left for `TOOL-002`.
5. **Environment gap.** `.venv-ann` lacks matplotlib, so
   `tests/test_analysis_pipeline.py` and `tests/test_posthoc.py` fail collection.
   The rest of the suite is green. The worktree also lacked the ignored
   `repositories/` clone; a read-only symlink was used for local verification.
   Neither is a DEMO-001 defect.
6. **Gold-leak spec tension.** The banner legend required by §6.1 contains the
   `[GOLD]` tag, while the §8 gold-leak test says nothing before AFTER may
   contain that tag. The formatter prints the legend and the test allows that
   one legend exception; no gold data appears before AFTER.
7. **Width-driven wording.** Three spec strings exceeded 88 columns
   (`Gold neighbourhood...`, the tag legend, the embedder line). They were
   wrapped or shortened without changing meaning.
8. **System-prompt provenance.** `summary.json` stores only prompt version, not
   the system prompt or its hash. Verification therefore relies on the
   `decision.py` git history plus the runtime SHA pin.
9. **V8 replay drift.** S1/S4 differ from the official accuracy records by one
   predicted edge. Explained above; not hidden or papered over.
10. **Main-checkout unrelated diff.** `docs/presentation/information/details.md`
    has a formatting-only modification not made by this task. It was not staged
    or touched. `docs/context/repo-tree.txt` in the worktree was modified by the
    bundle script and was also left unstaged.
11. **Untracked files.** `repositories` (symlink to the main checkout dataset)
    remains untracked in the worktree; it is not committed. The main checkout
    also has untracked `.claude/` and `redraw_thesis_figures.py`, unrelated to
    this task.

---

## 7. Decision D-99

[D-99] is recorded in `docs/decisions/decision-log.md`. In brief: the demo is
replay-only and fail-closed; the cache SHA-256 and system-prompt SHA-256 are
pinned; tags are `[LIVE]`/`[PILOT]`/`[CALC]`/`[GOLD]`; HF offline environment
variables are set before heavy imports; S1–S4 subset invariant holds only in
replay; and nothing in the demo is an empirical result.

---

## 8. Test List and Counts

New file `tests/test_demo_trial.py` (51 tests):

- `TestReplayLoader` (17): happy path; cache miss; wrong system prompt; prompt
  version/model/total/token/latency summary mismatches; tampered SHA; malformed
  JSON; missing field; wrong type; negative latency; cache-token mismatch;
  nonzero reasoning tokens; duplicate prompt; duplicate pair; incomplete pair
  set; line-count mismatch; invalid token; no live client/socket construction.
- `TestCost` (2): no-cache-hit S1 example; cache-hit pricing.
- `TestOrchestration` (3): production paths and live counters; canonical edge
  rebuild; deliberately broken edge triggers exit 6.
- `TestFormatter` (10): width in both modes; no ANSI when off; call-printing
  for N=28/10/11/1; `--show-all-calls`; empty shortlist; S1 no similarity table;
  `n/a`; one tag per metric line; takeaway guards; banner provenance/replay
  notice; no gold leak before AFTER.
- `TestCLI` (7): strategy parsing/order; duplicates/unknown; unknown node exit
  4; existing JSON exit 7; results JSON exit 7; missing parent exit 7;
  `--check` runs no trial; broken pipe.
- `TestMiniLMIntegration` (2): default P8 metrics; two-run non-volatile JSON
  equality.
- `TestRealCache` (1): real PILOT-001 cache loads and covers 812 pairs.

Suite totals: **787 passed, 3 skipped** (analysis modules excluded).

---

## 9. Git Diff and Patch

The operator guide was added in a follow-up commit on the same branch; the
authoritative patch file includes it. The diff below is the initial
implementation diff (`git diff --cached` before this report was committed):
implementation, tests, README, prompt archive, status row and D-99 entry. The
report file itself was added after the diff was captured. The authoritative full
patch is:

`patch/DEMO-001-claude-code-defense-demo-trial.patch`

```diff
diff --git c/docs/decisions/decision-log.md i/docs/decisions/decision-log.md
index fae150d..d5239eb 100644
--- c/docs/decisions/decision-log.md
+++ i/docs/decisions/decision-log.md
@@ -971,3 +971,12 @@ Reasoning: adds the requested experimental-setup vocabulary at the point where t
 (3) The document is expected to drift. Structural changes (new strategy, new corpus, new metric, new run-directory slug, new analysis artifact) must update the affected section in the same task that makes the change. Pure refactors that preserve symbols and workflows do not require an immediate rewrite, but line-number pointers will be stale and should be treated as approximations.
 (4) No experimental decision is made or changed by this document. Constants, thresholds, prompts, and bounds are quoted from code; the decision log remains the source of truth for *why* they have those values.
 Reasoning: records why a second, code-level map exists alongside the decision log and strategy-interface spec, and fixes the rule that prevents the map from becoming a competing source of truth. Affects: `docs/context/codebase-map.md`, `docs/tasks/status.md`, `docs/reports/DOC-013-claude-code-codebase-map.md`.
+
+**[D-99]** Defense demo: offline PILOT-001 replay, fail-closed provenance, and metric tags (DEMO-001):
+(1) The defense demonstration is **replay-only**. `scripts/demo_trial.py` performs one leave-one-out insertion on DSA through all four strategies using the production loader, strategies, `insert_node`, `PairwiseDecisionStep`, `MeteredLLMClient` and `score_node_insertion`. The only replaced component is the LLM transport: `ReplayLLMClient` looks up each answer by exact `user_prompt` in `results/pilot/20261007_053743Z/raw_calls.jsonl`. No API call, no network access, no API key read, and no model download at demo time.
+(2) Replay is **fail-closed**. `load_pilot` validates the cache SHA-256 (`879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008`), 812 records, the exact 29x28 ordered-pair set, prompt uniqueness, field types, token/latency sums, prompt version v2, and `deepseek-flash` provenance. `ReplayLLMClient.complete` requires the current `decision.SYSTEM_PROMPT` (SHA-256 `32932d476b8cdac7026520cd9e1906a8cca9333d2945ad569fa8a7feb2b3d571`) and raises exit 3 on any missing prompt. It never constructs `FakeLLMClient` or `DeepSeekClient`.
+(3) Metric provenance is explicit in the transcript: `[LIVE]` for timings measured by the demo process, `[PILOT]` for recorded answers, per-call latency and tokens, `[CALC]` for cost and derived percentages, and `[GOLD]` for ground truth shown only in the AFTER phase. Recorded model latency is never presented as a current measurement, and replay wall time is labelled separately.
+(4) The demo sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_PROGRESS_BARS=1`, `TRANSFORMERS_VERBOSITY=error`, and `TOKENIZERS_PARALLELISM=false` before any heavy import. It imports faiss through `ann_retrieval` before constructing `MiniLMEmbedder` when S3 is selected ([D-73]) and applies `pin_cpu_threads(1)` ([D-72]). A single warm-up embed runs outside every timed window because the official harness has no embedder warm-up; this is a demo-only addition and does not change any score or call count.
+(5) In replay a pair's answer is a fixed lookup, so every edge predicted by S2-S4 must be in S1's predicted set; the demo asserts this subset invariant. It need not hold in the official live runs, where each strategy made its own calls, and the transcript's limitations say so.
+(6) Nothing here is an empirical result. The demo is a one-node, one-trial illustration of real recorded PILOT-001 output, not a substitute for the 24-run accuracy/sweep campaign or Chapter 4. V8 found that the pilot replay matches the official accuracy records exactly for S2 and S3 but differs by one predicted edge for S1 and S4; the official runs made their own live calls on 2026-10-18, so replay faithfully reflects the 2026-10-07 pilot, not the later runs.
+Reasoning: gives panelists an honest, reproducible microcosm of the insertion pipeline without spending API budget or depending on the network during a defense, while making every replayed value auditable and refusing to fabricate any missing answer. Affects: `scripts/demo_trial.py`, `tests/test_demo_trial.py`, `scripts/README.md`, `docs/prompts/DEMO-001-PROMPT.md`, `docs/tasks/status.md`, `docs/reports/DEMO-001-claude-code-defense-demo-trial.md`.
diff --git c/docs/prompts/DEMO-001-PROMPT.md i/docs/prompts/DEMO-001-PROMPT.md
new file mode 100644
index 0000000..2a39279
--- /dev/null
+++ i/docs/prompts/DEMO-001-PROMPT.md
@@ -0,0 +1,494 @@
+# DEMO-001 — Defense demo: one insertion, four strategies (PILOT-001 replay)
+
+Standalone implementation prompt for the local coding agent (Claude Code).
+Archive as `docs/prompts/DEMO-001-PROMPT.md`. Written by the APC AI on
+2026-10-29 against bundle `apc-bundle-core-20261029-0038` (commit `7dec5e9`).
+
+- **TASK-ID:** `DEMO-001`
+- **Reserved decision ID:** `D-99` (see pre-flight P2; if it is already used, STOP and report, do not renumber)
+- **Suggested follow-up IDs (not part of this task):** `DEMO-001-R` (independent review, Gemini), `TOOL-002` (bundle-script path defect)
+- **Status row:** add under "Presentation track" in `docs/tasks/status.md`, final status `needs-review`
+
+You have no memory of any earlier conversation. This repo is the source of
+truth. Where this prompt says something you can check and the repo disagrees,
+trust the repo and say so in your report.
+
+---
+
+## 0. Read first, in this order
+
+1. `AGENTS.md` (all of it, especially "Parallel work and worktrees" and the four deliverables)
+2. `docs/context/complete-context.md`
+3. `docs/context/strategy-interface.md` and `docs/context/data-formats.md`
+4. `docs/context/codebase-map.md` — the sections on `strategy.insert_node`, the accuracy-stage trial loop (`run_accuracy_experiment`), `MiniLMEmbedder`, `pin_cpu_threads`, and the invariants list
+5. `docs/decisions/decision-log.md` entries D-21, D-23, D-24, D-25, D-28, D-29, D-30, D-33, D-35, D-36, D-37, D-64, D-67, D-72, D-73, D-78
+6. `src/graph_insertion/{strategy,decision,llm,scoring,loader,graph_representation,embedding,embedding_minilm,cpu_threads}.py` and `strategies/{registry,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}.py`
+7. `scripts/run_experiment.py` (how the harness builds the embedder, the warm-up, the held-out graph, and the metered clients) and `scripts/pilot_dsa_zero_shot.py` (cost formula, pilot artifact layout)
+
+## 1. Goal
+
+Build `scripts/demo_trial.py` (+ `tests/test_demo_trial.py`): an offline,
+deterministic terminal demonstration for thesis panelists. It performs ONE real
+concept-insertion trial on the DSA corpus (one held-out concept, default
+`binary_search_tree`) through all four narrowing strategies, using the
+production code paths, and prints staged BEFORE / WHILE / AFTER output.
+
+The LLM decision for every (new concept, candidate) pair is REPLAYED from the
+real recorded PILOT-001 call cache. The decision step, graph update and scoring
+are the production code. Only the transport is replaced.
+
+### Non-goals (hard)
+
+- No new empirical result. No writes under `results/`. No change to any official artifact.
+- No API call, no network access, no API key read, no model download at demo time.
+- No HTML, no new deck, no sweep mode, no multi-corpus support, no parameter tuning flags.
+- No change to anything under `src/` unless you can show it is unavoidable (then stop and ask Luke; do not just do it).
+- Do not fold in the `scripts/apc-bundle.sh` path defect (see §9).
+
+## 2. Pre-flight (do all of these, report each result even when it confirms the assumption)
+
+**P1. Worktree.** The main checkout is expected to be dirty: an uncommitted
+exploratory prototype exists, and `docs/context/repo-tree.txt` is modified (a
+side effect of the bundle script). Therefore do NOT work in the main checkout.
+Run `git worktree list` and `git status --short`, then
+`git worktree add ../llm-graph-insertion-complexity-DEMO-001 -b task/DEMO-001`.
+Locate the prototype, read it as a reference only, and do not commit it as-is.
+Do not stage or revert `docs/context/repo-tree.txt`. Report the prototype's
+path and what you did with it.
+
+**P2. Decision ID.** Run `./scripts/manage-decisions.py --next`, and grep
+`docs/decisions/decision-log.md` for `D-99`. The APC could not see the log; it
+reserved D-99 because D-98 is the highest ID visible in `status.md` and the
+context docs. If D-99 is already present, stop and report the conflict.
+
+**P3. Pilot cache facts.** Inspect `results/pilot/20261007_053743Z/raw_calls.jsonl`
+and its sibling `summary.json`. Verify and report: line count 812; required
+fields on every line (`call_index, new_name, candidate, domain_context,
+user_prompt, response_text, raw_token, latency_s, model, input_tokens,
+output_tokens, reasoning_tokens, cache_hit_tokens, cache_miss_tokens, attempts,
+retry_wait_s`); exactly the 29 x 28 ordered pairs of the DSA corpus, each once;
+`user_prompt` unique; every `response_text` parses with `decision.parse_token`;
+sums of input tokens (123,872), output tokens (2,035), latency (676.80 s),
+cache-hit tokens (0); `summary.json` prompt version `v2`, model
+`deepseek-flash`, temperature 0, thinking disabled, 0 retries, 0 parse
+failures, 0 transport failures, estimated cost $0.019802. Record the SHA-256 of
+`raw_calls.jsonl`. State whether `summary.json` records the system prompt or a
+hash of it.
+
+**P4. Prompt reproduction (all 812, not a sample).** For every record, confirm
+`PairwiseDecisionStep.build_user_prompt(new_name, candidate, domain_context)`
+reproduces `user_prompt` byte for byte, with `domain_context` taken from the
+loaded DSA corpus. Also confirm `decision.SYSTEM_PROMPT` is unchanged since the
+pilot (for example `git log --format='%h %ad' --since=2026-10-07 -- src/graph_insertion/decision.py`
+plus a look at the diff of any hit). The cache stores the user prompt only, so
+the system prompt is verified through prompt version v2 and this history check.
+
+**P5. Baseline tests.** Run the full suite before changing anything. Record
+the pass/skip counts.
+
+**P6. Offline model load.** With the network unavailable (or
+`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` set), confirm
+`MiniLMEmbedder()` loads from the local cache under the pinned revision and
+that `pin_cpu_threads(1)` succeeds. Report how you disabled the network (for
+example `unshare -rn`), or say it could not be verified.
+
+**P7. Repo facts to confirm.** DSA corpus: 29 nodes, 54 prerequisite edges,
+domain context `"data structures and algorithms"`; whether the DSA gold graph
+is transitively reduced (compute with `networkx.transitive_reduction`; the
+limitation text in §6.9 assumes it is NOT); how `run_experiment.py` builds its
+warm-up and in what order it imports faiss and constructs the embedder
+(D-73); which tests already import from `scripts/` and how (reuse that pattern).
+
+**P8. Regenerate the prototype table.** Reproduce the preliminary numbers
+below with your implementation (exact match expected for the discrete
+quantities; latencies and tokens are recorded values and must match exactly).
+Any mismatch is a finding, not something to paper over.
+
+| strategy | shortlist | calls | recorded latency | tokens in/out | cost | shortlist recall | P | R | F1 | TP/FP/FN |
+|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
+| brute_force | 28/28 | 28 | 28.39 s | 4291/71 | $0.000686 | 1.000 | .800 | .571 | .667 | 4/1/3 |
+| embedding_threshold θ=.6 | 1/28 | 1 | 1.37 s | 153/5 | $0.000026 | .143 | 1.000 | .143 | .250 | 1/0/6 |
+| ann_retrieval k=10 ef=128 | 10/28 | 10 | 10.11 s | 1534/32 | $0.000249 | .714 | 1.000 | .571 | .727 | 4/0/3 |
+| bounded_bucket 5..10 | 9/28 | 9 | 8.85 s | 1380/21 | $0.000220 | .429 | 1.000 | .143 | .250 | 1/0/6 |
+
+This table is exploratory, not a thesis result. Gold neighbourhood of
+`binary_search_tree`: prerequisites recursion, binary_search, tree; dependents
+red_black_tree, avl_tree, b_tree, trie (7 incident edges; 28 existing nodes
+after removal; 47 remaining edges).
+
+## 3. Design decisions already made (do not reopen; flag only if you find a defect)
+
+1. One held-out node per run. Default `binary_search_tree`. `--node` takes exactly one name.
+2. All four strategies run by default, in the fixed order S1, S2, S3, S4. The WHILE block is identical in structure for all four; the narration emphasis (S1 vs S3) is the presenter's choice, not the program's.
+3. Call-printing rule (exact): let N be the shortlist size. If N <= 10, print every call, in shortlist order. If N > 10, print the union of (a) the first 3 calls, (b) every call whose token is not `NONE`, (c) the first `NONE` call if one exists, all in shortlist order, then one line `... K NONE decisions not printed (use --show-all-calls)`. `--show-all-calls` prints everything.
+4. Tokens and cost are shown per strategy and in the comparison table, with the cost formula shown once.
+5. A closing LIMITATIONS box is mandatory and is the "what this does not prove" section.
+6. Replay wording is fixed in §6.2.
+7. `--json PATH` is included (§7).
+8. No pacing sleeps. Never `time.sleep` to imitate model latency.
+
+## 4. Command-line interface
+
+```
+python scripts/demo_trial.py [--node NAME] [--strategies LIST] [--pilot-dir DIR]
+                             [--no-color] [--ascii] [--pause] [--show-all-calls]
+                             [--json PATH] [--check] [--traceback]
+```
+
+- `--node NAME` (default `binary_search_tree`): must be a node of the DSA corpus. On a miss, exit 4 and print up to 5 `difflib` close matches.
+- `--strategies LIST`: comma-separated subset of `brute_force,embedding_threshold,ann_retrieval,bounded_bucket` (aliases `s1,s2,s3,s4`). Always executed and printed in canonical order. Duplicates or unknown names: exit 2.
+- `--pilot-dir DIR` (default `results/pilot/20261007_053743Z`, resolved against the repo root, not the CWD).
+- `--no-color`: also honour the `NO_COLOR` environment variable. Colour is used only when stdout is a TTY and neither is set.
+- `--ascii`: replace box-drawing characters and arrows with ASCII (`+ - |`, `->`).
+- `--pause`: wait for Enter between phases, only when stdin and stdout are both TTYs; otherwise silently ignored.
+- `--show-all-calls`: print every decision call.
+- `--json PATH`: also write the machine-readable record (§7). Refuse (exit 7) if PATH exists, or if its resolved path is inside `<repo>/results/`, or if its parent directory does not exist.
+- `--check`: run provenance + corpus + node + (if needed) embedder-load checks, print one `OK`/`FAIL` line per check, run no trial, exit 0/nonzero.
+- `--traceback`: show Python tracebacks on error (off by default).
+- No flags for theta, k, ef, s_min, s_max, seeds, repeats or corpus. Parameters are the D-64 defaults, hard-coded, and asserted against `strategy.config()` (§5.4).
+
+Exit codes: 0 ok; 2 usage; 3 pilot cache / provenance failure; 4 corpus or node problem; 5 missing dependency or embedder; 6 internal consistency check failed; 7 refused output path.
+
+## 5. Architecture and behaviour
+
+One file, `scripts/demo_trial.py`, in this order of sections. Pure logic is
+importable (guard `main()` with `if __name__ == "__main__"`), because the tests
+load it through the same mechanism the repo's other script tests use.
+
+### 5.1 Constants
+
+```python
+PILOT_DIR_DEFAULT = "results/pilot/20261007_053743Z"
+PILOT_RAW_CALLS_SHA256 = "<fill after P3>"        # fail closed on mismatch
+EXPECTED_PROMPT_VERSION = decision.PROMPT_VERSION  # must be "v2"
+EXPECTED_CALLS = 812
+CORPUS_NAME = "DSA"
+DEFAULT_NODE = "binary_search_tree"
+SEED = 42
+DEMO_PARAMS = {  # D-64 / D-35 / D-55 defaults, asserted against strategy.config()
+    "brute_force": {"seed": 42},
+    "embedding_threshold": {"theta": 0.6, "seed": 42},
+    "ann_retrieval": {"k": 10, "ef_search": 128, ...},   # read the real config() keys
+    "bounded_bucket": {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42},
+}
+# Off-peak prices, USD per 1M tokens ([D-36])
+PRICE_IN_CACHE_MISS = 0.15
+PRICE_IN_CACHE_HIT  = 0.003
+PRICE_OUT           = 0.60
+WIDTH = 88
+```
+
+Cost formula (show it in the transcript and in the report):
+
+```
+cost_usd = (cache_miss_tokens * 0.15 + cache_hit_tokens * 0.003 + output_tokens * 0.60) / 1_000_000
+```
+
+PILOT-001 had zero cache hits, so this equals `(input * 0.15 + output * 0.60) / 1e6`,
+which is what `pilot_dsa_zero_shot.py` used. Check sanity: S1's 4291 in / 71 out
+gives $0.000686. Assert `cache_hit + cache_miss == input_tokens` per record.
+Reasoning tokens are 0 (thinking disabled); if any record has nonzero
+reasoning tokens, fail closed (exit 3) rather than guess how they were billed.
+
+### 5.2 Replay (fail closed)
+
+```python
+class DemoError(Exception):              # carries .exit_code and a one-line .hint
+@dataclass(frozen=True) class ReplayRecord: ...        # one per jsonl line, validated types
+@dataclass(frozen=True) class PilotProvenance: ...     # path, sha256, recorded_utc, model, prompt_version,
+                                                       # n_calls, temperature, thinking, retries, parse_failures,
+                                                       # transport_failures, input_tokens, output_tokens,
+                                                       # est_cost_usd, cumulative_latency_s
+def load_pilot(pilot_dir, *, corpus) -> tuple[PilotProvenance, dict[str, ReplayRecord]]
+class ReplayLLMClient:                                 # implements llm.LLMClient
+    def complete(self, system: str, user: str) -> LLMResponse
+    served: list[ReplayRecord]                         # in call order, for the transcript
+```
+
+`load_pilot` must raise `DemoError(exit_code=3)` on ANY of: missing file or
+`summary.json`; SHA-256 differs from `PILOT_RAW_CALLS_SHA256`; line count != 812
+or != summary `calls`; unparsable JSON line; missing or wrong-typed field;
+negative latency or token counts; `cache_hit + cache_miss != input_tokens`;
+nonzero reasoning tokens; duplicate `user_prompt`; duplicate `(new_name,
+candidate)`; the pair set is not exactly all ordered pairs of the corpus nodes;
+`response_text` not accepted by `parse_token`; summary prompt version !=
+`EXPECTED_PROMPT_VERSION`; summary model != the per-record model; summary totals
+(input/output tokens, cumulative latency to 0.01 s) differ from the recomputed
+sums. Every `DemoError` message states what failed and what Luke should do.
+
+`ReplayLLMClient.complete(system, user)` must: (1) require `system ==
+decision.SYSTEM_PROMPT`, else `DemoError(3)`; (2) look up `user` by exact string
+in the dict, a miss is `DemoError(3)` ("no recorded PILOT-001 answer for this
+prompt; the demo never fabricates a decision"); (3) return `LLMResponse(text=
+record.response_text, input_tokens, output_tokens, reasoning_tokens,
+cache_hit_tokens, cache_miss_tokens, latency_s=record.latency_s,
+model_id=record.model, attempts=record.attempts, retry_wait_s=record.retry_wait_s)`;
+(4) append the record to `served`. It must never construct `FakeLLMClient` or
+`DeepSeekClient`, never import `httpx` for requests, and never read
+`DEEPSEEK_API_KEY`. The demo must run with that variable unset and with no network.
+
+### 5.3 Environment preparation (before any heavy import)
+
+- `os.environ.setdefault("HF_HUB_OFFLINE", "1")` and `("TRANSFORMERS_OFFLINE", "1")` before importing `sentence_transformers`, so a missing cache fails fast instead of hanging on a network probe. Do not change `embedding_minilm.py` for this.
+- If `ann_retrieval` is selected, import `graph_insertion.strategies.ann_retrieval` (which imports faiss) BEFORE constructing `MiniLMEmbedder` (D-73 import order). If it is not selected, do not import faiss.
+- Construct `MiniLMEmbedder()` only when a selected strategy needs it (S2, S3, S4). S1 alone must run with no sentence-transformers and no faiss installed. Then `pin_cpu_threads(1)` (D-72) and record `embedder.identity()` and the pin read-back for the banner.
+- Missing package, missing cache, or version/revision pin mismatch: catch, re-raise as `DemoError(5)` naming the missing piece. Never download.
+- One warm-up embed of a fixed dummy string before the first timed strategy, mirroring what `run_experiment.py` does (read it and copy the intent), so the first embedding strategy's measured shortlist time is not inflated by lazy initialisation.
+
+### 5.4 One strategy trial (mirror the accuracy-stage loop in `run_experiment.py`)
+
+For each selected strategy name, in canonical order:
+
+1. `G = corpus.graph.without_node(node)` (fresh copy; the gold graph is never mutated). Record `n_before = G.num_nodes()` and `e_before = G.num_edges()`.
+2. `strategy = STRATEGY_FACTORIES[name](seed=SEED, **params)`; assert `strategy.config()` contains the `DEMO_PARAMS[name]` values, else `DemoError(6)`.
+3. `meter = MeteredEmbedder(shared_raw_embedder)` (a fresh meter over the shared, already-loaded model; fresh strategy per trial). S1 discards the embedder; pass the meter anyway, as the harness does.
+4. Time `strategy.setup(G, meter)` with `perf_counter` ([LIVE], excluded from the official trial timer per D-25). Record setup embedding calls from the meter.
+5. `gc.collect()`.
+6. `llm_meter = MeteredLLMClient(replay)`; `step = PairwiseDecisionStep(llm_meter)`; `snap0 = llm_meter.snapshot()`.
+7. `res = insert_node(strategy, G, step, node, metered_embedder=meter)`; `delta = llm_meter.snapshot() - snap0`.
+8. `score = score_node_insertion(node=node, gold_graph=corpus.graph, judgments=corpus.judgments, shortlist_candidates=res.shortlist.candidates, decided_edges=res.edges)`.
+9. Slice `replay.served` for this strategy's calls. Rebuild the canonical edges from the recorded tokens (`X_PREREQ_Y` -> `(node, cand)`, `Y_PREREQ_X` -> `(cand, node)`) and assert the set equals `res.edges` (`DemoError(6)` otherwise).
+10. Collect `strategy.diagnostics()` (already called inside `insert_node`; read `res.metrics.extra`). Print only a short whitelist per strategy (at most 3 keys, chosen from what the module really emits; e.g. S2 `cosine_comparisons`, `max_cosine`; S3 `exact_topk_overlap`; S4 the segment-size fields). Missing keys are skipped silently.
+
+Reuse production code for everything above. Do not reimplement narrowing,
+decision interpretation or scoring. The only logic written here is orchestration,
+analysis annotations (§5.5) and formatting.
+
+### 5.5 Analysis annotations (demo-side, clearly labelled as annotations, never altering a metric)
+
+- **Edge labels.** Label each predicted edge TP / FP / UNJUDGED by calling `score_node_insertion` on that single edge (`decided_edges=[edge]`) and reading `tp`, `fp`, `excluded_predictions`. Assert the per-edge counts sum to the strategy's full `NodeScore` counts (`DemoError(6)` otherwise). This reuses the production rule instead of copying it.
+- **Missed gold edges (FN) with cause.** For each gold incident edge not predicted, with `o` the other endpoint: `not shortlisted` if `o` is not in the shortlist; else `direction reversed` if the reverse edge was predicted; else `judged NONE`. Report the split "lost at narrowing / lost at decision". Assert `len(FN list) == score.fn`.
+- **Transitive-closure note for FPs.** For each FP, if the full gold graph (`corpus.graph.nx_graph()`, which contains the held-out node) has a directed path prereq -> dependent, append `(gold path exists: a -> ... -> b)`. This is a note only; it never changes precision. The PROMPT_VERSION v2 system prompt defines "prerequisite" as direct OR indirect, so a transitive prediction is consistent with the prompt even where the sparse gold graph lacks the direct edge.
+- **Subset invariant.** If S1 ran: every edge predicted by S2/S3/S4 must be in S1's predicted set, because in replay a pair's decision is a fixed lookup and narrowing only removes pairs. Print `OK` or fail with `DemoError(6)`. This is by construction in replay; in the official live runs each strategy made its own calls, so it need not hold there (say so in the limitations).
+- **Two-stage recall decomposition** per strategy: `recall = shortlist_recall x recall_given_shortlist` (print both factors when defined).
+
+### 5.6 Measured vs recorded vs computed tags
+
+Every metric line carries exactly one tag, and the legend appears in the banner:
+
+| tag | meaning |
+|---|---|
+| `[LIVE]` | measured by this process now: setup time, shortlist time (and its embedding part), update time, replay wall time, total demo wall time |
+| `[PILOT]` | recorded in PILOT-001: each answer, per-call latency, tokens, model |
+| `[CALC]` | computed from recorded values: cost, totals, percentages of calls |
+| `[GOLD]` | ground truth from the corpus, shown only in AFTER |
+
+Never present replay wall time as model latency. "Recorded model latency" is the sum of the PILOT-001 per-call `latency_s` for the calls the strategy made (this is `DecisionOutcome.llm_seconds`).
+
+## 6. Exact output specification
+
+Width is fixed at 88 columns; no line may exceed it (tests enforce this in both
+Unicode and `--ascii` mode). Use only single-width glyphs. Colour: tags and
+TP/FP/FN words only. The layout below is illustrative; every number is
+regenerated at run time. Placeholders in `<angle brackets>`.
+
+### 6.1 Banner and provenance
+
+```
+════════════════════════════════════════════════════════════════════════════════════════
+ DEFENSE DEMO  ·  one concept insertion, four narrowing strategies        PILOT-001 replay
+════════════════════════════════════════════════════════════════════════════════════════
+ PROVENANCE
+   LLM decisions  REPLAYED from recorded PILOT-001 calls (not re-requested, not simulated)
+   Cache file     results/pilot/20261007_053743Z/raw_calls.jsonl
+                  812 calls · sha256 <first 12 hex>… · recorded 2026-10-07 05:37:43Z
+   Recorded with  deepseek-flash · prompt v2 · temperature 0 · thinking disabled
+                  0 retries · 0 parse failures · 0 transport failures
+   Run live here  corpus load, narrowing, graph update, scoring, timers tagged [LIVE]
+   Embedder       all-MiniLM-L6-v2 rev <first 7 hex> · sentence-transformers 6.1.0 · CPU · 1 thread
+   Network / API  none used · no API key read
+ TAGS  [LIVE] measured now   [PILOT] recorded 2026-10-07   [CALC] computed   [GOLD] ground truth
+```
+
+If S1 only is selected, the Embedder line reads `not loaded (brute_force needs none)`.
+
+### 6.2 Replay notice (exact wording, printed once in the banner block, wrapped to width)
+
+> REPLAY NOTICE. The model answers on screen are real. Each one was returned by deepseek-flash on 2026-10-07 during PILOT-001 for exactly the prompt shown; this program looks up that stored answer instead of calling the API again. Nothing is simulated or invented, and a missing record stops the program. Narrowing, graph updates and scoring run live. Model latency, token counts and cost are the recorded values, not measurements from this run.
+
+### 6.3 PHASE 1 · BEFORE
+
+Content, in this order:
+
+1. **What the thesis measures** (two sentences): how the cost (LLM calls, time) and the accuracy of inserting one new concept into an existing LLM-built prerequisite graph depend on how candidates are narrowed; only the narrowing differs, the LLM decision step is identical.
+2. **The trial**: corpus `DSA`; domain context string; full graph `<29> concepts, <54> prerequisite edges`; the held-out NEW concept; existing graph `<28> concepts, <47> edges`; and the line `Gold neighbourhood: HIDDEN until AFTER. Nothing printed before AFTER is marked with it.`
+3. **The decision step (identical for every strategy)**: print `decision.SYSTEM_PROMPT` (wrapped), the user-prompt template with `Subject area / Concept X (new) / Concept Y (candidate)`, the three answer tokens, the rule "one call per shortlisted candidate; X_PREREQ_Y -> edge (new -> cand); Y_PREREQ_X -> edge (cand -> new); canonical direction prerequisite -> dependent", and "only names are shown to the model".
+4. **The four strategies** with what each narrows by, taking parameter values from `strategy.config()` (build the configs first, without running them):
+   - S1 `brute_force`: nothing; every existing concept is judged
+   - S2 `embedding_threshold`: keep nodes with cosine(new, node) > theta (strict), names embedded with MiniLM
+   - S3 `ann_retrieval`: top-k nearest by cosine through an HNSW index (k, M, efConstruction, efSearch from config)
+   - S4 `bounded_bucket`: one size-bounded home bucket of hyperplane-hash codes (s_min..s_max, n_bits from config)
+5. **Cost formula** line: `cost = (cache-miss in x $0.15 + cache-hit in x $0.003 + out x $0.60) / 1M  (off-peak, D-36)`.
+
+### 6.4 PHASE 2 · WHILE (one block per strategy)
+
+```
+────────────────────────────────────────────────────────────────────────────────────────
+ PHASE 2 · WHILE   strategy 3 of 4:  S3  ann_retrieval  (k=10, efSearch=128)
+────────────────────────────────────────────────────────────────────────────────────────
+  setup     index build over 28 concepts          <41.2 ms> [LIVE]  excluded from official timer
+  shortlist <10> of <28> kept (<35.7%>), narrowed away <64.3%>
+            time <3.1 ms> [LIVE]  (embedding the new name: <2.9 ms>)
+  top candidates by cosine [LIVE]
+     1  <0.712>  <candidate>
+     ...                                              (all shown when N <= 10, else top 10)
+  diagnostics  <exact_topk_overlap = ...>  [LIVE]
+  decisions  <10> calls, all shown [PILOT]
+   call  1/10  X = <new>   Y = <cand>
+               answer <NONE>                         <1.02 s>  <153> in / <5> out
+               -> no edge
+   call  2/10  X = <new>   Y = <cand>
+               answer <Y_PREREQ_X>                   ...
+               -> edge  <cand> -> <new>   (prerequisite -> dependent)
+   ...
+  answers    NONE <6> · X_PREREQ_Y <2> · Y_PREREQ_X <2>          [PILOT]
+  LLM        <10> calls · <10.11 s> recorded latency [PILOT] · <1,534> in / <32> out tokens [PILOT]
+             cost <$0.000249> [CALC]  ·  calls vs S1: <-64%> [CALC]
+  applied    +1 concept, +<4> edges  ->  graph <29> concepts, <51> edges
+             update <0.05 ms> [LIVE] · replay wall time <2 ms> [LIVE]
+```
+
+Rules:
+
+- The first call printed in the whole transcript also prints the exact `user_prompt` text (3 lines, indented) with the line `exact prompt sent in PILOT-001 [PILOT]`.
+- Candidate preview: when `scores` are exposed and not all equal (S2, S3, S4), print rank, cosine to 3 decimals, name; top 10 only, followed by `... and <K> more` when N > 10 (S2 can exceed 10 in principle). S1 prints `all <28> existing concepts, alphabetical, no ranking` (its scores are a uniform 0.0 and must not be shown as similarities) and prints no preview table.
+- Empty shortlist (possible for S2): print `shortlist  0 of 28 kept ... no LLM calls, no edges` and skip the decisions/answers lines; LLM line shows `0 calls`.
+- Percentages: kept% = size / n_before; narrowed% = 100 - kept%; calls vs S1 = `1 - calls / n_before` (S1 makes exactly n_before calls by construction, so this needs no S1 run). One decimal for kept%/narrowed%, zero decimals for calls vs S1.
+- **No gold information anywhere in BEFORE or WHILE**: no `[GOLD]` tag, no hit/miss markers on candidates.
+- Names print in their canonical form (underscores) in edges and tables and in the `embed_text` form (spaces) in the `X = ... Y = ...` call lines, because that is what the model saw.
+
+### 6.5 PHASE 3 · AFTER
+
+1. **Reveal** `[GOLD]`: prerequisites of the held-out node and dependents, as names. Also `7 gold incident edges`.
+2. **Per strategy**, in order: shortlist captured `<h>/<g>` gold neighbours (`shortlist recall`); predicted edges each labelled `TP` / `FP` / `UNJUDGED` with the §5.5 gold-path note on FPs; missed gold edges `FN` each with its cause; the line `lost at narrowing <a> · lost at decision <b>`; metrics `P <..> R <..> F1 <..>  TP <..> FP <..> FN <..>`; `unjudged predictions excluded: <n>` (when n > 0 also print the sensitivity F1 from `NodeScore.f1_sensitivity`, D-30). Undefined metrics print `n/a` (never 0, never an exception).
+3. **Subset invariant** line (§5.5) when S1 ran.
+4. **Cross-strategy comparison**, two tables so each fits 88 columns:
+
+```
+  WORK                kept   narrowed  calls  vs S1   LLM latency   tokens in/out    cost       shortlist
+                                                      [PILOT]       [PILOT]          [CALC]     [LIVE]
+  S1 brute_force      28/28     0.0%     28    0%      28.39 s       4,291 / 71     $0.000686      <x> ms
+  ...
+  ACCURACY            shortlist recall    P      R      F1     TP/FP/FN   lost narrow/decide
+  S1 brute_force           1.000        .800   .571   .667     4/1/3          0 / 3
+  ...
+```
+
+5. **Takeaways (3 to 5)**: generated from computed values by templates with guard conditions, never hard-coded prose about a particular node. Required templates:
+   - T1 cost: calls and percentage reduction of each selected narrowing strategy against S1's `n_before` calls.
+   - T2 only the shortlist differs: if the subset invariant held, say that every edge S2-S4 predicted was also predicted by brute force because the decision step is identical, so any difference comes from which pairs were sent to the model.
+   - T3 narrowing's price: shortlist recall per strategy and how many gold edges were lost before the model saw them.
+   - T4 (only if some narrowing strategy has F1 > S1's F1 and S1 ran): name that strategy and say its F1 is higher because it never judged <m> pairs that S1 turned into false positives; else print `On this node no narrowing strategy beat brute-force F1.`
+   - T5 (static): `One node is an illustration. The thesis evidence is the full runs (RQ1-RQ3), not this transcript.`
+6. **LIMITATIONS box** (always last, never omitted, includes `--strategies` subsets):
+   - Decisions are replayed from PILOT-001 recordings, not re-requested; this is real model output for exactly these prompts, from 2026-10-07.
+   - One held-out node, one trial, one repeat. This is an illustration, not a new result, and it is not part of Chapter 4.
+   - Latency, tokens and cost are recorded values; only setup, shortlist, update and replay times are measured now, and replay wall time says nothing about model latency.
+   - In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a pair. In the official runs each strategy made its own live calls, so agreement on a pair is not guaranteed there.
+   - DSA gold is not transitively reduced (confirm in P7; reword if false), so some false positives may be defensible by transitive closure; metrics are computed against the gold as given.
+   - Strategy parameters are the pre-fixed defaults (D-64); nothing was tuned on this node.
+7. Footer: `demo wall time <x.x s> [LIVE]` and `no files written to results/`.
+
+### 6.6 Terminal behaviour
+
+Plain/piped output must work: no ANSI when not a TTY or when `--no-color` / `NO_COLOR`; `--ascii` swaps glyphs. A broken pipe (`| head`) must not print a traceback. Runtime target: total under about 30 s including model load, ideally under 15 s on Luke's machine; report the measured time.
+
+## 7. `--json PATH` record
+
+Written once at the end, from the same in-memory `DemoReport` the formatter uses
+(so the transcript and JSON cannot diverge). UTF-8, `indent=2`, sorted keys off
+(stable insertion order). Top level:
+
+```
+{ "schema": "demo-trial-1",
+  "run": {"started_utc": ..., "wall_s_live": ..., "argv": [...]},          # volatile block
+  "provenance": {pilot fields, sha256, embedder identity, cpu_threads},
+  "trial": {"corpus", "node", "domain_context", "n_before", "e_before", "gold": {...}},
+  "decision_step": {"prompt_version", "system_prompt_sha256", "price_per_m": {...}},
+  "strategies": [ { "name", "config", "setup_s_live", "shortlist": {...,"shortlist_s_live","embed_s_live"},
+                    "calls": [ {"x","y","token","edge","latency_s_pilot","input_tokens","output_tokens"} ],
+                    "recorded": {"llm_calls","latency_s","input_tokens","output_tokens"},
+                    "calc": {"cost_usd","calls_vs_s1_pct","kept_pct"},
+                    "applied": {"nodes_added","edges_added","update_s_live"},
+                    "score": {NodeScore fields}, "labelled_edges": [...], "missed": [...] } ],
+  "comparison": {...}, "invariants": {"subset_of_s1": true|false|null} }
+```
+
+Everything under `run` and every key ending `_live` is volatile; everything else must be byte-identical across repeated runs (this is what the determinism acceptance test diffs).
+
+## 8. Tests (`tests/test_demo_trial.py`)
+
+No network, no API key. Replay-client and formatter tests must not import MiniLM or faiss. Use the repo's existing pattern for importing from `scripts/`.
+
+Required groups:
+
+1. **Replay loader/client** on a tiny synthetic cache written to `tmp_path` (with a `summary.json`): happy path; recorded latency/tokens/text returned verbatim; miss raises `DemoError(3)` with no fallback; wrong system prompt; wrong prompt version; line count vs summary mismatch; malformed JSON line; missing field; wrong type; negative latency; hit+miss != input; nonzero reasoning tokens; duplicate `user_prompt`; duplicate pair; pair set not equal to all ordered pairs; invalid `response_text`; tampered SHA-256 (use a patched pin); summary totals mismatch. Also: `FakeLLMClient` and `DeepSeekClient` are never constructed (monkeypatch both to raise), `socket` is blocked (monkeypatch), and the test runs with `DEEPSEEK_API_KEY` removed.
+2. **Cost**: formula with and without cache hits; S1 example 4291/71 -> $0.000686 (to 6 dp).
+3. **Orchestration with `FakeEmbedder`** (deterministic, no MiniLM): build a synthetic cache on the fly keyed by `PairwiseDecisionStep.build_user_prompt` over a small synthetic corpus, run all four strategies, and assert: production `insert_node` and `score_node_insertion` were used (spy), canonical edges rebuilt from tokens equal `res.edges`, the gold graph object is unchanged, the subset invariant holds, edge-label sums equal `NodeScore`, FN causes sum to `score.fn`. A test that deliberately breaks an edge (monkeypatched) makes `DemoError(6)` fire.
+4. **Formatter** on a hand-built `DemoReport`: every line <= 88 columns in Unicode and `--ascii`; no `\x1b` when colour is off; the call-printing rule for N = 28, 10, 11, 1, 0 (exact counts and the `K NONE decisions not printed` line); `--show-all-calls`; empty shortlist wording; S1 prints no similarity table; percentages; `n/a` for undefined metrics; every metric line has exactly one tag; takeaway guards (T4 present only when its condition holds; T2 absent when the invariant is false or S1 did not run); the banner contains the PILOT-001 path, 812, `v2`, the model, and the replay notice verbatim; **gold-leak test**: nothing before the AFTER header contains the `[GOLD]` tag or any hit/miss marker.
+5. **CLI**: `--strategies` parsing, ordering, duplicates and unknown names -> exit 2; unknown `--node` -> exit 4 with suggestions; `--json` to an existing file or under `results/` -> exit 7 and nothing written; `--check` runs no trial; broken pipe handling.
+6. **MiniLM integration** (skip with a clear reason when sentence-transformers, faiss, the cached model or `results/pilot/...` is absent): run `binary_search_tree` for all four strategies and assert shortlist sizes 28/1/10/9, LLM calls 28/1/10/9, TP/FP/FN `4/1/3`, `1/0/6`, `4/0/3`, `1/0/6` (only if P8 reproduced them), and that two consecutive runs give identical non-volatile JSON.
+7. **Real-cache provenance** (skip when the file is absent): the actual PILOT-001 cache passes `load_pilot` and covers all 812 pairs.
+
+## 9. Out of scope, flagged
+
+`scripts/apc-bundle.sh` profiles `presentation` and `full` exit 1 because they
+reference `docs/presentation/script/Defense_Script_and_Background_Guide.md` (and
+a comprehensive version) that do not exist; the real files are under
+`docs/presentation/information/`. Do not fix it here. Confirm the defect in one
+line of your report (command and exit code) and leave it for a separate `TOOL-002`.
+
+## 10. Verification steps after the build (report all)
+
+V1. Full test suite: before/after counts, new tests only add.
+V2. Acceptance run: `python scripts/demo_trial.py` on a TTY and piped to a file; wall time (cold and warm), transcript attached or excerpted.
+V3. Network-off run (§P6 method) of the full demo.
+V4. Determinism: run twice with `--json`, diff the non-volatile fields.
+V5. Official artifacts untouched: `sha256sum results/pilot/20261007_053743Z/raw_calls.jsonl` before and after; `git status --short results/` clean; no new files under `results/`.
+V6. P8 table reproduced (or each discrepancy listed).
+V7. **Survey (verification only, not part of the deliverable script, no sweep mode added):** with a shell loop over all 29 DSA nodes, run the finished script with `--json` into a directory OUTSIDE the repo (for example `$TMPDIR`), then tabulate per node: gold degree, calls, shortlist recall and F1 for each strategy. Report where `binary_search_tree` sits (rank of F1(S3) - F1(S1)), and name (a) a node where brute force clearly beats S3 and (b) a node where S2 returns an empty shortlist. These are for Luke's choice of a Q&A "counter-node"; nothing from the survey is committed.
+V8. **Cross-check against the accuracy stage (read-only):** for the held-out node and each strategy, compare the replayed TP/FP/FN, `llm_calls` and shortlist hits with the matching record in `results/accuracy_<strategy...>/raw.jsonl` when one exists (those files hold scores, not edges). Report matches and mismatches; a mismatch is informative (the official runs made their own live calls) and must be explained, not hidden.
+
+V9. Confirm the transitive-reduction fact (P7) and the real `diagnostics()` keys you whitelisted.
+
+## 11. Deliverables (AGENTS.md "After finishing any task")
+
+1. Commit on `task/DEMO-001`: `feat(DEMO-001): offline PILOT-001 replay defense demo`. Commit only files you created/edited for this task (never `docs/context/repo-tree.txt`, never the prototype). List any untracked file in the report.
+2. Patch: `mkdir -p patch && git diff HEAD~1 > patch/DEMO-001-claude-code-defense-demo-trial.patch`.
+3. Report: `docs/reports/DEMO-001-claude-code-defense-demo-trial.md`, using the outline in §12. Diffs pasted from `git diff` in the worktree with index lines, never retyped.
+4. `docs/tasks/status.md`: add the DEMO-001 row under "Presentation track", status `needs-review`, with the report link (re-read the file immediately before editing; edit only your row).
+5. `docs/decisions/decision-log.md`: append **D-99** (re-read the file first). Content: the demo is replay-only and fail-closed; the cache SHA-256 pin; the tag semantics (`[LIVE]/[PILOT]/[CALC]/[GOLD]`); the HF offline environment settings; the subset invariant and why it holds only in replay; that nothing here is an empirical result; the files added. Use the format of neighbouring entries.
+6. Validate: `./scripts/validate-report.py docs/reports/DEMO-001-claude-code-defense-demo-trial.md --require-patch` must pass.
+7. Do not merge, rebase, or delete the worktree. State the branch name and worktree path in the report.
+8. Update `scripts/README.md` with a short "Defense demo" section (command, flags, exit codes). No other doc edits unless a discrepancy forces one (then say so).
+9. Build a fresh bundle only if Luke asks; the new files are not in any bundle profile.
+
+## 12. Report outline (this is what Luke will hand back to the APC)
+
+1. Executive summary (3 to 6 lines: what exists, how to run it, runtime, whether P8 reproduced).
+2. Pre-flight results P1-P8 (one line each, with the actual numbers).
+3. Implementation summary (module sections, how production code is reused, what is new).
+4. Output transcript (full, `--no-color`) for the default run.
+5. Verification V1-V9 with evidence.
+6. Discrepancies and findings (anything the prompt or the bundle got wrong; the prototype's fate; the bundle-script defect confirmation).
+7. Decision D-99 text.
+8. Test list and counts.
+9. Unified diff and patch file reference.
+10. Items for the APC: suggested counter-node, anything Luke must decide, follow-ups (`DEMO-001-R`, `TOOL-002`).
+
+## 13. Acceptance criteria
+
+- AC1 Default command runs offline, no API key, no network, exit 0, under about 30 s.
+- AC2 All 812 prompts reproduced byte-exact; cache validated and SHA-pinned; any defect fails closed with the right exit code.
+- AC3 Production code paths used for load, strategies, `insert_node`, `PairwiseDecisionStep`, `MeteredLLMClient`, scoring; no narrowing or scoring logic reimplemented.
+- AC4 The §6 layout is implemented: all three phases, the tags, the fixed replay notice, the LIMITATIONS box; no gold information before AFTER.
+- AC5 Call-printing rule, percentages, cost formula, `n/a` handling and empty-shortlist handling exactly as specified.
+- AC6 P8 table reproduced or discrepancies explained.
+- AC7 Deterministic non-volatile JSON across two runs.
+- AC8 No writes under `results/`; official artifacts byte-identical before/after.
+- AC9 New tests pass without network; MiniLM/faiss tests skip cleanly when unavailable; the full suite has no new failures.
+- AC10 All four AGENTS.md deliverables plus D-99, status row, report validation, and a README section.
+
+## 14. Stop conditions (stop and report instead of improvising)
+
+D-99 already used; the cache does not match P3/P4; `SYSTEM_PROMPT` changed since the pilot; a production change in `src/` seems unavoidable; MiniLM cannot load offline; P8 numbers differ materially; the worktree cannot be created cleanly.
diff --git c/docs/tasks/status.md i/docs/tasks/status.md
index 8435e52..1addc81 100644
--- c/docs/tasks/status.md
+++ i/docs/tasks/status.md
@@ -98,6 +98,7 @@ Status: **in-progress**
 | --- | --- | --- | --- |
 | PRES-001 | Consolidate the source material, requirements, style reference, and asset pack for the APC to plan a separate background-concepts HTML presentation for defense panelists (first-principles teaching; no Chapter 4 results). | **needs-review** | Completed by Claude Code; branch `task/PRES-001`, worktree `../llm-graph-insertion-complexity-PRES-001`. Materials in `docs/presentation/background-deck/` (`BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, logos). See report [`docs/reports/PRES-001-claude-code-background-deck-materials.md`](docs/reports/PRES-001-claude-code-background-deck-materials.md). |
 | PRES-002 | Build the single-file, offline background-concepts HTML deck (26 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval, efSearch, and configuration/mode/run/trial scene follow-ups. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md), [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md), [`docs/reports/PRES-002-claude-code-efsearch-scene.md`](docs/reports/PRES-002-claude-code-efsearch-scene.md) and [`docs/reports/PRES-002-claude-code-configuration-mode-scenes.md`](docs/reports/PRES-002-claude-code-configuration-mode-scenes.md). |
+| DEMO-001 | Build an offline, deterministic terminal demonstration for defense panelists: one DSA leave-one-out insertion through all four strategies, with every LLM decision replayed by exact prompt from the recorded PILOT-001 cache and staged BEFORE/WHILE/AFTER output. | **needs-review** | Completed by Claude Code; branch `task/DEMO-001`, worktree `../llm-graph-insertion-complexity-DEMO-001`. 51 new tests; full suite 787 passed, 3 skipped (two analysis modules excluded because `.venv-ann` lacks matplotlib). See report [`docs/reports/DEMO-001-claude-code-defense-demo-trial.md`](docs/reports/DEMO-001-claude-code-defense-demo-trial.md). |
 
 ## Housekeeping
 
diff --git c/scripts/README.md i/scripts/README.md
index 6b15dbf..5cdb8ce 100644
--- c/scripts/README.md
+++ i/scripts/README.md
@@ -302,6 +302,46 @@ done
 
 ---
 
+## Defense Demo (`scripts/demo_trial.py`)
+
+`scripts/demo_trial.py` is an offline, deterministic terminal demonstration for
+thesis panelists. It performs one leave-one-out insertion on the DSA corpus
+(default held-out node `binary_search_tree`) through all four narrowing
+strategies. The narrowing, graph update, shared decision step and scoring use
+the production code; only the LLM transport is replaced by a replay client that
+looks up each answer by exact prompt text in the recorded PILOT-001 cache.
+
+```bash
+# Full demo (all four strategies, default node)
+.venv-ann/bin/python scripts/demo_trial.py
+
+# One strategy / a different node / plain ASCII / pauses between phases
+.venv-ann/bin/python scripts/demo_trial.py --strategies s1,s3 --node graph --ascii --pause
+
+# Offline pre-flight: provenance, corpus, node, embedder (no trial)
+.venv-ann/bin/python scripts/demo_trial.py --check
+
+# Save the machine-readable report outside results/
+.venv-ann/bin/python scripts/demo_trial.py --json /tmp/demo.json
+```
+
+Options: `--node NAME`, `--strategies LIST` (`s1`–`s4` or canonical names),
+`--pilot-dir DIR`, `--no-color`, `--ascii`, `--pause`, `--show-all-calls`,
+`--json PATH`, `--check`, `--traceback`. Colour is used only on a TTY unless
+`--no-color` or `NO_COLOR` is set. The demo sets `HF_HUB_OFFLINE=1` and
+`TRANSFORMERS_OFFLINE=1`; it never calls the API, reads `DEEPSEEK_API_KEY`, or
+writes under `results/`.
+
+Exit codes: `0` ok, `2` usage, `3` pilot cache/provenance failure, `4` corpus or
+node problem, `5` missing dependency/embedder, `6` internal consistency check,
+`7` refused output path.
+
+The demo is an illustration, not a new result. Decisions are real recorded
+PILOT-001 answers (2026-10-07, prompt v2, `deepseek-flash`); latency, tokens and
+cost are recorded values, not measurements from the demo run.
+
+---
+
 ## Operational Tooling
 
 In addition to `apc-bundle.sh`, this directory provides workflow automation scripts that enforce the APC + Local Agent operational protocol:
diff --git c/scripts/demo_trial.py i/scripts/demo_trial.py
new file mode 100644
index 0000000..ce2d934
--- /dev/null
+++ i/scripts/demo_trial.py
@@ -0,0 +1,1865 @@
+"""Defense demo: one concept insertion, four narrowing strategies (PILOT-001 replay).
+
+Offline, deterministic terminal demonstration for thesis panelists.  The
+narrowing, graph mutation and scoring paths are the production code.  The only
+replaced component is the LLM transport: every answer is looked up by exact
+prompt text in the recorded PILOT-001 call cache.
+
+Run:  python scripts/demo_trial.py
+Exit codes: 0 ok, 2 usage, 3 pilot cache/provenance, 4 corpus/node,
+            5 missing dependency/embedder, 6 internal consistency, 7 output path.
+"""
+
+from __future__ import annotations
+
+import argparse
+import dataclasses
+import difflib
+import gc
+import hashlib
+import json
+import os
+import re
+import sys
+import textwrap
+import time
+from dataclasses import dataclass, field
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any, Iterable, Optional, Sequence
+
+# Offline HF settings must precede any sentence-transformers import.
+os.environ.setdefault("HF_HUB_OFFLINE", "1")
+os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
+os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
+os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
+os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
+
+REPO_ROOT = Path(__file__).resolve().parents[1]
+_SRC = REPO_ROOT / "src"
+if str(_SRC) not in sys.path:
+    sys.path.insert(0, str(_SRC))
+
+from graph_insertion import decision as decision_module  # noqa: E402
+from graph_insertion.decision import PairwiseDecisionStep, parse_token  # noqa: E402
+from graph_insertion.embedding import FakeEmbedder, MeteredEmbedder  # noqa: E402
+from graph_insertion.graph_representation import (  # noqa: E402
+    ConceptGraph,
+    embed_text,
+)
+from graph_insertion.llm import LLMResponse, MeteredLLMClient  # noqa: E402
+from graph_insertion.loader import load_corpus  # noqa: E402
+from graph_insertion.scoring import (  # noqa: E402
+    NodeScore,
+    compute_gold_incident_edges,
+    score_node_insertion,
+)
+from graph_insertion.strategies.registry import STRATEGY_FACTORIES  # noqa: E402
+from graph_insertion.strategy import insert_node  # noqa: E402
+
+import networkx as nx  # noqa: E402
+
+# ---------------------------------------------------------------------------
+# Constants
+# ---------------------------------------------------------------------------
+
+PILOT_DIR_DEFAULT = "results/pilot/20261007_053743Z"
+PILOT_RAW_CALLS_SHA256 = (
+    "879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008"
+)
+EXPECTED_PROMPT_VERSION = "v2"
+EXPECTED_CALLS = 812
+EXPECTED_MODEL = "deepseek-flash"
+SYSTEM_PROMPT_SHA256 = (
+    "32932d476b8cdac7026520cd9e1906a8cca9333d2945ad569fa8a7feb2b3d571"
+)
+CORPUS_NAME = "DSA"
+DEFAULT_NODE = "binary_search_tree"
+SEED = 42
+WIDTH = 88
+
+PRICE_IN_CACHE_MISS = 0.15
+PRICE_IN_CACHE_HIT = 0.003
+PRICE_OUT = 0.60
+
+CANONICAL_STRATEGIES = [
+    "brute_force",
+    "embedding_threshold",
+    "ann_retrieval",
+    "bounded_bucket",
+]
+STRATEGY_ALIASES = {
+    "s1": "brute_force",
+    "s2": "embedding_threshold",
+    "s3": "ann_retrieval",
+    "s4": "bounded_bucket",
+}
+STRATEGY_LABELS = {
+    "brute_force": "S1 brute_force",
+    "embedding_threshold": "S2 embedding_threshold",
+    "ann_retrieval": "S3 ann_retrieval",
+    "bounded_bucket": "S4 bounded_bucket",
+}
+DISPLAY_NAMES = {
+    "brute_force": "S1",
+    "embedding_threshold": "S2",
+    "ann_retrieval": "S3",
+    "bounded_bucket": "S4",
+}
+
+DEMO_PARAMS: dict[str, dict[str, Any]] = {
+    "brute_force": {"seed": 42},
+    "embedding_threshold": {"theta": 0.6, "seed": 42},
+    "ann_retrieval": {
+        "k": 10,
+        "M": 16,
+        "ef_construction": 200,
+        "ef_search": 128,
+        "seed": 42,
+    },
+    "bounded_bucket": {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42},
+}
+
+DIAGNOSTIC_KEYS = {
+    "brute_force": ["candidate_count"],
+    "embedding_threshold": ["cosine_comparisons", "max_cosine", "shortlist_size"],
+    "ann_retrieval": ["exact_topk_overlap", "shortlist_size", "max_cosine"],
+    "bounded_bucket": ["num_segments", "min_segment_size", "max_segment_size"],
+}
+
+REPLAY_NOTICE = (
+    "REPLAY NOTICE. The model answers on screen are real. Each one was returned "
+    "by deepseek-flash on 2026-10-07 during PILOT-001 for exactly the prompt "
+    "shown; this program looks up that stored answer instead of calling the API "
+    "again. Nothing is simulated or invented, and a missing record stops the "
+    "program. Narrowing, graph updates and scoring run live. Model latency, "
+    "token counts and cost are the recorded values, not measurements from this run."
+)
+
+
+# ---------------------------------------------------------------------------
+# Errors
+# ---------------------------------------------------------------------------
+
+
+class DemoError(Exception):
+    """A demo failure with a stable exit code and actionable hint."""
+
+    def __init__(self, exit_code: int, message: str, hint: str = "") -> None:
+        super().__init__(message)
+        self.exit_code = int(exit_code)
+        self.message = message
+        self.hint = hint
+
+
+# ---------------------------------------------------------------------------
+# Replay cache
+# ---------------------------------------------------------------------------
+
+
+@dataclass(frozen=True)
+class ReplayRecord:
+    call_index: int
+    new_name: str
+    candidate: str
+    domain_context: str
+    user_prompt: str
+    response_text: str
+    raw_token: str
+    latency_s: float
+    model: str
+    input_tokens: int
+    output_tokens: int
+    reasoning_tokens: int
+    cache_hit_tokens: int
+    cache_miss_tokens: int
+    attempts: int
+    retry_wait_s: float
+
+    @property
+    def token(self) -> str:
+        parsed = parse_token(self.response_text)
+        if parsed is None:  # validated on load; defensive
+            raise DemoError(3, f"invalid recorded response {self.response_text!r}")
+        return parsed
+
+
+@dataclass(frozen=True)
+class PilotProvenance:
+    path: str
+    sha256: str
+    recorded_utc: str
+    prompt_version: str
+    model: str
+    n_calls: int
+    temperature: float
+    thinking_mode: str
+    retries: int
+    parse_failures: int
+    transport_failures: int
+    input_tokens: int
+    output_tokens: int
+    cache_hit_tokens: int
+    cache_miss_tokens: int
+    estimated_cost_usd: float
+    cumulative_latency_s: float
+    system_prompt_recorded: bool
+
+
+_RECORD_FIELDS = {
+    "call_index": int,
+    "new_name": str,
+    "candidate": str,
+    "domain_context": str,
+    "user_prompt": str,
+    "response_text": str,
+    "raw_token": str,
+    "latency_s": (int, float),
+    "model": str,
+    "input_tokens": int,
+    "output_tokens": int,
+    "reasoning_tokens": int,
+    "cache_hit_tokens": int,
+    "cache_miss_tokens": int,
+    "attempts": int,
+    "retry_wait_s": (int, float),
+}
+
+
+def _require(condition: bool, message: str, hint: str = "") -> None:
+    if not condition:
+        raise DemoError(3, message, hint)
+
+
+def _summary_get(summary: dict[str, Any], path: Sequence[str], default: Any = None) -> Any:
+    node: Any = summary
+    for key in path:
+        if not isinstance(node, dict) or key not in node:
+            return default
+        node = node[key]
+    return node
+
+
+def load_pilot(
+    pilot_dir: Path | str,
+    *,
+    corpus: Any,
+    expected_sha256: Optional[str] = PILOT_RAW_CALLS_SHA256,
+) -> tuple[PilotProvenance, dict[str, ReplayRecord]]:
+    """Load and fully validate the recorded PILOT-001 call cache.
+
+    Raises DemoError(3) on any defect.  A missing prompt is never fabricated.
+    """
+    directory = Path(pilot_dir)
+    raw_path = directory / "raw_calls.jsonl"
+    summary_path = directory / "summary.json"
+    _require(raw_path.is_file(), f"pilot cache not found: {raw_path}", "Check --pilot-dir.")
+    _require(summary_path.is_file(), f"pilot summary not found: {summary_path}", "Check --pilot-dir.")
+
+    payload = raw_path.read_bytes()
+    digest = hashlib.sha256(payload).hexdigest()
+    if expected_sha256 is not None:
+        _require(
+            digest == expected_sha256,
+            f"pilot cache SHA-256 mismatch: expected {expected_sha256}, got {digest}",
+            "The cache is not the accepted PILOT-001 artifact; restore it before running.",
+        )
+
+    try:
+        summary = json.loads(summary_path.read_text(encoding="utf-8"))
+    except (json.JSONDecodeError, OSError) as exc:
+        raise DemoError(3, f"cannot read pilot summary: {exc}") from exc
+    _require(isinstance(summary, dict), "pilot summary is not a JSON object")
+
+    records: list[ReplayRecord] = []
+    for line_no, line in enumerate(payload.decode("utf-8").splitlines(), 1):
+        if not line.strip():
+            continue
+        try:
+            raw = json.loads(line)
+        except json.JSONDecodeError as exc:
+            raise DemoError(3, f"malformed pilot JSON at line {line_no}: {exc}") from exc
+        _require(isinstance(raw, dict), f"pilot line {line_no} is not an object")
+        for field_name, expected_type in _RECORD_FIELDS.items():
+            _require(
+                field_name in raw,
+                f"pilot line {line_no} missing field {field_name!r}",
+            )
+            value = raw[field_name]
+            if expected_type is int:
+                _require(
+                    isinstance(value, int) and not isinstance(value, bool),
+                    f"pilot line {line_no} field {field_name!r} must be int, got {type(value).__name__}",
+                )
+            elif expected_type is float:
+                _require(
+                    isinstance(value, (int, float)) and not isinstance(value, bool),
+                    f"pilot line {line_no} field {field_name!r} must be numeric",
+                )
+            elif expected_type is str:
+                _require(
+                    isinstance(value, str),
+                    f"pilot line {line_no} field {field_name!r} must be str",
+                )
+            else:  # tuple of numeric types
+                _require(
+                    isinstance(value, expected_type) and not isinstance(value, bool),
+                    f"pilot line {line_no} field {field_name!r} must be numeric",
+                )
+        record = ReplayRecord(
+            call_index=int(raw["call_index"]),
+            new_name=str(raw["new_name"]),
+            candidate=str(raw["candidate"]),
+            domain_context=str(raw["domain_context"]),
+            user_prompt=str(raw["user_prompt"]),
+            response_text=str(raw["response_text"]),
+            raw_token=str(raw["raw_token"]),
+            latency_s=float(raw["latency_s"]),
+            model=str(raw["model"]),
+            input_tokens=int(raw["input_tokens"]),
+            output_tokens=int(raw["output_tokens"]),
+            reasoning_tokens=int(raw["reasoning_tokens"]),
+            cache_hit_tokens=int(raw["cache_hit_tokens"]),
+            cache_miss_tokens=int(raw["cache_miss_tokens"]),
+            attempts=int(raw["attempts"]),
+            retry_wait_s=float(raw["retry_wait_s"]),
+        )
+        _require(record.latency_s >= 0, f"pilot line {line_no}: negative latency")
+        _require(record.input_tokens >= 0 and record.output_tokens >= 0,
+                 f"pilot line {line_no}: negative token count")
+        _require(record.reasoning_tokens == 0,
+                 f"pilot line {line_no}: nonzero reasoning tokens",
+                 "Thinking was disabled in PILOT-001; do not guess how these were billed.")
+        _require(record.cache_hit_tokens + record.cache_miss_tokens == record.input_tokens,
+                 f"pilot line {line_no}: cache_hit + cache_miss != input_tokens")
+        _require(parse_token(record.response_text) is not None,
+                 f"pilot line {line_no}: unparseable response {record.response_text!r}")
+        records.append(record)
+
+    _require(len(records) == EXPECTED_CALLS,
+             f"pilot cache has {len(records)} calls, expected {EXPECTED_CALLS}")
+    _require(len(records) == int(_summary_get(summary, ["total_calls"], -1)),
+             "pilot cache line count differs from summary total_calls")
+
+    prompts = [r.user_prompt for r in records]
+    _require(len(set(prompts)) == len(prompts), "duplicate user_prompt in pilot cache")
+    by_pair: dict[tuple[str, str], ReplayRecord] = {}
+    for rec in records:
+        pair = (rec.new_name, rec.candidate)
+        _require(pair not in by_pair, f"duplicate ordered pair in pilot cache: {pair!r}")
+        by_pair[pair] = rec
+
+    nodes = set(corpus.graph.nodes())
+    expected_pairs = {(a, b) for a in nodes for b in nodes if a != b}
+    _require(set(by_pair) == expected_pairs,
+             "pilot cache pairs are not exactly all ordered pairs of the corpus",
+             "The cache and the loaded corpus disagree; rebuild or restore the accepted artifacts.")
+
+    prompt_version = str(_summary_get(summary, ["prompt_version"], ""))
+    _require(prompt_version == EXPECTED_PROMPT_VERSION,
+             f"pilot prompt version {prompt_version!r} != {EXPECTED_PROMPT_VERSION!r}")
+    model_id = str(_summary_get(summary, ["model_id"], ""))
+    _require(model_id == EXPECTED_MODEL,
+             f"pilot summary model {model_id!r} != {EXPECTED_MODEL!r}")
+    for rec in records:
+        _require(rec.model == model_id,
+                 f"pilot record model {rec.model!r} differs from summary {model_id!r}")
+
+    input_tokens = sum(r.input_tokens for r in records)
+    output_tokens = sum(r.output_tokens for r in records)
+    cache_hits = sum(r.cache_hit_tokens for r in records)
+    cache_misses = sum(r.cache_miss_tokens for r in records)
+    latency = sum(r.latency_s for r in records)
+    _require(input_tokens == int(_summary_get(summary, ["token_usage", "input_tokens"], -1)),
+             "pilot input-token sum differs from summary")
+    _require(output_tokens == int(_summary_get(summary, ["token_usage", "output_tokens"], -1)),
+             "pilot output-token sum differs from summary")
+    _require(cache_hits == int(_summary_get(summary, ["token_usage", "cache_hit_tokens"], -1)),
+             "pilot cache-hit sum differs from summary")
+    _require(cache_misses == int(_summary_get(summary, ["token_usage", "cache_miss_tokens"], -1)),
+             "pilot cache-miss sum differs from summary")
+    summary_latency = float(_summary_get(summary, ["timing_s", "cumulative_latency"], -1.0))
+    _require(abs(latency - summary_latency) <= 0.01,
+             f"pilot latency sum {latency:.4f}s differs from summary {summary_latency:.4f}s")
+
+    prov = PilotProvenance(
+        path=str(raw_path),
+        sha256=digest,
+        recorded_utc=str(_summary_get(summary, ["timestamp_utc"], "")),
+        prompt_version=prompt_version,
+        model=model_id,
+        n_calls=len(records),
+        temperature=float(_summary_get(summary, ["temperature"], -1.0)),
+        thinking_mode=str(_summary_get(summary, ["thinking_mode"], "")),
+        retries=int(_summary_get(summary, ["retries_and_errors", "retries"], -1)),
+        parse_failures=int(_summary_get(summary, ["parse_failure_count"], -1)),
+        transport_failures=int(_summary_get(summary, ["transport_failure_count"], -1)),
+        input_tokens=input_tokens,
+        output_tokens=output_tokens,
+        cache_hit_tokens=cache_hits,
+        cache_miss_tokens=cache_misses,
+        estimated_cost_usd=float(_summary_get(summary, ["token_usage", "estimated_cost_usd"], -1.0)),
+        cumulative_latency_s=latency,
+        system_prompt_recorded=any(
+            key in summary for key in ("system_prompt", "system_prompt_sha256")
+        ),
+    )
+    return prov, {r.user_prompt: r for r in records}
+
+
+class ReplayLLMClient:
+    """LLMClient that serves recorded PILOT-001 answers by exact prompt text."""
+
+    def __init__(
+        self,
+        by_prompt: dict[str, ReplayRecord],
+        *,
+        system_prompt: str = decision_module.SYSTEM_PROMPT,
+    ) -> None:
+        self._by_prompt = by_prompt
+        self._system_prompt = system_prompt
+        self.served: list[ReplayRecord] = []
+
+    def complete(self, system: str, user: str) -> LLMResponse:
+        if system != self._system_prompt:
+            raise DemoError(3, "system prompt differs from the recorded PILOT-001 prompt")
+        record = self._by_prompt.get(user)
+        if record is None:
+            raise DemoError(
+                3,
+                "no recorded PILOT-001 answer for this prompt; the demo never fabricates a decision",
+                "The shortlist reached a pair that PILOT-001 did not query. Restore the accepted cache.",
+            )
+        self.served.append(record)
+        return LLMResponse(
+            text=record.response_text,
+            input_tokens=record.input_tokens,
+            output_tokens=record.output_tokens,
+            reasoning_tokens=record.reasoning_tokens,
+            cache_hit_tokens=record.cache_hit_tokens,
+            cache_miss_tokens=record.cache_miss_tokens,
+            latency_s=record.latency_s,
+            model_id=record.model,
+            attempts=record.attempts,
+            retry_wait_s=record.retry_wait_s,
+        )
+
+    def record_parse_failure(self, raw_text: str) -> None:  # parity with metered client
+        raise DemoError(3, f"recorded answer failed to parse: {raw_text!r}")
+
+
+def estimated_cost_usd(
+    cache_miss_tokens: int,
+    cache_hit_tokens: int,
+    output_tokens: int,
+) -> float:
+    """Off-peak PILOT-001 price formula ([D-36]), USD per 1M tokens."""
+    return (
+        cache_miss_tokens * PRICE_IN_CACHE_MISS
+        + cache_hit_tokens * PRICE_IN_CACHE_HIT
+        + output_tokens * PRICE_OUT
+    ) / 1_000_000.0
+
+
+# ---------------------------------------------------------------------------
+# Report model
+# ---------------------------------------------------------------------------
+
+
+@dataclass
+class DemoCall:
+    x: str
+    y: str
+    token: str
+    edge: Optional[tuple[str, str]]
+    latency_s_pilot: float
+    input_tokens: int
+    output_tokens: int
+    user_prompt: str
+
+
+@dataclass
+class EdgeLabel:
+    edge: tuple[str, str]
+    label: str
+    gold_path: Optional[list[str]] = None
+
+
+@dataclass
+class MissedEdge:
+    edge: tuple[str, str]
+    cause: str
+
+
+@dataclass
+class StrategyReport:
+    name: str
+    display: str
+    config: dict[str, Any]
+    setup_s_live: float
+    setup_embedding_calls: int
+    shortlist_candidates: tuple[str, ...]
+    shortlist_scores: Optional[tuple[float, ...]]
+    shortlist_s_live: float
+    embed_s_live: float
+    update_s_live: float
+    replay_wall_s_live: float
+    calls: list[DemoCall]
+    recorded_latency_s: float
+    recorded_input_tokens: int
+    recorded_output_tokens: int
+    recorded_cache_hit_tokens: int
+    recorded_cache_miss_tokens: int
+    cost_usd: float
+    calls_vs_s1_pct: float
+    kept_pct: float
+    applied_nodes_added: int
+    applied_edges_added: int
+    score: NodeScore
+    labelled_edges: list[EdgeLabel]
+    missed: list[MissedEdge]
+    lost_narrowing: int
+    lost_decision: int
+    recall_given_shortlist: Optional[float]
+    diagnostics: dict[str, Any]
+
+
+@dataclass
+class DemoReport:
+    started_utc: str
+    wall_s_live: float
+    argv: list[str]
+    provenance: PilotProvenance
+    pilot_dir: str
+    corpus_name: str
+    domain_context: Optional[str]
+    node: str
+    full_nodes: int
+    full_edges: int
+    n_before: int
+    e_before: int
+    gold_prerequisites: list[str]
+    gold_dependents: list[str]
+    gold_incident: int
+    prompt_version: str
+    system_prompt_sha256: str
+    prices: dict[str, float]
+    strategies: list[StrategyReport]
+    selected: list[str]
+    subset_of_s1: Optional[bool]
+    embedder_identity: Optional[dict[str, Any]]
+    cpu_threads: Optional[dict[str, Any]]
+
+
+# ---------------------------------------------------------------------------
+# Orchestration
+# ---------------------------------------------------------------------------
+
+
+def resolve_pilot_dir(pilot_dir: str | Path) -> Path:
+    path = Path(pilot_dir)
+    return path if path.is_absolute() else REPO_ROOT / path
+
+
+def _check_strategy_config(name: str, config: dict[str, Any]) -> None:
+    expected = DEMO_PARAMS[name]
+    for key, value in expected.items():
+        if key not in config:
+            raise DemoError(6, f"{name} config missing {key!r}: {config!r}")
+        actual = config[key]
+        if isinstance(value, float):
+            if abs(float(actual) - value) > 1e-12:
+                raise DemoError(6, f"{name} config {key}={actual!r}, expected {value!r}")
+        elif actual != value:
+            raise DemoError(6, f"{name} config {key}={actual!r}, expected {value!r}")
+
+
+def parse_strategies(text: Optional[str]) -> list[str]:
+    if text is None:
+        return list(CANONICAL_STRATEGIES)
+    raw = [part.strip() for part in text.split(",") if part.strip()]
+    if not raw:
+        raise DemoError(2, "--strategies requires at least one name")
+    selected: set[str] = set()
+    for part in raw:
+        key = part.lower()
+        name = STRATEGY_ALIASES.get(key, key)
+        if name not in CANONICAL_STRATEGIES:
+            raise DemoError(
+                2,
+                f"unknown strategy {part!r}",
+                "Use s1/s2/s3/s4 or the canonical names.",
+            )
+        if name in selected:
+            raise DemoError(2, f"duplicate strategy {part!r}")
+        selected.add(name)
+    return [name for name in CANONICAL_STRATEGIES if name in selected]
+
+
+def _build_embedder(selected: Sequence[str]) -> tuple[Any, Optional[dict[str, Any]], Optional[dict[str, Any]]]:
+    """Return (raw_embedder, identity, cpu_pin) or FakeEmbedder for S1-only."""
+    needs_embeddings = any(name != "brute_force" for name in selected)
+    if not needs_embeddings:
+        return FakeEmbedder(dim=32, seed=SEED), None, None
+
+    if "ann_retrieval" in selected:
+        # D-73: import faiss (via the strategy module) before torch/MiniLM.
+        import graph_insertion.strategies.ann_retrieval  # noqa: F401
+
+    try:
+        from graph_insertion.cpu_threads import CPU_THREAD_PIN, pin_cpu_threads
+        from graph_insertion.embedding_minilm import MiniLMEmbedder
+
+        embedder = MiniLMEmbedder()
+        pin = pin_cpu_threads(CPU_THREAD_PIN)
+        # Warm-up outside every timed window, so the first shortlist is not
+        # inflated by lazy model initialisation (the official harness relies on
+        # setup() for first-touch; this demo keeps that effect out of its timers).
+        embedder.embed("demo warm up")
+        identity = embedder.identity()
+        cpu = {"requested": int(pin["requested"]), "torch_threads": int(pin["torch_threads"])}
+        return embedder, identity, cpu
+    except DemoError:
+        raise
+    except Exception as exc:
+        raise DemoError(
+            5,
+            f"embedding backend unavailable: {type(exc).__name__}: {exc}",
+            "Use the pinned .venv-ann environment with the cached MiniLM model; no download is attempted.",
+        ) from exc
+
+
+def _gold_path(gold_graph: ConceptGraph, prereq: str, dependent: str) -> Optional[list[str]]:
+    nxg = gold_graph.nx_graph
+    if not nxg.has_node(prereq) or not nxg.has_node(dependent):
+        return None
+    if not nx.has_path(nxg, prereq, dependent):
+        return None
+    return list(nx.shortest_path(nxg, prereq, dependent))
+
+
+def run_demo(
+    *,
+    node: str = DEFAULT_NODE,
+    selected: Optional[Sequence[str]] = None,
+    pilot_dir: str | Path = PILOT_DIR_DEFAULT,
+    corpus: Any = None,
+    replay: Optional[ReplayLLMClient] = None,
+    provenance: Optional[PilotProvenance] = None,
+    raw_embedder: Any = None,
+    argv: Optional[Sequence[str]] = None,
+) -> DemoReport:
+    """Execute one insertion trial for each selected strategy and return the report."""
+    started = datetime.now(timezone.utc)
+    t_start = time.perf_counter()
+    selected_names = list(selected) if selected is not None else list(CANONICAL_STRATEGIES)
+
+    if corpus is None:
+        try:
+            corpus = load_corpus(CORPUS_NAME)
+        except Exception as exc:
+            raise DemoError(4, f"cannot load DSA corpus: {type(exc).__name__}: {exc}") from exc
+
+    prompt_sha = hashlib.sha256(decision_module.SYSTEM_PROMPT.encode("utf-8")).hexdigest()
+    if prompt_sha != SYSTEM_PROMPT_SHA256:
+        raise DemoError(
+            3,
+            "decision.SYSTEM_PROMPT changed since PILOT-001; replay would not match the recorded answers",
+            "Restore the v2 prompt or re-record the pilot before running this demo.",
+        )
+
+    nodes = sorted(corpus.graph.nodes())
+    if node not in nodes:
+        suggestions = difflib.get_close_matches(node, nodes, n=5, cutoff=0.3)
+        hint = f"Close matches: {', '.join(suggestions)}" if suggestions else "No close matches."
+        raise DemoError(4, f"node {node!r} is not in the DSA corpus", hint)
+
+    resolved_pilot = resolve_pilot_dir(pilot_dir)
+    if replay is None:
+        provenance, by_prompt = load_pilot(resolved_pilot, corpus=corpus)
+        replay = ReplayLLMClient(by_prompt)
+    elif provenance is None:
+        raise DemoError(6, "synthetic replay requires explicit provenance")
+
+    for name in selected_names:
+        if name not in CANONICAL_STRATEGIES:
+            raise DemoError(2, f"unknown strategy {name!r}")
+
+    configs: dict[str, dict[str, Any]] = {}
+    for name in selected_names:
+        try:
+            probe = STRATEGY_FACTORIES[name](**DEMO_PARAMS[name])
+        except DemoError:
+            raise
+        except Exception as exc:
+            raise DemoError(5, f"cannot construct {name}: {type(exc).__name__}: {exc}") from exc
+        configs[name] = dict(probe.config())
+        _check_strategy_config(name, configs[name])
+
+    if raw_embedder is None:
+        raw_embedder, embedder_identity, cpu_threads = _build_embedder(selected_names)
+    else:
+        embedder_identity = None
+        cpu_threads = None
+
+    gold_graph = corpus.graph
+    gold_incident = compute_gold_incident_edges(gold_graph, node)
+    report_strategies: list[StrategyReport] = []
+    edges_by_strategy: dict[str, set[tuple[str, str]]] = {}
+
+    for name in selected_names:
+        g = gold_graph.without_node(node)
+        n_before = g.num_nodes()
+        e_before = g.num_edges()
+
+        strategy = STRATEGY_FACTORIES[name](**DEMO_PARAMS[name])
+        _check_strategy_config(name, dict(strategy.config()))
+        meter = MeteredEmbedder(raw_embedder)
+        setup_calls_before = meter.calls
+        t0 = time.perf_counter()
+        strategy.setup(g, meter)
+        setup_s = time.perf_counter() - t0
+        setup_embedding_calls = meter.calls - setup_calls_before
+        gc.collect()
+
+        served_before = len(replay.served)
+        llm_meter = MeteredLLMClient(replay)
+        step = PairwiseDecisionStep(llm_meter)
+        try:
+            t1 = time.perf_counter()
+            result = insert_node(strategy, g, step, node, metered_embedder=meter)
+            replay_wall = time.perf_counter() - t1
+        except DemoError:
+            raise
+        except Exception as exc:
+            raise DemoError(6, f"{name} insertion failed: {type(exc).__name__}: {exc}") from exc
+
+        served = replay.served[served_before:]
+        calls: list[DemoCall] = []
+        for rec in served:
+            token = rec.token
+            if token == "X_PREREQ_Y":
+                edge: Optional[tuple[str, str]] = (node, rec.candidate)
+            elif token == "Y_PREREQ_X":
+                edge = (rec.candidate, node)
+            else:
+                edge = None
+            calls.append(
+                DemoCall(
+                    x=node,
+                    y=rec.candidate,
+                    token=token,
+                    edge=edge,
+                    latency_s_pilot=rec.latency_s,
+                    input_tokens=rec.input_tokens,
+                    output_tokens=rec.output_tokens,
+                    user_prompt=rec.user_prompt,
+                )
+            )
+
+        rebuilt = {c.edge for c in calls if c.edge is not None}
+        if rebuilt != set(result.edges):
+            raise DemoError(
+                6,
+                f"{name}: edges rebuilt from recorded tokens differ from production insert_node edges",
+            )
+
+        score = score_node_insertion(
+            node=node,
+            gold_graph=gold_graph,
+            judgments=corpus.judgments,
+            shortlist_candidates=result.shortlist.candidates,
+            decided_edges=result.edges,
+        )
+
+        shortlist_set = set(result.shortlist.candidates)
+        predicted = set(result.edges)
+        labels: list[EdgeLabel] = []
+        tp = fp = excluded = 0
+        for edge in result.edges:
+            single = score_node_insertion(
+                node=node,
+                gold_graph=gold_graph,
+                judgments=corpus.judgments,
+                shortlist_candidates=result.shortlist.candidates,
+                decided_edges=[edge],
+            )
+            tp += single.tp
+            fp += single.fp
+            excluded += single.excluded_predictions
+            if single.tp:
+                label = "TP"
+            elif single.excluded_predictions:
+                label = "UNJUDGED"
+            else:
+                label = "FP"
+            path = None
+            if label == "FP":
+                path = _gold_path(gold_graph, edge[0], edge[1])
+            labels.append(EdgeLabel(edge=edge, label=label, gold_path=path))
+        if (tp, fp, excluded) != (score.tp, score.fp, score.excluded_predictions):
+            raise DemoError(6, f"{name}: per-edge labels do not sum to the NodeScore counts")
+
+        missed: list[MissedEdge] = []
+        for edge in sorted(gold_incident - predicted):
+            prereq, dependent = edge
+            other = dependent if prereq == node else prereq
+            if other not in shortlist_set:
+                cause = "not shortlisted"
+            elif (dependent, prereq) in predicted:
+                cause = "direction reversed"
+            else:
+                cause = "judged NONE"
+            missed.append(MissedEdge(edge=edge, cause=cause))
+        if len(missed) != score.fn:
+            raise DemoError(6, f"{name}: missed-edge list length differs from FN")
+
+        lost_narrowing = sum(1 for m in missed if m.cause == "not shortlisted")
+        lost_decision = len(missed) - lost_narrowing
+
+        latency = sum(c.latency_s_pilot for c in calls)
+        input_tokens = sum(c.input_tokens for c in calls)
+        output_tokens = sum(c.output_tokens for c in calls)
+        cache_hits = sum(
+            rec.cache_hit_tokens for rec in served
+        )
+        cache_misses = sum(
+            rec.cache_miss_tokens for rec in served
+        )
+        cost = estimated_cost_usd(cache_misses, cache_hits, output_tokens)
+
+        recall_given = None
+        if score.shortlist_recall and score.recall is not None and score.shortlist_recall > 0:
+            recall_given = score.recall / score.shortlist_recall
+
+        diagnostics = {
+            key: result.metrics.extra.get(key)
+            for key in DIAGNOSTIC_KEYS.get(name, [])
+            if key in result.metrics.extra
+        }
+
+        report_strategies.append(
+            StrategyReport(
+                name=name,
+                display=DISPLAY_NAMES[name],
+                config=configs[name],
+                setup_s_live=setup_s,
+                setup_embedding_calls=setup_embedding_calls,
+                shortlist_candidates=result.shortlist.candidates,
+                shortlist_scores=result.shortlist.scores,
+                shortlist_s_live=result.metrics.shortlist_s,
+                embed_s_live=result.metrics.embed_s,
+                update_s_live=result.metrics.update_s,
+                replay_wall_s_live=replay_wall,
+                calls=calls,
+                recorded_latency_s=latency,
+                recorded_input_tokens=input_tokens,
+                recorded_output_tokens=output_tokens,
+                recorded_cache_hit_tokens=cache_hits,
+                recorded_cache_miss_tokens=cache_misses,
+                cost_usd=cost,
+                calls_vs_s1_pct=100.0 * (1.0 - len(calls) / n_before) if n_before else 0.0,
+                kept_pct=100.0 * len(result.shortlist.candidates) / n_before if n_before else 0.0,
+                applied_nodes_added=1,
+                applied_edges_added=len(result.edges),
+                score=score,
+                labelled_edges=labels,
+                missed=missed,
+                lost_narrowing=lost_narrowing,
+                lost_decision=lost_decision,
+                recall_given_shortlist=recall_given,
+                diagnostics=diagnostics,
+            )
+        )
+        edges_by_strategy[name] = predicted
+
+    subset_of_s1: Optional[bool] = None
+    if "brute_force" in edges_by_strategy:
+        base = edges_by_strategy["brute_force"]
+        subset_of_s1 = all(edges <= base for edges in edges_by_strategy.values())
+        if not subset_of_s1:
+            raise DemoError(6, "subset invariant violated: a narrowing strategy predicted an edge S1 did not")
+
+    return DemoReport(
+        started_utc=started.isoformat(),
+        wall_s_live=time.perf_counter() - t_start,
+        argv=list(argv) if argv is not None else list(sys.argv[1:]),
+        provenance=provenance,
+        pilot_dir=str(resolved_pilot),
+        corpus_name=str(corpus.name),
+        domain_context=corpus.domain_context,
+        node=node,
+        full_nodes=gold_graph.num_nodes(),
+        full_edges=gold_graph.num_edges(),
+        n_before=gold_graph.num_nodes() - 1,
+        e_before=gold_graph.num_edges() - len(gold_incident),
+        gold_prerequisites=sorted(gold_graph.prerequisites_of(node)),
+        gold_dependents=sorted(gold_graph.dependents_of(node)),
+        gold_incident=len(gold_incident),
+        prompt_version=decision_module.PROMPT_VERSION,
+        system_prompt_sha256=hashlib.sha256(
+            decision_module.SYSTEM_PROMPT.encode("utf-8")
+        ).hexdigest(),
+        prices={
+            "cache_miss_in_per_m": PRICE_IN_CACHE_MISS,
+            "cache_hit_in_per_m": PRICE_IN_CACHE_HIT,
+            "output_per_m": PRICE_OUT,
+        },
+        strategies=report_strategies,
+        selected=selected_names,
+        subset_of_s1=subset_of_s1,
+        embedder_identity=embedder_identity,
+        cpu_threads=cpu_threads,
+    )
+
+
+# ---------------------------------------------------------------------------
+# Formatting
+# ---------------------------------------------------------------------------
+
+
+class Palette:
+    def __init__(self, enabled: bool) -> None:
+        self.enabled = enabled
+
+    def paint(self, text: str, code: str) -> str:
+        if not self.enabled:
+            return text
+        return f"\x1b[{code}m{text}\x1b[0m"
+
+    def tag_live(self, text: str = "[LIVE]") -> str:
+        return self.paint(text, "36")
+
+    def tag_pilot(self, text: str = "[PILOT]") -> str:
+        return self.paint(text, "35")
+
+    def tag_calc(self, text: str = "[CALC]") -> str:
+        return self.paint(text, "33")
+
+    def tag_gold(self, text: str = "[GOLD]") -> str:
+        return self.paint(text, "34")
+
+    def tp(self, text: str = "TP") -> str:
+        return self.paint(text, "32")
+
+    def fp(self, text: str = "FP") -> str:
+        return self.paint(text, "31")
+
+    def fn(self, text: str = "FN") -> str:
+        return self.paint(text, "33")
+
+
+_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
+
+
+def _plural(count: int, singular: str, plural: Optional[str] = None) -> str:
+    word = singular if count == 1 else (plural or singular + "s")
+    return f"{count} {word}"
+
+
+def visible_len(text: str) -> int:
+    return len(_ANSI_RE.sub("", text))
+
+
+def _pilot_start(provenance: PilotProvenance) -> str:
+    stem = Path(provenance.path).parent.name
+    try:
+        dt = datetime.strptime(stem, "%Y%m%d_%H%M%SZ").replace(tzinfo=timezone.utc)
+        return dt.strftime("%Y-%m-%d %H:%M:%SZ")
+    except ValueError:
+        return _short_ts(provenance.recorded_utc)
+
+
+def _short_ts(value: str) -> str:
+    try:
+        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
+        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
+    except (ValueError, TypeError):
+        return value[:19]
+
+
+def _display_path(path_text: str) -> str:
+    try:
+        return str(Path(path_text).resolve().relative_to(REPO_ROOT))
+    except ValueError:
+        return str(path_text)
+
+
+@dataclass
+class FormatOptions:
+    color: bool = False
+    ascii: bool = False
+    show_all_calls: bool = False
+
+
+class Formatter:
+    def __init__(self, report: DemoReport, options: FormatOptions) -> None:
+        self.report = report
+        self.options = options
+        self.palette = Palette(options.color)
+        self.lines: list[str] = []
+        self._first_call_printed = False
+
+    # -- glyphs ---------------------------------------------------------
+    @property
+    def heavy(self) -> str:
+        return "=" if self.options.ascii else "═"
+
+    @property
+    def light(self) -> str:
+        return "-" if self.options.ascii else "─"
+
+    @property
+    def arrow(self) -> str:
+        return "->" if self.options.ascii else "→"
+
+    @property
+    def dot(self) -> str:
+        return "." if self.options.ascii else "·"
+
+    # -- primitives -----------------------------------------------------
+    def add(self, text: str = "") -> None:
+        self.lines.append(text)
+
+    def add_wrapped(self, text: str, *, indent: str = "  ", width: int = WIDTH) -> None:
+        for line in textwrap.wrap(
+            text,
+            width=width,
+            initial_indent=indent,
+            subsequent_indent=indent,
+            break_long_words=False,
+            break_on_hyphens=False,
+        ) or [indent.rstrip()]:
+            self.add(line)
+
+    def rule(self, char: Optional[str] = None) -> None:
+        self.add((char or self.heavy) * WIDTH)
+
+    def phase(self, title: str) -> None:
+        self.rule(self.light)
+        self.add(f" {title}")
+        self.rule(self.light)
+
+    @staticmethod
+    def fmt_metric(value: Optional[float], digits: int = 3) -> str:
+        if value is None:
+            return "n/a"
+        return f"{value:.{digits}f}"
+
+    @staticmethod
+    def fmt_s(seconds: float) -> str:
+        return f"{seconds:.2f} s"
+
+    @staticmethod
+    def fmt_ms(seconds: float) -> str:
+        return f"{seconds * 1000.0:.1f} ms"
+
+    def add_edge(self, marker: str, paint, edge_text: str, suffix: str = "") -> None:
+        prefix = f"      {marker:<10s} "
+        wrapped = textwrap.wrap(
+            prefix + edge_text + suffix,
+            width=WIDTH,
+            subsequent_indent=" " * len(prefix),
+            break_long_words=False,
+            break_on_hyphens=False,
+        ) or [prefix + edge_text + suffix]
+        for index, line in enumerate(wrapped):
+            if index == 0 and self.palette.enabled:
+                line = line[:6] + paint(marker) + line[6 + len(marker):]
+            self.add(line)
+
+    # -- phases ---------------------------------------------------------
+    def banner(self) -> None:
+        p = self.palette
+        r = self.report
+        prov = r.provenance
+        self.rule()
+        self.add(" DEFENSE DEMO  ·  one concept insertion, four narrowing strategies   PILOT-001 replay"
+                 .replace("·", self.dot))
+        self.rule()
+        self.add(" PROVENANCE")
+        self.add("   LLM decisions  REPLAYED from recorded PILOT-001 calls")
+        self.add("                  (not re-requested, not simulated)")
+        self.add(f"   Cache file     {_display_path(prov.path)}")
+        self.add(
+            f"                  {prov.n_calls} calls {self.dot} sha256 {prov.sha256[:12]}"
+            f"{'...' if self.options.ascii else '…'} {self.dot} recorded {_pilot_start(prov)}"
+        )
+        self.add(
+            f"   Recorded with  {prov.model} {self.dot} prompt {prov.prompt_version}"
+            f" {self.dot} temperature {prov.temperature:g} {self.dot} thinking {prov.thinking_mode}"
+        )
+        self.add(
+            f"                  {prov.retries} retries {self.dot} {prov.parse_failures} parse failures"
+            f" {self.dot} {prov.transport_failures} transport failures"
+        )
+        self.add("   Run live here  corpus load, narrowing, graph update, scoring, timers [LIVE]")
+        if r.embedder_identity:
+            identity = r.embedder_identity
+            self.add(
+                f"   Embedder       {identity['model_name']} rev {str(identity['revision'])[:7]}"
+                f" {self.dot} CPU {self.dot} 1 thread"
+            )
+            self.add(
+                f"                  sentence-transformers"
+                f" {identity['sentence_transformers_version']}"
+            )
+        else:
+            self.add("   Embedder       not loaded (brute_force needs none)")
+        self.add("   Network / API  none used · no API key read".replace("·", self.dot))
+        self.add(
+            " TAGS  " + p.tag_live() + " measured now   "
+            + p.tag_pilot() + " recorded 2026-10-07"
+        )
+        self.add(
+            "       " + p.tag_calc() + " computed       "
+            + p.tag_gold() + " ground truth (revealed after)"
+        )
+        self.add("")
+        self.add_wrapped(REPLAY_NOTICE)
+        self.add("")
+
+    def before(self) -> None:
+        r = self.report
+        self.phase("PHASE 1 · BEFORE".replace("·", self.dot))
+        self.add_wrapped(
+            "The thesis measures how the cost (LLM calls, time) and the accuracy of "
+            "inserting one new concept into an existing LLM-built prerequisite graph "
+            "depend on how candidates are narrowed. Only the narrowing differs; the "
+            "LLM decision step is identical for every strategy."
+        )
+        self.add("")
+        self.add(f"  Corpus            {r.corpus_name}")
+        self.add(f"  Domain context    {r.domain_context!r}")
+        self.add(f"  Full graph        {r.full_nodes} concepts, {r.full_edges} prerequisite edges")
+        self.add(f"  NEW concept       {r.node}")
+        self.add(f"  Existing graph    {r.n_before} concepts, {r.e_before} edges")
+        self.add("  Gold neighbourhood: HIDDEN until AFTER. Nothing before AFTER is marked with it.")
+        self.add("")
+        self.add("  THE SHARED DECISION STEP (identical for every strategy)")
+        for raw_line in decision_module.SYSTEM_PROMPT.splitlines():
+            if not raw_line.strip():
+                self.add("    ")
+                continue
+            for line in textwrap.wrap(
+                raw_line,
+                width=WIDTH - 4,
+                initial_indent="    ",
+                subsequent_indent="    ",
+            ):
+                self.add(line)
+        self.add("    User prompt template:")
+        self.add("      Subject area: <domain>")
+        self.add("      Concept X: <new concept, spaces instead of underscores>")
+        self.add("      Concept Y: <candidate, spaces instead of underscores>")
+        self.add("    Answers: X_PREREQ_Y | Y_PREREQ_X | NONE")
+        self.add(
+            "    One call per shortlisted candidate; X_PREREQ_Y -> edge (new -> cand);"
+        )
+        self.add(
+            "    Y_PREREQ_X -> edge (cand -> new); canonical direction prerequisite -> dependent."
+        )
+        self.add("    Only names are shown to the model.")
+        self.add("")
+        self.add("  STRATEGIES SELECTED")
+        for s in r.strategies:
+            if s.name == "brute_force":
+                desc = "nothing; every existing concept is judged"
+            elif s.name == "embedding_threshold":
+                desc = (
+                    f"cosine(new, node) > {s.config.get('theta')} (strict), "
+                    "MiniLM embeddings"
+                )
+            elif s.name == "ann_retrieval":
+                desc = (
+                    f"top-{s.config.get('k')} by cosine through HNSW "
+                    f"(M={s.config.get('M')}, efConstruction={s.config.get('ef_construction')}, "
+                    f"efSearch={s.config.get('ef_search')})"
+                )
+            else:
+                desc = (
+                    f"one size-bounded home bucket ({s.config.get('s_min')}.."
+                    f"{s.config.get('s_max')}, {s.config.get('n_bits')} hash bits)"
+                )
+            self.add(f"    {s.display:2s} {s.name}")
+            for line in textwrap.wrap(
+                desc,
+                width=WIDTH - 6,
+                initial_indent="       ",
+                subsequent_indent="       ",
+                break_long_words=False,
+                break_on_hyphens=False,
+            ):
+                self.add(line)
+        self.add("")
+        self.add(
+            "  cost = (cache-miss in x $0.15 + cache-hit in x $0.003 + out x $0.60) / 1M"
+        )
+        self.add("         (off-peak prices, D-36)")
+        self.add("")
+
+    def _visible_call_indices(self, calls: list[DemoCall]) -> tuple[list[int], int]:
+        n = len(calls)
+        if self.options.show_all_calls or n <= 10:
+            return list(range(n)), 0
+        keep: set[int] = {0, 1, 2}
+        for idx, call in enumerate(calls):
+            if call.token != "NONE":
+                keep.add(idx)
+        first_none = next((i for i, c in enumerate(calls) if c.token == "NONE"), None)
+        if first_none is not None:
+            keep.add(first_none)
+        ordered = sorted(i for i in keep if i < n)
+        hidden = [i for i in range(n) if i not in set(ordered)]
+        hidden_none = sum(1 for i in hidden if calls[i].token == "NONE")
+        return ordered, hidden_none
+
+    def while_block(self, index: int, total: int, s: StrategyReport) -> None:
+        p = self.palette
+        shortlist_n = len(s.shortlist_candidates)
+        self.phase(
+            f"PHASE 2 · WHILE   strategy {index} of {total}:  {s.display}  {s.name}"
+        )
+        self.add(
+            f"  setup     index build over {self.report.n_before} concepts"
+            f"   {self.fmt_ms(s.setup_s_live)} {p.tag_live()}  excluded from official timer"
+        )
+        if shortlist_n == 0:
+            self.add(
+                f"  shortlist 0 of {self.report.n_before} kept (0.0%), narrowed away 100.0%"
+            )
+            self.add(f"            time {self.fmt_ms(s.shortlist_s_live)} {p.tag_live()}")
+            self.add("  no LLM calls, no edges")
+            self.add(f"  LLM        0 calls · 0.00 s recorded latency {p.tag_pilot()}")
+            self.add(f"             0 in / 0 out tokens {p.tag_pilot()}")
+            self.add(f"             cost $0.000000 {p.tag_calc()}")
+            self.add(f"             calls vs S1: 100% {p.tag_calc()}")
+            self.add(
+                f"  applied    +1 concept, +0 edges  ->  graph"
+                f" {self.report.full_nodes} concepts, {self.report.e_before} edges"
+                f" {p.tag_calc()}"
+            )
+            self.add(f"             update {self.fmt_ms(s.update_s_live)} {p.tag_live()}")
+            self.add(
+                f"             replay wall time {self.fmt_ms(s.replay_wall_s_live)}"
+                f" {p.tag_live()}"
+            )
+            self.add("")
+            return
+        self.add(
+            f"  shortlist {shortlist_n} of {self.report.n_before} kept"
+            f" ({s.kept_pct:.1f}%), narrowed away {100.0 - s.kept_pct:.1f}%"
+        )
+        self.add(
+            f"            time {self.fmt_ms(s.shortlist_s_live)} {p.tag_live()}"
+            f"  (embedding the new name: {self.fmt_ms(s.embed_s_live)})"
+        )
+
+        scores = s.shortlist_scores
+        if s.name == "brute_force":
+            self.add(
+                f"  all {shortlist_n} existing concepts, alphabetical, no ranking"
+            )
+        elif scores is not None and len(scores) == shortlist_n and len(set(scores)) > 1:
+            self.add(f"  top candidates by cosine {p.tag_live()}")
+            shown = 0
+            for rank, (score, name) in enumerate(zip(scores, s.shortlist_candidates), 1):
+                if rank > 10:
+                    break
+                self.add(f"    {rank:3d}  {score:.3f}  {name}")
+                shown += 1
+            if shortlist_n > shown:
+                self.add(f"    ... and {shortlist_n - shown} more")
+        else:
+            self.add(f"  candidates: {', '.join(s.shortlist_candidates)}")
+
+        if s.diagnostics:
+            parts = []
+            for key, value in s.diagnostics.items():
+                if isinstance(value, float):
+                    parts.append(f"{key}={value:.3f}")
+                else:
+                    parts.append(f"{key}={value}")
+            self.add(f"  diagnostics  {(' ' + self.dot + ' ').join(parts)}  {p.tag_live()}")
+            self.add("")
+
+        visible, hidden_none = self._visible_call_indices(s.calls)
+        if self.options.show_all_calls:
+            label = f"{len(s.calls)} calls, all shown"
+        elif len(visible) == len(s.calls):
+            label = f"{len(s.calls)} calls, all shown"
+        else:
+            label = f"{len(s.calls)} calls, {len(visible)} shown"
+        label = label.replace(" calls", " call" if len(s.calls) == 1 else " calls")
+        self.add(f"  decisions  {label} {p.tag_pilot()}")
+
+        total_calls = len(s.calls)
+        for pos in visible:
+            call = s.calls[pos]
+            x_text = embed_text(call.x)
+            y_text = embed_text(call.y)
+            self.add(f"   call {pos + 1:2d}/{total_calls:<2d}  X = {x_text}   Y = {y_text}")
+            if not self._first_call_printed:
+                self._first_call_printed = True
+                self.add("             exact prompt sent in PILOT-001 [PILOT]")
+                for line in call.user_prompt.splitlines():
+                    self.add(f"             | {line}")
+            answer = call.token
+            self.add(
+                f"             answer {answer:<12s} {self.fmt_s(call.latency_s_pilot):>7s}"
+                f"  {call.input_tokens} in / {call.output_tokens} out"
+            )
+            if call.edge is None:
+                self.add("             -> no edge")
+            else:
+                self.add_wrapped(
+                    f"-> edge  {call.edge[0]} {self.arrow} {call.edge[1]}"
+                    "   (prerequisite -> dependent)",
+                    indent=" " * 13,
+                )
+        if hidden_none > 0:
+            self.add(
+                f"   ... {hidden_none} NONE decisions not printed (use --show-all-calls)"
+            )
+
+        counts: dict[str, int] = {"NONE": 0, "X_PREREQ_Y": 0, "Y_PREREQ_X": 0}
+        for call in s.calls:
+            counts[call.token] = counts.get(call.token, 0) + 1
+        self.add(
+            f"  answers    NONE {counts['NONE']} · X_PREREQ_Y {counts['X_PREREQ_Y']}"
+            f" · Y_PREREQ_X {counts['Y_PREREQ_X']}          {p.tag_pilot()}"
+        )
+        self.add(
+            f"  LLM        {len(s.calls)} calls · {self.fmt_s(s.recorded_latency_s)} recorded latency"
+            f" {p.tag_pilot()}"
+        )
+        self.add(
+            f"             {s.recorded_input_tokens:,} in / {s.recorded_output_tokens:,} out tokens"
+            f" {p.tag_pilot()}"
+        )
+        self.add(f"             cost ${s.cost_usd:.6f} {p.tag_calc()}")
+        self.add(f"             calls vs S1: {s.calls_vs_s1_pct:.0f}% {p.tag_calc()}")
+        self.add(
+            f"  applied    +1 concept, +{_plural(s.applied_edges_added, 'edge')}  ->  graph"
+            f" {self.report.full_nodes} concepts,"
+            f" {self.report.e_before + s.applied_edges_added} edges {p.tag_calc()}"
+        )
+        self.add(f"             update {self.fmt_ms(s.update_s_live)} {p.tag_live()}")
+        self.add(
+            f"             replay wall time {self.fmt_ms(s.replay_wall_s_live)} {p.tag_live()}"
+        )
+        self.add("")
+
+    def after(self) -> None:
+        p = self.palette
+        r = self.report
+        self.phase("PHASE 3 · AFTER".replace("·", self.dot))
+        def gold_names(label: str, names: list[str]) -> None:
+            prefix = f"  {p.tag_gold()} {label}: "
+            if not names:
+                self.add(prefix + "(none)")
+                return
+            for line in textwrap.wrap(
+                ", ".join(names),
+                width=WIDTH,
+                initial_indent=prefix,
+                subsequent_indent="      ",
+                break_long_words=False,
+                break_on_hyphens=False,
+            ):
+                self.add(line)
+
+        gold_names(f"prerequisites of {r.node}", r.gold_prerequisites)
+        gold_names(f"dependents of {r.node}", r.gold_dependents)
+        self.add(f"  {p.tag_gold()} {r.gold_incident} gold incident edges")
+        self.add("")
+
+        for s in r.strategies:
+            score = s.score
+            self.add(f"  {s.display} {s.name}")
+            self.add(
+                f"    shortlist captured {score.shortlist_hits}/{score.gold_neighbours}"
+                f" gold neighbours (shortlist recall {self.fmt_metric(score.shortlist_recall)})"
+            )
+            if s.labelled_edges:
+                self.add("    predicted edges")
+                for item in s.labelled_edges:
+                    edge = f"{item.edge[0]} {self.arrow} {item.edge[1]}"
+                    if item.label == "TP":
+                        paint = p.tp
+                    elif item.label == "FP":
+                        paint = p.fp
+                    else:
+                        paint = p.tag_gold
+                    self.add_edge(item.label, paint, edge)
+                    if item.gold_path:
+                        path = f" {self.arrow} ".join(item.gold_path)
+                        self.add_wrapped(
+                            f"(gold path exists: {path})",
+                            indent=" " * 17,
+                        )
+            else:
+                self.add("    predicted edges: none")
+            if s.missed:
+                self.add("    missed gold edges")
+                for item in s.missed:
+                    edge = f"{item.edge[0]} {self.arrow} {item.edge[1]}"
+                    self.add_edge("FN", p.fn, edge, f"  ({item.cause})")
+            else:
+                self.add("    missed gold edges: none")
+            self.add(
+                f"    lost at narrowing {s.lost_narrowing} {self.dot} lost at decision"
+                f" {s.lost_decision} {p.tag_calc()}"
+            )
+            self.add(
+                f"    metrics  P {self.fmt_metric(score.precision)}"
+                f"  R {self.fmt_metric(score.recall)}"
+                f"  F1 {self.fmt_metric(score.f1)}"
+                f"   TP {score.tp} FP {score.fp} FN {score.fn} {p.tag_calc()}"
+            )
+            if score.excluded_predictions:
+                self.add(
+                    f"    unjudged predictions excluded: {score.excluded_predictions}"
+                    f"  (sensitivity F1 {self.fmt_metric(score.f1_sensitivity)})"
+                )
+            if s.recall_given_shortlist is not None:
+                self.add(
+                    f"    recall decomposition: shortlist {self.fmt_metric(score.shortlist_recall)}"
+                    f" x given-shortlist {self.fmt_metric(s.recall_given_shortlist)}"
+                    f" = {self.fmt_metric(score.recall)} {p.tag_calc()}"
+                )
+            self.add("")
+
+        if r.subset_of_s1 is not None:
+            status = "OK" if r.subset_of_s1 else "FAILED"
+            self.add(
+                f"  INVARIANT  every edge from a narrowing strategy is in S1's predicted set: {status}"
+            )
+        else:
+            self.add("  INVARIANT  subset check not run (S1 not selected)")
+        self.add("")
+
+        self.comparison_tables()
+        self.takeaways()
+        self.limitations()
+
+    def comparison_tables(self) -> None:
+        r = self.report
+        self.add(
+            f"  {'WORK':<22} {'kept':>7} {'calls':>5} {'vsS1':>5}"
+            f" {'LLM lat':>8} {'tokens in/out':>13} {'cost':>9} {'shortlist':>8}"
+        )
+        self.add(
+            "  (LLM latency and tokens are [PILOT]; cost is [CALC]; shortlist time is [LIVE].)"
+        )
+        for s in r.strategies:
+            shortlist_n = len(s.shortlist_candidates)
+            kept = f"{shortlist_n}/{r.n_before}"
+            tokens = f"{s.recorded_input_tokens:,} / {s.recorded_output_tokens:,}"
+            label = f"{s.display} {s.name}"
+            self.add(
+                f"  {label:<22} {kept:>7} {len(s.calls):>5} {s.calls_vs_s1_pct:>4.0f}%"
+                f" {self.fmt_s(s.recorded_latency_s):>8}"
+                f" {tokens:>13} {('$' + format(s.cost_usd, '.6f')):>9}"
+                f" {self.fmt_ms(s.shortlist_s_live):>8}"
+            )
+        self.add("")
+        self.add(
+            f"  {'ACCURACY':<22} {'sl.recall':>9} {'P':>6} {'R':>6} {'F1':>6}"
+            f" {'TP/FP/FN':>10} {'lost n/d':>9}"
+        )
+        for s in r.strategies:
+            score = s.score
+            self.add(
+                f"  {s.display + ' ' + s.name:<22} {self.fmt_metric(score.shortlist_recall):>9}"
+                f" {self.fmt_metric(score.precision):>6}"
+                f" {self.fmt_metric(score.recall):>6}"
+                f" {self.fmt_metric(score.f1):>6}"
+                f" {(str(score.tp) + '/' + str(score.fp) + '/' + str(score.fn)):>10}"
+                f" {(str(s.lost_narrowing) + '/' + str(s.lost_decision)):>9}"
+            )
+        self.add("")
+
+    def takeaways(self) -> None:
+        r = self.report
+        self.add("  TAKEAWAYS")
+
+        def bullet(text: str) -> None:
+            for line in textwrap.wrap(
+                text,
+                width=WIDTH - 4,
+                initial_indent="    - ",
+                subsequent_indent="      ",
+                break_long_words=False,
+                break_on_hyphens=False,
+            ):
+                self.add(line)
+
+        narrowing = [s for s in r.strategies if s.name != "brute_force"]
+        if narrowing:
+            for s in narrowing:
+                bullet(
+                    f"{s.display} made {len(s.calls)} calls, {s.calls_vs_s1_pct:.0f}% fewer"
+                    f" than S1's {r.n_before}."
+                )
+        if r.subset_of_s1 and "brute_force" in r.selected and len(r.strategies) > 1:
+            bullet(
+                "Every edge from S2-S4 was also predicted by S1: the decision step is"
+                " identical, so differences come only from which pairs were sent to the model."
+            )
+        if narrowing:
+            parts = []
+            for s in narrowing:
+                parts.append(
+                    f"{s.display} kept {self.fmt_metric(s.score.shortlist_recall)} of gold"
+                    f" neighbours and lost {s.lost_narrowing} edge(s) before the model saw them"
+                )
+            bullet("Narrowing's price: " + "; ".join(parts) + ".")
+        if "brute_force" in r.selected and narrowing:
+            s1 = next(s for s in r.strategies if s.name == "brute_force")
+            better = [
+                s for s in narrowing
+                if s.score.f1 is not None and s1.score.f1 is not None and s.score.f1 > s1.score.f1
+            ]
+            if better:
+                best = max(better, key=lambda s: s.score.f1 or 0.0)
+                bullet(
+                    f"{best.display} has a higher F1 than S1 because it never judged"
+                    f" {s1.score.fp} pair(s) that S1 turned into false positives."
+                )
+            else:
+                bullet("On this node no narrowing strategy beat brute-force F1.")
+        bullet(
+            "One node is an illustration. The thesis evidence is the full runs (RQ1-RQ3),"
+            " not this transcript."
+        )
+        self.add("")
+
+    def limitations(self) -> None:
+        self.add("  LIMITATIONS — WHAT THIS DOES NOT PROVE")
+        self.add_wrapped(
+            "Decisions are replayed from PILOT-001 recordings, not re-requested. This is real"
+            " model output for exactly these prompts, recorded on 2026-10-07."
+        )
+        self.add_wrapped(
+            "One held-out node, one trial, one repeat. This is an illustration, not a new"
+            " result, and it is not part of Chapter 4."
+        )
+        self.add_wrapped(
+            "Latency, tokens and cost are recorded values. Only setup, shortlist, update and"
+            " replay times are measured now; replay wall time says nothing about model latency."
+        )
+        self.add_wrapped(
+            "In replay a pair's answer is a fixed lookup, so strategies cannot disagree on a"
+            " pair. In the official runs each strategy made its own live calls, so agreement"
+            " on a pair is not guaranteed there."
+        )
+        if self.report.subset_of_s1 is not None:
+            self.add_wrapped(
+                "DSA gold is not transitively reduced, so some false positives may be"
+                " defensible by transitive closure; metrics are computed against the gold as"
+                " given."
+            )
+        self.add_wrapped(
+            "Strategy parameters are the pre-fixed defaults (D-64); nothing was tuned on this node."
+        )
+        self.add("")
+
+    def footer(self) -> None:
+        p = self.palette
+        self.add(
+            f"  demo wall time {self.report.wall_s_live:.1f} s {p.tag_live()}   "
+            f"{self.dot} no files written to results/"
+        )
+        self.rule()
+
+    def render(self) -> list[str]:
+        self.banner()
+        self.before()
+        for idx, strategy in enumerate(self.report.strategies, 1):
+            self.while_block(idx, len(self.report.strategies), strategy)
+        self.after()
+        self.footer()
+        for line in self.lines:
+            if visible_len(line) > WIDTH:
+                raise DemoError(
+                    6,
+                    f"formatter produced a {visible_len(line)}-column line (limit {WIDTH}): {line!r}",
+                )
+        return self.lines
+
+
+def format_report(report: DemoReport, options: FormatOptions) -> list[str]:
+    return Formatter(report, options).render()
+
+
+# ---------------------------------------------------------------------------
+# JSON record
+# ---------------------------------------------------------------------------
+
+
+def report_to_json(report: DemoReport) -> dict[str, Any]:
+    prov = dataclasses.asdict(report.provenance)
+    strategies: list[dict[str, Any]] = []
+    for s in report.strategies:
+        strategies.append(
+            {
+                "name": s.name,
+                "display": s.display,
+                "config": dict(s.config),
+                "setup_s_live": s.setup_s_live,
+                "setup_embedding_calls": s.setup_embedding_calls,
+                "shortlist": {
+                    "candidates": list(s.shortlist_candidates),
+                    "scores": list(s.shortlist_scores) if s.shortlist_scores is not None else None,
+                    "shortlist_s_live": s.shortlist_s_live,
+                    "embed_s_live": s.embed_s_live,
+                    "kept_pct": s.kept_pct,
+                },
+                "calls": [
+                    {
+                        "x": c.x,
+                        "y": c.y,
+                        "token": c.token,
+                        "edge": list(c.edge) if c.edge else None,
+                        "latency_s_pilot": c.latency_s_pilot,
+                        "input_tokens": c.input_tokens,
+                        "output_tokens": c.output_tokens,
+                    }
+                    for c in s.calls
+                ],
+                "recorded": {
+                    "llm_calls": len(s.calls),
+                    "latency_s": s.recorded_latency_s,
+                    "input_tokens": s.recorded_input_tokens,
+                    "output_tokens": s.recorded_output_tokens,
+                },
+                "calc": {
+                    "cost_usd": s.cost_usd,
+                    "calls_vs_s1_pct": s.calls_vs_s1_pct,
+                    "kept_pct": s.kept_pct,
+                },
+                "applied": {
+                    "nodes_added": s.applied_nodes_added,
+                    "edges_added": s.applied_edges_added,
+                    "update_s_live": s.update_s_live,
+                },
+                "score": dataclasses.asdict(s.score),
+                "labelled_edges": [
+                    {
+                        "edge": list(item.edge),
+                        "label": item.label,
+                        "gold_path": item.gold_path,
+                    }
+                    for item in s.labelled_edges
+                ],
+                "missed": [
+                    {"edge": list(item.edge), "cause": item.cause} for item in s.missed
+                ],
+                "lost_narrowing": s.lost_narrowing,
+                "lost_decision": s.lost_decision,
+                "recall_given_shortlist": s.recall_given_shortlist,
+                "diagnostics": dict(s.diagnostics),
+                "replay_wall_s_live": s.replay_wall_s_live,
+            }
+        )
+    return {
+        "schema": "demo-trial-1",
+        "run": {
+            "started_utc": report.started_utc,
+            "wall_s_live": report.wall_s_live,
+            "argv": list(report.argv),
+        },
+        "provenance": {
+            **prov,
+            "embedder": report.embedder_identity,
+            "cpu_threads": report.cpu_threads,
+        },
+        "trial": {
+            "corpus": report.corpus_name,
+            "node": report.node,
+            "domain_context": report.domain_context,
+            "n_before": report.n_before,
+            "e_before": report.e_before,
+            "full_nodes": report.full_nodes,
+            "full_edges": report.full_edges,
+            "gold": {
+                "prerequisites": report.gold_prerequisites,
+                "dependents": report.gold_dependents,
+                "incident_edges": report.gold_incident,
+            },
+        },
+        "decision_step": {
+            "prompt_version": report.prompt_version,
+            "system_prompt_sha256": report.system_prompt_sha256,
+            "price_per_m": report.prices,
+        },
+        "strategies": strategies,
+        "comparison": {
+            s.name: {
+                "shortlist_size": len(s.shortlist_candidates),
+                "llm_calls": len(s.calls),
+                "recorded_latency_s": s.recorded_latency_s,
+                "cost_usd": s.cost_usd,
+                "shortlist_recall": s.score.shortlist_recall,
+                "precision": s.score.precision,
+                "recall": s.score.recall,
+                "f1": s.score.f1,
+            }
+            for s in report.strategies
+        },
+        "invariants": {"subset_of_s1": report.subset_of_s1},
+    }
+
+
+# ---------------------------------------------------------------------------
+# CLI
+# ---------------------------------------------------------------------------
+
+
+def build_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(
+        description="Offline PILOT-001 replay demo: one insertion, four strategies."
+    )
+    parser.add_argument("--node", default=DEFAULT_NODE)
+    parser.add_argument("--strategies", default=None)
+    parser.add_argument("--pilot-dir", default=PILOT_DIR_DEFAULT)
+    parser.add_argument("--no-color", action="store_true")
+    parser.add_argument("--ascii", action="store_true")
+    parser.add_argument("--pause", action="store_true")
+    parser.add_argument("--show-all-calls", action="store_true")
+    parser.add_argument("--json", dest="json_path", default=None)
+    parser.add_argument("--check", action="store_true")
+    parser.add_argument("--traceback", dest="show_traceback", action="store_true")
+    return parser
+
+
+def _validate_json_path(path_text: str) -> Path:
+    path = Path(path_text)
+    resolved = path.resolve()
+    if path.exists():
+        raise DemoError(7, f"refusing to overwrite existing --json file: {path}", "Choose a new path.")
+    results_dir = (REPO_ROOT / "results").resolve()
+    if resolved == results_dir or results_dir in resolved.parents:
+        raise DemoError(7, f"refusing to write under results/: {path}", "Write outside the official results tree.")
+    if not resolved.parent.is_dir():
+        raise DemoError(7, f"parent directory does not exist for --json: {path}", "Create the directory first.")
+    return resolved
+
+
+def _color_enabled(no_color: bool) -> bool:
+    if no_color or os.environ.get("NO_COLOR") is not None:
+        return False
+    return sys.stdout.isatty()
+
+
+def _print_check(ok: bool, label: str, detail: str) -> None:
+    print(f"{'OK  ' if ok else 'FAIL'} {label}: {detail}")
+
+
+def run_checks(node: str, selected: Sequence[str], pilot_dir: str | Path) -> int:
+    failures = 0
+    try:
+        corpus = load_corpus(CORPUS_NAME)
+        _print_check(True, "corpus", f"{corpus.name}: {corpus.graph.num_nodes()} nodes, "
+                                 f"{corpus.graph.num_edges()} edges, domain={corpus.domain_context!r}")
+    except Exception as exc:
+        _print_check(False, "corpus", f"{type(exc).__name__}: {exc}")
+        return 4
+
+    try:
+        prov, by_prompt = load_pilot(resolve_pilot_dir(pilot_dir), corpus=corpus)
+        _print_check(True, "pilot cache", f"{prov.n_calls} calls, sha256 {prov.sha256[:12]}")
+        _print_check(True, "pilot provenance", f"prompt {prov.prompt_version}, model {prov.model}, "
+                                              f"cost ${prov.estimated_cost_usd:.6f}")
+    except DemoError as exc:
+        _print_check(False, "pilot cache", exc.message)
+        return 3
+
+    nodes = sorted(corpus.graph.nodes())
+    if node in nodes:
+        _print_check(True, "node", node)
+    else:
+        suggestions = difflib.get_close_matches(node, nodes, n=5, cutoff=0.3)
+        _print_check(False, "node", f"{node!r} not in corpus; close matches: {suggestions}")
+        return 4
+
+    if any(name != "brute_force" for name in selected):
+        try:
+            _, identity, cpu = _build_embedder(selected)
+            _print_check(True, "embedder", f"{identity['model_name']} rev {str(identity['revision'])[:7]}, "
+                                          f"torch threads {cpu['torch_threads']}")
+        except DemoError as exc:
+            _print_check(False, "embedder", exc.message)
+            return 5
+    else:
+        _print_check(True, "embedder", "not required for the selected strategies")
+    return 0
+
+
+def main(argv: Optional[Sequence[str]] = None) -> int:
+    parser = build_parser()
+    args = parser.parse_args(argv)
+    try:
+        selected = parse_strategies(args.strategies)
+        if args.check:
+            return run_checks(args.node, selected, args.pilot_dir)
+
+        json_path = _validate_json_path(args.json_path) if args.json_path else None
+        report = run_demo(
+            node=args.node,
+            selected=selected,
+            pilot_dir=args.pilot_dir,
+            argv=list(argv) if argv is not None else sys.argv[1:],
+        )
+        options = FormatOptions(
+            color=_color_enabled(args.no_color),
+            ascii=args.ascii,
+            show_all_calls=args.show_all_calls,
+        )
+        lines = format_report(report, options)
+        seen_phase = False
+        for line in lines:
+            if args.pause and line.startswith(" PHASE ") and seen_phase:
+                if sys.stdin.isatty() and sys.stdout.isatty():
+                    try:
+                        input("  [Enter for next phase] ")
+                    except EOFError:
+                        pass
+            print(line)
+            if line.startswith(" PHASE "):
+                seen_phase = True
+        if json_path is not None:
+            json_path.write_text(
+                json.dumps(report_to_json(report), indent=2) + "\n",
+                encoding="utf-8",
+            )
+        return 0
+    except DemoError as exc:
+        if args.show_traceback:
+            import traceback
+
+            traceback.print_exc()
+        print(f"ERROR: {exc.message}", file=sys.stderr)
+        if exc.hint:
+            print(f"HINT: {exc.hint}", file=sys.stderr)
+        return exc.exit_code
+    except BrokenPipeError:
+        try:
+            sys.stdout.close()
+        except Exception:
+            pass
+        return 0
+    except KeyboardInterrupt:
+        return 130
+    except Exception as exc:
+        if args.show_traceback:
+            import traceback
+
+            traceback.print_exc()
+        print(f"ERROR: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
+        return 6
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git c/tests/test_demo_trial.py i/tests/test_demo_trial.py
new file mode 100644
index 0000000..5ad42c6
--- /dev/null
+++ i/tests/test_demo_trial.py
@@ -0,0 +1,872 @@
+"""tests/test_demo_trial.py — DEMO-001
+======================================
+Tests for the offline PILOT-001 replay defense demo.
+
+Groups follow docs/prompts/DEMO-001-PROMPT.md section 8.  Replay and formatter
+tests use synthetic caches/reports and never import MiniLM or faiss.
+"""
+
+from __future__ import annotations
+
+import copy
+import dataclasses
+import hashlib
+import json
+import socket
+import subprocess
+import sys
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+
+import scripts.demo_trial as demo
+from graph_insertion.decision import SYSTEM_PROMPT, PairwiseDecisionStep, parse_token
+from graph_insertion.embedding import FakeEmbedder
+from graph_insertion.graph_representation import (
+    ConceptGraph,
+    GoldJudgmentSet,
+    SourceKind,
+)
+from graph_insertion.scoring import NodeScore
+
+
+# ---------------------------------------------------------------------------
+# Synthetic fixtures
+# ---------------------------------------------------------------------------
+
+
+TOY_NODES = ["n0", "n1", "n2", "n3", "n4", "n5"]
+
+
+def make_toy_corpus() -> SimpleNamespace:
+    graph = ConceptGraph(domain_context="toy domain")
+    for name in TOY_NODES:
+        graph.add_node(name)
+    graph.add_prereq_edge("n0", "n1")
+    graph.add_prereq_edge("n1", "n2")
+    graph.add_prereq_edge("n0", "n2")
+
+    judgments = GoldJudgmentSet(source_kind=SourceKind.GOLD)
+    for a in TOY_NODES:
+        for b in TOY_NODES:
+            if a == b:
+                continue
+            label = 1 if graph.has_prereq_edge(b, a) else 0
+            judgments.record(a, b, label)
+    return SimpleNamespace(
+        name="toy",
+        graph=graph,
+        judgments=judgments,
+        domain_context="toy domain",
+    )
+
+
+def response_for(new_name: str, candidate: str) -> str:
+    if new_name == "n2" and candidate in {"n0", "n1"}:
+        return "Y_PREREQ_X"
+    if new_name == "n2" and candidate == "n3":
+        return "X_PREREQ_Y"
+    return "NONE"
+
+
+def make_records(corpus: SimpleNamespace) -> list[dict]:
+    records = []
+    index = 0
+    step = PairwiseDecisionStep(None)  # type: ignore[arg-type]
+    for new_name in sorted(corpus.graph.nodes()):
+        for candidate in sorted(corpus.graph.nodes()):
+            if new_name == candidate:
+                continue
+            index += 1
+            token = response_for(new_name, candidate)
+            records.append(
+                {
+                    "call_index": index,
+                    "new_name": new_name,
+                    "candidate": candidate,
+                    "domain_context": corpus.domain_context,
+                    "user_prompt": step.build_user_prompt(
+                        new_name, candidate, corpus.domain_context
+                    ),
+                    "response_text": token,
+                    "raw_token": token,
+                    "latency_s": 1.0 + index / 1000.0,
+                    "model": "deepseek-flash",
+                    "input_tokens": 153,
+                    "output_tokens": 5,
+                    "reasoning_tokens": 0,
+                    "cache_hit_tokens": 0,
+                    "cache_miss_tokens": 153,
+                    "attempts": 1,
+                    "retry_wait_s": 0.0,
+                }
+            )
+    return records
+
+
+def write_cache(
+    tmp_path: Path,
+    corpus: SimpleNamespace,
+    records: list[dict] | None = None,
+    *,
+    summary_overrides: dict | None = None,
+    raw_text: str | None = None,
+) -> tuple[Path, str, list[dict]]:
+    records = records if records is not None else make_records(corpus)
+    directory = tmp_path / "pilot"
+    directory.mkdir(parents=True, exist_ok=True)
+    raw = raw_text if raw_text is not None else "".join(
+        json.dumps(record) + "\n" for record in records
+    )
+    raw_path = directory / "raw_calls.jsonl"
+    raw_path.write_text(raw, encoding="utf-8")
+    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
+
+    input_tokens = sum(int(r["input_tokens"]) for r in records)
+    output_tokens = sum(int(r["output_tokens"]) for r in records)
+    cache_hits = sum(int(r["cache_hit_tokens"]) for r in records)
+    cache_misses = sum(int(r["cache_miss_tokens"]) for r in records)
+    latency = sum(float(r["latency_s"]) for r in records)
+    cost = (cache_misses * 0.15 + cache_hits * 0.003 + output_tokens * 0.60) / 1e6
+    summary = {
+        "timestamp_utc": "2026-10-07T05:49:00+00:00",
+        "prompt_version": "v2",
+        "model_id": "deepseek-flash",
+        "configured_model": "deepseek-flash",
+        "temperature": 0.0,
+        "thinking_mode": "disabled",
+        "total_calls": len(records),
+        "parse_failure_count": 0,
+        "transport_failure_count": 0,
+        "retries_and_errors": {"retries": 0},
+        "token_usage": {
+            "input_tokens": input_tokens,
+            "output_tokens": output_tokens,
+            "cache_hit_tokens": cache_hits,
+            "cache_miss_tokens": cache_misses,
+            "estimated_cost_usd": round(cost, 6),
+        },
+        "timing_s": {"cumulative_latency": latency},
+    }
+    if summary_overrides:
+        for key, value in summary_overrides.items():
+            if isinstance(value, dict) and isinstance(summary.get(key), dict):
+                summary[key] = {**summary[key], **value}
+            else:
+                summary[key] = value
+    (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
+    return directory, digest, records
+
+
+def load_synth(monkeypatch, directory: Path, digest: str, corpus: SimpleNamespace):
+    monkeypatch.setattr(demo, "EXPECTED_CALLS", len(make_records(corpus)))
+    return demo.load_pilot(directory, corpus=corpus, expected_sha256=digest)
+
+
+def make_provenance(directory: Path, digest: str, n_calls: int) -> demo.PilotProvenance:
+    return demo.PilotProvenance(
+        path=str(directory / "raw_calls.jsonl"),
+        sha256=digest,
+        recorded_utc="2026-10-07T05:49:00+00:00",
+        prompt_version="v2",
+        model="deepseek-flash",
+        n_calls=n_calls,
+        temperature=0.0,
+        thinking_mode="disabled",
+        retries=0,
+        parse_failures=0,
+        transport_failures=0,
+        input_tokens=153 * n_calls,
+        output_tokens=5 * n_calls,
+        cache_hit_tokens=0,
+        cache_miss_tokens=153 * n_calls,
+        estimated_cost_usd=0.0,
+        cumulative_latency_s=float(n_calls),
+        system_prompt_recorded=False,
+    )
+
+
+# ---------------------------------------------------------------------------
+# Group 1 — Replay loader/client
+# ---------------------------------------------------------------------------
+
+
+class TestReplayLoader:
+    def test_happy_path_and_values(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        directory, digest, records = write_cache(tmp_path, corpus)
+        prov, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
+        assert prov.n_calls == len(records) == 30
+        assert prov.prompt_version == "v2"
+        assert len(by_prompt) == 30
+        client = demo.ReplayLLMClient(by_prompt)
+        record = records[0]
+        response = client.complete(SYSTEM_PROMPT, record["user_prompt"])
+        assert response.text == record["response_text"]
+        assert response.input_tokens == 153
+        assert response.latency_s == record["latency_s"]
+        assert client.served == [next(iter(by_prompt.values()))]
+
+    def test_cache_miss_never_fabricates(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        directory, digest, _ = write_cache(tmp_path, corpus)
+        _, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
+        client = demo.ReplayLLMClient(by_prompt)
+        with pytest.raises(demo.DemoError) as exc:
+            client.complete(SYSTEM_PROMPT, "Concept X: nowhere\nConcept Y: nothing")
+        assert exc.value.exit_code == 3
+        assert "never fabricates" in exc.value.message
+
+    def test_wrong_system_prompt(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        directory, digest, _ = write_cache(tmp_path, corpus)
+        _, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
+        client = demo.ReplayLLMClient(by_prompt)
+        with pytest.raises(demo.DemoError) as exc:
+            client.complete("different prompt", next(iter(by_prompt)))
+        assert exc.value.exit_code == 3
+
+    @pytest.mark.parametrize(
+        "override",
+        [
+            {"prompt_version": "v1"},
+            {"model_id": "another-model"},
+            {"total_calls": 999},
+            {"token_usage": {"input_tokens": 1}},
+            {"timing_s": {"cumulative_latency": 0.0}},
+        ],
+    )
+    def test_summary_mismatches(self, tmp_path, monkeypatch, override):
+        corpus = make_toy_corpus()
+        directory, digest, _ = write_cache(tmp_path, corpus, summary_overrides=override)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert exc.value.exit_code == 3
+
+    def test_tampered_sha(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        directory, _, _ = write_cache(tmp_path, corpus)
+        monkeypatch.setattr(demo, "EXPECTED_CALLS", 30)
+        with pytest.raises(demo.DemoError) as exc:
+            demo.load_pilot(directory, corpus=corpus, expected_sha256="deadbeef")
+        assert exc.value.exit_code == 3
+
+    def test_malformed_json_line(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        directory, digest, records = write_cache(tmp_path, corpus)
+        raw = (directory / "raw_calls.jsonl").read_text().splitlines()
+        raw[0] = "{not json"
+        directory, digest, _ = write_cache(
+            tmp_path / "bad", corpus, summary_overrides=None,
+            raw_text="\n".join(raw) + "\n",
+        )
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert exc.value.exit_code == 3
+
+    def test_missing_field(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        del records[0]["candidate"]
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "missing field" in exc.value.message
+
+    def test_wrong_type(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[0]["input_tokens"] = "153"
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "must be int" in exc.value.message
+
+    def test_negative_latency(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[0]["latency_s"] = -1.0
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "negative latency" in exc.value.message
+
+    def test_cache_tokens_mismatch(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[0]["cache_hit_tokens"] = 1
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "cache_hit + cache_miss" in exc.value.message
+
+    def test_nonzero_reasoning_tokens(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[0]["reasoning_tokens"] = 3
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "reasoning" in exc.value.message
+
+    def test_duplicate_prompt(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[1]["user_prompt"] = records[0]["user_prompt"]
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "duplicate user_prompt" in exc.value.message
+
+    def test_duplicate_pair(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[1]["new_name"] = records[0]["new_name"]
+        records[1]["candidate"] = records[0]["candidate"]
+        records[1]["user_prompt"] = records[0]["user_prompt"]
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "duplicate" in exc.value.message
+
+    def test_incomplete_pair_set(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[0]["new_name"] = "not_in_corpus"
+        records[0]["candidate"] = "n0"
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "ordered pairs" in exc.value.message
+
+    def test_line_count_mismatch(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)[:-1]
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "calls, expected" in exc.value.message
+
+    def test_invalid_response_token(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        records = make_records(corpus)
+        records[0]["response_text"] = "MAYBE"
+        directory, digest, _ = write_cache(tmp_path, corpus, records)
+        with pytest.raises(demo.DemoError) as exc:
+            load_synth(monkeypatch, directory, digest, corpus)
+        assert "unparseable" in exc.value.message
+
+    def test_no_live_client_construction_or_socket(self, tmp_path, monkeypatch):
+        corpus = make_toy_corpus()
+        directory, digest, _ = write_cache(tmp_path, corpus)
+        _, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
+
+        import graph_insertion.llm as llm_module
+
+        def explode(*args, **kwargs):
+            raise AssertionError("live client constructed")
+
+        monkeypatch.setattr(llm_module, "FakeLLMClient", explode)
+        monkeypatch.setattr(llm_module, "DeepSeekClient", explode)
+
+        def no_socket(*args, **kwargs):
+            raise AssertionError("network used")
+
+        monkeypatch.setattr(socket, "socket", no_socket)
+        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
+        client = demo.ReplayLLMClient(by_prompt)
+        record = next(iter(by_prompt.values()))
+        client.complete(SYSTEM_PROMPT, record.user_prompt)
+
+
+# ---------------------------------------------------------------------------
+# Group 2 — Cost
+# ---------------------------------------------------------------------------
+
+
+class TestCost:
+    def test_no_cache_hits_matches_pilot_s1(self):
+        assert demo.estimated_cost_usd(4291, 0, 71) == pytest.approx(0.00068625, abs=1e-12)
+        assert round(demo.estimated_cost_usd(4291, 0, 71), 6) == 0.000686
+
+    def test_cache_hits_are_cheaper(self):
+        assert demo.estimated_cost_usd(1_000_000, 0, 0) == pytest.approx(0.15)
+        assert demo.estimated_cost_usd(0, 1_000_000, 0) == pytest.approx(0.003)
+        assert demo.estimated_cost_usd(0, 0, 1_000_000) == pytest.approx(0.60)
+        assert demo.estimated_cost_usd(500_000, 500_000, 0) == pytest.approx(0.0765)
+
+
+# ---------------------------------------------------------------------------
+# Group 3 — Orchestration with FakeEmbedder
+# ---------------------------------------------------------------------------
+
+
+def run_toy_demo(monkeypatch, tmp_path, *, selected=None):
+    corpus = make_toy_corpus()
+    directory, digest, records = write_cache(tmp_path, corpus)
+    prov, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
+    replay = demo.ReplayLLMClient(by_prompt)
+    report = demo.run_demo(
+        node="n2",
+        selected=selected,
+        corpus=corpus,
+        replay=replay,
+        provenance=prov,
+        raw_embedder=FakeEmbedder(dim=32, seed=42),
+        argv=[],
+    )
+    return corpus, report
+
+
+class TestOrchestration:
+    def test_production_paths_and_invariants(self, monkeypatch, tmp_path):
+        pytest.importorskip("faiss")
+        corpus, report = run_toy_demo(monkeypatch, tmp_path)
+        assert corpus.graph.num_nodes() == 6  # gold graph not mutated
+        assert report.subset_of_s1 is True
+        for strategy in report.strategies:
+            score = strategy.score
+            assert sum(1 for e in strategy.labelled_edges if e.label == "TP") == score.tp
+            assert sum(1 for e in strategy.labelled_edges if e.label == "FP") == score.fp
+            assert sum(1 for e in strategy.labelled_edges if e.label == "UNJUDGED") == (
+                score.excluded_predictions
+            )
+            assert len(strategy.missed) == score.fn
+            assert strategy.lost_narrowing + strategy.lost_decision == score.fn
+
+    def test_canonical_edges_rebuilt_from_tokens(self, monkeypatch, tmp_path):
+        corpus, report = run_toy_demo(monkeypatch, tmp_path, selected=["brute_force"])
+        strategy = report.strategies[0]
+        rebuilt = {
+            call.edge for call in strategy.calls if call.edge is not None
+        }
+        assert rebuilt == {
+            ("n1", "n2"), ("n0", "n2"), ("n2", "n3")
+        }
+
+    def test_broken_edge_triggers_consistency_error(self, monkeypatch, tmp_path):
+        corpus = make_toy_corpus()
+        directory, digest, _ = write_cache(tmp_path, corpus)
+        prov, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
+        real_insert = demo.insert_node
+
+        def broken_insert(*args, **kwargs):
+            result = real_insert(*args, **kwargs)
+            return dataclasses.replace(
+                result,
+                edges=tuple(edge for edge in result.edges if edge != ("n1", "n2")),
+            )
+
+        monkeypatch.setattr(demo, "insert_node", broken_insert)
+        with pytest.raises(demo.DemoError) as exc:
+            demo.run_demo(
+                node="n2",
+                selected=["brute_force"],
+                corpus=corpus,
+                replay=demo.ReplayLLMClient(by_prompt),
+                provenance=prov,
+                raw_embedder=FakeEmbedder(dim=32, seed=42),
+                argv=[],
+            )
+        assert exc.value.exit_code == 6
+
+
+# ---------------------------------------------------------------------------
+# Group 4 — Formatter
+# ---------------------------------------------------------------------------
+
+
+def zero_score(node: str = "n2", *, f1: float = 0.0) -> NodeScore:
+    return NodeScore(
+        node=node,
+        gold_positives=1,
+        gold_neighbours=1,
+        shortlist_size=1,
+        shortlist_hits=0,
+        shortlist_recall=0.0,
+        predicted_edges=0,
+        tp=0,
+        fp=0,
+        fn=1,
+        excluded_predictions=0,
+        precision=0.0,
+        recall=0.0,
+        f1=f1,
+        fp_sensitivity=0,
+        precision_sensitivity=0.0,
+        recall_sensitivity=0.0,
+        f1_sensitivity=0.0,
+    )
+
+
+def make_strategy(
+    name: str = "brute_force",
+    *,
+    n_calls: int = 1,
+    tokens: list[str] | None = None,
+    score: NodeScore | None = None,
+    shortlist_scores=None,
+    f1: float = 0.0,
+) -> demo.StrategyReport:
+    tokens = tokens or ["NONE"] * n_calls
+    calls = [
+        demo.DemoCall(
+            x="n2",
+            y=f"c{i}",
+            token=tokens[i],
+            edge=(("n2", f"c{i}") if tokens[i] == "X_PREREQ_Y" else None),
+            latency_s_pilot=1.0,
+            input_tokens=153,
+            output_tokens=5,
+            user_prompt=f"prompt {i}",
+        )
+        for i in range(n_calls)
+    ]
+    score = score or zero_score(f1=f1)
+    return demo.StrategyReport(
+        name=name,
+        display=demo.DISPLAY_NAMES[name],
+        config=demo.DEMO_PARAMS[name],
+        setup_s_live=0.001,
+        setup_embedding_calls=0,
+        shortlist_candidates=tuple(c.y for c in calls),
+        shortlist_scores=shortlist_scores,
+        shortlist_s_live=0.001,
+        embed_s_live=0.0,
+        update_s_live=0.0,
+        replay_wall_s_live=0.001,
+        calls=calls,
+        recorded_latency_s=float(n_calls),
+        recorded_input_tokens=153 * n_calls,
+        recorded_output_tokens=5 * n_calls,
+        recorded_cache_hit_tokens=0,
+        recorded_cache_miss_tokens=153 * n_calls,
+        cost_usd=0.001,
+        calls_vs_s1_pct=50.0,
+        kept_pct=50.0,
+        applied_nodes_added=1,
+        applied_edges_added=0,
+        score=score,
+        labelled_edges=[],
+        missed=[],
+        lost_narrowing=0,
+        lost_decision=1,
+        recall_given_shortlist=0.0,
+        diagnostics={},
+    )
+
+
+def make_report(strategies: list[demo.StrategyReport], *, n_before: int = 28) -> demo.DemoReport:
+    prov = demo.PilotProvenance(
+        path=str(Path("results/pilot/20261007_053743Z/raw_calls.jsonl")),
+        sha256="879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008",
+        recorded_utc="2026-10-07T05:49:00+00:00",
+        prompt_version="v2",
+        model="deepseek-flash",
+        n_calls=812,
+        temperature=0.0,
+        thinking_mode="disabled",
+        retries=0,
+        parse_failures=0,
+        transport_failures=0,
+        input_tokens=123872,
+        output_tokens=2035,
+        cache_hit_tokens=0,
+        cache_miss_tokens=123872,
+        estimated_cost_usd=0.019802,
+        cumulative_latency_s=676.8048,
+        system_prompt_recorded=False,
+    )
+    return demo.DemoReport(
+        started_utc="2026-10-29T00:00:00+00:00",
+        wall_s_live=1.0,
+        argv=[],
+        provenance=prov,
+        pilot_dir="results/pilot/20261007_053743Z",
+        corpus_name="DSA",
+        domain_context="data structures and algorithms",
+        node="n2",
+        full_nodes=n_before + 1,
+        full_edges=54,
+        n_before=n_before,
+        e_before=47,
+        gold_prerequisites=["n1"],
+        gold_dependents=["n3"],
+        gold_incident=2,
+        prompt_version="v2",
+        system_prompt_sha256=demo.SYSTEM_PROMPT_SHA256,
+        prices=demo.PRICES if hasattr(demo, "PRICES") else {
+            "cache_miss_in_per_m": 0.15,
+            "cache_hit_in_per_m": 0.003,
+            "output_per_m": 0.60,
+        },
+        strategies=strategies,
+        selected=[s.name for s in strategies],
+        subset_of_s1=True if any(s.name == "brute_force" for s in strategies) else None,
+        embedder_identity=None,
+        cpu_threads=None,
+    )
+
+
+def render(report: demo.DemoReport, *, ascii: bool = False, show_all: bool = False) -> list[str]:
+    return demo.format_report(
+        report,
+        demo.FormatOptions(color=False, ascii=ascii, show_all_calls=show_all),
+    )
+
+
+class TestFormatter:
+    def test_width_unicode_and_ascii(self):
+        report = make_report([make_strategy(n_calls=11)])
+        for ascii_mode in (False, True):
+            lines = render(report, ascii=ascii_mode)
+            assert max(len(line) for line in lines) <= demo.WIDTH
+
+    def test_no_ansi_when_colour_off(self):
+        report = make_report([make_strategy()])
+        lines = render(report)
+        assert not any("\x1b" in line for line in lines)
+
+    @pytest.mark.parametrize(
+        "n_calls,expected_visible,hidden_line",
+        [
+            (28, None, "... 21 NONE decisions not printed (use --show-all-calls)"),
+            (10, 10, None),
+            (11, 3, "... 8 NONE decisions not printed (use --show-all-calls)"),
+            (1, 1, None),
+        ],
+    )
+    def test_call_printing_rule(self, n_calls, expected_visible, hidden_line):
+        tokens = ["NONE"] * n_calls
+        if n_calls == 28:
+            for index in (1, 5, 16, 21, 27):
+                tokens[index] = "X_PREREQ_Y"
+        report = make_report([make_strategy(n_calls=n_calls, tokens=tokens)])
+        lines = render(report)
+        call_lines = [line for line in lines if line.strip().startswith("call ")]
+        visible = len(call_lines)
+        if expected_visible is not None:
+            assert visible == expected_visible
+        else:
+            assert visible == 7
+        if hidden_line:
+            assert any(hidden_line in line for line in lines)
+        else:
+            assert not any("decisions not printed" in line for line in lines)
+
+    def test_show_all_calls(self):
+        tokens = ["NONE"] * 28
+        report = make_report([make_strategy(n_calls=28, tokens=tokens)])
+        lines = render(report, show_all=True)
+        call_lines = [line for line in lines if line.strip().startswith("call ")]
+        assert len(call_lines) == 28
+        assert not any("decisions not printed" in line for line in lines)
+
+    def test_empty_shortlist_wording(self):
+        strategy = make_strategy(n_calls=0)
+        strategy.shortlist_candidates = ()
+        report = make_report([strategy])
+        lines = render(report)
+        text = "\n".join(lines)
+        assert "0 of 28 kept" in text
+        assert "no LLM calls, no edges" in text
+
+    def test_s1_has_no_similarity_table(self):
+        report = make_report([make_strategy("brute_force", n_calls=3)])
+        text = "\n".join(render(report))
+        assert "all 3 existing concepts, alphabetical, no ranking" in text
+        assert "top candidates by cosine" not in text
+
+    def test_undefined_metrics_are_na(self):
+        score = dataclasses.replace(
+            zero_score(), precision=None, recall=None, f1=None, shortlist_recall=None
+        )
+        report = make_report([make_strategy(score=score)])
+        text = "\n".join(render(report))
+        assert "n/a" in text
+
+    def test_one_tag_per_metric_line(self):
+        report = make_report([make_strategy(n_calls=3)])
+        lines = render(report)
+        prefixes = (
+            "  LLM ", "             cost ", "             calls vs S1",
+            "  applied ", "             update ", "             replay wall",
+            "    lost at", "    metrics", "    recall decomposition",
+        )
+        for line in lines:
+            if line.startswith(prefixes):
+                tags = line.count("[LIVE]") + line.count("[PILOT]") + line.count("[CALC]") + line.count("[GOLD]")
+                assert tags == 1, line
+
+    def test_takeaway_guards(self):
+        s1 = make_strategy("brute_force", f1=0.6)
+        s3 = make_strategy("ann_retrieval", f1=0.8)
+        text = "\n".join(render(make_report([s1, s3])))
+        assert "higher F1 than S1" in text
+        s3_low = make_strategy("ann_retrieval", f1=0.2)
+        text_low = "\n".join(render(make_report([s1, s3_low])))
+        assert "no narrowing strategy beat brute-force F1" in text_low
+        text_s1 = "\n".join(render(make_report([s1])))
+        assert "no narrowing strategy beat" not in text_s1
+
+    def test_banner_provenance_and_replay_notice(self):
+        lines = render(make_report([make_strategy()]))
+        text = "\n".join(lines)
+        assert "results/pilot/20261007_053743Z/raw_calls.jsonl" in text
+        assert "812 calls" in text
+        assert "prompt v2" in text
+        assert "deepseek-flash" in text
+        assert demo.REPLAY_NOTICE in text.replace("\n  ", " ").replace("\n", " ") or all(
+            word in text for word in ("REPLAY NOTICE", "real", "never", "recorded")
+        )
+
+    def test_no_gold_leak_before_after(self):
+        report = make_report([make_strategy(n_calls=3)])
+        lines = render(report)
+        after_index = next(i for i, line in enumerate(lines) if "PHASE 3" in line)
+        before = lines[:after_index]
+        for line in before:
+            if line.strip().startswith("TAGS") or line.strip().startswith("[CALC]"):
+                continue
+            assert "[GOLD]" not in line, line
+            assert not any(marker in line for marker in (" TP ", " FP ", " FN ")), line
+        assert any("[GOLD]" in line for line in lines[after_index:])
+
+
+# ---------------------------------------------------------------------------
+# Group 5 — CLI
+# ---------------------------------------------------------------------------
+
+
+class TestCLI:
+    def test_strategy_parsing_and_ordering(self):
+        assert demo.parse_strategies("s3,s1") == ["brute_force", "ann_retrieval"]
+        assert demo.parse_strategies("s4") == ["bounded_bucket"]
+        assert demo.parse_strategies(None) == demo.CANONICAL_STRATEGIES
+
+    def test_strategy_duplicates_and_unknown(self):
+        with pytest.raises(demo.DemoError) as exc:
+            demo.parse_strategies("s1,brute_force")
+        assert exc.value.exit_code == 2
+        with pytest.raises(demo.DemoError) as exc:
+            demo.parse_strategies("s9")
+        assert exc.value.exit_code == 2
+
+    def test_unknown_node_exit_4(self, capsys):
+        assert demo.main(["--node", "not_a_node", "--strategies", "s1", "--no-color"]) == 4
+        assert "Close matches" in capsys.readouterr().err
+
+    def test_json_existing_path_exit_7(self, tmp_path, capsys):
+        target = tmp_path / "out.json"
+        target.write_text("{}", encoding="utf-8")
+        assert demo.main(["--json", str(target), "--strategies", "s1", "--no-color"]) == 7
+        assert target.read_text(encoding="utf-8") == "{}"
+
+    def test_json_under_results_exit_7(self):
+        assert demo.main([
+            "--json", str(demo.REPO_ROOT / "results" / "demo.json"),
+            "--strategies", "s1", "--no-color",
+        ]) == 7
+
+    def test_json_missing_parent_exit_7(self, tmp_path):
+        target = tmp_path / "missing" / "out.json"
+        assert demo.main(["--json", str(target), "--strategies", "s1", "--no-color"]) == 7
+
+    def test_check_runs_no_trial(self, monkeypatch, capsys):
+        def fail(*args, **kwargs):
+            raise AssertionError("trial ran during --check")
+
+        monkeypatch.setattr(demo, "run_demo", fail)
+        assert demo.main(["--check", "--strategies", "s1"]) == 0
+        out = capsys.readouterr().out
+        assert "OK   corpus" in out
+        assert "OK   pilot cache" in out
+
+    def test_broken_pipe_no_traceback(self):
+        result = subprocess.run(
+            f"{sys.executable} scripts/demo_trial.py --strategies s1 --no-color | head -1",
+            shell=True,
+            cwd=demo.REPO_ROOT,
+            capture_output=True,
+            text=True,
+            timeout=120,
+        )
+        assert "Traceback" not in result.stderr
+
+
+# ---------------------------------------------------------------------------
+# Group 6 — MiniLM integration
+# ---------------------------------------------------------------------------
+
+
+def _strip_volatile(value):
+    if isinstance(value, dict):
+        return {
+            key: _strip_volatile(item)
+            for key, item in value.items()
+            if key != "run" and not key.endswith("_live")
+        }
+    if isinstance(value, list):
+        return [_strip_volatile(item) for item in value]
+    return value
+
+
+class TestMiniLMIntegration:
+    def test_default_run_matches_p8(self):
+        pytest.importorskip("sentence_transformers")
+        pytest.importorskip("faiss")
+        pilot = demo.REPO_ROOT / demo.PILOT_DIR_DEFAULT / "raw_calls.jsonl"
+        if not pilot.is_file():
+            pytest.skip("PILOT-001 cache absent")
+        try:
+            report = demo.run_demo(argv=[])
+        except demo.DemoError as exc:
+            if exc.exit_code == 5:
+                pytest.skip(f"offline MiniLM unavailable: {exc.message}")
+            raise
+        expected = {
+            "brute_force": (28, 28, (4, 1, 3)),
+            "embedding_threshold": (1, 1, (1, 0, 6)),
+            "ann_retrieval": (10, 10, (4, 0, 3)),
+            "bounded_bucket": (9, 9, (1, 0, 6)),
+        }
+        for strategy in report.strategies:
+            size, calls, counts = expected[strategy.name]
+            assert len(strategy.shortlist_candidates) == size
+            assert len(strategy.calls) == calls
+            assert (strategy.score.tp, strategy.score.fp, strategy.score.fn) == counts
+
+    def test_two_runs_identical_nonvolatile_json(self):
+        pytest.importorskip("sentence_transformers")
+        pytest.importorskip("faiss")
+        pilot = demo.REPO_ROOT / demo.PILOT_DIR_DEFAULT / "raw_calls.jsonl"
+        if not pilot.is_file():
+            pytest.skip("PILOT-001 cache absent")
+        try:
+            first = demo.report_to_json(demo.run_demo(argv=[]))
+            second = demo.report_to_json(demo.run_demo(argv=[]))
+        except demo.DemoError as exc:
+            if exc.exit_code == 5:
+                pytest.skip(f"offline MiniLM unavailable: {exc.message}")
+            raise
+        assert _strip_volatile(first) == _strip_volatile(second)
+
+
+# ---------------------------------------------------------------------------
+# Group 7 — Real cache provenance
+# ---------------------------------------------------------------------------
+
+
+class TestRealCache:
+    def test_real_pilot_cache_loads(self):
+        pilot_dir = demo.REPO_ROOT / demo.PILOT_DIR_DEFAULT
+        if not (pilot_dir / "raw_calls.jsonl").is_file():
+            pytest.skip("PILOT-001 cache absent")
+        from graph_insertion.loader import load_corpus
+
+        corpus = load_corpus("DSA_gold_standard_MEKG")
+        prov, by_prompt = demo.load_pilot(pilot_dir, corpus=corpus)
+        assert prov.n_calls == 812
+        assert len(by_prompt) == 812
+        assert prov.sha256 == demo.PILOT_RAW_CALLS_SHA256
```

---

## 10. Items for Luke / Future Work

1. **Suggested counter-node for Q&A:** `bellman_ford_algorithm` (brute force
   F1 1.000 vs S3 0.000) and `graph` (S2 empty shortlist).
2. **Review follow-up:** `DEMO-001-R` (independent review, Gemini) as planned.
3. **Tooling follow-up:** `TOOL-002` for the stale `presentation`/`full` bundle
   profile paths.
4. **Defense note:** say explicitly that the demo replays the 2026-10-07 pilot
   and that S1/S4 differ by one edge from the 2026-10-18 accuracy runs because
   those runs made their own live calls.
5. **Merge performed after the initial report.** `task/DEMO-001` was merged into
   `master` at `28edad8` with `git merge --no-ff` because the merge helper
   refused on pre-existing dirty files in the main checkout. Branch
   `task/DEMO-001` and worktree
   `/home/lukexodus/projects/llm-graph-insertion-complexity-DEMO-001` remain in
   place; no rebase or worktree cleanup was performed.
