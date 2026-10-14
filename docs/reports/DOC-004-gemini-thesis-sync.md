# DOC-004: Thesis Sync After Strategy Track (Proposed Edits Only)

- **Date:** 2026-10-14
- **Agent Identity:** Antigravity (Gemini)
- **Session ID:** `098dcdd4-c444-4fcd-af8f-1b2054b31802`
- **Task ID:** `DOC-004`
- **Decision ID:** None (decision log untouched per prompt instructions)
- **Repo State:** Branch `master` at commit `d6d442e` (`INFRA-007-Q`)

---

## 1. Agent Identity

- **Agent Name / Tool:** Antigravity (Gemini)
- **Conversation / Session ID:** `098dcdd4-c444-4fcd-af8f-1b2054b31802`
- **Operational Mode:** Read-only inspection of repository and thesis text; proposed edits applied strictly to an out-of-tree copy at `/tmp/doc004/thesis.md` and exported as a unified diff artifact.

---

## 2. Summary Table of Proposed Thesis Changes

| Item | Thesis Section | Current Lines | Change Type | Severity | Core Rationale |
|---|---|---|---|---|---|
| **Item 1** | §3.2.5 (Strategy D) | 188–191 | Replace / Expand | **Must-fix before submission** | Specify fixed parameters ($s_{\min}=5, s_{\max}=10, n_{\text{bits}}=12$, seed 42), Gray-code 1D linearisation adaptation, midpoint bisection, planned bounds (600 / 300 / 1,200), capacity nuance (mean shortlist $\approx 7$), and methodological limitations (single un-amortised step, fixed seed, expected top-10 overlap). |
| **Item 2** | §1.1, §2.2.4, §3.5 | 17, 136, 138, 272 | Replace / Insert | **Must-fix before submission** | Resolve symbol collision where Theorem 4 in [4] uses $n$ for hyperplane count, clashing with thesis graph size $n$; rename to $b$ in $\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$; scope $S_{\text{LLM}}$ to single-layer pairwise candidate queries (at most $s_{\max}$ calls) as a structural analogy; clarify CPU projection cost. |
| **Item 3** | §3.2.4 (Strategy C), §3.4 | 184, 186, 266 | Replace / Expand | **Must-fix before submission** | Align Strategy C parameter specification ($k=10, M=16, \text{efConstruction}=200, \text{efSearch}=128$); sensitivity grid $\{64, 256\}$ for efSearch and $\{5, 20\}$ for $k$; include synthetic Gaussian recall evidence (0.841, 0.968, 0.999); note single-threaded determinism; fix empirical tuning contradiction per [D-35(5)]. |
| **Item 4** | §3.2.4 (Strategy C) | 184 | Replace (Fallback Rewording) | **Should-fix** | Replace uncited claim ("common default-range settings") with fallback rewording stating $M=16$ and $\text{efConstruction}=200$ are standard library operational ranges fixed a priori without tuning; candidate primary sources tagged `[Unverified]` in report for Luke/adviser verification. |
| **Item 5** | §1.5 (Scope & Limitations), §3.2.3, §3.4 | 68, 180, 266 | Insert / Replace | **Must-fix before submission** | Document that $\theta=0.6$ is an uncalibrated heuristic adopted a priori from prior literature ([2], [D-46]); note asymmetry in sensitivity grid ($\theta \in \{0.4, 0.5\}$ are looser, no stricter threshold evaluated); explain consequence of uncapped candidate shortlist (up to $n$ candidates, 38,500 call guard bound). |

---

## 3. Prompt Corrections

Every statement and assumption in the `DOC-004` task prompt was verified directly against the live repository files. Findings:

1. **Task ID Uniqueness:**
   - *Prompt statement:* "Task ID: DOC-004. Grep docs/tasks/status.md and docs/reports/ first; if DOC-004 is already used, take the next unused DOC number and say so."
   - *Repo verification:* `docs/tasks/status.md` ends at `DOC-002`. No `DOC-003` or `DOC-004` existed in `docs/reports/` or `status.md`. `DOC-004` is available and used. **[Confirmed]**
2. **Decision ID Reservation:**
   - *Prompt statement:* "Decision ID: none (do not touch decision-log.md)."
   - *Repo verification:* The latest decision is `[D-67]` (closed under `INFRA-007-Q`). `DOC-004` touches no decision entries. **[Confirmed]**
3. **Thesis File Copies and Current Content:**
   - *Prompt statement:* "The repo has two copies: `docs/thesis/An Empirical Complexity Analysis...md` and `docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md`... hash `8db1a65f48600e7c20355ce9246a6a38542c725607eb86b12272210bacb34410` at commit `d9f7797`."
   - *Repo verification:* As anticipated by the prompt's warning that text may have changed, the canonical thesis was amended in commit `6315f35` (DOC-002). The live SHA-256 hash of the canonical thesis is `15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a` (298 lines, 65,294 bytes). The other copy is an early draft (94 lines, 10,742 bytes). **[Confirmed & Updated]**
4. **Strategy D Implementation Facts:**
   - *Prompt statement:* Defaults are $s_{\min}=5, s_{\max}=10, n_{\text{bits}}=12$, seed 42; sensitivity pairs are $(2, 5)$ and $(10, 20)$ with $(3, 6)$ and bit variants withdrawn per [D-62(1)]; Gray-code curve ordering, midpoint bisection (`len // 2`), and neighbour tie-breaking.
   - *Repo verification:* Verified in `src/graph_insertion/strategies/bounded_bucket.py` (lines 78–81), `src/graph_insertion/strategies/registry.py` (lines 124–144), `[D-59]`, `[D-62]`, and `[D-64]`. **[Confirmed]**
5. **Strategy C Implementation Facts:**
   - *Prompt statement:* Defaults are $k=10, M=16, \text{ef_construction}=200, \text{ef_search}=128$; sensitivity $k \in \{5, 20\}$ and $\text{ef_search} \in \{64, 256\}$; single-threaded deterministic build.
   - *Repo verification:* Verified in `src/graph_insertion/strategies/ann_retrieval.py` (lines 108–115, 122–141), `registry.py` (lines 101–121), `[D-47]`, `[D-55]`, and `[D-58(2)]`. **[Confirmed]**
