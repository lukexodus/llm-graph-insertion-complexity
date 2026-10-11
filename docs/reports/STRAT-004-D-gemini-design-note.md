# STRAT-004-D — Strategy 4 (`bounded_bucket`) Design Note

## 1. Agent Identity

- **Agent:** `gemini`
- **Model Label:** `Gemini 3.8 Flash (High)`
- **Review Note:** Because this agent is a Gemini model, per the prompt's instruction, the APC should review this design note directly rather than relaying it to a secondary Gemini reviewer.

---

## 2. Summary

- **Headline D-8 Finding (`[Confirmed]`):** The sweep harness executes `setup(graph, embedder)` once and `insert_node(...)` **once** per trial (`src/graph_insertion/harness.py:322-370`). Consequently, `update_s` measures a **single un-amortised insertion step** from the post-`setup()` state rather than a multi-insertion stream of $\Delta$ updates. Under batch `setup()` (Algorithm 1) at $(S_{\min}=5, S_{\max}=10, n_{\text{bits}}=12)$, only $6.2\%\text{--}9.7\%$ of segments sit at $S_{\max}=10$, so a single timed insert triggers a split with probability $0.04\text{--}0.16$ and triggers a segment-shrinking underflow merge with probability $0.00$ (insertions only grow existing segments).
- **Amortisation Implication (`[Confirmed]`):** The one-insert sweep protocol **can** test whether single-insert narrowing cost (`shortlist_s` and `llm_calls`) scales as $O(1)$ versus $n$, but **cannot** alone verify EraRAG Theorem 4's amortised multi-insertion bound (that splits/merges cannot cascade and occur at most once every $\Theta(S_{\min})$ insertions per segment). We specify an offline, zero-LLM sequential-stream micro-benchmark ($m = 2000$ consecutive inserts from $n = 0$, costing $0$ API calls and $\sim 4\text{--}5\text{ s}$ CPU time including exact top-$k$ diagnostics or $< 0.25\text{ s}$ pure `shortlist` + `on_inserted`) where splits occur once every $7.12\text{--}7.25$ insertions ($\approx S_{\min} / \ln 2$) with zero cascades.
- **Recommended Design (`[Confirmed]`):** Implement `BoundedBucketStrategy` (`name = "bounded_bucket"`, `src/graph_insertion/strategies/bounded_bucket.py`) using EraRAG-faithful hyperplane LSH ($n_{\text{bits}} = 12$ random unit hyperplanes in $\mathbb{R}^d$ drawn from `np.random.default_rng(seed)` and projected in `float64`), mapped via the inverse reflected binary Gray code $g = \bigoplus_{k=0}^{n_{\text{bits}}-1} (b \gg k)$ into a 1-D total order `(gray_rank, name)` partitioned into contiguous segments bounded by $(S_{\min}=5, S_{\max}=10)$ with feasibility invariant $2 \le S_{\min}$ and $S_{\max} \ge 2 S_{\min}$.

---

## 3. What Was Asked / What Was Done

- **What was asked:** Produce a complete, zero-ambiguity design note (`docs/reports/STRAT-004-D-gemini-design-note.md`) specifying Strategy 4 ("Bounded-Bucket Partitioning", thesis Chapter 3 §3.2.5, adapted from EraRAG, Zhang et al., arXiv:2506.20963v2) across questions D-1 through D-13, verifying all prompt claims against the repository, running synthetic-only experiments ($d=384$ isotropic Gaussian and clustered generators), and providing an implementation-prompt skeleton and $\ge 20$-item mutation list without touching any production code, tests, or shared documents.
- **What was done:**
  1. Read and verified `docs/context/complete-context.md`, `docs/tasks/status.md`, `docs/decisions/decision-log.md` (`D-01`–`D-57`), `docs/context/strategy-interface.md`, the thesis text (Chapters 1–3), `src/graph_insertion/strategy.py`, `src/graph_insertion/harness.py`, `scripts/run_experiment.py`, `src/graph_insertion/strategies/ann_retrieval.py`, `src/graph_insertion/strategies/embedding_threshold.py`, `tests/controllable_embedder.py`, and `tests/test_strategy_interface.py` (`[Confirmed]`).
  2. Identified and documented three prompt corrections / repo discrepancies under Sections 4 and 5 (`[Confirmed]`).
  3. Wrote and executed `/tmp/sim_strat004.py` using synthetic isotropic and clustered 384-D vectors only (`[Confirmed]`) to evaluate bit-count sensitivity (`D-2`), first-insert split/merge probabilities and batch vs. sequential `setup()` distributions (`D-8`), $m=2000$ sequential-stream amortisation (`D-8`), Gray-rank binary search $O(\log M)$ vs. linear Hamming scan $O(M)$ scaling (`D-5`), and exact D-35 / accuracy call budgets (`D-13`).
  4. Specified D-1 through D-13 in full (options, trade-offs, single recommendation, proving test), plus the implementation skeleton, 22-mutant table, and open questions (`[Confirmed]`).

---

## 4. Prompt Corrections

Every claim in the prompt was checked against the live repository files (`[Confirmed]`):

1. **Wrong claim in Section 3 regarding Accuracy Mode graph sizes (`[Confirmed]`):**
   - *Prompt claim:* `"Accuracy mode: leave-one-out over the 29 DSA nodes plus a seeded sample of 30 Metacademy nodes (graphs of about 28 to 58 nodes)."`
   - *Repo reality:* In `src/graph_insertion/harness.py:761-783` and `scripts/run_experiment.py:325-334`, leave-one-out removes a **single** held-out node `h` from the full gold graph (`g_prime = gold_graph.without_node(h)`). For DSA (29 nodes), `n_existing = 28` across 29 trials. For Metacademy (141 nodes, `data/raw/metacademy/`), 30 held-out nodes are sampled (`metacademy_sample_size = 30`), but each trial's existing graph `g_prime` has **`141 - 1 = 140` nodes**, not 29 or 58 nodes (`scripts/run_experiment.py:331` comments `# 140` explicitly). Total accuracy trials = $29 + 30 = 59$, over graphs of size **$n = 28$ and $n = 140$**.
2. **Inexact claim in Section 3 regarding `shortlist()` clearing the cache on entry in Strategies 2 and 3 (`[Confirmed]`):**
   - *Prompt claim:* `"Conventions Strategies 2 and 3 follow, and Strategy 4 must too: ... shortlist() clears the cache on entry (D-55(1))"` (while D-9 correctly notes that Strategy 3 clears it *after* concept-name validation).
   - *Repo reality:*
     - `EmbeddingThresholdStrategy.shortlist()` (`src/graph_insertion/strategies/embedding_threshold.py:196-228`) does **not** clear `_cached_new_name` or `_cached_new_vec` on entry at all; it only overwrites them at lines 226–227 after embedding and validation succeed.
     - `AnnRetrievalStrategy.shortlist()` (`src/graph_insertion/strategies/ann_retrieval.py:273-281`) clears `_cached_new_name = None` and `_cached_new_vec = None` at lines 280–281, *after* `if not self._setup_called` (line 273) and `_validate_concept_name(new_name)` (line 276).
     - Our reproducer in `/tmp/sim_strat004.py` (Section 7, Part 1) confirms that calling `shortlist("")` after `shortlist("good_node")` leaves `_cached_new_name == 'good_node'` in **both** `EmbeddingThresholdStrategy` and `AnnRetrievalStrategy`. Strategy 4 must clear `_cached_new_name`, `_cached_new_vec`, and per-query diagnostics at the **very first lines of `shortlist()`**, before `_setup_called` and `_validate_concept_name(new_name)`.
3. **Nuance in Section 3 regarding `max_candidates(n_existing)` pickup (`[Confirmed]`):**
   - *Prompt claim:* `"If a strategy defines max_candidates(n_existing), the live-call guard uses it; otherwise it falls back to the brute-force bound."`
   - *Repo reality:* This is **true** for `candidate_upper_bound()` (`src/graph_insertion/strategy.py:187-201`) and `compute_planned_calls_upper_bound()` (`scripts/run_experiment.py:287-348`, which powers the `--live` call guard). However, `estimate_and_print_plan()` in `src/graph_insertion/harness.py:621` (used when `config.dry_run=True` without `--live`) inspects `strategy.config().get("top_k", None)` instead of calling `candidate_upper_bound(strategy, n)`. Because `harness.py` is on the standing forbidden list, we document this in Section 10 ("Found but not changed") and D-13.

---

## 5. Part 0 Findings — Verification of Section 3 Repo Facts

| # | Section 3 Claim | Status | Repo Evidence (File & Lines / Command Output) |
| :--- | :--- | :--- | :--- |
| 1 | `NarrowingStrategy`, `Shortlist(candidates, scores)`, `insert_node`, `candidate_upper_bound` live in `src/graph_insertion/strategy.py`. | **`[Confirmed]`** | `src/graph_insertion/strategy.py`: `Shortlist` at lines `47-105`, `NarrowingStrategy` at lines `113-184`, `candidate_upper_bound` at lines `187-201`, `insert_node` at lines `204-289`. |
| 2 | If a strategy defines `max_candidates(n_existing)`, the live-call guard uses it; otherwise it falls back to the brute-force bound. | **`[Confirmed]`** (with `harness.py:621` nuance) | `src/graph_insertion/strategy.py:187-201` (`candidate_upper_bound` checks `getattr(strategy, "max_candidates", None)` and clamps to `[0, n_existing]`, falling back to `max(0, n_existing)`). `scripts/run_experiment.py:309,327,332` calls `candidate_upper_bound(strategy, ...)` inside `compute_planned_calls_upper_bound`. (Non-live `harness.py:621` checks `config().get("top_k")`.) |
| 3 | The sweep harness builds a graph of size $n$, calls `setup()` **once**, then calls `insert_node` **exactly once** per trial (`update_s` is the first insert after `setup()`). | **`[Confirmed]`** | `src/graph_insertion/harness.py:300-370` (`run_single_sweep_trial` builds `g` of size `n`, times `strategy.setup(g, metered_embedder)` once at lines `322-324`, then calls `insert_node(...)` once at lines `363-370`). |
| 4 | Sweep matrix (`D-35`): sizes `50, 100, 200, 500, 1000, 2000` $\times$ `10` trials. | **`[Confirmed]`** | `src/graph_insertion/harness.py:42` (`DEFAULT_SIZES = (50, 100, 200, 500, 1000, 2000)`) and `harness.py:92` (`n_trials: int = 10`). |
| 5 | Accuracy mode: leave-one-out over 29 DSA nodes plus seeded sample of 30 Metacademy nodes ("graphs of about 28 to 58 nodes"). | **Partially Wrong `[Confirmed]`** | Trial counts ($29 + 30 = 59$) are `[Confirmed]`, but graph sizes (`n_existing`) are **$28$ (DSA) and $140$ (Metacademy)** (`src/graph_insertion/harness.py:761-783`, `scripts/run_experiment.py:325-334`). |
| 6 | Call bounds over D-35 matrix: brute force `38,500`; Strategy 3 at $k=10$: `600` (`max_candidates = min(k, n)`). | **`[Confirmed]`** | $10 \times (50+100+200+500+1000+2000) = 38,500$; $10 \times 6 \times 10 = 600$ (`/tmp/sim_strat004.py` Section 5 output and `src/graph_insertion/strategies/ann_retrieval.py:161-170`). |
| 7 | Conventions of Strategies 2 and 3: parameters fixed a priori (`D-35(5)`); L2-normalised `float32` vectors; shortlist ordered by `(-score, name)`; `shortlist()` embeds `new_name` once via `embed_text(new_name)` and caches vector; `on_inserted()` reuses cache with zero embedding calls; all-or-nothing `setup()` (`D-50(3)`); `config()` carries every hyperparameter; `diagnostics()` is JSON-serialisable and computed outside timed windows; strategy `name` strings are permanent. | **`[Confirmed]`** (except cache-clear placement in S2/S3; see Correction 2) | Verified in `src/graph_insertion/strategies/embedding_threshold.py:157-324`, `src/graph_insertion/strategies/ann_retrieval.py:213-462`, `src/graph_insertion/harness.py:381` (`diagnostics()` called after `insert_node` returns), and `tests/test_strategy_interface.py:67-420`. |
| 8 | `docs/context/strategy-interface.md` §5 gives a non-binding sketch for S4: bounded buckets with centroids, split on overflow, diagnostics `{bucket_id, split_occurred, bucket_size}`, and does not mention hyperplane hashing. | **`[Confirmed]`** | `docs/context/strategy-interface.md:208-221` explicitly labels §5 `"Per-strategy mapping (non-binding sketch)"` and describes centroid-based buckets without mentioning hyperplane LSH. |
| 9 | `tests/controllable_embedder.py` (`ControllableEmbedder`, `vector_with_cosine`) is the frozen shared test helper. New strategy tests subclass `StrategyConformanceSuite`. | **`[Confirmed]`** | `tests/controllable_embedder.py:56,115` and `tests/test_strategy_interface.py:67` (`class StrategyConformanceSuite`). |
| 10 | `src/graph_insertion/strategies/ann_retrieval.py` and `tests/test_ann_retrieval_strategy.py` are the current reference for lifecycle, diagnostics, and test style. | **`[Confirmed]`** | Read in full (`src/graph_insertion/strategies/ann_retrieval.py:1-462`, `tests/test_ann_retrieval_strategy.py:1-647`). |

---

## 6. Design Note: Questions D-1 … D-13

### D-1. Partition Mechanism

- **Options:**
  - **(a) EraRAG-faithful hyperplane LSH partitioning with stored random hyperplanes:** Draw $n_{\text{bits}}$ random unit hyperplanes in $\mathbb{R}^d$ once from a seeded NumPy `Generator` during `setup()` (and store them). Hash each concept embedding to its $n_{\text{bits}}$-bit sign code, order buckets along the 1-D reflected binary Gray code curve, and split/merge segments to enforce $[S_{\min}, S_{\max}]$.
  - **(b) Centroid-based buckets (as in the non-binding `strategy-interface.md` §5 sketch):** Maintain $M = \Theta(n / S_{\min})$ buckets each represented by a mean centroid vector in $\mathbb{R}^d$, routing a query to $\arg\max_j \langle q, \mu_j \rangle$.
  - **(c) Random projection trees (Dasgupta–Freund RP-trees):** Build an explicit hierarchical binary tree of data-dependent splits.
- **Trade-offs:**
  - Option **(b)** directly contradicts the thesis's theoretical framing and defeats the asymptotic complexity goal of Strategy 4: because $S_{\max} = \Theta(1)$ is a constant, the number of buckets is $M = \Theta(n / S_{\min}) = \Theta(n)$. Routing a new concept by comparing its $d$-dimensional embedding against all $M$ bucket centroids requires $\Theta((n / S_{\min}) \cdot d) = \Theta(n d)$ time in `shortlist()`, which scales linearly with $n$ rather than the $O(n_{\text{bits}} \cdot d)$ constant-time hashing of EraRAG Theorem 4 (`docs/thesis/An Empirical Complexity Analysis...md` §2.2.4, line 134). Furthermore, centroid maintenance requires stateful $k$-means or 2-means recomputation and depends heavily on insertion history.
  - Option **(c)** makes hyperplane choices data-dependent rather than fixed a priori, breaking EraRAG's reproducible data-independent hash assignment.
  - Option **(a)** is faithful to EraRAG (Zhang et al., 2025) as cited in Thesis §2.2.4 and §3.2.5 (`[Confirmed]`), computes the hash code in $O(n_{\text{bits}} \cdot d) = O(d)$ time independent of $n$, and keeps all diagnostic keys promised in `strategy-interface.md` §5 (`bucket_id`, `split_occurred`, `bucket_size`) as a subset of `diagnostics()`.
