# DOC-004-A Report: Amend the DOC-004 Thesis-Sync Proposal (Proposed Edits Only)

Date: 2026-10-14  
Task ID: `DOC-004-A`  
Branch: `master`  
Decision ID: None (decision log unmodified)  

---

## 1. Identity and Independence

- **Agent Name / Tool:** Antigravity / Gemini
- **Model Label:** `Gemini 3.8 Flash (Medium)` (exact tool label reported by platform)
- **Session / Conversation ID:** `512aecca-d185-438b-b8e7-d6dba3b507fb`
- **Independence Confirmation:** Confirmed fresh session. Excluded session `098dcdd4-c444-4fcd-af8f-1b2054b31802` (which authored DOC-004, DOC-005, and INFRA-007-P/Q) and excluded prefixes `455d24de…`, `b8ab4203…`, `900404ed…`, `2b098fc9…`, and `ede0cb54…` are all distinct from this session ID.
- **Task ID Verification:** `DOC-004-A` verified unused in `docs/tasks/status.md` and `docs/reports/`.
- **Decision ID:** None allocated; `docs/decisions/decision-log.md` is strictly read-only for this task.

---

## 2. Verification of APC Findings (F-1 to F-5, S-1 to S-5)

### Must-Fix Findings

- **F-1. Out of sync with D-68:** **Agree.**  
  *Evidence:* In `docs/reports/DOC-004-gemini-thesis-proposed.diff`, lines 29 and 73, the proposed text still claimed that the empirical curve is "directly compared against that claimed bound as a structural analogy" (§3.5), called the benchmark "an empirical test of the structural constant-scaling analogy" (§2.2.4), and left §2.2.4's phrase "a gap this study's proposed empirical measurement is directly designed to address" in place. Under [D-68](1), [D-68](6)(c), and [D-69](5), no multi-insertion benchmark is run; the sweep evaluates an un-amortised single insertion per trial after `setup()`, so `update_s` measures one un-amortised step and cannot evaluate EraRAG's multi-insertion amortisation claim (Theorem 4). In this replacement proposal, all overclaiming phrases are replaced with explicit statements of the single-step limitation, without touching RQ4 (§1.2) or Objective 4 (§1.3).
- **F-2. Unmeasured claim stated as fact:** **Agree.**  
  *Evidence:* DOC-004 proposed text asserted that "the mean segment size in practice is approximately 7, so realised LLM call counts are on average lower than Strategy C" (§3.2.5) and "Strategy D's realized call counts are substantially lower on average" (§3.4). These statements derive an expectation from the range $[s_{\min}, s_{\max}] = [5, 10]$ ([D-62](3)), but nobody has measured the empirical distribution across trials, and mean segment size differs from the specific segment a new node enters. Furthermore, [D-70](1) withdrew the analogous unmeasured claim for Strategy 2. All such claims are dropped; the text states only that candidate counts cannot exceed $s_{\max}$, with realised calls measured empirically.
- **F-3. Unverified claims inside proposed sentences:** **Agree.**  
  *Evidence:* DOC-004 embedded several paper-dependent claims directly in the diff rather than gating them for Luke to check: (a) that EraRAG's Theorem 4 originally denoted hyperplanes as $n$ and that $S_{\text{LLM}}$ represents "re-summarizing affected text buckets across hierarchical layers" (§1.1, §2.2.4); (b) that $\theta = 0.6$ was "used with a different embedding model" in [2] (§1.5); (c) that EraRAG buckets are "merged with Hamming-adjacent buckets" (§3.2.5, whereas [D-59](7) notes the paper does not specify merge adjacency ordering); (d) that $M=16, \text{efConstruction}=200$ fall within "the standard operational range recommended for HNSW" (§3.2.4). All such claims have been removed from the core diff and either moved to the gated diff or discarded.