6. **Strategy B Implementation Facts:**
   - *Prompt statement:* Default $\theta=0.6$, sensitivity $\theta \in \{0.4, 0.5\}$; uncapped shortlist up to $n$ calls.
   - *Repo verification:* Verified in `src/graph_insertion/strategies/embedding_threshold.py` (lines 35–45), `registry.py` (lines 80–99), `[D-35]`, `[D-41]`, and `[D-46]`. **[Confirmed]**
7. **Line Number References in Handoff Summary:**
   - *Prompt / summary statement:* Summary referenced §3.4 at line 305 and thesis length of 342 lines.
   - *Repo verification:* In the canonical thesis file, total line count is 298 lines (297 newline characters). Section 3.4's "Parameter fixing and sensitivity" paragraph is located at line 266; Section 3.5 is at lines 270–275. **[Corrected]**

---

## 4. Orientation Findings

### 4.1 Canonical Thesis Establishment
- **Canonical Document:** `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`
  - *Evidence:* Defined as the sole canonical source of truth for the thesis text by `docs/context/complete-context.md` (lines 11–17: *"The full, formal thesis text is in `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`... The thesis file is the source of truth if the two ever disagree."*) and referenced in `AGENTS.md`.
  - *SHA-256:* `15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a`
  - *Size:* 298 lines (297 newline-terminated lines; 65,294 bytes).
- **Secondary Copy:** `docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md`
  - *SHA-256:* `3081fce128521995592c6ae82f0767e140dbfa4e2f59ae3bb34322df29233c98`
  - *Size:* 94 lines (10,742 bytes).
  - *Difference:* This file is an early abridged proposal outline, lacking the full formal chapter structure, methodology subsections, and decision anchors. It is not canonical and should not be edited.
- **Companion Overview:** `docs/reports/to-be-shared/thesis-orientation.md`
  - *SHA-256:* `9d81ba8a1ef46791fb66775f92c501d06210d733566ac52259f186e7f6270c3a`
  - *Size:* 52 lines (5,933 bytes). Plain-English project summary for human onboarding.

### 4.2 Section Map of the Canonical Thesis
The canonical thesis comprises Chapters 1 through 3 and a reference list:
- **Title / Front Matter:** Lines 1–8
- **Chapter 1: Introduction:** Line 9
  - §1.1 Background and Context: Lines 10–26
  - §1.2 Statement of the Problem: Lines 27–37
  - §1.3 Objectives of the Study: Lines 38–49
  - §1.4 Significance of the Study: Lines 50–57
  - §1.5 Scope and Limitations: Lines 58–69
  - §1.6 Definition of Terms: Lines 70–79
- **Chapter 2: Review of Related Literature:** Line 80
  - §2.1 Theoretical Framework: Lines 82–116
    - §2.1.1 Time and Query Complexity in Graph Construction: Lines 84–99
    - §2.1.2 Amortized Complexity Analysis for Dynamic Data Structures: Lines 100–116
  - §2.2 Related Systems and Approaches: Lines 117–144
    - §2.2.1 Brute-Force and Full-Graph Comparison: Lines 119–124
    - §2.2.2 Embedding-Based Filtering and Similarity Thresholds: Lines 125–129
    - §2.2.3 Classification-Based Incremental Expansion: Lines 130–133
    - §2.2.4 Bounded-Structure Incremental Updates and Their Theoretical Claims: Lines 134–139
    - §2.2.5 Expert-Verified Prerequisite Graph Construction: Lines 140–144
  - §2.3 Synthesis and Research Gap: Lines 145–165
- **Chapter 3: Methodology:** Line 166
  - §3.1 Research Design: Lines 168–171
  - §3.2 The Candidate-Narrowing Strategies: Lines 172–203
    - §3.2.1 Overview and Shared Pipeline: Line 174
    - §3.2.2 Strategy A: Brute-Force Full Comparison (Control): Lines 175–177
    - §3.2.3 Strategy B: Embedding-Similarity Thresholding: Lines 178–181
    - §3.2.4 Strategy C: Approximate Nearest-Neighbor (ANN) Retrieval: Lines 182–187
    - §3.2.5 Strategy D: Bounded-Bucket Partitioning: Lines 188–191
    - §3.2.6 The Shared Decision Step: Lines 192–203
  - §3.3 Data Sources and Materials: Lines 204–256
    - §3.3.1 Evaluation Datasets: Lines 206–256
  - §3.4 Experimental Procedure and Instrumentation: Lines 257–269
  - §3.5 Data Analysis: Lines 270–276
- **References:** Lines 278–298 (`[1]` to `[10]`)

---

## 5. The Five Items: Detailed Analysis and Proposals

### 5.1 Item 1: Strategy D Parameters and the "Adapted" Wording (§3.2.5 and §3.4)

#### 5.1.1 Current Text
- **Location:** §3.2.5, lines 188–191:
```markdown
### 3.2.5 Strategy D: Bounded-Bucket Partitioning

This strategy organizes existing nodes into size-bounded groups ("buckets"), such that inserting a new node only ever requires comparing it against the members of one bounded bucket, rather than the whole graph. This study's implementation adapts the general bucket-partitioning principle described in [4] — specifically, the idea that bucket size is capped by a small constant, and that a bucket exceeding this cap is split while a bucket falling below a lower bound is merged with an adjacent bucket — to the concept-node insertion task, rather than reproducing EraRAG's own text-chunk-summarization architecture directly. This distinction is stated explicitly here because, as discussed in Chapter 2 Section 2.2.4, EraRAG's insertion operation (summarizing a bucket of text chunks) and this study's insertion operation (semantically placing a concept node) are not the same underlying task, even though both share the same bounded-partition *structural principle*.
```
- **Location:** §3.4, line 266:
```markdown
and (s_min, s_max) ∈ {(2, 5), (10, 20)} for Strategy D. ... The same planned upper bounds apply to Strategy D with s_max in place of *k* (600, 300 and 1,200 for s_max = 10, 5 and 20); because bucket sizes lie between s_min and s_max, its actual call counts are expected to be lower.
```