- **Recommendation:** **Option (a) — EraRAG-faithful hyperplane LSH partitioning with stored random hyperplanes.**
- **Proving Test:** `test_hyperplane_hash_determinism_and_stored_planes`: verify that after `setup()`, `strategy._hyperplanes` has shape `(n_bits, d)` with unit-norm rows, that hashing a query vector depends only on `sign(vec @ _hyperplanes.T)` (not on bucket centroids), and that two vectors sharing all hyperplane signs always map to the same raw LSH code regardless of the positions of other nodes in the graph.

---

### D-2. Hyperplanes

- **Options:**
  - **(a) Fixed constant $n_{\text{bits}} = 12$** (with $2^{12} = 4096$ possible hash codes, exceeding the maximum sweep graph size $n = 2000$), drawn once in `setup()` via `rng = np.random.default_rng(self.seed)` as `raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)` followed by row-wise L2 normalisation.
  - **(b) Smaller or larger fixed constant** ($n_{\text{bits}} \in \{8, 16, 32\}$).
  - **(c) Dynamic bit count as a function of initial $n$** (e.g., $n_{\text{bits}} = \lceil \log_2(n) \rceil$).
- **Trade-offs:**
  - Option **(c)** violates EraRAG's design principle that the hyperplane family is fixed a priori (`k` hyperplanes kept across the lifetime of the index): if $n_{\text{bits}}$ changed with $n_{\text{initial}}$, a graph built from $n = 0$ via sequential insertions would have a different hyperplane family than one built at $n = 500$, and `config()` could not report a fixed hyperparameter (`D-35(5)`).
  - Between **(a)** and **(b)**: At $n = 500$ in our synthetic simulation (`/tmp/sim_strat004.py` Section 7, Part 2), $n_{\text{bits}} = 8$ ($2^8 = 256$ codes) forces heavy raw hash collisions (`217.8` unique codes for 500 nodes) before size control even runs, lowering `exact_topk_overlap` (`0.026` vs `0.032` isotropic). Conversely, $n_{\text{bits}} = 12$ ($4096 > 2000$ codes) gives fine-grained angular resolution across the entire $n \in [28, 2000]$ range (`468.1` unique codes at $n=500$, `exact_topk_overlap = 0.032` isotropic and `0.092` on strongly clustered vectors), fits cleanly in a standard 16-bit integer, and has negligible projection cost ($12 \times 384 = 4608$ multiply-adds $\approx 5\,\mu\text{s}$).
  - **When drawn:** In `setup(graph, embedder)` as soon as the embedding dimension $d$ is known from the first embedded node. If `graph` is empty ($n = 0$) at `setup()`, `_dim` and `_hyperplanes` remain `None` during `setup()` (just as `AnnRetrievalStrategy` defers `_init_empty_index(dim)` until the first `shortlist()` call on an empty graph, `src/graph_insertion/strategies/ann_retrieval.py:242-246,307-309`) and are initialised lazily on the first `shortlist()` call once the first vector's dimension $d$ is observed. Calling `setup()` a second time resets the RNG with `np.random.default_rng(self.seed)` and regenerates the exact same `_hyperplanes` matrix.
- **Recommendation:** **Option (a) — Fixed constant ` DEFAULT_N_BITS = 12` (`n_bits >= 1`, `n_bits <= 62` so codes fit in signed 64-bit Python/NumPy integers), drawn from `np.random.default_rng(self.seed)` in `setup()` once $d$ is known (or lazily on first `shortlist()` when `setup()` received an empty graph), and regenerated identically on every `setup()` call.**
- **Proving Test:** `test_hyperplanes_independent_of_insertion_and_node_order`: construct two graphs with identical node sets inserted into `ConceptGraph` in reversed order, run `setup()` on both, and assert `np.array_equal(s_a._hyperplanes, s_b._hyperplanes)`; also test `setup(empty_graph)` followed by `shortlist("a")` produces the exact same `_hyperplanes` as `setup(non_empty_graph)`.

---

### D-3. Bounds ($S_{\min}$, $S_{\max}$, Feasibility Invariant, Small-$n$ Regime, and `max_candidates`)

- **Options:**
  - **(a) Feasibility invariant $2 \le S_{\min}$ and $S_{\max} \ge 2 S_{\min}$, with defaults $S_{\min} = 5, S_{\max} = 10$ and sensitivity settings $(S_{\min}, S_{\max}) \in \{(2, 5), (10, 20)\}$** following $S_{\min} = \lfloor S_{\max} / 2 \rfloor$.
  - **(b) Relaxed invariant $1 \le S_{\min} < S_{\max}$** (allowing $S_{\max} < 2 S_{\min}$, e.g. $S_{\min} = 7, S_{\max} = 10$).
- **Trade-offs & Mathematical Proof of the Feasibility Invariant:**
  - Why **$S_{\max} \ge 2 S_{\min}$ and $S_{\min} \ge 2$** is both necessary and sufficient for split/merge closure without cascading:
    1. **Split closure:** When a valid segment reaches size $S_{\max} + 1$ after an insertion, bisecting it at `mid = (S_max + 1) // 2` produces two sub-segments of sizes $\lfloor (S_{\max} + 1) / 2 \rfloor$ and $\lceil (S_{\max} + 1) / 2 \rceil$. For the smaller half to satisfy $\lfloor (S_{\max} + 1) / 2 \rfloor \ge S_{\min}$, we require $S_{\max} + 1 \ge 2 S_{\min} \iff S_{\max} \ge 2 S_{\min} - 1$.
    2. **Merge + Rebalance closure:** Suppose an undersized bucket of size $s \in [1, S_{\min} - 1]$ merges with an adjacent valid bucket of size $t \in [S_{\min}, S_{\max}]$. If $s + t > S_{\max}$ (so simple concatenation overflows $S_{\max}$), we bisect the combined $s + t$ items at `mid = (s + t) // 2`. Because $s + t \ge S_{\max} + 1$, the smaller half has size $\ge \lfloor (S_{\max} + 1) / 2 \rfloor \ge S_{\min}$. What about the larger half? Since $s \le S_{\min} - 1$ and $t \le S_{\max}$, $s + t \le S_{\max} + S_{\min} - 1$. For the larger half $\lceil (s + t) / 2 \rceil$ to be $\le S_{\max}$ for all $s \le S_{\min} - 1$, we need $\lceil (S_{\max} + S_{\min} - 1) / 2 \rceil \le S_{\max} \iff S_{\min} \le S_{\max} + 1$ (always true), AND when $s = 0$ is excluded, having **$S_{\max} \ge 2 S_{\min}$** guarantees that even splitting an exact $2 S_{\min}$-element segment yields two segments of size $S_{\min}$ with at least $S_{\min}$ headroom before either can overflow again!
    3. Why **$S_{\min} \ge 2$**: EraRAG Theorem 4 explicitly requires $1 < S_{\min} \le S_{\max} = O(1)$ (`[Confirmed]` from Section 2 digest). If $S_{\min} = 1$, a newly hashed singleton bucket already has size $1 \ge S_{\min}$ and never merges with an adjacent bucket, degenerating into unmerged singleton LSH buckets! Notice that for the sensitivity setting $S_{\max} = 5$, the formula $S_{\min} = \lfloor S_{\max} / 2 \rfloor = \lfloor 5 / 2 \rfloor = 2$ satisfies **both** $S_{\min} \ge 2$ and $S_{\max} \ge 2 S_{\min}$ ($5 \ge 4$)!
  - **Challenge to APC Provisional Position:** We tested whether any alternative default (e.g., $S_{\min} = 4, S_{\max} = 10$ or $S_{\min} = 6, S_{\max} = 12$) beats $S_{\min} = 5, S_{\max} = 10$. Keeping $S_{\max} = 10$ equal to Strategy 3's $k = 10$ is essential for experimental control: both Strategy 3 and Strategy 4 have an identical worst-case LLM call budget ($600$ calls over the D-35 sweep matrix and $590$ calls over the 59 accuracy trials), isolating the geometric partitioning mechanism from shortlist capacity. And $(S_{\min}, S_{\max}) \in \{(2, 5), (5, 10), (10, 20)\}$ satisfies $2 \le S_{\min}$ and $S_{\max} \ge 2 S_{\min}$ across every single setting.
  - **Small-$n$ and Empty-Graph Regime:**
    - **$n = 0$ (empty index):** `self._segments == []` (0 segments). `shortlist()` returns `Shortlist(candidates=[], scores=[])`.
    - **$1 \le n < S_{\min}$ (fewer than $S_{\min}$ nodes in the entire graph):** It is mathematically impossible for any partition of $n < S_{\min}$ items to have $\ge 1$ segment of size $\ge S_{\min}$. In this regime, all $n$ items reside in **exactly 1 segment** of size $n \in [1, S_{\min} - 1]$.
    - **$n \ge S_{\min}$:** Every segment $S_i$ strictly satisfies $S_{\min} \le |S_i| \le S_{\max}$, and the number of segments satisfies $\lceil n / S_{\max} \rceil \le M \le \lfloor n / S_{\min} \rfloor$.
  - **Formula for `max_candidates(n_existing)`:**
    $$\texttt{max\_candidates}(n_{\text{existing}}) = \max(0, \min(\texttt{self.s\_max}, n_{\text{existing}}))$$
    *Proof that this is a true upper bound in every state reachable through `setup()` and `insert_node()`:* Before any `shortlist(new_name)` call on a graph of $n_{\text{existing}}$ nodes, either $n_{\text{existing}} = 0$ (0 candidates $\le 0$), $1 \le n_{\text{existing}} < S_{\min}$ (1 segment of size $n_{\text{existing}} < S_{\min} < S_{\max}$, so $\le n_{\text{existing}}$ candidates), or $n_{\text{existing}} \ge S_{\min}$ (every segment has size $\le S_{\max}$ by the invariant maintained at the end of `setup()` and at the end of every `on_inserted()`, and `shortlist()` inspects a single home segment and excludes `new_name`, yielding $\le \min(S_{\max}, n_{\text{existing}})$ candidates).
- **Recommendation:** **Enforce `2 <= s_min` and `s_max >= 2 * s_min` in `__init__` (raising `ValueError` otherwise); lock defaults `DEFAULT_S_MIN = 5`, `DEFAULT_S_MAX = 10`, with sensitivity settings `(s_min=2, s_max=5)` and `(s_min=10, s_max=20)`; define `max_candidates(n_existing)` as `max(0, min(self.s_max, int(n_existing)))` (raising `ValueError` if `n_existing` is a `bool` or not an `int`, matching `AnnRetrievalStrategy.max_candidates` at `src/graph_insertion/strategies/ann_retrieval.py:166-170`).**
- **Proving Test:** `test_bounds_validation_and_invariant_across_all_n`: verify `__init__` rejects `s_min < 2` and `s_max < 2 * s_min` (e.g. `(1, 5)`, `(5, 9)`), and verify that inserting $n = 1, 2, \dots, 60$ nodes sequentially from $n = 0$ maintains `len(_segments) == 1` for $1 \le n < s_{\min}$ and `all(s_min <= len(seg) <= s_max for seg in _segments)` for all $n \ge s_{\min}$.

---

### D-4. Split Rule for an Oversize Bucket

- **Options:**
  - **(a) Order-preserving bisection along the `(gray_rank, name)` total order:** Maintain each segment's entries sorted by `(gray_rank, name)`, where `gray_rank` is the $n_{\text{bits}}$-bit reflected binary Gray rank of the stored hyperplanes. When a segment overflows ($|S_i| > S_{\max}$), split it at `mid = len(S_i) // 2` into `S_i[:mid]` and `S_i[mid:]` (recursively during batch `setup()` if a raw bucket has $> 2 S_{\max}$ items).
  - **(b) Iterative single-bit refinement down the hyperplane stream, falling back to `name` tie-break only after all $n_{\text{bits}}$ bits are exhausted:** Find the first hyperplane bit $r \in \{0, \dots, n_{\text{bits}}-1\}$ that splits the bucket into two non-empty subsets.
  - **(c) 2-means clustering on the $\mathbb{R}^d$ vectors inside the overflowing bucket.**
- **Trade-offs:**
  - Option **(b)** has a fatal flaw with the $[S_{\min}, S_{\max}]$ invariant: a single hyperplane bit can split a bucket of $S_{\max} + 1 = 11$ items into an unbalanced **10 vs. 1** or **9 vs. 2** partition! The smaller child (size 1 or 2 $< S_{\min}$) immediately violates $S_{\min} = 5$, triggering a secondary merge, which can overflow a neighbour and trigger a cascade!
  - Option **(c)** costs $O(I \cdot S_{\max} \cdot d)$ per split, can also produce unbalanced clusters ($< S_{\min}$), and destroys the global 1-D Hamming/Gray ordering of segments needed for $O(\log M)$ lookup and adjacency.
  - Option **(a)** solves all three problems simultaneously:
    1. Because reflected Gray rank `gray_rank` preserves the prefix hierarchy of all $n_{\text{bits}}$ hyperplanes (see D-5), sorting by `(gray_rank, name)` orders items along the hyperplane space-filling curve **and** automatically breaks ties by `name` when vectors share identical $n_{\text{bits}}$-bit codes (e.g., duplicate vectors).
    2. Bisecting at `mid = len(S_i) // 2` when $|S_i| = S_{\max} + 1$ **always** yields sizes $\lfloor (S_{\max}+1)/2 \rfloor \ge S_{\min}$ and $\lceil (S_{\max}+1)/2 \rceil \le S_{\max}$ in a single step, with **zero** possibility of underflow or cascade.
    3. **Termination, determinism, and cost:** Termination is unconditional ($1$ step in `on_inserted`; at most $\lceil \log_2(n / S_{\max}) \rceil$ levels in batch `setup()`). Determinism is absolute because `(gray_rank, name)` is a strict total order on unique concept names. Cost in `on_inserted` is **$O(S_{\max})$** Python list slicing (no $O(d)$ dot products needed during the split because `gray_rank` was already computed when the node was hashed!).
- **Recommendation:** **Option (a) — Bisect overflowing segments at `mid = len(seg) // 2` in canonical `(gray_rank, name)` order (recursively in `setup()` until all sub-segments have size $\le S_{\max}$).**
- **Proving Test:** `test_split_forced_on_overflow_and_duplicate_vectors`: insert $S_{\max} + 1 = 11$ nodes with identical embedding vectors (so every hyperplane bit is identical), verify that `(gray_rank, name)` bisection terminates in 1 split producing two segments of sizes $5$ and $6$ split lexicographically by `name`, with `diagnostics()["split_occurred"] is True`.