- **F-4. Neighbour rule misdescribed:** **Agree.**  
  *Evidence:* DOC-004 described the undersize segment merge rule as "merged with their nearest Gray-curve neighbour (breaking ties by lower index)". In `src/graph_insertion/strategies/bounded_bucket.py` lines 270–288, `_choose_neighbour` computes a 4-tuple for candidate neighbours: `(hamming_at_touching_endpoints, gray_gap_at_touching_endpoints, neighbour_size, side_tiebreak)`. Because `left_key <= right_key` selects the left neighbour, the **smaller** neighbour wins on size (`len(seg)`), and ties break to the left (side 0 vs 1). The replacement diff accurately describes this 4-tuple rule.
- **F-5. Decision IDs in thesis prose:** **Agree.**  
  *Evidence:* The DOC-004 diff added 19 citations of `[D-nn]` into Chapter 1, 2, and 3 prose. The thesis uses square brackets exclusively for literature citations (`[1]`, `[2]`, `[4]`). All decision IDs have been removed from the thesis diffs and are documented in this report's provenance table.

### Should-Fix Findings

- **S-1. Plain-text maths vs. LaTeX:** **Agree.**  
  *Evidence:* DOC-004 introduced heavy LaTeX math environments (`$\mathcal{O}(\Delta(b \cdot d + S_{\text{LLM}}))$`, `$s_{\min} = 5$`, `$\theta \in \{0.4, 0.5\}$`) into a thesis that consistently uses plain-text math notation (`O(Δ(nd + S_LLM))`, $\theta$, *k*, s_min). The replacement diffs adhere strictly to the thesis's plain-text math style and preserve line-level escaping conventions (`\[4\]`, `\=`).
- **S-2. Hyperplane count tied to Strategy D's `n_bits`:** **Agree.**  
  *Evidence:* In the gated diff, the renamed theorem parameter $b$ is explicitly linked to Strategy D's `n_bits = 12` configuration.
- **S-3. FAISS citation candidate and defaults:** **Agree.**  
  *Evidence:* Johnson et al. (2019) is a GPU similarity search paper, not an HNSW reference. Furthermore, host verification via FAISS 1.15.1 (`IndexHNSWFlat(8, 16)`) confirmed that FAISS library defaults are `efConstruction = 40` and `efSearch = 16`. The core diff states factually that $M=16$, $\text{efConstruction}=200$, and $\text{efSearch}=128$ are fixed a priori and differ from library defaults, without making uncited "standard operational range" assertions.
- **S-4. Decision-step micro-benchmark distinct from amortised benchmark:** **Agree.**  
  *Evidence:* [D-68](1) explicitly states that the decision-step micro-benchmark (evaluating pairwise LLM inference in isolation without narrowing) is distinct from the amortised multi-insertion benchmark dropped under D1, and remains unsettled awaiting adviser input.
- **S-5. Report errata for DOC-004 report:** **Agree.**  
  *Evidence:* Documented below in Section 8 of this report.

---

## 3. What Changed Versus the DOC-004 Diff

1. **Chapter 1, §1.1:**
   - *DOC-004:* Embedded Theorem 4 notation renaming ($n \to b$) and $S_{\text{LLM}}$ interpretation in LaTeX in the primary diff.
   - *DOC-004-A:* Left unmodified in the core diff. The notation change is isolated in `DOC-004-A-gemini-thesis-gated.diff` using plain-text math, explicitly tied to `n_bits = 12`.
2. **Chapter 1, §1.5 (Scope and Limitations):**
   - *DOC-004:* Added unverified claim that [2] used a different embedding model; used LaTeX $\theta$.
   - *DOC-004-A:* Preserves plain-text math ($\theta = 0.6$). Accurately records that sensitivity runs explore looser filtering ($\theta \in \{0.4, 0.5\}$) where shortlists expand, without evaluating stricter thresholds ($\theta > 0.6$). Notes that shortlists under Strategy B are uncapped by design (up to $n$ candidates). Omits unverified claims about [2]'s model.