#### 5.1.2 Problem
1. **Missing Concrete Parameter Specifications:** §3.2.5 lacks the explicit primary values: $s_{\min}=5, s_{\max}=10, n_{\text{bits}}=12$, seed 42 ([D-59], [D-62], [D-64]).
2. **Missing Justification for $n_{\text{bits}}=12$:** The choice of 12 bits provides $2^{12} = 4,096$ possible codes, ensuring that the hash code space does not saturate across graph sizes up to $n = 2,000$. It is chosen for address capacity, not tuned for retrieval quality.
3. **Missing Headroom Convention Clarification:** The requirement $s_{\max} \ge 2 s_{\min}$ is a chosen convention for post-split headroom; it is sufficient for legal bisection closure, but not strictly necessary ($s_{\max} \ge 2 s_{\min} - 1$ already guarantees $\lfloor (s_{\max} + 1) / 2 \rfloor \ge s_{\min}$).
4. **Unspecified Adaptation Mechanics:** EraRAG assigns hash codes via random hyperplanes, but does not define an unambiguous 1D ordering, split mechanism, or neighbour merge tie rule. This study designed a specific 1D linearisation: mapping codes to an integer Gray sequence, grouping concepts into contiguous intervals ("segments"), splitting oversize segments via midpoint bisection (`len // 2`), and merging undersize segments with the nearest Gray-curve neighbour. Consequently, segments span contiguous intervals of Gray codes rather than single codes, and Hamming-adjacent codes can be separated on the 1D curve. It must never be described as "EraRAG-faithful" or claiming to "isolate geometry from shortlist capacity".
5. **Planned Bounds vs. Realised Shortlist Capacity:** Worst-case call bounds equal Strategy C's at $s_{\max}=10$ (600 sweep / 590 accuracy calls; 300 / 295 at $(2, 5)$; 1,200 / 1,180 at $(10, 20)$ per [D-62(2)]), but because segments bisect upon reaching $s_{\max} + 1$, the mean shortlist size is $\approx 7$, so realised calls are substantially lower on average.
6. **Methodological Limitations:** The sweep benchmarks an un-amortised single insertion per trial after `setup()`, so `update_s` measures a single step rather than evaluating EraRAG's amortised claim across long streams. Hyperplane seed is fixed at 42 (variance across draws is unsampled). Lower overlap with exact top-10 at larger $n$ is an expected geometric property of space partitioning, not a defect to be tuned away on evaluation data ([D-35(5)]).

#### 5.1.3 Proposed Text
- **Replace §3.2.5 (line 190) with:**
```markdown
This strategy organizes existing nodes into size-bounded groups ("buckets" or "segments"), such that inserting a new node only ever requires comparing it against the members of one bounded bucket, rather than the whole graph. This study's implementation adapts the general size-bounded hyperplane-LSH partitioning principle described in [4] (specifically Algorithms 1 and 3) to the concept-node insertion task, rather than reproducing EraRAG's own multi-layer text-chunk summarization architecture directly. In EraRAG, nodes are assigned hash codes via random hyperplanes, and buckets with identical codes are split when exceeding an upper bound or merged with Hamming-adjacent buckets when falling below a lower bound. Because EraRAG leaves several concrete data-structural choices unspecified, this study adopts a specific 1D linearisation: hash codes are mapped to an integer Gray-curve sequence, existing concepts are grouped into contiguous intervals ("segments") along this curve, oversize segments are split via midpoint bisection (`len // 2`), and undersize segments are merged with their nearest Gray-curve neighbour (breaking ties by lower index) ([D-59]). Because segments span contiguous intervals of Gray codes rather than single hash codes, and because the Gray curve can separate Hamming-close codes, this implementation is an adaptation of EraRAG's structural partitioning principle rather than an identical replica of its retrieval mechanics, and it does not isolate geometric distance from segment capacity.

The primary parameters are fixed a priori before experimental execution: lower segment bound $s_{\min} = 5$, upper segment bound $s_{\max} = 10$, hash bit count $n_{\text{bits}} = 12$, and random hyperplane seed fixed to 42 (matching the experiment harness default seed) ([D-59], [D-62], [D-64]). The choice of $n_{\text{bits}} = 12$ is justified strictly by code space: $2^{12} = 4,096$ possible codes comfortably exceeds the largest evaluated graph size ($n = 2,000$), ensuring the hash space does not artificially saturate, rather than by tuning retrieval quality. The constraint $s_{\max} \ge 2 s_{\min}$ is a chosen convention to maintain post-split headroom; it is a sufficient condition for midpoint bisection closure rather than a mathematically necessary one ($s_{\max} \ge 2 s_{\min} - 1$ already guarantees $\lfloor (s_{\max} + 1) / 2 \rfloor \ge s_{\min}$). Sensitivity runs examine parameter variations one at a time: $(s_{\min}, s_{\max}) \in \{(2, 5), (10, 20)\}$ with $n_{\text{bits}} = 12$ and seed 42 held constant (Section 3.4).

Because a new concept is compared only against existing concepts in its assigned home segment, the candidate shortlist size is bounded by $s_{\max} = 10$. Over the 60-trial sweep matrix (6 sizes $\times$ 10 trials), the planned upper bound on LLM calls is 600 calls (300 calls for sensitivity setting $(2, 5)$ and 1,200 calls for $(10, 20)$; in accuracy mode, 590 / 295 / 1,180 calls) ([D-62(2)]). Although this worst-case bound identically matches Strategy C ($k = 10$), the actual candidate count per insertion is smaller: because segments bisect upon reaching $s_{\max} + 1$, the mean segment size in practice is approximately 7, so realised LLM call counts are on average lower than Strategy C.