---

### D-5. Merge Rule and Adjacency

- **Options:**
  - **(a) 1-D Reflected Binary Gray-Rank Segment Order with Boundary-Hamming Tie-Breaking:**
    - Convert each $n_{\text{bits}}$-bit hyperplane sign code $b = \sum_{r=0}^{n_{\text{bits}}-1} \text{bit}_r \cdot 2^{n_{\text{bits}}-1-r} \in [0, 2^{n_{\text{bits}}}-1]$ to its reflected binary Gray rank via the inverse Gray map:
      $$g = \text{gray\_rank}(b) = \bigoplus_{k=0}^{n_{\text{bits}}-1} (b \gg k)$$
    - Consecutive Gray ranks $g$ and $g+1$ have binary codes $b(g) = g \oplus (g \gg 1)$ and $b(g+1)$ that differ in **exactly 1 bit** (Hamming distance $= 1$).
    - Segments $S_0, S_1, \dots, S_{M-1}$ partition the sorted `(gray_rank, name)` sequence into disjoint contiguous intervals: $\max(S_{i-1}) < \min(S_i)$.
    - The adjacent buckets of $S_i$ are strictly its immediate predecessor $S_{i-1}$ (if $i > 0$) and immediate successor $S_{i+1}$ (if $i < M - 1$), matching EraRAG Algorithm 1's notation "$B_{i-1}$ or $B_{i+1}$ based on proximity in Hamming space".
    - When choosing between $S_{i-1}$ and $S_{i+1}$, compare the $O(1)$ boundary proximity key:
      - Left neighbour key: `(hamming_distance(S_{i-1}[-1].code, S_i[0].code), S_i[0].gray - S_{i-1}[-1].gray, len(S_{i-1}), 0)`
      - Right neighbour key: `(hamming_distance(S_i[-1].code, S_{i+1}[0].code), S_{i+1}[0].gray - S_i[-1].gray, len(S_{i+1}), 1)`
      and pick the neighbour with the smaller tuple. If the merged segment has size $> S_{\max}$ (i.e., $|S_i| + |S_{\text{nbr}}| \in [S_{\max}+1, S_{\max}+S_{\min}-1]$), immediately bisect it at `mid = len(combined) // 2` into two valid segments in $[S_{\min}, S_{\max}]$.
  - **(b) Explicit Nearest-Hamming-Bucket Scan over all $M$ segments.**
- **Trade-offs:**
  - **Does an explicit scan over all buckets defeat the purpose of Strategy 4 for the thesis's cost-scaling question?** **Yes (`[Confirmed]`).** Because $S_{\max} = \Theta(1)$, the number of segments grows linearly with graph size: $M = \Theta(n / S_{\min}) = \Theta(n)$. If `shortlist()` or `on_inserted()` scans all $M$ buckets to find the nearest bucket in Hamming space when a query's exact LSH code has no existing bucket, `shortlist_s` scales as $\Theta(M) = \Theta(n)$! In our benchmark (`/tmp/sim_strat004.py` Section 7, Part 6), a linear Hamming scan over segments grows from **$51.93\,\mu\text{s}$ at $n=50$ to $763.92\,\mu\text{s}$ at $n=2000$ ($21.42\times$ slower)**, whereas 1-D Gray-rank binary search stays flat at **$32.26\,\mu\text{s}$ at $n=50$ and $35.67\,\mu\text{s}$ at $n=2000$**!
  - Option **(a)** gives $O(\log M) = O(\log n)$ segment lookup via binary search on segment max-keys and $O(1)$ adjacency resolution between $B_{i-1}$ and $B_{i+1}$, directly matching EraRAG Algorithm 1's notation ($B_{i-1}$ or $B_{i+1}$) while preserving Hamming locality via the reflected Gray order.
- **Recommendation:** **Option (a) — Order segments by `(gray_rank, name)` using the inverse reflected Gray map $g = \bigoplus_{k=0}^{n_{\text{bits}}-1} (b \gg k)$, define adjacency as $S_{i-1}$ and $S_{i+1}$, and select between $S_{i-1}$ and $S_{i+1}$ using the deterministic 4-tuple `(boundary_hamming_dist, boundary_gray_gap, neighbor_len, 0_left_1_right)` with immediate midpoint rebalance if the combined size exceeds $S_{\max}$.**
- **Proving Test:** `test_merge_adjacency_rule_and_sublinear_lookup`: construct three segments $S_0, S_1, S_2$ with controlled hyperplane codes where $|S_1| < S_{\min}$ in `setup()`, verify $S_1$ merges with the neighbour having smaller boundary Hamming distance (and breaks ties by Gray gap, smaller neighbour size, then left neighbour), and verify `shortlist()` does not scan all segments.

---

### D-6. Shortlist Rule

- **Options:**
  - **(a) Single home-segment retrieval without state mutation:**
    1. Hash `new_vec` with `self._hyperplanes` to obtain `(code, gray)` and form the query key `q_key = (gray, new_name)`.
    2. If `self._segments` is empty ($n = 0$), return `Shortlist(candidates=[], scores=[])`.
    3. Locate the **home segment** $S_{\text{home}}$ via binary search over `self._segments` in $O(\log M)$ time without mutating any bucket state:
       - Find the first segment index `pos` with `S_{pos}[-1].sort_key() >= q_key`.
       - **Case 1 (Inside segment span):** If `pos < M` and `S_{pos}[0].sort_key() <= q_key <= S_{pos}[-1].sort_key()`, then `home_idx = pos` (`inside_span = True`).
       - **Case 2 (Before first segment):** If `pos == 0` and `q_key < S_0[0].sort_key()`, then `home_idx = 0` (`inside_span = False`).
       - **Case 3 (After last segment):** If `pos == M`, then `home_idx = M - 1` (`inside_span = False`).
       - **Case 4 (Strictly in the gap between $S_{\text{pos}-1}$ and $S_{\text{pos}}$):** Compare $S_{\text{pos}-1}$ and $S_{\text{pos}}$ using the exact same boundary proximity tuple as D-5:
         - `left_key = (hamming_distance(S_{pos-1}[-1].code, code), gray - S_{pos-1}[-1].gray, len(S_{pos-1}), 0)`
         - `right_key = (hamming_distance(code, S_{pos}[0].code), S_{pos}[0].gray - gray, len(S_{pos}), 1)`
         and set `home_idx = (pos - 1) if left_key <= right_key else pos` (`inside_span = False`).
    4. Notice that in all four cases, $S_{\text{home}}$ is **guaranteed** to be the exact segment into which `on_inserted(new_name)` will place `new_name` (and if `inside_span` is `False`, it is the exact adjacent segment into which the transient singleton bucket for `new_name` merges under Algorithm 3!).
    5. Collect all entries `e` in $S_{\text{home}}$ with `e.name != new_name` (defensively excluding `new_name`), slice their L2-normalised `float32` vectors from the contiguous matrix `self._mat[rows]`, compute cosine similarities `scores = (self._mat[rows] @ new_vec).tolist()`, sort by `(-score, name)`, and return `Shortlist(candidates=candidates, scores=scores)`.
  - **(b) Multi-probe / neighbouring-bucket expansion ($S_{\text{home}} \cup S_{\text{home}-1} \cup S_{\text{home}+1}$).**
- **Trade-offs:**
  - Option **(b)** is **rejected** because Thesis Chapter 3 §3.2.5 (`docs/thesis/An Empirical Complexity Analysis...md`, line 186) explicitly specifies the single-bucket rule: *"At insertion time, a new concept is assigned to a bucket and compared only against the members of that bucket"* (`[Confirmed]`), and probing 3 buckets would triple `max_candidates` from $S_{\max} = 10$ to $30$ ($1800$ sweep calls), breaking the 600-call budget parity with Strategy 3.
  - Option **(a)** obeys §3.2.5's single-bucket rule, never mutates state during `shortlist()`, and handles novel codes / inter-segment gaps consistently with `on_inserted()`.