3. **Chapter 2, §2.2.4:**
   - *DOC-004:* Retained "a gap this study's proposed empirical measurement is directly designed to address" and framed the single-step insertion as an "empirical test of the structural constant-scaling analogy".
   - *DOC-004-A:* Replaced the overclaiming phrase with a direct, factual statement that the size-sweep protocol evaluates an un-amortised single step per trial after `setup()`, so `update_s` measures an un-amortised single step and does not evaluate EraRAG's multi-insertion amortisation claim. In the gated diff, $n$ is renamed to $b$ and $S_{\text{LLM}}$ is clarified as pairwise queries over at most $s_{\max}$ candidates.
4. **Chapter 3, §3.2.3 (Strategy B):**
   - *DOC-004:* Included decision citations `[D-35]`, `[D-41]`, `[D-46]`; used LaTeX $\theta$.
   - *DOC-004-A:* Uses plain-text math; removes decision IDs. Records worst-case planned bounds (38,500 sweep, 5,012 accuracy) and incorporates the [D-70](1) wording: realised calls depend on concepts exceeding $\theta$, are not known before the run, and for lower $\theta$ may approach brute force.
5. **Chapter 3, §3.2.4 (Strategy C):**
   - *DOC-004:* Included decision IDs `[D-47]`, `[D-55]`; called parameters "recommended"; cited synthetic recall.
   - *DOC-004-A:* Removes decision IDs and "recommended" phrasing. Factual statement that parameters differ from library defaults (`efConstruction = 40`, `efSearch = 16` in FAISS 1.15.1). Quotes synthetic recall figures strictly per `STRAT-003-A-gemini.md` section 6 (0.841 at 64, 0.968 at 128, 0.999 at 256 for isotropic Gaussian vectors; 0.999 across all settings for clustered vectors). Notes MiniLM recall on domain corpora is unmeasured prior to execution and monitored by `exact_topk_overlap`.
6. **Chapter 3, §3.2.5 (Strategy D):**
   - *DOC-004:* Asserted mean segment size "approximately 7" and "substantially lower" calls; misdescribed merge rule; claimed EraRAG merged "Hamming-adjacent" buckets; used LaTeX math; included 6 decision citations.
   - *DOC-004-A:* Drops "approximately 7" and "substantially lower" completely. Accurately describes EraRAG attribution per [D-59](7) and this study's concrete linearisation (Gray-curve grouping, midpoint bisection, 4-tuple neighbour selection with smaller neighbour winning on size). Cites exact worst-case bounds (600/300/1,200 sweep; 590/295/1,180 accuracy), notes that equal bounds with Strategy C mean the comparison does not isolate geometry from shortlist capacity, and records the three D-62 limitations (un-amortised single step, fixed seed 42, and lower `exact_topk_overlap` as an expected structural property).
7. **Chapter 3, §3.4:**
   - *DOC-004:* Asserted mean segment size 7 and substantially lower calls; included 4 decision IDs.
   - *DOC-004-A:* Drops unmeasured assertions; removes decision IDs; documents uncapped Strategy B bounds (38,500 sweep, 5,012 accuracy) and that Strategy C/D bounds are independent of `efSearch` and tied to $s_{\max}$.
8. **Chapter 3, §3.5:**
   - *DOC-004:* Retained "the observed empirical curve is directly compared against that claimed bound as a structural analogy to assess consistency, addressing Research Question 4".
   - *DOC-004-A:* Replaced with text stating that because the protocol measures an un-amortised single step per trial after setup, the empirical curve characterizes single-insertion cost scaling rather than evaluating the sequential amortized bound in [4], with the framing against RQ4 noted as a methodological boundary awaiting adviser guidance.

---

## 4. Provenance Table for Core Diff

Every added sentence in `docs/reports/DOC-004-A-gemini-thesis-core.diff` is mapped to its exact repository authority below:

| Thesis Section | Added Sentence / Clause | Repository Source / Provenance Authority |
|---|---|---|
| **§1.5** | Primary similarity threshold θ = 0.6 fixed a priori following [2] and not calibrated or tuned on evaluation datasets. | [D-35](5), [D-46], thesis §1.5, §3.2.3 |
| **§1.5** | Sensitivity values θ ∈ {0.4, 0.5} explore looser filtering where shortlists expand, without evaluating stricter thresholds (θ > 0.6). | [D-64](4), `scripts/README.md` lines 193–194, 216–217 |
| **§1.5** | Candidate shortlists under Strategy B are uncapped by design, returning up to n existing nodes. | [D-41](1), [D-68](2), `embedding_threshold.py:max_candidates()`, `scripts/README.md:226` |
| **§2.2.4** | Size-sweep protocol evaluates an un-amortised single insertion per trial after setup(); update_s measures a single un-amortised step and does not evaluate EraRAG's multi-insertion amortisation claim. | [D-68](1), [D-68](6)(c), [D-69](5), `scripts/README.md` Section 1 |
| **§3.2.3** | Shortlist uncapped up to n existing nodes (yielding worst-case planned bound up to 38,500 sweep calls, 5,012 accuracy calls). | [D-41](1), [D-64](4), [D-68](2), `scripts/README.md:213,226` |
| **§3.2.3** | Realised calls depend on concepts exceeding θ, are not known before the run, and for lower θ may approach brute force. | [D-70](1), `scripts/README.md:226` |
| **§3.2.4** | Index is FAISS HNSW graph with M = 16, efConstruction = 200, efSearch = 128, fixed in advance and not tuned on evaluation corpora. | [D-47](1), [D-55](2), `ann_retrieval.py:70-85`, `scripts/README.md:214` |
| **§3.2.4** | Values differ from FAISS library defaults (FAISS 1.15.1 defaults to efConstruction = 40, efSearch = 16). | Host environment verification via FAISS 1.15.1 (`IndexHNSWFlat(8, 16)`) |
| **§3.2.4** | Index built and queried single-threaded (via FAISS thread controls) for deterministic results without altering vector search complexity. | [D-47](3), [D-68](5), `ann_retrieval.py:235,310` |
| **§3.2.4** | Sensitivity runs vary k ∈ {5, 20} (bounds 300, 1,200 sweep; 295, 1,180 accuracy) and efSearch ∈ {64, 256}, where call bounds are independent of efSearch. | [D-64](4), [D-68](2), `scripts/README.md:218-221` |
| **§3.2.4** | efSearch calibrated via synthetic measurements on 384-d isotropic Gaussian vectors (recall@10 was 0.841 at 64, 0.968 at 128, 0.999 at 256; clustered vectors achieved 0.999). | [D-55](2), `docs/reports/STRAT-003-A-gemini.md` section 6 (lines 236–244) |
| **§3.2.4** | Figures represent synthetic baseline; MiniLM recall on domain embeddings is unmeasured prior to run and monitored via `exact_topk_overlap`. | [D-55](2), `ann_retrieval.py:diagnostics()` |
| **§3.2.5** | EraRAG paper provides hyperplane-LSH partitioning and [s_min, s_max] split/merge lifecycle, but leaves oversize-split and merge-adjacency ordering unspecified. | [D-59](7), `bounded_bucket.py` docstrings |
| **§3.2.5** | Operational specification implements 1D linearisation: Gray-curve grouping, midpoint bisection (`len // 2`), and undersize merge via 4-tuple comparison where smaller neighbour wins on size and ties break left. | [D-59](3), [D-59](7), `bounded_bucket.py:270-288` (`_choose_neighbour`) |
| **§3.2.5** | Parameters fixed a priori: s_min = 5, s_max = 10, n_bits = 12, seed 42. n_bits = 12 justified by code space ($2^{12} = 4,096 > 2,000$). Sensitivity (s_min, s_max) ∈ {(2, 5), (10, 20)}. | [D-59](4), [D-64](4), `bounded_bucket.py:145-155`, `scripts/README.md:215,222-223` |
| **§3.2.5** | Planned upper bounds 600 sweep calls (300 for (2, 5), 1,200 for (10, 20); 590, 295, 1,180 accuracy). Candidate counts cannot exceed s_max; realised calls measured empirically. | [D-59](2), [D-62](2), [D-68](2), `scripts/README.md:215` |
| **§3.2.5** | Equal worst-case bounds with Strategy C (k = 10) mean comparison does not isolate partitioning geometry from shortlist capacity. | [D-62](3) |
| **§3.2.5** | Methodological limitations: un-amortised single insertion per trial after setup(); fixed seed 42; lower top-10 candidate overlap at larger n is an expected structural consequence. | [D-35](5), [D-62](4), [D-68](1) |
| **§3.4** | Strategy B uncapped up to n candidates (up to 38,500 sweep, 5,012 accuracy calls); Strategy C/D bounds (600, 300, 1,200) independent of efSearch; candidate counts at most s_max and realised counts measured experimentally. | [D-64](4), [D-68](2), `scripts/README.md:211-224` |
| **§3.5** | For Strategy D, empirical curve characterizes single-insertion cost scaling rather than evaluating the sequential amortized bound in [4]; framing against RQ4 noted as methodological boundary. | [D-68](1), [D-68](6)(c), [D-69](5) |