Two methodological limitations of this formulation should be noted. First, the size-sweep benchmark evaluates an un-amortised single insertion per trial after initializing the graph via `setup()`; it therefore directly measures the single-step latency and call count of `on_inserted()`, but does not simulate long multi-step insertion streams to evaluate EraRAG's amortised theoretical bound. Second, the random hyperplane orientation is fixed by seed 42 and not varied across draws. Finally, lower candidate overlap with the exact top-10 nearest neighbours at larger graph sizes is an expected structural consequence of coarse hyperplane space partitioning; parameters were not tuned against this metric on evaluation corpora ([D-35(5)]).
```

#### 5.1.4 Evidence
- Parameter values, Gray-code ordering, bisection rule: `src/graph_insertion/strategies/bounded_bucket.py` lines 46–60, 78–81; `[D-59]`.
- Withdrawn sensitivity variants and call bounds: `[D-62]`, `docs/reports/STRAT-004-gemini-bounded-bucket.md`.
- Registry factory and seed forwarding: `src/graph_insertion/strategies/registry.py` lines 124–144; `[D-64]`.
- No tuning on evaluation corpora: `[D-35(5)]`.

#### 5.1.5 What Could Not Be Verified Offline
- EraRAG's verbatim algorithm text in arXiv:2506.20963v2 `[Unverified]`.

---

### 5.2 Item 2: Definition of $n$ in Theorem 4, and Meaning of $S_{\text{LLM}}$ (§1.1, §2.2.4, §3.5)

#### 5.2.1 Current Text
- **Location:** §1.1, line 17:
```markdown
and EraRAG [4] organizes nodes into size-bounded "buckets," such that inserting a new node only ever requires modifying one bounded bucket rather than searching the whole graph, a design for which the authors provide a formal proof (their Theorem 4) claiming an amortized insertion cost of O(Δ(nd + S_LLM)) — meaning, informally, that the cost of an insertion should not grow simply because the existing graph has grown.
```
- **Location:** §2.2.4, lines 136, 138:
```markdown
The authors formally prove this property as their Theorem 4, establishing an amortized time complexity of O(Δ(nd + S_LLM)) for inserting Δ new items — a bound that, if it holds, implies insertion cost should not increase merely because the pre-existing graph has grown larger.
...
The proof itself — while broadly consistent with established amortized-analysis techniques such as those described in Section 2.1.2 — warrants closer scrutiny: the proof's central step — asserting that repeated bucket splits and merges will not cascade without formally invoking a standard amortized-analysis technique such as a potential-function or accounting argument — falls short of the rigor typically expected of such a bound, a gap this study's proposed empirical measurement is directly designed to address.
```
- **Location:** §3.5, line 272:
```markdown
Where a strategy's underlying literature makes an explicit theoretical claim about its scaling behavior (most notably, the amortized bound proposed in [4] for bucket-based partitioning), the observed empirical curve is directly compared against that claimed bound to assess consistency, addressing Research Question 4.
```

#### 5.2.2 Problem
1. **Severe Symbol Collision on $n$:** In EraRAG [4] Theorem 4, $n$ represents the *number of random hyperplanes* ($n_{\text{bits}}$ or $b$), $d$ is embedding dimension, $\Delta$ is batch size, and $S_{\text{LLM}}$ is LLM re-summarisation cost of affected buckets across hierarchical layers. In this thesis, $n$ universally denotes *graph size* (number of existing nodes). Quoting $\mathcal{O}(\Delta(nd + S_{\text{LLM}}))$ creates an acute misinterpretation: readers may assume cost grows linearly with graph size $n$, or fail to recognise that $n$ is a constant hyperparameter.
2. **Structural Analogy vs. Direct Measurement:** In this study, insertion is strictly incremental ($\Delta = 1$), and $S_{\text{LLM}}$ represents sequential pairwise relationship decisions over at most $s_{\max}$ candidates in a single flat layer (no summarisation hierarchy). The thesis evaluates this complexity bound as a structural analogy, not a direct equivalence to EraRAG's multi-layer text-summarisation process.
3. **Negligible CPU Projection Overhead:** The hyperplane dot-product term $b \cdot d$ is a trivial CPU vector-matrix projection cost, orders of magnitude smaller than LLM inference latency and token overhead.

#### 5.2.3 Proposed Text
- **In §1.1 (line 17), replace:**
```markdown
claiming an amortized insertion cost of O(Δ(nd + S_LLM)) — meaning, informally, that the cost of an insertion should not grow simply because the existing graph has grown.
```
**with:**
```markdown
claiming an amortized insertion cost of $\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$ (originally stated in [4] using $n$ for the number of hyperplanes $b$, which this thesis renames to avoid collision with graph size $n$) — meaning, informally, that the cost of inserting $\Delta$ items should depend on the embedding dimension $d$, the fixed number of hyperplanes $b$, and the local LLM decision cost $S_{\text{LLM}}$, rather than growing with the total size of the existing graph.
```
- **In §2.2.4 (line 136), replace:**
```markdown
The authors formally prove this property as their Theorem 4, establishing an amortized time complexity of O(Δ(nd + S_LLM)) for inserting Δ new items — a bound that, if it holds, implies insertion cost should not increase merely because the pre-existing graph has grown larger.
```
**with:**
```markdown
The authors formally prove this property as their Theorem 4, establishing an amortized time complexity of $\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$ for inserting $\Delta$ new items, where $d$ is the embedding dimension, $b$ is the number of random hyperplanes (denoted $n$ in the original paper, but renamed to $b$ throughout this thesis to avoid ambiguity with graph size $n$), and $S_{\text{LLM}}$ is the cost of invoking an LLM on affected segments. In their formulation, $b \cdot d$ represents the CPU cost of computing hyperplane hash projections for the new items (a negligible dot-product overhead compared to language model inference), while $S_{\text{LLM}}$ represents the cost of re-summarizing affected text buckets across hierarchical layers. If this bound holds, it implies that insertion cost should not increase merely because the pre-existing graph has grown larger.
```
- **In §2.2.4 (line 138), append:**
```markdown
In the context of the present study, where insertion is strictly incremental ($\Delta = 1$) and restricted to a single flat layer without hierarchical summarization, $S_{\text{LLM}}$ corresponds directly to the sequential pairwise LLM decision queries over candidates within a single bounded bucket (at most $s_{\max}$ calls). Comparing empirical scaling curves against this theoretical bound therefore serves as an empirical test of the structural constant-scaling analogy, rather than an identical replication of EraRAG's multi-layer text-summarization pipeline.
```
- **In §3.5 (line 272), replace:**
```markdown
Where a strategy's underlying literature makes an explicit theoretical claim about its scaling behavior (most notably, the amortized bound proposed in [4] for bucket-based partitioning), the observed empirical curve is directly compared against that claimed bound to assess consistency, addressing Research Question 4.
```
**with:**
```markdown
Where a strategy's underlying literature makes an explicit theoretical claim about its scaling behavior (most notably, the amortized bound $\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$ proposed in [4] for bucket-based partitioning, where $b$ is the hyperplane count), the observed empirical curve is directly compared against that claimed bound as a structural analogy to assess consistency, addressing Research Question 4.
```

#### 5.2.4 Evidence
- EraRAG Theorem 4 digest and symbol definition: APC reading of arXiv:2506.20963v2; `docs/reports/STRAT-004-D-gemini-design-note.md`.
- Strategy D single-layer implementation and single-embedding caching: `src/graph_insertion/strategies/bounded_bucket.py` lines 30–35; `[D-26]`, `[D-28]`, `[D-59]`.
- Decision step contract: `[D-24]`, `[D-29]`.

#### 5.2.5 What Could Not Be Verified Offline
- The exact proof and mathematical phrasing of Theorem 4 in arXiv:2506.20963v2 `[Unverified]`.

---

### 5.3 Item 3: efSearch {64, 256} and Strategy C Index Parameters (§3.2.4 and §3.4)

#### 5.3.1 Current Text
- **Location:** §3.2.4, lines 184, 186:
```markdown
This study implements this strategy using FAISS, a widely used open-source library for efficient similarity search, configured to retrieve the top-*k* most similar existing nodes, with *k* \= 10 fixed before any experimental run and not tuned on this study's evaluation data. ... The index is a FAISS hierarchical navigable small-world (HNSW) graph with M \= 16 links per node, construction depth efConstruction \= 200 and search depth efSearch \= 128, also fixed in advance. These are common default-range settings and are not tuned on the evaluation corpora. The index is built single-threaded so that repeated runs produce identical results.
...
Sensitivity runs therefore vary *k* (5 and 20) and efSearch (64 and 256) one at a time around the primary configuration (Section 3.4). This directly addresses the open concern raised in [2] about threshold selection, by replacing a value-based cutoff with a count-based one whose effect is measured rather than assumed.
```
- **Location:** §3.4, line 266:
```markdown
*k* ∈ {5, 20} and efSearch ∈ {64, 256} for Strategy C; ... for Strategy C the number of LLM calls per insertion cannot exceed *k*, so a configuration adds at most 10 trials × 6 sizes × *k* calls (600 for *k* = 10, including each efSearch variant; 300 for *k* = 5; 1,200 for *k* = 20).
```

#### 5.3.2 Problem
1. **Rationale for efSearch 128 vs. Sensitivity Values {64, 256}:** The text does not explain why `efSearch = 128` is the primary default and why $\{64, 256\}$ were chosen for sensitivity. In synthetic benchmark testing on 384-dimensional isotropic Gaussian vectors ($n = 2,000$), mean recall@10 against exact search was 0.841 at $\text{efSearch}=64$, 0.968 at $\text{efSearch}=128$ (supporting 128 as the primary default per [D-55]), and 0.999 at $\text{efSearch}=256$ (near-converged reference condition). On clustered synthetic data, recall was $\approx 1.0$ across all settings (`docs/reports/STRAT-003-A-gemini.md`). The thesis must state that these are synthetic benchmark measurements (recall on MiniLM concept embeddings was not measured offline) and that `exact_topk_overlap` recorded in diagnostics measures approximation fidelity per trial, disentangling ANN approximation loss from embedding representation loss.
2. **Determinism Clarification:** FAISS multithreading during HNSW construction and search is non-deterministic. Setting `faiss.omp_set_num_threads(1)` guarantees strict bit-for-bit repeatability across identical runs; this is an operational choice affecting execution latency, not graph retrieval complexity ([D-47(5)]).
3. **Consistency of "Fixed a Priori":** Ensure no phrasing suggests empirical parameter calibration on evaluation corpora, strictly honoring [D-35(5)].

#### 5.3.3 Proposed Text
- **In §3.2.4 (line 184), replace:**
```markdown
configured to retrieve the top-*k* most similar existing nodes, with *k* \= 10 fixed before any experimental run and not tuned on this study's evaluation data.
```
**with:**
```markdown
configured to retrieve the top-*k* most similar existing nodes, with *k* = 10 fixed a priori before any experimental run and not tuned on this study's evaluation data ([D-35], [D-47]).
```
- **In §3.2.4 (line 184), replace:**
```markdown
The index is a FAISS hierarchical navigable small-world (HNSW) graph with M \= 16 links per node, construction depth efConstruction \= 200 and search depth efSearch \= 128, also fixed in advance. These are common default-range settings and are not tuned on the evaluation corpora. The index is built single-threaded so that repeated runs produce identical results.
```
**with:**
```markdown
The index is a FAISS hierarchical navigable small-world (HNSW) graph with M = 16 links per node, construction depth efConstruction = 200, and query search depth efSearch = 128, all fixed a priori before experimental execution ([D-47], [D-55]). The parameters M = 16 and efConstruction = 200 are set within the standard operational range recommended for HNSW graph construction and used by common vector libraries, held constant without tuning on the evaluation corpora; their influence is not varied beyond the pre-specified efSearch sensitivity runs. Index construction and querying are executed strictly single-threaded (via FAISS OpenMP controls) to guarantee identical, deterministic results across repeated runs without altering vector search complexity ([D-47]).
```
- **In §3.2.4 (line 186), replace:**
```markdown
Sensitivity runs therefore vary *k* (5 and 20) and efSearch (64 and 256) one at a time around the primary configuration (Section 3.4). This directly addresses the open concern raised in [2] about threshold selection, by replacing a value-based cutoff with a count-based one whose effect is measured rather than assumed.
```
**with:**
```markdown
Sensitivity runs vary *k* ∈ {5, 20} (with planned call bounds of 300 and 1,200 over the sweep matrix) and efSearch ∈ {64, 256} one at a time around the primary configuration (Section 3.4), where call bounds depend strictly on *k* and are independent of efSearch. The choice of primary efSearch = 128 and sensitivity variants {64, 256} is supported by synthetic benchmark evaluations on 384-dimensional isotropic Gaussian vectors (n = 2,000), where mean recall@10 against exact search was 0.841 at efSearch = 64, 0.968 at efSearch = 128, and 0.999 at efSearch = 256 (serving as a near-converged reference condition), while clustered synthetic vectors achieved approximately 1.0 recall across all settings. These figures represent synthetic baseline measurements rather than domain concept embeddings; for every insertion, the diagnostic metric `exact_topk_overlap` directly records the realized fraction of candidates matching exact cosine search, separating ANN approximation loss from embedding representation fidelity. This directly addresses the open concern raised in [2] about threshold selection, by replacing a value-based cutoff with a count-based one whose effect is measured rather than assumed.
```

#### 5.3.4 Evidence
- Strategy C specifications, FAISS bindings, OpenMP thread pinning: `src/graph_insertion/strategies/ann_retrieval.py` lines 38–45, 108–115; `[D-47]`, `[D-55]`.
- Synthetic recall benchmark numbers (0.841, 0.968, 0.999): `docs/reports/STRAT-003-A-gemini.md` Section 6.
- Call bounds (300 / 600 / 1,200): `[D-41]`, `[D-62(2)]`.

#### 5.3.5 What Could Not Be Verified Offline
- Offline recall of FAISS HNSW on domain concept names from DSA/Metacademy (only synthetic Gaussian and clustered benchmarks were evaluated) `[Confirmed]`.

---

### 5.4 Item 4: The Uncited $M=16$ and $\text{efConstruction}=200$ Defaults (§3.2.4)

#### 5.4.1 Current Text
- **Location:** §3.2.4, line 184:
```markdown
The index is a FAISS hierarchical navigable small-world (HNSW) graph with M \= 16 links per node, construction depth efConstruction \= 200 and search depth efSearch \= 128, also fixed in advance. These are common default-range settings and are not tuned on the evaluation corpora.
```

#### 5.4.2 Problem
The phrase "These are common default-range settings and are not tuned on the evaluation corpora" lacks a primary academic citation. However, because agents have no internet or arXiv access, inventing a citation with unverified page numbers or asserting facts from memory would risk introducing errors into the thesis.

#### 5.4.3 Deliverables
**(a) Fallback Rewording (Applied in Proposed Diff):**
Reword cleanly to state the values are fixed a priori within standard operational ranges used by HNSW implementations and vector libraries, held constant without tuning on evaluation data:
```markdown
The parameters M = 16 and efConstruction = 200 are set within the standard operational range recommended for HNSW graph construction and used by common vector libraries, held constant without tuning on the evaluation corpora; their influence is not varied beyond the pre-specified efSearch sensitivity runs.
```

**(b) Candidate Primary Sources Tagged `[Unverified]` for Luke / Adviser Verification:**
1. **HNSW Paper:**
   - *Citation:* Y. A. Malkov and D. A. Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 42, no. 4, pp. 824–836, Apr. 2020, doi: 10.1109/TPAMI.2018.2889473. (Preprint arXiv:1603.09320, 2016/2018). `[Unverified]`
   - *What Luke should check:* Sections 4 and 5, specifically the authors' discussion of parameter selection recommending $M \in [12, 48]$ for high-dimensional vectors and $\text{efConstruction} \in [100, 200]$ as a construction trade-off.
2. **FAISS Paper:**
   - *Citation:* J. Johnson, M. Douze, and H. Jégou, "Billion-scale similarity search with GPUs," *IEEE Transactions on Big Data*, vol. 7, no. 3, pp. 535–547, 2021, doi: 10.1109/TBDATA.2019.2921572. (Preprint arXiv:1702.08734, 2017). `[Unverified]`
   - *What Luke should check:* Section III-B / IV on CPU HNSW indexing and default parameter configurations in FAISS.

**(c) Proposed Bibliography Entries (IEEE Style, `[Unverified]`):**
```text
[11] Y. A. Malkov and D. A. Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 42, no. 4, pp. 824–836, Apr. 2020, doi: 10.1109/TPAMI.2018.2889473. [Unverified]