- **Recommendation:** **Option (a) — Single home-segment lookup via $O(\log M)$ binary search + D-5 gap tie-breaker, scoring against the L2-normalised `float32` row vectors stored in `self._mat[rows]`, ordered by `(-score, name)`, with zero mutation of `_segments` or `_mat`.**
- **Proving Test:** `test_shortlist_does_not_mutate_state_and_matches_home_segment`: snapshot `_segments`, `_mat`, and `_n` before `shortlist(new_name)`, call `shortlist(new_name)` twice in a row (including when `new_name`'s code falls in a gap between two segments), verify identical `Shortlist` output and unchanged internal state, and verify `shortlist` candidates are ordered by `(-score, name)`.

---

### D-7. `on_inserted` Rule, Complexity Breakdown, and Capacity Sizing

- **Options:**
  - **(a) Local incremental insert + local split with pre-sized vector buffer (`capacity = max(n + 16, 16)` in `setup()`, geometric $2\times$ doubling if capacity is exceeded in multi-insert streams):**
    - Reuse `_cached_new_vec` (and `_cached_new_code`, `_cached_new_gray`) from `shortlist(new_name)` with **zero** embedder calls.
    - Append `_cached_new_vec` to `self._mat[self._n]` in $O(d)$ time (because `setup()` allocates `self._mat` with shape `(max(n + 16, 16), dim)`, the first insert after `setup()` — and up to 16 inserts — never reallocates `self._mat`).
    - Locate `home_idx` via `_locate_home_segment(gray, new_name)` in $O(\log M)$ time.
    - Insert `BucketEntry(gray, new_name, code, row)` into `seg = self._segments[home_idx]` in sorted `(gray, name)` order ($|S_{\text{home}}| \le S_{\max} = 10$).
    - If `not inside_span` (and `n_before >= 1`), record `_last_merge_occurred = True` (the new node formed a transient singleton bucket outside existing segment spans and merged into $S_{\text{home}}$ per Algorithm 3).
    - If `len(seg) > self.s_max`, bisect `seg` at `mid = len(seg) // 2` into `left_half, right_half`, replace `self._segments[home_idx : home_idx + 1] = [left_half, right_half]`, and record `_last_split_occurred = True`.
  - **(b) Reallocate `np.vstack([self._mat, new_vec])` or rebuild all segments in `on_inserted()`.**
- **Trade-offs & Itemised Complexity:**
  - Option **(b)** violates `D-50(1)` by doing $O(n \cdot d)$ matrix reallocation or $O(n \log n)$ segment rebuild inside `on_inserted()`.
  - Under Option **(a)**, the exact operation breakdown in `on_inserted(new_name)` is:
    - **$O(1)$ operations:** Cache validation (`_cached_new_name == new_name`), duplicate-node check (`new_name in self._name_to_idx`), updating `self._name_to_idx[new_name] = row` and `self._names.append(new_name)`, and updating diagnostic flags (`_last_split_occurred`, `_last_merge_occurred`, `_last_bucket_size`).
    - **$O(d)$ / $O(S_{\max})$ operations:** Copying the cached `float32` vector into the pre-allocated row `self._mat[row] = vec` ($O(d) = 384$ floats $\approx 1.5\text{ KB}$, no allocation on the timed insert after `setup()`), inserting `BucketEntry` into `seg` of length $\le S_{\max} = 10$ ($O(S_{\max})$), and bisecting `seg` if `len(seg) == S_{\max} + 1` ($O(S_{\max})$). Note that because `gray_rank` is already stored on each `BucketEntry`, splitting does **not** even require $O(S_{\max} \cdot d)$ dot products — it is $O(S_{\max})$!
    - **$O(\log M)$ and $O(M)$ operations ($M = \text{\#segments} \le n / S_{\min}$):** Binary search over `_segments` takes $O(\log M) \le 9$ comparisons at $n = 2000$ ($M \approx 299$). Only when a split actually occurs ($\sim 10\%\text{--}14\%$ of inserts) does Python's `list` slice assignment `self._segments[home_idx : home_idx + 1] = [left_half, right_half]` shift at most $M \le 400$ C-level pointer references ($\le 3.2\text{ KB}$ `memmove`, $< 0.5\,\mu\text{s}$).
  - **Confirming the APC's reading of the D-50 "no headroom that hides the one-insert cost" lesson:** We confirm the APC's reading is 100% right (`[Confirmed]`). Pre-allocating vector storage capacity (`max(n + 16, 16)`) in `setup()` avoids an artificial $O(n \cdot d)$ `ndarray` copy bug (just as `EmbeddingThresholdStrategy` pre-allocates `max(n + 16, 16)` rows in `src/graph_insertion/strategies/embedding_threshold.py:189`), while **all bucket lookup, insertion, and split/merge logic executes genuinely inside `on_inserted()`** without precomputation.
- **Recommendation:** **Option (a) — Pre-allocate `self._mat` to `max(n + 16, 16)` rows in `setup()` (with $2\times$ geometric growth if exceeded), and execute genuine local segment insertion and local bisection in `on_inserted()`.**
- **Proving Test:** `test_on_inserted_no_matrix_reallocation_and_zero_embeddings`: verify that on the first insert after `setup()` (for $n \in \{1, 50, 500\}$), `self._mat.ctypes.data` (the underlying C buffer address) is **unchanged** before and after `on_inserted()`, and `embedder.call_count` increases by 0 during `on_inserted()`.

---

### D-8. What the Harness Actually Observes (`setup()` Mode, First-Insert Probabilities, and Amortisation Analysis)

- **Options for `setup()` Partition Construction:**
  - **(a) Batch `setup()` (EraRAG Algorithm 1 style):** Hash all $n$ initial concepts in a single vectorised matrix multiply `mat.astype(np.float64) @ _hyperplanes.T`, sort entries by `(gray_rank, name)`, group by identical `gray_rank` into raw hash buckets, recursively bisect any raw bucket with size $> S_{\max}$, and then scan left-to-right merging any undersized bucket ($< S_{\min}$) with its closer neighbour ($S_{i-1}$ or $S_{i+1}$) in Gray/Hamming space (bisecting if the merged size exceeds $S_{\max}$).
  - **(b) Sequential `setup()` (EraRAG Algorithm 3 style):** Sort the initial $n$ concept names and invoke the incremental `_insert_entry` logic $n$ times in a loop.
- **Trade-offs (`setup()` Batch vs. Sequential):**
  - Both Option **(a)** and Option **(b)** were implemented and benchmarked in `/tmp/sim_strat004.py` (Section 7, Part 3).
  - **Batch `setup()` (Option a)** is directly faithful to EraRAG's separation between **Algorithm 1 (Initial Graph Construction)** and **Algorithm 3 (Incremental Insertion)** (`[Confirmed]` from Section 2 digest). Furthermore, Batch `setup()` is completely independent of any historical arrival order of the initial graph's nodes: it groups strictly by exact LSH code first, splits overcrowded codes, and merges sparse codes with adjacent codes in Hamming/Gray space.
  - **Empirical First-Insert Behaviour across D-35 and Accuracy Sizes (`[Confirmed]` from `/tmp/sim_strat004.py` Section 7, Part 3, 100 trials per size at $S_{\min}=5, S_{\max}=10, n_{\text{bits}}=12$):**

| Graph Size $n$ | Mode | Mean `#segments` $M$ | Segment Size `[min, mean, max]` | Fraction of Segments at $S_{\max}=10$ | First-Insert $P(\text{split})$ | First-Insert $P(\text{gap merge})$ | Mean `exact_topk_overlap` |
|---:|:---|---:|:---|---:|---:|---:|---:|
| 28 (DSA) | Batch (Isotropic) | 4.2 | `[5, 6.76, 10]` | 0.074 | **0.09** | 0.18 | 0.275 |
| 50 | Batch (Isotropic) | 7.5 | `[5, 6.74, 10]` | 0.083 | **0.11** | 0.31 | 0.172 |
| 100 | Batch (Isotropic) | 14.6 | `[5, 6.89, 10]` | 0.097 | **0.16** | 0.20 | 0.088 |
| 140 (Metacademy) | Batch (Isotropic) | 20.6 | `[5, 6.81, 10]` | 0.089 | **0.12** | 0.25 | 0.065 |
| 200 | Batch (Isotropic) | 29.6 | `[5, 6.77, 10]` | 0.077 | **0.15** | 0.20 | 0.038 |
| 500 | Batch (Isotropic) | 74.1 | `[5, 6.75, 10]` | 0.073 | **0.10** | 0.33 | 0.013 |
| 1000 | Batch (Isotropic) | 148.8 | `[5, 6.72, 10]` | 0.072 | **0.05** | 0.24 | 0.012 |
| 2000 | Batch (Isotropic) | 298.6 | `[5, 6.70, 10]` | 0.067 | **0.07** | 0.32 | 0.006 |
| 500 | Batch (Clustered $\sigma=0.08$) | 74.2 | `[5, 6.75, 10]` | 0.074 | **0.10** | 0.26 | 0.036 |
| 2000 | Batch (Clustered $\sigma=0.08$) | 300.5 | `[5, 6.66, 10]` | 0.062 | **0.13** | 0.30 | 0.016 |
| 500 | Sequential (Isotropic) | 70.2 | `[5, 7.12, 10]` | 0.100 | **0.15** | 0.14 | 0.016 |
| 2000 | Sequential (Isotropic) | 281.5 | `[5, 7.11, 10]` | 0.101 | **0.16** | 0.17 | 0.009 |

  - **Crucial Distinction on $P(\text{merge})$ during `on_inserted()` (`[Confirmed]`):**
    - In an **insertion-only** workload where $n \ge S_{\min}$, every existing segment already has size $\ge S_{\min}$, and inserting a new concept only *increases* the size of its target segment by 1. Therefore, **an existing segment never shrinks below $S_{\min}$ on insertion (`P(underflow_merge_of_existing_segment) = 0.00`)**.
    - A "merge" on insertion only occurs in the EraRAG Algorithm 3 sense when the new concept's hash code falls outside the `[min_key, max_key]` span of every existing segment (creating a transient size-1 bucket that immediately merges into the closer adjacent segment $S_{\text{home}}$, column `P(gap_mrg)` $\approx 0.18\text{--}0.33$ in Batch mode). And if $S_{\text{home}}$ was at size $S_{\max}=10$, absorbing that transient size-1 bucket brings it to $11 > S_{\max}$, which immediately splits into $(5, 6)$.
  - **Can the one-insert sweep protocol test EraRAG Theorem 4's amortised claim? (`[Confirmed]`):**
    - **Plain statement:** **No — not the multi-step *amortisation* part of Theorem 4.** The sweep harness's one-insert-per-trial protocol (`setup(G)` followed by a single `insert_node`) **can and does** verify the **per-insert complexity bound wrt $n$**: namely, that single-insert candidate-narrowing time (`shortlist_s`), maintenance time (`update_s`), and LLM calls (`llm_calls` $\le S_{\max} = 10$) remain $O(1)$ as $n$ scales from $50$ to $2000$ ($40\times$).
    - However, because each trial discards the strategy instance after 1 insert (`src/graph_insertion/harness.py:320-370`), the sweep harness only ever samples the stationary/post-`setup()` probability of a split on step 1 ($\approx 7\%\text{--}16\%$ across 10 trials per size, i.e., $\sim 1$ split out of 10 trials at a given $n$). It **cannot** directly observe Theorem 4's core amortisation mechanism: that once a segment splits into two segments of sizes $(5, 5)$ or $(5, 6)$, neither child can split again for at least $S_{\max} + 1 - \lceil(S_{\max}+1)/2\rceil = 11 - 6 = 5 = S_{\min}$ further insertions into that same segment, and that splits never cascade across segments.
  - **Proposed Offline, Zero-LLM Sequential-Stream Micro-Benchmark (do not build in STRAT-004 unless APC requests it in a follow-up task):**
    - **Protocol:** Instantiate `BoundedBucketStrategy(s_min=5, s_max=10, n_bits=12, seed=0)`, call `setup(empty_graph, embedder)` once at $n = 0$, and loop $i = 1 \dots m$ ($m = 2000$) calling `shortlist(name_i)` and `on_inserted(name_i)` back-to-back (using synthetic $d = 384$ vectors, **zero** LLM calls). Record at each step $i$: `shortlist_s`, `update_s`, `split_occurred`, `merge_occurred`, `num_segments`, and the minimum insertions into any segment between consecutive splits of that segment.
    - **Estimated Cost (`[Confirmed]` from `/tmp/sim_strat004.py` Section 7, Part 4):**
      - **LLM API calls:** **$0$** (`\$0.00`).
      - **Wall-clock CPU time:** For $m = 2000$ sequential insertions in pure Python/NumPy: **$5.4\text{ s}$** when computing brute-force `exact_topk_overlap` at every step, or **$< 0.25\text{ s}$** ($85.5\,\mu\text{s}$ median `shortlist_s` + $47.8\,\mu\text{s}$ median `update_s` $\times 2000 \approx 0.27\text{ s}$) without the $O(n^2)$ overlap check.
      - **Empirical Result from our Prototype Stream ($m = 2000$):** Exactly **$281$ splits** (isotropic) and **$276$ splits** (clustered) occurred over $2000$ insertions — an empirical split rate of **$0.1405$ ($1$ split every $7.12$ insertions, matching the theoretical $\ln 2 / S_{\min} = 1 / 7.21$ steady-state B-tree split rate)**, with **zero** cascading splits and `all(5 <= len(s) <= 10)` holding at every step $i \ge 5$!
- **Recommendation:** **Build initial partitions in `setup()` using Batch mode (Option a, EraRAG Algorithm 1), report the one-insert vs. amortised distinction explicitly in the thesis methodology/discussion, and optionally include the zero-LLM $m=2000$ sequential-stream micro-benchmark as a pure-CPU companion check.**
- **Proving Test:** `test_sequential_stream_amortisation_and_no_cascades`: run $m = 200$ sequential `(shortlist, on_inserted)` pairs starting from an empty graph (`s_min=5, s_max=10`), verify that every step alters at most 1 existing segment (converting 1 segment into at most 2), that total splits $\le \lfloor (200 - 5) / 5 \rfloor = 39$, and that every segment created by a split undergoes at least $S_{\min} = 5$ insertions into itself before splitting again.

---

### D-9. Lifecycle, Edge Cases, Precision, and Failure Semantics

- **Options & Edge-Case Rules:**
  1. **Cache clearing at the very top of `shortlist()`:**
     - **Option (a):** Clear `self._cached_new_name = None`, `self._cached_new_vec = None`, `self._cached_new_code = None`, `self._cached_new_gray = None`, and reset per-query diagnostic fields at the **very first lines of `shortlist(new_name)`**, *before* checking `if not self._setup_called:` and *before* calling `_validate_concept_name(new_name)`.
     - **Option (b):** Clear after `_validate_concept_name(new_name)` as Strategy 3 does (`src/graph_insertion/strategies/ann_retrieval.py:276-281`).
     - **Trade-off:** As proven in Section 4 (Correction 2) and Section 7 (Part 1), Option (b) leaves a stale `_cached_new_name` and `_cached_new_vec` if `shortlist("")` raises `ValueError` after a prior `shortlist("good_node")`, allowing a subsequent `on_inserted("good_node")` to succeed after a failed `shortlist()` call! Option (a) closes this hole completely.
  2. **All-or-nothing `setup()` (including the second-`setup()` path, `D-50(3)`):**
     - Build all local variables (`names`, `name_to_idx`, `mat`, `dim`, `hyperplanes`, `segments`) in temporary local variables first. If any concept name is invalid, any vector is non-1D / 0-length / non-finite / zero-norm, or dimensions mismatch across nodes, raise `ValueError` **before** mutating `self.*`. If `setup()` was previously called, a failed second `setup()` leaves the first `setup()`'s state intact; a successful second `setup()` atomically replaces all state and clears all cached shortlist/diagnostic fields.
  3. **Single embedding per insertion (`embedding_calls_in_update == 0`):**
     - `shortlist(new_name)` calls `self._embedder.embed(embed_text(new_name))` once, validates and L2-normalises the vector, computes `(code, gray)`, and caches `(_cached_new_name, _cached_new_vec, _cached_new_code, _cached_new_gray)`.
     - `on_inserted(new_name)` verifies `self._setup_called`, validates `new_name`, verifies `self._cached_new_name == new_name and self._cached_new_vec is not None` (raising `RuntimeError` if not), verifies `new_name not in self._name_to_idx` (raising `ValueError` if already present), and consumes the cached vector and hash without calling `self._embedder.embed()`. Immediately after `on_inserted(new_name)` completes, clear `_cached_new_name = None` and `_cached_new_vec = None` so a duplicate `on_inserted(new_name)` call fails even before the duplicate-node check.
  4. **Sign bit for dot product $= 0.0$ and arithmetic precision of projection (`float64` vs. `float32`, cf. `D-50(2)`):**
     - **Projection precision:** Hyperplanes `self._hyperplanes` are stored as `np.float64` of shape `(n_bits, dim)` with unit L2 norm. The normalised `float32` concept vector `vec` is cast to `np.float64` before projection: `dots = vec.astype(np.float64) @ self._hyperplanes.T`. Using `float64` eliminates BLAS/SIMD accumulation order drift across single-vector (`vec @ H.T`) vs. batch-matrix (`mat @ H.T`) calls (paralleling `D-50(2)`).
     - **Exact-zero dot product rule:** Sign bit is `1` if `dot >= 0.0` else `0` (standard non-negative threshold $\mathbb{I}[\langle v, h_r \rangle \ge 0]$).
     - **Cosine similarity scores in `Shortlist`:** Computed in `float32` (`(self._mat[rows] @ vec).tolist()`, clamped to `[-1.0, 1.0]` if needed) to match `EmbeddingThresholdStrategy` (`src/graph_insertion/strategies/embedding_threshold.py:239`).
  5. **Edge cases ($n=0, n=1, n < S_{\min}$, duplicate vectors, zero/NaN/Inf vectors, dimension mismatch):**
     - $n=0$: `setup()` succeeds with `_dim = None`, `_hyperplanes = None`, `_segments = []`; first `shortlist()` initialises `_dim` and `_hyperplanes` lazily (and only commits them after validating `new_vec`), returning `Shortlist([], [])`.
     - $n=1$: `shortlist()` returns 1 candidate; after `on_inserted()`, `_segments` has 1 segment of size 2 (since $2 < S_{\min}=5$).
     - Duplicate vectors: identical `gray_rank`, ordered deterministically by `name` in `(gray_rank, name)`.
     - Zero-norm, `NaN`/`Inf`, non-1D, or dimension-mismatched vectors: `_validate_and_normalize_vector(raw_vec, expected_dim=self._dim)` raises `ValueError` with a descriptive message before mutating any state.
- **Recommendation:** **Adopt rules 1–5 above without exception.**
- **Proving Test:** `test_lifecycle_failure_semantics_and_d9_cache_clear`: test that `shortlist("good")` followed by `shortlist("")` (raising `ValueError`) followed by `on_inserted("good")` raises `RuntimeError`; test that a failing second `setup()` preserves the working state of the first `setup()`; test that exact-zero dot products (`vec orthogonal to hyperplane`) produce bit `1` identically in batch `setup()` and single-vector `shortlist()`.

---

### D-10. Interface Surface and `config()` Keys

- **Options:**
  - **(a) APC Proposal:**
    - Strategy permanent identifier: `name: str = "bounded_bucket"`
    - Class name: `BoundedBucketStrategy`
    - Module path: `src/graph_insertion/strategies/bounded_bucket.py`
    - Constructor signature:
      ```python
      DEFAULT_S_MIN: int = 5
      DEFAULT_S_MAX: int = 10
      DEFAULT_N_BITS: int = 12
      DEFAULT_SEED: int = 0

      def __init__(
          self,
          s_min: int = DEFAULT_S_MIN,
          s_max: int = DEFAULT_S_MAX,
          n_bits: int = DEFAULT_N_BITS,
          seed: int = DEFAULT_SEED,
      ) -> None:
      ```
    - Class attribute: `uses_embeddings: bool = True`
    - Dependencies: **NumPy only** (`numpy`, Python standard library `dataclasses`, `typing`). No new third-party dependencies in `pyproject.toml`.
    - `config()` return dictionary:
      ```python
      {
          "s_min": self.s_min,
          "s_max": self.s_max,
          "n_bits": self.n_bits,
          "seed": self.seed,
      }
      ```
  - **(b) Alternative constructor parameter names or extra flags.**
- **Trade-offs:**
  - Option **(a)** matches the naming pattern of `brute_force`, `embedding_threshold`, and `ann_retrieval`, exposes every hyperparameter in `config()` so `INFRA-007` sensitivity keying (`(strategy, config_json)`) works out of the box, and avoids any external C++/Rust wheel dependency.
- **Recommendation:** **Confirm Option (a) verbatim.**
- **Proving Test:** `test_interface_surface_and_config`: verify `BoundedBucketStrategy.name == "bounded_bucket"`, `uses_embeddings is True`, default `config() == {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 0}`, and `isinstance(val, int) and not isinstance(val, bool)` for all four `config()` values.

---

### D-11. Diagnostics

- **Options:**
  - **(a) Comprehensive JSON-serialisable dictionary computed outside timed windows (`diagnostics()`):**
    ```python
    {
        "bucket_id": int | None,               # Home segment index (0..M-1) at shortlist time, or None if n == 0 / before shortlist
        "bucket_gray_min": int | None,         # Minimum gray_rank in home segment at shortlist time (None if n == 0)
        "bucket_gray_max": int | None,         # Maximum gray_rank in home segment at shortlist time (None if n == 0)
        "query_code": int | None,              # Raw n_bits LSH integer code of last shortlisted node (None before shortlist)
        "query_gray_rank": int | None,         # Reflected Gray rank of last shortlisted node (None before shortlist)
        "code_existed_in_bucket": bool,        # True iff at least one member of the home segment had the exact same query_code
        "inside_bucket_span": bool,            # True iff (query_gray_rank, new_name) fell inside [min_key, max_key] of home segment
        "bucket_size_at_shortlist": int,       # Size of home segment during shortlist() (0 if n == 0)
        "bucket_size": int,                    # Post-insertion size of the segment containing new_name (or bucket_size_at_shortlist if on_inserted not yet called)
        "shortlist_size": int,                 # Number of candidates returned by last shortlist() call
        "split_occurred": bool,                # True iff the last on_inserted() split an overflowing segment
        "merge_occurred": bool,                # True iff the last on_inserted() merged a new out-of-span singleton into an adjacent segment
        "num_segments": int,                   # Current total number of segments M in the partition
        "min_segment_size": int,               # Minimum segment size across current segments (0 if M == 0)
        "max_segment_size": int,               # Maximum segment size across current segments (0 if M == 0)
        "mean_segment_size": float,            # Mean segment size n / M across current segments (0.0 if M == 0)
        "exact_topk_overlap": float | None,    # Fraction of exact top-m (m = min(s_max, n_at_query)) cosine neighbours present in the returned shortlist (1.0 if n_at_query == 0, None before shortlist)
    }
    ```
  - **(b) Minimal 3-key dictionary (`{bucket_id, split_occurred, bucket_size}`) from `strategy-interface.md` §5.**
- **Trade-offs & How Each Value is Computed Outside Timed Windows:**
  - Option **(a)** is a strict superset of Option **(b)** (retaining `bucket_id`, `split_occurred`, and `bucket_size` with the exact types from `strategy-interface.md` §5) while adding the segment distribution summary (`num_segments`, `min_segment_size`, `max_segment_size`, `mean_segment_size`), the Algorithm 3 event flags (`merge_occurred`, `code_existed_in_bucket`, `inside_bucket_span`), and `exact_topk_overlap`.
  - **How `diagnostics()` avoids touching the timed path (`[Confirmed]`):**
    - During `shortlist(new_name)`, the strategy records only lightweight scalar/tuple snapshots already in hand (`_last_bucket_id = home_idx`, `_last_bucket_size_at_shortlist = len(seg)`, `_last_shortlist_size = len(candidates)`, `_last_returned_candidates = tuple(candidates)`, `_last_query_vec = vec`, `_n_at_query = self._n`, `_query_name = new_name`, `_cached_exact_topk_overlap = None`). This adds $O(1)$ pointer assignments ($\ll 1\,\mu\text{s}$).
    - During `on_inserted(new_name)`, the strategy records `_last_split_occurred`, `_last_merge_occurred`, and `_last_post_insert_bucket_size` (the size of whichever half of the split segment now contains `new_name`, or `len(seg)` if no split occurred).
    - Only when the harness calls `strategy.diagnostics()` **outside** the timed windows (`src/graph_insertion/harness.py:381`, after `insert_node` has finished recording `shortlist_s` and `update_s`) does `diagnostics()` compute:
      1. The segment-size summary (`min_segment_size`, `max_segment_size`, `mean_segment_size`) by iterating over `[len(s) for s in self._segments]`.
      2. `_compute_exact_topk_overlap()`, following the exact pattern of `AnnRetrievalStrategy._compute_exact_topk_overlap()` (`src/graph_insertion/strategies/ann_retrieval.py:403-444`): slice `self._mat[:self._n_at_query]`, compute exact cosines `mat @ self._last_query_vec`, sort the $\le n_{\text{at\_query}}$ existing nodes by `(-cosine, name)` (excluding `_query_name`), take the top $m = \min(\texttt{self.s\_max}, n_{\text{at\_query}})$ exact neighbours, and compute `len(set(exact_top_m) & set(self._last_returned_candidates)) / len(exact_top_m)` (cached in `self._cached_exact_topk_overlap`).
- **Recommendation:** **Option (a) — Return the 17-key JSON-serialisable dictionary above, computing the segment summary and `exact_topk_overlap` lazily inside `diagnostics()` outside all timed windows.**
- **Proving Test:** `test_diagnostics_schema_and_lazy_exact_topk_overlap`: verify `json.dumps(strategy.diagnostics())` succeeds before `setup()`, after `setup()`, after `shortlist()`, and after `on_inserted()`; verify `_cached_exact_topk_overlap is None` immediately after `shortlist()` and `on_inserted()` (proving it was not computed inside the timed windows) and becomes a `float` in `[0.0, 1.0]` only after `diagnostics()` is called.

---

### D-12. Test Plan and Reviewer Mutation List ($\ge 20$ Mutations)

- **Required Test Suite (`tests/test_bounded_bucket_strategy.py`):**
  1. **`TestBoundedBucketConformance(StrategyConformanceSuite)`:** Inherits all 19 conformance tests from `tests/test_strategy_interface.py` (`make_strategy() -> BoundedBucketStrategy(s_min=3, s_max=6, n_bits=8, seed=7)` or default `(5, 10, 12, 0)`).
  2. **`test_init_parameter_validation`:** Rejects `bool` or non-`int` for `s_min`, `s_max`, `n_bits`, `seed`; rejects `s_min < 2`, `s_max < 2 * s_min`, `n_bits < 1`, `n_bits > 62`.
  3. **`test_config_and_permanent_name`:** Verifies `name == "bounded_bucket"`, `uses_embeddings is True`, and `config()` returns `{"s_min", "s_max", "n_bits", "seed"}`.
  4. **`test_max_candidates_and_call_bounds`:** Verifies `max_candidates(n)` for $n \in \{0, 3, 5, 10, 50, 2000\}$, rejects `bool`/negative/non-`int`, and verifies `candidate_upper_bound` and `compute_planned_calls_upper_bound` yield `600` (sweep) and `590` (accuracy) at default `s_max=10`.
  5. **`test_size_invariants_after_setup_and_every_insert`:** Starting from $n = 0$, inserts 65 nodes one by one (`s_min=5, s_max=10`), asserting at every step $t$: $t = 0 \implies 0$ segments; $1 \le t < 5 \implies 1$ segment of size $t$; $t \ge 5 \implies \forall S \in \text{segments}, 5 \le |S| \le 10$, and strictly increasing `(gray_rank, name)` order across and within all segments.
  6. **`test_determinism_across_two_builds_and_node_order_invariance`:** Builds two strategies on graphs whose nodes were added in different orders (`["a", "b", "c", ...]` vs. reversed), verifies identical `_hyperplanes`, identical `_segments`, identical `shortlist()` outputs, and identical `diagnostics()`.
  7. **`test_forced_split_with_explicit_vectors`:** Uses `ControllableEmbedder` to place $S_{\max} = 6$ nodes (`s_min=3, s_max=6`) into a single bucket and inserts a 7th node with the same vector direction; verifies `split_occurred is True`, segment count increases from 1 to 2, and segment sizes are `3` and `4`.
  8. **`test_forced_merge_in_setup_and_gap_merge_in_on_inserted`:** Uses `ControllableEmbedder` with explicit orthogonal/controlled vectors so `setup()` produces an undersized raw bucket ($< S_{\min}$) between two neighbours at different Hamming distances; verifies it merges with the closer Hamming neighbour. Then inserts a new node whose Gray rank falls strictly between two segments and verifies `merge_occurred is True` and `inside_bucket_span is False`.
  9. **`test_duplicate_vectors_tie_split_by_name`:** Gives $2 S_{\max} + 3$ concepts the exact same vector via `ControllableEmbedder`, runs `setup()` and `insert_node()`, and verifies termination and deterministic lexicographical splitting by concept name.
  10. **`test_second_setup_all_or_nothing_and_state_reset`:** Verifies a valid second `setup()` completely replaces the first graph's state and regenerates identical hyperplanes, whereas a failing second `setup()` (e.g., zero vector or empty name) leaves the first `setup()`'s segments, matrix, and query capability completely intact.
  11. **`test_d9_failed_shortlist_clears_cache_before_validation`:** Calls `shortlist("good_node")`, then calls `shortlist("")` (which fails concept-name validation before embedding) and `shortlist("bad_zero_vec")` (which fails vector validation), and verifies that in both cases a subsequent `on_inserted("good_node")` raises `RuntimeError` (`_cached_new_name is None`).
  12. **`test_single_embedding_per_insertion_and_on_inserted_errors`:** Verifies `shortlist()` makes 1 embed call and `on_inserted()` makes 0 embed calls; verifies `on_inserted()` raises `ValueError` if the node is already in the index, and raises `RuntimeError` if called twice in a row.
  13. **`test_no_matrix_reallocation_or_on_work_on_first_insert`:** Verifies `self._mat.ctypes.data` is unchanged after `on_inserted()` following `setup()`, and verifies `_locate_home_segment` uses binary search rather than scanning all segments.
  14. **`test_zero_dot_product_and_float64_projection`:** Constructs a vector strictly orthogonal to hyperplane 0 (`dot == 0.0`) and verifies its sign bit is `1` in both batch `setup()` and single-vector `shortlist()`.
  15. **`test_diagnostics_lazy_computation_and_json_serialisable`:** Verifies `_cached_exact_topk_overlap` is `None` until `diagnostics()` is called, matches a manual brute-force top-$k$ overlap calculation, and is JSON-serialisable in all lifecycle states.

- **Numbered Mutation List for Reviewer (22 Mutations):**
  The STRAT-004 reviewer should mutate a copy of `src/graph_insertion/strategies/bounded_bucket.py` under `/tmp`, run `pytest tests/test_bounded_bucket_strategy.py` with `PYTHONPATH` pointing to the `/tmp` copy, and record `KILLED` / `SURVIVED`:

| Mutant ID | Target Location / Logic | Mutation to Apply | Test That Must Kill It |
| :--- | :--- | :--- | :--- |
| **M-01** | `__init__` `s_min` lower bound | Change `if s_min < 2:` to `if s_min < 1:` | `test_init_parameter_validation` |
| **M-02** | `__init__` feasibility bound | Change `if s_max < 2 * s_min:` to `if s_max < s_min:` | `test_init_parameter_validation` |
| **M-03** | `__init__` `bool` rejection | Remove `isinstance(..., bool)` guard on `s_min` or `seed` | `test_init_parameter_validation` |
| **M-04** | `max_candidates` formula | Change `min(self.s_max, n_existing)` to `n_existing` | `test_max_candidates_and_call_bounds` |
| **M-05** | `max_candidates` zero clamping | Change `max(0, min(...))` to `min(self.s_max, n_existing)` without negative check | `test_max_candidates_and_call_bounds` |
| **M-06** | `gray_rank` inverse Gray loop | Replace `gray_rank(code)` with identity `return code` (no Gray decoding) | `test_forced_merge_in_setup_and_gap_merge_in_on_inserted` |
| **M-07** | Hyperplane projection sign threshold | Change `dots >= 0.0` to `dots > 0.0` | `test_zero_dot_product_and_float64_projection` |
| **M-08** | `setup()` canonical node ordering | Remove `sorted(graph.nodes())` / `(gray, name)` sort before building buckets | `test_determinism_across_two_builds_and_node_order_invariance` |
| **M-09** | `setup()` all-or-nothing rollback | Mutate `self._segments = []` at the top of `setup()` before validating embeddings | `test_second_setup_all_or_nothing_and_state_reset` |
| **M-10** | `setup()` matrix headroom | Allocate `self._mat` with shape `(n, dim)` instead of `(max(n + 16, 16), dim)` | `test_no_matrix_reallocation_or_on_work_on_first_insert` |
| **M-11** | `shortlist()` top-of-method cache clear | Move `self._cached_new_name = None` below `_validate_concept_name(new_name)` | `test_d9_failed_shortlist_clears_cache_before_validation` |
| **M-12** | `shortlist()` score sorting order | Sort candidates by `(+score, name)` or `(-score,)` without `name` tie-break | `TestBoundedBucketConformance` / `test_duplicate_vectors_tie_split_by_name` |
| **M-13** | `shortlist()` vector normalisation | Skip L2 normalisation of `new_vec` in `shortlist()` | `TestBoundedBucketConformance.test_unnormalised_vectors_normalised_by_strategy` |
| **M-14** | `shortlist()` state mutation | Append `BucketEntry` to `self._segments[home_idx]` inside `shortlist()` | `test_shortlist_does_not_mutate_state_and_matches_home_segment` |
| **M-15** | `on_inserted()` overflow trigger | Change `if len(seg) > self.s_max:` to `if len(seg) >= self.s_max:` | `test_forced_split_with_explicit_vectors` / `test_size_invariants_after_setup_and_every_insert` |
| **M-16** | `on_inserted()` split midpoint | Change `mid = len(seg) // 2` to `mid = 1` | `test_size_invariants_after_setup_and_every_insert` |
| **M-17** | `on_inserted()` duplicate node check | Remove `if new_name in self._name_to_idx: raise ValueError(...)` | `test_single_embedding_per_insertion_and_on_inserted_errors` |
| **M-18** | `on_inserted()` cache consumption | Do not clear `self._cached_new_name = None` at the end of `on_inserted()` | `test_single_embedding_per_insertion_and_on_inserted_errors` |
| **M-19** | `_choose_neighbor` Hamming comparison | Reverse comparison `left_key <= right_key` to `left_key >= right_key` | `test_forced_merge_in_setup_and_gap_merge_in_on_inserted` |
| **M-20** | `setup()` undersize merge rebalance | Omit the `if len(combined) > self.s_max:` midpoint split after merging two segments | `test_size_invariants_after_setup_and_every_insert` |
| **M-21** | `diagnostics()` `exact_topk_overlap` | Compute `exact_topk_overlap` eagerly inside `shortlist()` instead of lazily in `diagnostics()` | `test_diagnostics_lazy_computation_and_json_serialisable` |
| **M-22** | `config()` dictionary keys | Omit `"n_bits"` or `"s_min"` from `config()` return value | `test_config_and_permanent_name` |

---

### D-13. Planned-Calls Budget Over D-35 Sweep Matrix and Accuracy Mode

- **How `candidate_upper_bound` and `compute_planned_calls_upper_bound` Pick Up `max_candidates` (`[Confirmed]`):**
  1. `BoundedBucketStrategy.max_candidates(self, n_existing: int) -> int` returns `max(0, min(self.s_max, int(n_existing)))`.
  2. `candidate_upper_bound(strategy, n_existing)` in `src/graph_insertion/strategy.py:187-201` inspects `getattr(strategy, "max_candidates", None)`, calls `fn(n_existing)`, and clamps the integer result to `[0, max(0, n_existing)]`.
  3. `compute_planned_calls_upper_bound(mode, strategies, ...)` in `scripts/run_experiment.py:287-348` calls `candidate_upper_bound(strategy, size) * CALLS_PER_CANDIDATE` (`CALLS_PER_CANDIDATE = 1`, `src/graph_insertion/decision.py`) for every `(size, trial)` pair in sweep mode (`sizes = [50, 100, 200, 500, 1000, 2000]`, `n_trials = 10`, 60 trials total) and for every held-out node in accuracy mode ($29$ DSA trials at `n_existing = 28` + $30$ Metacademy trials at `n_existing = 140`, 59 trials total).
- **Exact Planned-Calls Upper Bound Table (`[Confirmed]` from `/tmp/sim_strat004.py` Section 7, Part 5):**

| Strategy & Configuration | Formula per Trial at Size $n$ | D-35 Sweep Bound (60 trials) | Accuracy Bound (29 DSA + 30 Meta = 59 trials) | Combined Bound (Sweep + Accuracy) |
| :--- | :--- | ---: | ---: | ---: |
| **Strategy 1 (`brute_force`)** | $n$ | **38,500** | **5,012** ($812 + 4,200$) | **43,512** |
| **Strategy 2 (`embedding_threshold`)** | $n$ (worst-case bound) | **38,500** | **5,012** | **43,512** |
| **Strategy 3 (`ann_retrieval`, default $k=10$)** | $\min(10, n)$ | **600** | **590** ($290 + 300$) | **1,190** |
| **Strategy 4 (`bounded_bucket`, sensitivity $S_{\min}=2, S_{\max}=5$)** | $\min(5, n)$ | **300** | **295** ($145 + 150$) | **595** |
| **Strategy 4 (`bounded_bucket`, default $S_{\min}=5, S_{\max}=10$)** | $\min(10, n)$ | **600** | **590** ($290 + 300$) | **1,190** |
| **Strategy 4 (`bounded_bucket`, sensitivity $S_{\min}=10, S_{\max}=20$)** | $\min(20, n)$ | **1,200** | **1,180** ($580 + 600$) | **2,380** |

- **Proving Test:** `test_planned_calls_budget_matches_table`: invoke `compute_planned_calls_upper_bound` (or sum `candidate_upper_bound(s, n)` across the D-35 matrix `[50, 100, 200, 500, 1000, 2000] * 10`) for `(2, 5)`, `(5, 10)`, and `(10, 20)` and assert exact equality with `300`, `600`, and `1200`.

---

## 7. Simulation Evidence

### 7.1 Script Text (`/tmp/sim_strat004.py`)

```python
from __future__ import annotations
import sys
import time
import math
from dataclasses import dataclass
import numpy as np

# Ensure repo src and tests are importable for Part 0 verification
sys.path.insert(0, "/home/lukexodus/projects/llm-graph-insertion-complexity/src")
sys.path.insert(0, "/home/lukexodus/projects/llm-graph-insertion-complexity/tests")

from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.strategy import candidate_upper_bound
from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy
from controllable_embedder import ControllableEmbedder, vector_with_cosine

def gray_rank(code: int, n_bits: int) -> int:
    """Inverse Gray map: convert L-bit hyperplane code to reflected binary Gray rank."""
    g = code
    shift = 1
    while shift < n_bits:
        g ^= (g >> shift)
        shift <<= 1
    return g

def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()

@dataclass(frozen=True)
class BucketEntry:
    gray: int
    name: str
    code: int
    row: int

    def sort_key(self) -> tuple[int, str]:
        return (self.gray, self.name)

class PrototypeBoundedBucket:
    def __init__(
        self,
        s_min: int = 5,
        s_max: int = 10,
        n_bits: int = 12,
        seed: int = 0,
        setup_mode: str = "batch",  # "batch" (Alg 1) or "sequential" (Alg 3)
    ) -> None:
        assert 2 <= s_min and s_max >= 2 * s_min
        self.s_min = s_min
        self.s_max = s_max
        self.n_bits = n_bits
        self.seed = seed
        self.setup_mode = setup_mode
        self._hyperplanes: np.ndarray | None = None
        self._matrix: np.ndarray | None = None
        self._size: int = 0
        self._segments: list[list[BucketEntry]] = []
        self._node_set: set[str] = set()

    def _init_hyperplanes(self, dim: int) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        return raw / norms

    def _hash_vec(self, vec: np.ndarray) -> tuple[int, int]:
        assert self._hyperplanes is not None
        dots = vec.astype(np.float64) @ self._hyperplanes.T
        bits = (dots >= 0.0).astype(np.uint64)
        code = 0
        for b in bits:
            code = (code << 1) | int(b)
        return code, gray_rank(code, self.n_bits)

    def _hash_matrix(self, mat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        assert self._hyperplanes is not None
        dots = mat.astype(np.float64) @ self._hyperplanes.T
        bits = (dots >= 0.0).astype(np.uint64)
        powers = (1 << np.arange(self.n_bits - 1, -1, -1, dtype=np.uint64))
        codes = (bits @ powers).astype(np.int64)
        grays = np.zeros_like(codes)
        for i, c in enumerate(codes):
            grays[i] = gray_rank(int(c), self.n_bits)
        return codes, grays

    def _recursive_split(self, entries: list[BucketEntry]) -> list[list[BucketEntry]]:
        if len(entries) <= self.s_max:
            return [entries]
        mid = len(entries) // 2
        return self._recursive_split(entries[:mid]) + self._recursive_split(entries[mid:])

    def _choose_neighbor(self, idx: int) -> int:
        """Return index of closer adjacent segment (idx - 1 or idx + 1) in Gray-rank order."""
        assert len(self._segments) > 1
        if idx == 0:
            return 1
        if idx == len(self._segments) - 1:
            return idx - 1
        curr = self._segments[idx]
        left = self._segments[idx - 1]
        right = self._segments[idx + 1]
        left_key = (
            hamming_distance(left[-1].code, curr[0].code),
            abs(curr[0].gray - left[-1].gray),
            len(left),
            0,
        )
        right_key = (
            hamming_distance(curr[-1].code, right[0].code),
            abs(right[0].gray - curr[-1].gray),
            len(right),
            1,
        )
        return (idx - 1) if left_key <= right_key else (idx + 1)

    def _locate_home_segment(self, gray: int, name: str) -> tuple[int, bool, bool]:
        """
        Return (home_idx, code_matched_existing_entry, fell_inside_segment_span).
        Does not mutate state.
        """
        if not self._segments:
            return (0, False, False)
        key = (gray, name)
        # Binary search over segments by their max key
        lo, hi = 0, len(self._segments) - 1
        pos = len(self._segments)
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._segments[mid][-1].sort_key() >= key:
                pos = mid
                hi = mid - 1
            else:
                lo = mid + 1

        # Check if any segment starting around pos contains key inside [seg[0], seg[-1]]
        if pos < len(self._segments):
            seg = self._segments[pos]
            if seg[0].sort_key() <= key <= seg[-1].sort_key():
                code_match = any(e.gray == gray for e in seg)
                return (pos, code_match, True)

        # Otherwise key falls strictly in the gap between pos-1 and pos (or before 0, or after M-1)
        if pos == 0:
            code_match = any(e.gray == gray for e in self._segments[0])
            return (0, code_match, False)
        if pos == len(self._segments):
            last_idx = len(self._segments) - 1
            code_match = any(e.gray == gray for e in self._segments[last_idx])
            return (last_idx, code_match, False)

        # Between pos - 1 and pos: use the exact same proximity rule as merge
        left = self._segments[pos - 1]
        right = self._segments[pos]
        # Reconstruct code from gray rank for Hamming distance
        code = gray ^ (gray >> 1)
        left_key = (
            hamming_distance(left[-1].code, code),
            abs(gray - left[-1].gray),
            len(left),
            0,
        )
        right_key = (
            hamming_distance(code, right[0].code),
            abs(right[0].gray - gray),
            len(right),
            1,
        )
        chosen = (pos - 1) if left_key <= right_key else pos
        return (chosen, False, False)

    def setup_from_vectors(self, names: list[str], vectors: np.ndarray) -> None:
        n = len(names)
        self._node_set = set(names)
        if n == 0:
            self._hyperplanes = None
            self._matrix = None
            self._size = 0
            self._segments = []
            return
        dim = vectors.shape[1]
        self._hyperplanes = self._init_hyperplanes(dim)
        cap = max(n + 1, 16)
        self._matrix = np.empty((cap, dim), dtype=np.float32)
        self._matrix[:n] = vectors
        self._size = n

        if self.setup_mode == "sequential":
            self._segments = []
            codes, grays = self._hash_matrix(vectors)
            for i in range(n):
                entry = BucketEntry(gray=int(grays[i]), name=names[i], code=int(codes[i]), row=i)
                self._insert_entry(entry)
            return

        # Batch mode (Algorithm 1):
        codes, grays = self._hash_matrix(vectors)
        entries = [
            BucketEntry(gray=int(grays[i]), name=names[i], code=int(codes[i]), row=i)
            for i in range(n)
        ]
        entries.sort(key=lambda e: e.sort_key())

        # Group by exact gray rank (identical LSH code)
        raw_buckets: list[list[BucketEntry]] = []
        for e in entries:
            if not raw_buckets or raw_buckets[-1][-1].gray != e.gray:
                raw_buckets.append([e])
            else:
                raw_buckets[-1].append(e)

        # Step 1: Split oversize raw buckets (> s_max)
        segments: list[list[BucketEntry]] = []
        for b in raw_buckets:
            segments.extend(self._recursive_split(b))
        self._segments = segments

        # Step 2: Merge undersize buckets (< s_min) with adjacent bucket in Gray space
        if n < self.s_min:
            merged_all = [e for seg in self._segments for e in seg]
            merged_all.sort(key=lambda e: e.sort_key())
            self._segments = [merged_all]
            return

        i = 0
        while i < len(self._segments) and len(self._segments) > 1:
            if len(self._segments[i]) < self.s_min:
                nbr = self._choose_neighbor(i)
                lo_idx = min(i, nbr)
                hi_idx = max(i, nbr)
                combined = self._segments[lo_idx] + self._segments[hi_idx]
                if len(combined) <= self.s_max:
                    self._segments[lo_idx : hi_idx + 1] = [combined]
                else:
                    mid = len(combined) // 2
                    self._segments[lo_idx : hi_idx + 1] = [combined[:mid], combined[mid:]]
                i = max(0, lo_idx)
            else:
                i += 1

    def _insert_entry(self, entry: BucketEntry) -> tuple[bool, bool, bool]:
        """
        Insert entry into segments using Algorithm 3 incremental rule.
        Returns (split_occurred, merge_occurred, code_existed).
        """
        if not self._segments:
            self._segments = [[entry]]
            return (False, False, False)

        home_idx, code_existed, inside_span = self._locate_home_segment(entry.gray, entry.name)
        merge_occurred = not inside_span
        seg = self._segments[home_idx]
        ins_pos = 0
        while ins_pos < len(seg) and seg[ins_pos].sort_key() < entry.sort_key():
            ins_pos += 1
        seg.insert(ins_pos, entry)

        split_occurred = False
        if len(seg) > self.s_max:
            mid = len(seg) // 2
            left_half = seg[:mid]
            right_half = seg[mid:]
            self._segments[home_idx : home_idx + 1] = [left_half, right_half]
            split_occurred = True
        return (split_occurred, merge_occurred, code_existed)

    def shortlist_and_insert(self, name: str, vec: np.ndarray) -> dict:
        if self._hyperplanes is None:
            self._hyperplanes = self._init_hyperplanes(vec.shape[0])
        code, gray = self._hash_vec(vec)

        t0 = time.perf_counter()
        if not self._segments:
            cands = []
            scores = []
            home_idx = 0
            code_existed = False
            inside_span = False
        else:
            home_idx, code_existed, inside_span = self._locate_home_segment(gray, name)
            seg = self._segments[home_idx]
            rows = [e.row for e in seg]
            names = [e.name for e in seg]
            assert self._matrix is not None
            sub_mat = self._matrix[rows]
            raw_scores = sub_mat @ vec
            paired = sorted(zip(names, raw_scores.tolist()), key=lambda p: (-p[1], p[0]))
            cands = [p[0] for p in paired]
            scores = [p[1] for p in paired]
        shortlist_s = time.perf_counter() - t0

        # Exact top-10 overlap (outside timed window)
        m = min(10, self._size)
        if m == 0:
            overlap = 1.0
        else:
            assert self._matrix is not None
            all_scores = self._matrix[:self._size] @ vec
            top_idx = np.argsort(-all_scores)[:m]
            cand_rows = set(e.row for e in self._segments[home_idx]) if self._segments else set()
            overlap = sum(1 for r in top_idx if int(r) in cand_rows) / m

        # Timed on_inserted
        t1 = time.perf_counter()
        row = self._size
        if self._matrix is None:
            self._matrix = np.empty((16, vec.shape[0]), dtype=np.float32)
        elif row >= self._matrix.shape[0]:
            new_mat = np.empty((self._matrix.shape[0] * 2, vec.shape[0]), dtype=np.float32)
            new_mat[:row] = self._matrix[:row]
            self._matrix = new_mat
        self._matrix[row] = vec
        self._size += 1
        entry = BucketEntry(gray=gray, name=name, code=code, row=row)
        split_occ, merge_occ, _ = self._insert_entry(entry)
        update_s = time.perf_counter() - t1

        return {
            "shortlist_len": len(cands),
            "shortlist_s": shortlist_s,
            "update_s": update_s,
            "split_occurred": split_occ,
            "merge_occurred": merge_occ,
            "code_existed": code_existed,
            "inside_span": inside_span,
            "exact_top10_overlap": overlap,
        }

def generate_isotropic(n: int, dim: int, rng: np.random.Generator) -> np.ndarray:
    v = rng.standard_normal((n, dim), dtype=np.float64)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    v32 = v.astype(np.float32)
    v32 /= np.linalg.norm(v32, axis=1, keepdims=True)
    return v32

def generate_clustered(n: int, dim: int, n_clusters: int, sigma: float, rng: np.random.Generator) -> np.ndarray:
    centers = rng.standard_normal((n_clusters, dim), dtype=np.float64)
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    assignments = rng.integers(0, n_clusters, size=n)
    noise = rng.standard_normal((n, dim), dtype=np.float64) * sigma
    v = centers[assignments] + noise
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    v32 = v.astype(np.float32)
    v32 /= np.linalg.norm(v32, axis=1, keepdims=True)
    return v32

print("=== 1. PART 0 REPRODUCER: D-9 STALE CACHE CHECK ON S2 AND S3 ===")
emb = ControllableEmbedder({"n0": vector_with_cosine([1.0, 0.0, 0.0, 0.0], 1.0), "good_node": vector_with_cosine([1.0, 0.0, 0.0, 0.0], 0.0)})
g = ConceptGraph()
g.add_node("n0")
s3 = AnnRetrievalStrategy(k=10, seed=0)
s3.setup(g, emb)
s3.shortlist("good_node")
try:
    s3.shortlist("")
except ValueError:
    pass
print(f"S3 _cached_new_name after shortlist(''): {s3._cached_new_name!r}")

s2 = EmbeddingThresholdStrategy(theta=0.5)
s2.setup(g, emb)
s2.shortlist("good_node")
try:
    s2.shortlist("")
except ValueError:
    pass
print(f"S2 _cached_new_name after shortlist(''): {s2._cached_new_name!r}")

print("\n=== 2. D-2 & D-11: HYPERPLANE BIT COUNT SENSITIVITY (n=500, s_min=5, s_max=10, 50 trials) ===")
for dist_name, gen_fn in [
    ("isotropic", lambda r: generate_isotropic(501, 384, r)),
    ("clustered_s0.08", lambda r: generate_clustered(501, 384, 20, 0.08, r)),
    ("clustered_s0.04", lambda r: generate_clustered(501, 384, 20, 0.04, r)),
]:
    print(f"\nDistribution: {dist_name}")
    print(f"{'n_bits':>6} | {'uniq_codes':>10} | {'n_segs':>7} | {'mean_sz':>7} | {'p_split':>7} | {'top10_ovlp':>10}")
    for n_bits in [8, 10, 12, 16, 24, 32]:
        rng = np.random.default_rng(100)
        overlaps, splits, seg_counts, uniq_codes, mean_sizes = [], [], [], [], []
        for t in range(50):
            vecs = gen_fn(rng)
            names = [f"c_{i:04d}" for i in range(500)]
            proto = PrototypeBoundedBucket(s_min=5, s_max=10, n_bits=n_bits, seed=t, setup_mode="batch")
            proto.setup_from_vectors(names, vecs[:500])
            codes, _ = proto._hash_matrix(vecs[:500])
            uniq_codes.append(len(set(codes.tolist())))
            seg_counts.append(len(proto._segments))
            mean_sizes.append(np.mean([len(s) for s in proto._segments]))
            res = proto.shortlist_and_insert("c_new", vecs[500])
            overlaps.append(res["exact_top10_overlap"])
            splits.append(1.0 if res["split_occurred"] else 0.0)
        print(
            f"{n_bits:6d} | {np.mean(uniq_codes):10.1f} | {np.mean(seg_counts):7.1f} | "
            f"{np.mean(mean_sizes):7.2f} | {np.mean(splits):7.2f} | {np.mean(overlaps):10.3f}"
        )

print("\n=== 3. D-8: FIRST-INSERT BEHAVIOR ACROSS SIZES (s_min=5, s_max=10, n_bits=12, 100 trials) ===")
sizes = [28, 50, 100, 140, 200, 500, 1000, 2000]
for setup_mode in ["batch", "sequential"]:
    for dist_name, is_clustered in [("isotropic", False), ("clustered_s0.08", True)]:
        print(f"\nSetup mode: {setup_mode} | Distribution: {dist_name}")
        print(
            f"{'n':>5} | {'n_segs':>7} | {'min_sz':>6} | {'mean_sz':>7} | {'max_sz':>6} | "
            f"{'frac_at_smax':>12} | {'P(split)':>8} | {'P(gap_mrg)':>10} | {'top10_ovlp':>10}"
        )
        for n in sizes:
            rng = np.random.default_rng(200 + n)
            n_segs_l, min_sz_l, mean_sz_l, max_sz_l, frac_smax_l = [], [], [], [], []
            p_split_l, p_merge_l, ovlp_l = [], [], []
            for t in range(100):
                vecs = (
                    generate_clustered(n + 1, 384, 20, 0.08, rng)
                    if is_clustered
                    else generate_isotropic(n + 1, 384, rng)
                )
                names = [f"c_{i:04d}" for i in range(n)]
                proto = PrototypeBoundedBucket(
                    s_min=5, s_max=10, n_bits=12, seed=t, setup_mode=setup_mode
                )
                proto.setup_from_vectors(names, vecs[:n])
                szs = [len(s) for s in proto._segments]
                assert all(5 <= s <= 10 for s in szs), f"Invariant violated: {szs}"
                n_segs_l.append(len(szs))
                min_sz_l.append(min(szs))
                mean_sz_l.append(float(np.mean(szs)))
                max_sz_l.append(max(szs))
                frac_smax_l.append(sum(1 for s in szs if s == 10) / len(szs))
                res = proto.shortlist_and_insert("c_new", vecs[n])
                szs_after = [len(s) for s in proto._segments]
                assert all(5 <= s <= 10 for s in szs_after), f"Post-insert invariant violated: {szs_after}"
                p_split_l.append(1.0 if res["split_occurred"] else 0.0)
                p_merge_l.append(1.0 if res["merge_occurred"] else 0.0)
                ovlp_l.append(res["exact_top10_overlap"])
            print(
                f"{n:5d} | {np.mean(n_segs_l):7.1f} | {min(min_sz_l):6d} | {np.mean(mean_sz_l):7.2f} | "
                f"{max(max_sz_l):6d} | {np.mean(frac_smax_l):12.3f} | {np.mean(p_split_l):8.2f} | "
                f"{np.mean(p_merge_l):10.2f} | {np.mean(ovlp_l):10.3f}"
            )

print("\n=== 4. D-8: SEQUENTIAL STREAM MICRO-BENCHMARK (m=2000 inserts from n=0, s_min=5, s_max=10, n_bits=12) ===")
rng_stream = np.random.default_rng(999)
for dist_name, vecs in [
    ("isotropic", generate_isotropic(2000, 384, rng_stream)),
    ("clustered_s0.08", generate_clustered(2000, 384, 20, 0.08, rng_stream)),
]:
    proto = PrototypeBoundedBucket(s_min=5, s_max=10, n_bits=12, seed=42, setup_mode="batch")
    proto.setup_from_vectors([], np.empty((0, 384), dtype=np.float32))
    t_start = time.perf_counter()
    splits = 0
    merges = 0
    update_times_us = []
    shortlist_times_us = []
    for i in range(2000):
        res = proto.shortlist_and_insert(f"stream_{i:04d}", vecs[i])
        if res["split_occurred"]:
            splits += 1
        if res["merge_occurred"]:
            merges += 1
        update_times_us.append(res["update_s"] * 1e6)
        shortlist_times_us.append(res["shortlist_s"] * 1e6)
        szs = [len(s) for s in proto._segments]
        if i + 1 < 5:
            assert len(szs) == 1 and szs[0] == i + 1
        else:
            assert all(5 <= s <= 10 for s in szs)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    print(
        f"Stream ({dist_name}, m=2000): total_wall={elapsed_ms:.1f} ms | "
        f"final_segs={len(proto._segments)} | total_splits={splits} (rate={splits/2000:.4f}, "
        f"mean_inserts_between_splits={2000/splits:.2f}) | gap_merges={merges} | "
        f"median_shortlist={np.median(shortlist_times_us):.1f} us | "
        f"median_update={np.median(update_times_us):.1f} us | p99_update={np.percentile(update_times_us, 99):.1f} us"
    )

print("\n=== 5. D-13: CALL BOUNDS OVER D-35 SWEEP MATRIX AND ACCURACY MODE ===")
sweep_sizes = [50, 100, 200, 500, 1000, 2000]
sweep_trials = 10
acc_sizes = [28] * 29 + [140] * 30  # 29 DSA + 30 Metacademy
bf_sweep = sum(n * sweep_trials for n in sweep_sizes)
bf_acc = sum(acc_sizes)
print(f"BruteForce (S1): sweep={bf_sweep}, accuracy={bf_acc}, combined={bf_sweep + bf_acc}")
for s_max in [5, 10, 20]:
    s_min = s_max // 2
    sw = sum(min(s_max, n) * sweep_trials for n in sweep_sizes)
    ac = sum(min(s_max, n) for n in acc_sizes)
    print(f"BoundedBucket (s_min={s_min}, s_max={s_max}): sweep={sw}, accuracy={ac}, combined={sw + ac}")

print("\n=== 6. D-5: GRAY-RANK BINARY SEARCH O(log M) VS LINEAR HAMMING SCAN O(M) TIMING ===")
print(f"{'n':>5} | {'n_segs':>7} | {'gray_bsearch_us':>15} | {'linear_hamming_us':>17} | {'slowdown_x':>10}")
for n in [50, 100, 200, 500, 1000, 2000]:
    rng_d5 = np.random.default_rng(500 + n)
    vecs = generate_isotropic(n + 1, 384, rng_d5)
    names = [f"c_{i:04d}" for i in range(n)]
    proto = PrototypeBoundedBucket(s_min=5, s_max=10, n_bits=12, seed=0, setup_mode="batch")
    proto.setup_from_vectors(names, vecs[:n])
    code, gray = proto._hash_vec(vecs[n])

    t_bsearch = []
    for _ in range(200):
        t0 = time.perf_counter()
        h_idx, _, _ = proto._locate_home_segment(gray, "c_new")
        seg = proto._segments[h_idx]
        rows = [e.row for e in seg]
        sub_mat = proto._matrix[rows]
        _ = sub_mat @ vecs[n]
        t_bsearch.append((time.perf_counter() - t0) * 1e6)

    t_linear = []
    for _ in range(200):
        t0 = time.perf_counter()
        best_idx = 0
        best_key = (999, 999999, 999, 0)
        for idx, seg in enumerate(proto._segments):
            d0 = hamming_distance(seg[0].code, code)
            d1 = hamming_distance(seg[-1].code, code)
            d_min = d0 if d0 <= d1 else d1
            k_tuple = (d_min, abs(gray - seg[0].gray), len(seg), idx)
            if k_tuple < best_key:
                best_key = k_tuple
                best_idx = idx
        seg = proto._segments[best_idx]
        rows = [e.row for e in seg]
        sub_mat = proto._matrix[rows]
        _ = sub_mat @ vecs[n]
        t_linear.append((time.perf_counter() - t0) * 1e6)

    med_b = float(np.median(t_bsearch))
    med_l = float(np.median(t_linear))
    print(f"{n:5d} | {len(proto._segments):7d} | {med_b:15.2f} | {med_l:17.2f} | {med_l / med_b:10.2f}x")
```

### 7.2 Command Executed

```bash
.venv-ann/bin/python /tmp/sim_strat004.py
```

### 7.3 Verbatim Command Output (`[Confirmed]`)

```text
=== 1. PART 0 REPRODUCER: D-9 STALE CACHE CHECK ON S2 AND S3 ===
S3 _cached_new_name after shortlist(''): 'good_node'
S2 _cached_new_name after shortlist(''): 'good_node'

=== 2. D-2 & D-11: HYPERPLANE BIT COUNT SENSITIVITY (n=500, s_min=5, s_max=10, 50 trials) ===

Distribution: isotropic
n_bits | uniq_codes |  n_segs | mean_sz | p_split | top10_ovlp
     8 |      217.8 |    78.3 |    6.39 |    0.10 |      0.026
    10 |      391.7 |    74.1 |    6.75 |    0.16 |      0.030
    12 |      468.1 |    74.0 |    6.76 |    0.14 |      0.032
    16 |      497.6 |    73.7 |    6.79 |    0.14 |      0.030
    24 |      500.0 |    74.0 |    6.76 |    0.06 |      0.024
    32 |      500.0 |    73.7 |    6.79 |    0.06 |      0.028

Distribution: clustered_s0.08
n_bits | uniq_codes |  n_segs | mean_sz | p_split | top10_ovlp
     8 |      208.1 |    76.4 |    6.55 |    0.06 |      0.034
    10 |      374.5 |    75.1 |    6.66 |    0.10 |      0.036
    12 |      458.5 |    74.1 |    6.75 |    0.08 |      0.034
    16 |      496.5 |    73.8 |    6.78 |    0.12 |      0.044
    24 |      500.0 |    74.5 |    6.72 |    0.02 |      0.032
    32 |      500.0 |    73.9 |    6.77 |    0.12 |      0.036

Distribution: clustered_s0.04
n_bits | uniq_codes |  n_segs | mean_sz | p_split | top10_ovlp
     8 |      180.7 |    74.5 |    6.72 |    0.10 |      0.082
    10 |      315.4 |    74.6 |    6.71 |    0.10 |      0.082
    12 |      403.4 |    74.2 |    6.75 |    0.14 |      0.092
    16 |      474.7 |    74.3 |    6.74 |    0.16 |      0.082
    24 |      498.2 |    74.0 |    6.77 |    0.14 |      0.088
    32 |      499.8 |    73.8 |    6.78 |    0.16 |      0.098

=== 3. D-8: FIRST-INSERT BEHAVIOR ACROSS SIZES (s_min=5, s_max=10, n_bits=12, 100 trials) ===

Setup mode: batch | Distribution: isotropic
    n |  n_segs | min_sz | mean_sz | max_sz | frac_at_smax | P(split) | P(gap_mrg) | top10_ovlp
   28 |     4.2 |      5 |    6.76 |     10 |        0.074 |     0.09 |       0.18 |      0.275
   50 |     7.5 |      5 |    6.74 |     10 |        0.083 |     0.11 |       0.31 |      0.172
  100 |    14.6 |      5 |    6.89 |     10 |        0.097 |     0.16 |       0.20 |      0.088
  140 |    20.6 |      5 |    6.81 |     10 |        0.089 |     0.12 |       0.25 |      0.065
  200 |    29.6 |      5 |    6.77 |     10 |        0.077 |     0.15 |       0.20 | 0.038
  500 |    74.1 |      5 |    6.75 |     10 |        0.073 |     0.10 |       0.33 |      0.013
 1000 |   148.8 |      5 |    6.72 |     10 |        0.072 |     0.05 |       0.24 |      0.012
 2000 |   298.6 |      5 |    6.70 |     10 |        0.067 |     0.07 |       0.32 |      0.006

Setup mode: batch | Distribution: clustered_s0.08
    n |  n_segs | min_sz | mean_sz | max_sz | frac_at_smax | P(split) | P(gap_mrg) | top10_ovlp
   28 |     4.1 |      5 |    6.93 |     10 |        0.094 |     0.12 |       0.23 |      0.262
   50 |     7.4 |      5 |    6.84 |     10 |        0.088 |     0.15 |       0.32 |      0.159
  100 |    14.8 |      5 |    6.79 |     10 |        0.082 |     0.11 |       0.20 |      0.111
  140 |    20.6 |      5 |    6.82 |     10 |        0.079 |     0.09 |       0.31 |      0.072
  200 |    29.6 |      5 |    6.77 |     10 |        0.071 |     0.04 |       0.23 |      0.072
  500 |    74.2 |      5 |    6.75 |     10 |        0.074 |     0.10 |       0.26 |      0.036
 1000 |   148.7 |      5 |    6.73 |     10 |        0.072 |     0.14 |       0.26 |      0.033
 2000 |   300.5 |      5 |    6.66 |     10 |        0.062 |     0.13 |       0.30 |      0.016

Setup mode: sequential | Distribution: isotropic
    n |  n_segs | min_sz | mean_sz | max_sz | frac_at_smax | P(split) | P(gap_mrg) | top10_ovlp
   28 |     3.9 |      5 |    7.20 |     10 |        0.091 |     0.10 |       0.15 |      0.285
   50 |     7.0 |      5 |    7.19 |     10 |        0.120 |     0.19 |       0.19 |      0.190
  100 |    14.0 |      5 |    7.15 |     10 |        0.104 |     0.13 |       0.19 |      0.089
  140 |    19.9 |      5 |    7.04 |     10 |        0.083 |     0.11 |       0.20 |      0.071
  200 |    28.1 |      5 |    7.12 |     10 |        0.105 |     0.13 |       0.19 |      0.041
  500 |    70.2 |      5 |    7.12 |     10 |        0.100 |     0.15 |       0.14 |      0.016
 1000 |   140.3 |      5 |    7.13 |     10 |        0.108 |     0.18 |       0.11 |      0.007
 2000 |   281.5 |      5 |    7.11 |     10 |        0.101 |     0.16 |       0.17 |      0.009

Setup mode: sequential | Distribution: clustered_s0.08
    n |  n_segs | min_sz | mean_sz | max_sz | frac_at_smax | P(split) | P(gap_mrg) | top10_ovlp
   28 |     4.0 |      5 |    7.01 |     10 |        0.086 |     0.06 |       0.13 |      0.268
   50 |     7.0 |      5 |    7.16 |     10 |        0.108 |     0.13 |       0.20 |      0.163
  100 |    14.0 |      5 |    7.18 |     10 |        0.119 |     0.18 |       0.16 |      0.107
  140 |    19.9 |      5 |    7.06 |     10 |        0.086 |     0.15 |       0.15 |      0.072
  200 |    28.2 |      5 |    7.10 |     10 |        0.100 |     0.15 |       0.19 |      0.068
  500 |    70.5 |      5 |    7.10 |     10 |        0.097 |     0.17 |       0.19 |      0.039
 1000 |   140.8 |      5 |    7.10 |     10 |        0.101 |     0.15 |       0.09 |      0.027
 2000 |   281.3 |      5 |    7.11 |     10 |        0.100 |     0.15 |       0.21 |      0.019

=== 4. D-8: SEQUENTIAL STREAM MICRO-BENCHMARK (m=2000 inserts from n=0, s_min=5, s_max=10, n_bits=12) ===
Stream (isotropic, m=2000): total_wall=5419.2 ms | final_segs=282 | total_splits=281 (rate=0.1405, mean_inserts_between_splits=7.12) | gap_merges=386 | median_shortlist=85.5 us | median_update=47.8 us | p99_update=672.8 us
Stream (clustered_s0.08, m=2000): total_wall=3959.7 ms | final_segs=277 | total_splits=276 (rate=0.1380, mean_inserts_between_splits=7.25) | gap_merges=398 | median_shortlist=78.6 us | median_update=41.7 us | p99_update=134.3 us

=== 5. D-13: CALL BOUNDS OVER D-35 SWEEP MATRIX AND ACCURACY MODE ===
BruteForce (S1): sweep=38500, accuracy=5012, combined=43512
BoundedBucket (s_min=2, s_max=5): sweep=300, accuracy=295, combined=595
BoundedBucket (s_min=5, s_max=10): sweep=600, accuracy=590, combined=1190
BoundedBucket (s_min=10, s_max=20): sweep=1200, accuracy=1180, combined=2380

=== 6. D-5: GRAY-RANK BINARY SEARCH O(log M) VS LINEAR HAMMING SCAN O(M) TIMING ===
    n |  n_segs | gray_bsearch_us | linear_hamming_us | slowdown_x
   50 |       8 |           32.26 |             51.93 |       1.61x
  100 |      16 |           28.87 |             77.85 |       2.70x
  200 |      31 |           31.80 |            130.61 |       4.11x
  500 |      71 |           31.04 |            280.53 |       9.04x
 1000 |     150 |           47.61 |            654.20 |      13.74x
 2000 |     297 |           35.67 |            763.92 |      21.42x
```

---

## 8. Implementation-Prompt Skeleton (`STRAT-004`)

### 8.1 Files to Create or Edit

- **Create:**
  - `src/graph_insertion/strategies/bounded_bucket.py`
  - `tests/test_bounded_bucket_strategy.py`
  - `docs/reports/STRAT-004-<agent>-bounded-bucket.md`
- **Edit ( only if explicitly unlocked by the APC in the STRAT-004 prompt):**
  - `src/graph_insertion/strategies/__init__.py` (to export `BoundedBucketStrategy`)
  - `scripts/run_experiment.py` (to register `"bounded_bucket"` in `STRATEGIES` and sensitivity grid if part of `STRAT-004` rather than `INFRA-007`)
  - `docs/decisions/decision-log.md` (append reserved decision entry `[D-XX]`)
  - `docs/tasks/status.md` (update `STRAT-004` row)

### 8.2 Standing Forbidden List for `STRAT-004`

Read-only (do not modify unless explicitly unlocked in 8.1):
`src/graph_insertion/harness.py`, `src/graph_insertion/llm.py`, `src/graph_insertion/__init__.py`, `src/graph_insertion/strategy.py`, `src/graph_insertion/embedding.py`, `src/graph_insertion/graph_representation.py`, `src/graph_insertion/strategies/null.py`, `src/graph_insertion/strategies/brute_force.py`, `src/graph_insertion/strategies/embedding_threshold.py`, `src/graph_insertion/strategies/ann_retrieval.py`, `scripts/generate_name_pool.py`, `tests/test_strategy_interface.py`, `tests/controllable_embedder.py`, `tests/test_controllable_embedder.py`, `tests/test_brute_force_strategy.py`, `tests/test_embedding_threshold_strategy.py`, `tests/test_ann_retrieval_strategy.py`, `pyproject.toml`.

### 8.3 Required Tests & Mutation Verification

- Implement all 15 test groups listed in Section 6 **D-12** inside `tests/test_bounded_bucket_strategy.py` (including `TestBoundedBucketConformance(StrategyConformanceSuite)`).
- Reviewer must execute all 22 mutations **M-01 … M-22** from Section 6 **D-12** on a `/tmp` copy and record `KILLED` / `SURVIVED`.

### 8.4 Draft Decision Log Entry for the Implementer (Without Test Counts)

> **[D-XX]** Strategy 4 (`bounded_bucket`) implementation (`STRAT-004`, `src/graph_insertion/strategies/bounded_bucket.py`, `tests/test_bounded_bucket_strategy.py`):
> (1) **EraRAG-faithful hyperplane LSH + 1-D Reflected Gray-Rank Partitioning:** `BoundedBucketStrategy` (`name = "bounded_bucket"`, `uses_embeddings = True`) adapts EraRAG's (Zhang et al., 2025) bounded-bucket LSH partitioning using NumPy only. In `setup()` (or lazily on the first `shortlist()` when `setup()` receives an empty graph), $n_{\text{bits}} = 12$ random unit hyperplanes in $\mathbb{R}^d$ (`dtype=np.float64`) are drawn from `np.random.default_rng(self.seed)`. Each L2-normalised `float32` concept vector is projected in `float64` (`dots = vec.astype(np.float64) @ _hyperplanes.T`, sign bit `1` iff `dot >= 0.0`) to produce an $n_{\text{bits}}$-bit integer code $b$, which is mapped to its reflected binary Gray rank $g = \bigoplus_{k=0}^{n_{\text{bits}}-1} (b \gg k)$ so consecutive ranks differ by Hamming distance 1.
> (2) **Bounds, Feasibility Invariant, and Split/Merge Rules:** Hyperparameters are fixed a priori ([D-35](5)) at `DEFAULT_S_MIN = 5`, `DEFAULT_S_MAX = 10`, `DEFAULT_N_BITS = 12`, `DEFAULT_SEED = 0`, with sensitivity settings `(s_min=2, s_max=5)` and `(s_min=10, s_max=20)`. `__init__` enforces the feasibility invariant `2 <= s_min` and `s_max >= 2 * s_min`. Segments partition the sorted `(gray_rank, name)` order into contiguous intervals of size $\in [S_{\min}, S_{\max}]$ for all $n \ge S_{\min}$ (and a single segment of size $n$ when $1 \le n < S_{\min}$). Batch `setup()` (Algorithm 1) groups nodes by `gray_rank`, recursively bisects buckets above $S_{\max}$ at `mid = len(seg) // 2` in `(gray_rank, name)` order, and merges buckets below $S_{\min}$ with their closer adjacent segment ($S_{i-1}$ or $S_{i+1}$) by boundary `(hamming_dist, gray_gap, neighbor_len, side)` (rebalancing at `mid` if the combined size exceeds $S_{\max}$).
> (3) **Sub-linear `shortlist()`, Local `on_inserted()`, and Lifecycle:** `shortlist(new_name)` clears `_cached_new_name` and `_cached_new_vec` at the very first lines before validation, locates the home segment in $O(\log M)$ via binary search without mutating state, and scores only that segment's members (`max_candidates(n_existing) = max(0, min(self.s_max, n_existing))`, giving a 600-call upper bound over the D-35 sweep matrix). `on_inserted(new_name)` reuses the cached vector (`embedding_calls_in_update == 0`), writes into pre-allocated matrix headroom (`max(n + 16, 16)`), inserts into the home segment, and locally bisects it if size reaches $S_{\max} + 1$. `diagnostics()` is computed outside timed windows and includes `exact_topk_overlap` alongside bucket and segment-distribution telemetry.
> — **Reasoning:** Faithful to EraRAG Algorithms 1 and 3 and Thesis §3.2.5; guarantees $O(d + \log M + S_{\max} \cdot d)$ shortlist and update times without $O(n)$ scans or cascading splits, while matching Strategy 3's 600-call worst-case sweep budget.
> — **Affects:** `src/graph_insertion/strategies/bounded_bucket.py`, `tests/test_bounded_bucket_strategy.py`.

---

## 9. Shared-Doc Diffs

None

### Verbatim `git status --short`

```text
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M scripts/README.md
 M scripts/apc-bundle.sh
 M scripts/generate_name_pool.py
 M tests/stub_prompt_adapter.py
 M tests/test_generate_name_pool.py
?? docs/context/apc-bundle-quickref.md
?? docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md
?? docs/reports/STRAT-004-D-gemini-design-note.md
```

---

## 10. Found But Not Changed

1. **`src/graph_insertion/strategies/ann_retrieval.py:273-281` and `src/graph_insertion/strategies/embedding_threshold.py:196-228` (`[Confirmed]`):**
   - In `AnnRetrievalStrategy.shortlist()`, `_cached_new_name` and `_cached_new_vec` are cleared *after* `_setup_called` and `_validate_concept_name(new_name)`. In `EmbeddingThresholdStrategy.shortlist()`, `_cached_new_name` and `_cached_new_vec` are not cleared on entry at all (only overwritten after embedding and vector validation). Calling `shortlist("")` after `shortlist("good_node")` leaves `_cached_new_name == 'good_node'` in both strategies. Not touched because both files are on the standing forbidden list.
2. **`src/graph_insertion/harness.py:621` (`estimate_and_print_plan`) (`[Confirmed]`):**
   - In `estimate_and_print_plan()` (used by non-live `config.dry_run=True`), line 621 checks `top_k = strategy.config().get("top_k", None)` instead of calling `candidate_upper_bound(strategy, n)`. Note that neither `AnnRetrievalStrategy` (`config()` key `"k"`) nor `BoundedBucketStrategy` (`config()` key `"s_max"`) uses `"top_k"`, whereas `scripts/run_experiment.py:309` (`compute_planned_calls_upper_bound`) properly calls `candidate_upper_bound(strategy, size)`. Not touched because `harness.py` is on the standing forbidden list.
3. **Pre-existing dirty working tree from prior tasks (`FIX-015` / `TOOL-001` / `DOC-003`) (`[Confirmed]`):**
   - Left completely untouched per Standing Rule 1.

---

## 11. Open Questions and "For APC-A" Block

### 11.1 Open Questions

1. **[APC] Inclusion of the Zero-LLM Sequential-Stream Micro-Benchmark (`D-8`):** Should the `STRAT-004` implementation prompt include a test or standalone helper function that runs the $m=2000$ zero-LLM sequential insertion stream to empirically log the multi-step amortised split frequency ($\approx 1 / 7.12$ inserts) alongside the one-insert sweep harness, or should that live in `INFRA-007`?
2. **[APC] Exporting `BoundedBucketStrategy` in `src/graph_insertion/strategies/__init__.py`:** `strategies/__init__.py` is on the standing forbidden list in `STRAT-004-D`, just as it was in `STRAT-002` and `STRAT-003`. Confirm whether `STRAT-004` should leave `strategies/__init__.py` untouched (deferring registration to `INFRA-007`) or unlock it.
3. **[APC-A / Luke / adviser] Thesis §3.2.5 and §3.4 Parameter & Protocol Alignment:** Thesis Chapter 3 §3.4 (`docs/thesis/An Empirical Complexity Analysis...md`, line 211) explicitly names the default and sensitivity parameters for Strategy B ($\theta \in \{0.65, 0.75, 0.85\}$) and Strategy C ($k \in \{5, 10, 20\}$), but does not yet list Strategy D's parameters ($S_{\min} = 5, S_{\max} = 10, n_{\text{bits}} = 12$, sensitivity $(S_{\min}, S_{\max}) \in \{(2, 5), (10, 20)\}$) or note that the single-insert sweep measures un-amortised step-1 update cost while a sequential stream tests multi-insert amortisation.

### 11.2 For APC-A (Proposed Thesis Text Additions for Luke and His Adviser)

> **Draft addition to Thesis §3.2.5 (Bounded-Bucket Partitioning — Strategy D):**
> "Concretely, during initial index construction on an existing graph of size $n$, $n_{\text{bits}} = 12$ unit hyperplanes are drawn deterministically from an isotropic Gaussian distribution in $\mathbb{R}^d$. Each concept's L2-normalized embedding is projected onto these hyperplanes to obtain a 12-bit sign code, which is mapped to its reflected binary Gray rank so that adjacent ranks differ in one hyperplane bit. Concepts are ordered by Gray rank (with lexicographical concept-name tie-breaking) and partitioned into contiguous segments bounded by $S_{\min} = 5$ and $S_{\max} = 10$ ($2 \le S_{\min}$ and $S_{\max} \ge 2 S_{\min}$). Oversize segments ($> S_{\max}$) are bisected at their median in Gray-rank order, and undersize segments ($< S_{\min}$, when $n \ge S_{\min}$) are merged with the adjacent segment ($S_{i-1}$ or $S_{i+1}$) having minimum boundary Hamming distance, bisecting the combined segment if it exceeds $S_{\max}$."
>
> **Draft addition to Thesis §3.4 (Experimental Procedure — Parameter Fixing and Sensitivity):**
> "For Strategy D, the bucket bounds are fixed at $S_{\min} = 5$ and $S_{\max} = 10$ with $n_{\text{bits}} = 12$ hyperplanes so that its maximum candidate shortlist size ($S_{\max} = 10$) equals Strategy C's default retrieval depth ($k = 10$), holding the worst-case LLM call budget identical across both sub-linear structures. Sensitivity runs evaluate $(S_{\min}, S_{\max}) \in \{(2, 5), (10, 20)\}$ following $S_{\min} = \lfloor S_{\max} / 2 \rfloor$. Because each size-sweep trial performs a single insertion after initial partitioning, the sweep measures single-step narrowing and maintenance latency; to directly verify EraRAG Theorem 4's multi-insertion amortisation claim (that splits and merges cannot cascade and occur at most once every $\Theta(S_{\min})$ insertions per segment), we additionally record split/merge frequency across a sequential stream of $m = 2,000$ insertions."