---

## 5. Check Output (§4.2 Verifications)

### 5.1 Host FAISS Defaults Check
```bash
.venv-ann/bin/python -c "import faiss; i=faiss.IndexHNSWFlat(8,16); print(faiss.__version__, i.hnsw.efConstruction, i.hnsw.efSearch)"
```
```
1.15.1 40 16
```
*(Confirms that FAISS library defaults are `efConstruction = 40` and `efSearch = 16`, validating that the experimental values 200 and 128 differ from library defaults).*

### 5.2 SHA-256 Hashes and Line Counts Across Staging Lifecycle
```bash
sha256sum /tmp/doc004a-thesis-work/thesis-original.md /tmp/doc004a-thesis-work/thesis-core.md /tmp/doc004a-thesis-work/thesis-gated.md "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
```
```
15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a  /tmp/doc004a-thesis-work/thesis-original.md
9d6a3af4b2c88dec3bf3e8ae763799863daa340eb9cf4b4fa78f2ed7403a2ff7  /tmp/doc004a-thesis-work/thesis-core.md
1e42d2aab3811f0af8f30ec5ce2b8eded64fba571cbb7363421a093365d775fc  /tmp/doc004a-thesis-work/thesis-gated.md
15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
```
*(The repository canonical thesis remains byte-identical and unmodified).*

### 5.3 Diff Application Checks (`patch --dry-run` and `git apply --check`)
On fresh copy:
```bash
patch --dry-run -p1 -i docs/reports/DOC-004-A-gemini-thesis-core.diff /tmp/doc004a-thesis-work/test-apply.md
```
```
checking file /tmp/doc004a-thesis-work/test-apply.md
```

```bash
git apply --check docs/reports/DOC-004-A-gemini-thesis-core.diff
```
*(Exited with code 0; zero errors).*

On core-patched copy:
```bash
patch --dry-run -p1 -i docs/reports/DOC-004-A-gemini-thesis-gated.diff /tmp/doc004a-thesis-work/test-apply.md
```
```
checking file /tmp/doc004a-thesis-work/test-apply.md
```

In temporary Git test repository on core-patched tree:
```bash
git apply --check docs/reports/DOC-004-A-gemini-thesis-gated.diff
```
*(Exited with code 0; zero errors).*

### 5.4 Pattern Checks on Added Lines
```bash
grep '^+' docs/reports/DOC-004-A-gemini-thesis-core.diff | grep -v '^\+\+\+' | grep -c '\[D-[0-9]'
0
grep '^+' docs/reports/DOC-004-A-gemini-thesis-core.diff | grep -v '^\+\+\+' | grep -c '\$'
0
grep '^+' docs/reports/DOC-004-A-gemini-thesis-gated.diff | grep -v '^\+\+\+' | grep -c '\[D-[0-9]'
0
grep '^+' docs/reports/DOC-004-A-gemini-thesis-gated.diff | grep -v '^\+\+\+' | grep -c '\$'
0
```