[12] J. Johnson, M. Douze, and H. Jégou, "Billion-scale similarity search with GPUs," IEEE Transactions on Big Data, vol. 7, no. 3, pp. 535–547, 2021, doi: 10.1109/TBDATA.2019.2921572. [Unverified]
```
*(Note: These entries are NOT applied in the proposed diff; they are provided here for Luke and the adviser to review and insert if formal citations are preferred).*

**(d) Recommendation:**
Adopt the fallback rewording in the main text (as implemented in the proposed diff). Adding explicit citations should only occur after Luke verifies the exact page numbers and parameter recommendations in the primary literature.

---

### 5.5 Item 5: $\theta = 0.6$ Calibration Limitation (§1.5, §3.2.3, §3.4)

#### 5.5.1 Current Text
- **Location:** §1.5 (Scope and Limitations), line 68:
```markdown
Concepts are represented strictly by their canonical names, without per-node expository text, definitions, or structural summaries. Strategies B, C, and D embed bare concept names, so candidate narrowing and relationship evaluation depend on the models' parametric knowledge. A single decision-step model and a single fixed prompt are used across all strategies. The accuracy attainable from bare names is bounded by an empirical baseline established in leave-one-out testing on the DSA benchmark, which gave a micro F1 of 0.541, micro recall of 0.611, micro precision of 0.485, a direction-flip rate of 15.38%, and a swap consistency of 85.71%. The synthetic concept pool used to extend the cost-scaling measurements to 2,000 nodes was generated by a model accessed through a web interface; it carries no ground-truth edges and is used only to measure cost and latency scaling.
```
- **Location:** §3.2.3, line 180:
```markdown
Following the precedent established in [2], the threshold is fixed at 0.6 before any experimental run and is not tuned on this study's own evaluation data; this keeps the shortlist rule from being adjusted after seeing results. To show how sensitive the findings are to this choice, the threshold is additionally evaluated at 0.4 and 0.5 as separate sensitivity runs (Section 3.4). Similarity is computed as cosine similarity between embeddings produced by the all-MiniLM-L6-v2 sentence-embedding model run locally on CPU, and the shortlist may be empty, in which case no LLM call is made for that insertion.
```
- **Location:** §3.4, line 266:
```markdown
θ ∈ {0.4, 0.5} for Strategy B;
```

#### 5.5.2 Problem
1. **Uncalibrated Heuristic from Different Embedding Model:** Reference [2] (iText2KG) utilized a similarity threshold $\approx 0.6$ with a different embedding model and application. It was adopted directly as an a priori heuristic in this study without calibration for `all-MiniLM-L6-v2`.
2. **Asymmetric Sensitivity Grid:** Both sensitivity values ($\theta \in \{0.4, 0.5\}$) are looser than the default $\theta = 0.6$. The study evaluates the impact of looser filtering, but does not test sensitivity to stricter thresholds ($\theta > 0.6$). This asymmetry should be explicitly declared as a limitation.
3. **Uncapped Candidate List Consequence:** Strategy B shortlists *all* existing nodes exceeding $\theta$. As $\theta$ decreases (e.g., at 0.4), candidate counts expand dramatically, approaching brute-force cost (up to $n$ calls per insertion, bounded only by the safety guard of 38,500 calls across the sweep matrix [D-41]).

#### 5.5.3 Proposed Text
- **In §1.5 (line 68), append to the end of the section:**
```markdown
Additionally, for Strategy B (embedding-similarity thresholding), the primary similarity threshold $\theta = 0.6$ is an uncalibrated heuristic adopted a priori from prior literature ([2]) where it was used with a different embedding model; it was not calibrated or tuned for the all-MiniLM-L6-v2 model on the evaluation datasets. Because both sensitivity values evaluated ($\theta \in \{0.4, 0.5\}$) are lower than the default, the study explores looser filtering—where candidate shortlists expand and call counts approach brute-force cost—but does not evaluate sensitivity to stricter thresholds ($\theta > 0.6$).
```
- **In §3.2.3 (line 180), replace:**
```markdown
Following the precedent established in [2], the threshold is fixed at 0.6 before any experimental run and is not tuned on this study's own evaluation data; this keeps the shortlist rule from being adjusted after seeing results. To show how sensitive the findings are to this choice, the threshold is additionally evaluated at 0.4 and 0.5 as separate sensitivity runs (Section 3.4). Similarity is computed as cosine similarity between embeddings produced by the all-MiniLM-L6-v2 sentence-embedding model run locally on CPU, and the shortlist may be empty, in which case no LLM call is made for that insertion.
```
**with:**
```markdown
Following the precedent established in [2], the threshold is fixed a priori at $\theta = 0.6$ from the literature and is not calibrated or tuned on this study's evaluation data ([D-35], [D-46]); this keeps the shortlist rule from being adjusted after seeing results. To show how sensitive the findings are to this choice, the threshold is additionally evaluated at $\theta \in \{0.4, 0.5\}$ as separate one-at-a-time sensitivity runs (Section 3.4). Similarity is computed as cosine similarity between embeddings produced by the all-MiniLM-L6-v2 sentence-embedding model run locally on CPU, and the shortlist may be empty, in which case no LLM call is made for that insertion. Because Strategy B does not cap the shortlist size, an insertion may shortlist up to $n$ existing nodes if their similarity exceeds the threshold (yielding a worst-case bound of up to 38,500 LLM calls across the sweep matrix [D-41]); looser thresholds such as $\theta = 0.4$ can therefore cause candidate counts and latency to approach brute-force cost.
```
- **In §3.4 (line 266), replace:**
```markdown
For brute force the cost bound is determined by the graph size; for Strategy C the number of LLM calls per insertion cannot exceed *k*, so a configuration adds at most 10 trials × 6 sizes × *k* calls (600 for *k* = 10, including each efSearch variant; 300 for *k* = 5; 1,200 for *k* = 20). The same planned upper bounds apply to Strategy D with s_max in place of *k* (600, 300 and 1,200 for s_max = 10, 5 and 20); because bucket sizes lie between s_min and s_max, its actual call counts are expected to be lower.
```
**with:**
```markdown
For brute force the cost bound is determined directly by graph size n; Strategy B is uncapped and may shortlist up to n existing concepts if similarities exceed θ (up to 38,500 calls across the sweep matrix [D-41]); for Strategy C the number of LLM calls per insertion cannot exceed *k*, adding at most 10 trials × 6 sizes × *k* calls (600 for *k* = 10, including each efSearch variant; 300 for *k* = 5; 1,200 for *k* = 20), independent of efSearch. The same planned upper bounds apply to Strategy D with s_max in place of *k* (600, 300, and 1,200 calls for s_max = 10, 5, and 20 over the sweep matrix; 590, 295, and 1,180 calls in accuracy mode); because bucket sizes lie between s_min and s_max with midpoint bisection producing a mean segment size of approximately 7, Strategy D's realized call counts are substantially lower on average.
```

#### 5.5.4 Evidence
- Threshold adoption and sensitivity grid: `[D-35(5)]`, `[D-46]`.
- Uncapped shortlist bound of 38,500 calls: `[D-41]`.
- Embedding implementation: `src/graph_insertion/strategies/embedding_threshold.py`.

#### 5.5.5 What Could Not Be Verified Offline
- The exact embedding model and calibration details in Lairgi et al. [2] `[Unverified]`.

---

## 6. Consistency Sweep

A comprehensive sweep across the canonical thesis identified all locations where strategy terminology, bounds, and parameters appear:

1. **Section 1.1 (Background and Context, line 17):**
   - *Term:* EraRAG Theorem 4 complexity bound.
   - *Status:* Updated in proposed diff to $\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$ to resolve symbol collision with graph size $n$.
2. **Section 1.2 (Statement of the Problem, line 36 — RQ4):**
   - *Text:* `4. To what extent do the empirical cost-scaling behaviors observed in this study match the theoretical complexity claims made in existing literature — specifically, the amortized bound proposed by [4] for bucket-based insertion?`
   - *Analysis:* The phrasing accurately introduces the high-level research question. As discussed under Item 2, the formal structural analogy is defined in §1.1, §2.2.4, and §3.5; keeping RQ4 clean and uncluttered avoids premature technical exposition in the problem statement.
3. **Section 1.3 (Objectives, line 47 — Objective 4):**
   - *Text:* `4. To analyze whether the observed cost-scaling behavior is consistent with the theoretical complexity claims found in [4].`
   - *Analysis:* Consistent with RQ4; no change required.
4. **Section 1.5 (Scope and Limitations, line 68):**
   - *Term:* Zero-shot formulation limitations and synthetic concept pool purpose.
   - *Status:* Updated in proposed diff to add the Strategy B $\theta=0.6$ calibration limitation and sensitivity asymmetry.
5. **Section 2.2.4 (Bounded-Structure Updates, lines 136, 138):**
   - *Term:* Theorem 4 statement and EraRAG experimental limitations.
   - *Status:* Updated in proposed diff to define $b$, scope $S_{\text{LLM}}$ to single-layer pairwise candidate decisions, and frame the evaluation as a structural constant-scaling analogy.
6. **Section 3.2.3 (Strategy B, line 180):**
   - *Term:* $\theta = 0.6$ and sensitivity runs.
   - *Status:* Updated in proposed diff to specify a priori literature adoption, uncalibrated nature, and uncapped candidate call count risks.
7. **Section 3.2.4 (Strategy C, lines 184, 186):**
   - *Term:* HNSW index parameters, FAISS configuration, sensitivity runs.
   - *Status:* Updated in proposed diff to include synthetic Gaussian recall evidence, single-threaded determinism, and fallback rewording for $M=16, \text{efConstruction}=200$.
8. **Section 3.2.5 (Strategy D, line 190):**
   - *Term:* Bounded-bucket partitioning.
   - *Status:* Substantially expanded in proposed diff to specify $s_{\min}=5, s_{\max}=10, n_{\text{bits}}=12$, seed 42, Gray-curve 1D linearisation, midpoint bisection, call bounds, mean shortlist size $\approx 7$, and methodological limitations.
9. **Section 3.4 (Experimental Procedure, line 266):**
   - *Term:* Parameter fixing and sensitivity paragraph.
   - *Status:* Updated in proposed diff to incorporate Strategy B's uncapped bound (38,500), Strategy C's independence from efSearch, and Strategy D's call bounds and mean shortlist capacity.
10. **Section 3.5 (Data Analysis, line 272):**
    - *Term:* Comparison against Theorem 4 amortized bound.
    - *Status:* Updated in proposed diff to include the structural analogy notation.

---

## 7. For Luke to Verify Against Sources Before Submission

Before final submission of the thesis, Luke should verify the following four items against original primary literature:

1. **EraRAG Theorem 4 (arXiv:2506.20963v2):**
   - Verify the exact mathematical statement of Theorem 4 in the paper.
   - Confirm that $n$ is defined as the number of random hyperplanes ($n_{\text{bits}}$), $d$ as embedding dimension, $\Delta$ as chunk batch size, and $S_{\text{LLM}}$ as the cost of LLM re-summarisation across hierarchical layers.
   - Confirm the proof's condition $1 < S_{\min} \le S_{\max} = \mathcal{O}(1)$ and whether the amortisation relies on a potential function or an accounting argument.
2. **HNSW and FAISS Parameter Defaults:**
   - Verify in Malkov & Yashunin (2018/2020) (IEEE TPAMI) Section 4/5 whether $M \in [12, 48]$ and $\text{efConstruction} \in [100, 200]$ are explicitly recommended as general-purpose operational defaults.
   - Verify in Johnson et al. (2019/2021) (IEEE TBD) or the FAISS documentation whether $M=16$ and $\text{efConstruction}=200$ match default FAISS index settings.
3. **Origin of $\theta = 0.6$ in iText2KG:**
   - Verify in Lairgi et al. [2] (WISE 2024) whether $\theta \approx 0.6$ was determined by a threshold sweep on their benchmark corpus or cited from prior work, and note which sentence transformer model was used in their experiments.
4. **Symbol Selection for Hyperplane Count:**
   - Confirm with the thesis adviser whether $b$ (as adopted in the proposed diff) or $n_{\text{bits}}$ is preferred to replace $n$ in the discussion of Theorem 4 to avoid collision with graph size $n$.

---

## 8. Open Questions (Tagged for Luke or Adviser)

1. `[Adviser / Luke]` **Symbol for Hyperplane Count in Theorem 4:**
   In Theorem 4 of EraRAG, the authors used $n$ for the number of random hyperplanes. In the thesis, $n$ is reserved for graph size. The proposed diff uses $b$ (i.e., $\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$). Does the adviser prefer $b$, $n_{\text{bits}}$, or another notation?
2. `[Adviser]` **Sensitivity Grid Asymmetry for Strategy B ($\theta$):**
   The sensitivity values evaluated for Strategy B are $\theta \in \{0.4, 0.5\}$, both looser than the primary threshold $\theta = 0.6$. This explores the behavior of looser filtering (where candidate lists expand and call counts approach brute-force cost), but does not test sensitivity to stricter filtering (e.g., $\theta = 0.7$). Should a stricter threshold be added, or is the current asymmetric grid acceptable as an exploration of candidate-expansion behavior?
3. `[Adviser / Luke]` **Citation vs. Rewording for Strategy C HNSW Parameters:**
   Does the adviser prefer citing Malkov & Yashunin (2018) and Johnson et al. (2019) explicitly once page numbers are verified, or retaining the clean fallback rewording stating that $M=16$ and $\text{efConstruction}=200$ are standard library operational defaults fixed a priori without tuning?
4. `[Adviser / Luke]` **Experimental Modes per Configuration across the 12 Configurations:**
   Across the 12 experimental configurations (4 primary + 8 sensitivity), the exact assignment of modes (sweep mode up to $n=2,000$ vs. gold-standard accuracy mode on DSA/Metacademy) remains open. Should all 12 configurations be run across both sweep and accuracy modes, or should sensitivity runs be evaluated in sweep mode only?
5. `[Adviser]` **Inclusion of a Decision-Step Micro-Benchmark:**
   Should a standalone micro-benchmark evaluating the LLM pairwise decision step in isolation be added to the thesis, or does the leave-one-out baseline validation on DSA ([D-37]) provide sufficient characterization of the decision step's baseline accuracy?

---

## 9. Found but Not Changed

1. **Reference `[8]` in Bibliography:**
   - In lines 294–295 of the canonical thesis, reference `[8]` is currently `[8] TBC`. This placeholder slot was noted in `docs/context/complete-context.md` line 187. Because resolving reference `[8]` requires external bibliographic assignment by Luke and his adviser, it was not modified.
2. **High-Level Phrasing of RQ4 and Objective 4:**
   - In line 36 (§1.2) and line 47 (§1.3), Research Question 4 and Objective 4 refer generally to "the theoretical complexity claims made in existing literature — specifically, the amortized bound proposed by [4] for bucket-based insertion". As noted in the consistency sweep, high-level research questions and objectives should remain readable and concise. The precise mathematical symbol resolution ($b$) and structural analogy definitions were placed in §1.1, §2.2.4, and §3.5, leaving RQ4 unchanged.
3. **Table Formatting in Methodology:**
   - The thesis text currently structures parameter descriptions in clear paragraphs (§3.2 and §3.4) rather than a Markdown summary table. Introducing a new summary table was avoided to preserve the author's narrative flow and styling.

---

## 10. Verification Artifacts

### 10.1 File Hashes and Line Counts (Untouched Repository Copies)
```text
$ sha256sum "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md" docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md docs/reports/to-be-shared/thesis-orientation.md
15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
3081fce128521995592c6ae82f0767e140dbfa4e2f59ae3bb34322df29233c98  docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md
9d81ba8a1ef46791fb66775f92c501d06210d733566ac52259f186e7f6270c3a  docs/reports/to-be-shared/thesis-orientation.md

$ wc -l "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md" docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md docs/reports/to-be-shared/thesis-orientation.md
297 docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
 94 docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md
 51 docs/reports/to-be-shared/thesis-orientation.md
442 total
```

### 10.2 Proposed Diff Validation
```text
$ patch --dry-run -p0 -i docs/reports/DOC-004-gemini-thesis-proposed.diff
checking file 'docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md'

$ git apply -p0 --check docs/reports/DOC-004-gemini-thesis-proposed.diff
(exit code 0, clean check)
```