```bash
grep '^+' docs/reports/DOC-004-A-gemini-thesis-core.diff | grep -v '^\+\+\+' | grep -n -i -E 'approximately 7|in practice|substantially lower|Hamming-adjacent|different embedding model|recommended'
```
*(Zero matches confirmed).*

---

## 6. For Luke to Verify Before Applying Gated Diff

The edits in `DOC-004-A-gemini-thesis-gated.diff` depend on external primary sources that cannot be verified from repository files alone. Luke should check the following before applying:

1. **EraRAG Theorem 4 Parameter Notation ($b$ vs. $n$):**
   - *Source to check:* Zhang et al., "EraRAG: Efficient and incremental retrieval augmented generation for growing corpora", arXiv:2506.20963, Section 4.2 / Theorem 4.
   - *What to look for:* Verify whether the paper's Theorem 4 proof actually states the bound as $O(\Delta(nd + S_{\text{LLM}}))$ where $n$ denotes the number of random hyperplanes (hash bits) rather than the graph size. If confirmed, the renaming of $n \to b$ (or $n \to n_{\text{bits}}$) in the thesis is necessary to prevent collision with total graph size $n$.
2. **EraRAG $S_{\text{LLM}}$ Operational Meaning:**
   - *Source to check:* arXiv:2506.20963, Algorithm 1 and Theorem 4 proof.
   - *What to look for:* Verify what operations $S_{\text{LLM}}$ subsumes in EraRAG (e.g. text summarisation across tree levels). Confirm that interpreting $S_{\text{LLM}}$ in this study as pairwise relationship classification over at most $s_{\max}$ candidates within a single flat bucket accurately captures the structural parallel.
3. **iText2KG Threshold Provenance:**
   - *Source to check:* Lairgi et al. [2] (WISE 2024 paper).
   - *What to look for:* Confirm whether the $\approx 0.6$ threshold was fitted using a specific model (e.g., CamemBERT or text-embedding-ada-002) on a GPT-4 entity dataset, confirming that 0.6 is an uncalibrated heuristic when applied to MiniLM on educational concept graphs.
4. **HNSW Parameter References:**
   - *Source to check:* Malkov & Yashunin (2018), "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs" (IEEE TPAMI) or Douze et al. (2024), "The Faiss library", arXiv:2401.08281.
   - *What to look for:* Confirm whether $M=16, \text{efConstruction}=200$ match reference experimental setups.

### Candidate Bibliographic Entries (For Report Only — Tagged `[Unverified]`)

- `[Unverified]` Y. A. Malkov and D. A. Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 42, no. 4, pp. 824–836, 2018, doi: 10.1109/TPAMI.2018.2889473.
- `[Unverified]` M. Douze, A. Guzhva, C. Deng, J. Johnson, G. Szilvasy, P.-E. Mazaré, M. Lomeli, L. Hosseini, and H. Jégou, "The Faiss library," *arXiv preprint arXiv:2401.08281*, 2024.

---

## 7. Found But Not Changed

1. **Stale Theorem 4 Promise in `docs/tasks/high-level-tasks.md`:**  
   Line 81 promises to "Directly compare the bucket-capped strategy's empirical curve against EraRAG's Theorem 4's predicted shape". As recorded in [D-68](6)(d), this phrasing is stale because the size-sweep benchmark evaluates an un-amortised single step per trial after `setup()`. Left unmodified per prompt instructions.
2. **Thesis Bibliography Entry `[8]`:**  
   Entry `[8]` in `docs/thesis/An Empirical Complexity Analysis...md` line 292 is currently placeholder text `[8] TBC`. Left unmodified.
3. **Earlier Proposal Snapshot:**  
   `docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md` is an older 94-line proposal snapshot from September 2026; left unmodified.
4. **Canonical Thesis:**  
   `docs/thesis/An Empirical Complexity Analysis...md` remains completely unmodified (sha256 `15ae6059...`).

---

## 8. DOC-004 Report Errata (S-5)

The write-once report `docs/reports/DOC-004-gemini-thesis-sync.md` contains the following two minor factual errors:
1. **Secondary Thesis File Size:** Section 3.1 reported `docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md` as 10,742 bytes. Host verification shows the actual size is 13,110 bytes (the SHA-256 hash reported was correct).
2. **`thesis-orientation.md` Line Count:** Section 3.1 reported `docs/reports/to-be-shared/thesis-orientation.md` as 52 lines in one location and 51 lines in another. Host verification confirms the actual line count is 51 lines.

---

## 9. Neutral Questions for the Adviser

The following design and alignment questions are submitted for adviser guidance, without recommendation:

1. **Similarity Threshold Sensitivity Grid (Strategy B):**  
   The evaluated threshold grid is $\theta \in \{0.4, 0.5, 0.6\}$, which explores looser filtering but includes no value stricter than the default 0.6.  
   - *Option A:* Accept the asymmetric grid, documenting as a limitation that stricter filtering was not evaluated.  
   - *Option B:* Add a stricter threshold run (e.g. $\theta = 0.7$), noting that adding one sensitivity configuration adds 2 benchmark runs (1 sweep + 1 accuracy) and expands the D-68 planned call bound by up to 43,512 calls.
2. **Symbol for Hyperplane Count in Theorem Statement:**  
   EraRAG's Theorem 4 uses $n$ for the number of random hyperplanes, which collides with graph size $n$ used throughout this thesis.  
   - *Option A:* Rename the hyperplane count to $b$ (representing hash bit count / hyperplanes), explicitly tying it to Strategy D's $n_{\text{bits}} = 12$.  
   - *Option B:* Use $n_{\text{bits}}$ or $k_{\text{LSH}}$ directly in the asymptotic expression $O(\Delta(n_{\text{bits}} \cdot d + S_{\text{LLM}}))$.  
   - *Option C:* Retain EraRAG's literal notation $n$ and add a parenthetical footnote distinguishing it from graph size $n$.
3. **HNSW Parameter Provenance and Citations:**  
   Parameters $M=16$ and $\text{efConstruction}=200$ were chosen a priori before evaluation.  
   - *Option A:* Keep neutral, uncited phrasing stating that parameters are fixed a priori and held constant without tuning on evaluation data.  
   - *Option B:* Cite primary literature (e.g. Malkov & Yashunin 2018 for HNSW; Douze et al. 2024 for FAISS) as the source of common benchmark settings.
4. **Decision-Step Micro-Benchmark Status:**  
   [D-68](1) clarifies that an isolated micro-benchmark evaluating the LLM pairwise relationship inference step without narrowing is distinct from the ruled-out amortised multi-insertion benchmark, and remains unsettled.  
   - *Option A:* Drop the decision-step micro-benchmark from the thesis scope entirely, relying on the DSA brute-force pilot baseline (micro F1 0.541).  
   - *Option B:* Implement a standalone offline micro-benchmark on isolated pairs if supplementary validation of the decision step is desired.
5. **RQ4, Objective 4, and §3.5 Framing Regarding EraRAG's Amortised Bound ([D-69](5)):**  
   Under [D-68](1), the benchmark evaluates single insertions after `setup()`, measuring an un-amortised single step rather than multi-insertion amortisation.  
   - *Option A:* Retain RQ4 and Objective 4 as written, but explicitly interpret the empirical curve in §3.5 as evaluating whether the single-step structural adaptation exhibits constant-cost scaling, acknowledging that multi-insertion amortisation is not directly tested.  
   - *Option B:* Reword RQ4 and Objective 4 to focus specifically on single-step insertion cost scaling as a function of graph size, removing the claim of evaluating the amortised theorem.  
   - *Option C:* Treat EraRAG's Theorem 4 strictly as theoretical motivation in Chapter 2, framing Chapter 3's empirical evaluation entirely around comparative scaling behavior.
