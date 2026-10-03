# Evidence Report: DATA-003 — Evidence for the Build-Phase Source-Text Decision

- **Task ID:** DATA-003
- **Agent:** Gemini (Antigravity)
- **Date:** 2026-10-03
- **Status:** Complete (Awaiting Luke's Decision)

---

## 1. Executive Summary & Recommendation

```
1. [repo] Thesis Chapter 3 defines nodes strictly by concept name and embeddings; no per-node text field is specified.
2. [repo] The shared decision step (§3.2.6) and brute force (§3.2.2) state the LLM is prompted with the concepts, not source text.
3. [repo] In the ACE paper (catalogue #9), gold graphs were produced via embedding scoring + human review; zero-shot/RAG used names.
4. [repo] Git archaeology reveals deleted zips held pairwise concept scores, not expository text; no local CS/ML text exists.
5. [net] Metacademy content exists on GitHub under CC-BY-SA 3.0, covering ~83% of concepts (117/141), but 0% of DSA concepts.
6. [net] Wikipedia provides 100% coverage for DSA and Metacademy, but requires manual title curation for ~35% (404s/disambiguation).
7. [judgment] Concept name audit shows 89.4% of names are crystal clear in CS/ML; only 10.6% benefit from a domain prefix hint.
8. [judgment] Option (a) introduces massive length disparities (134 to 815 chars) and breaks comparability with large synthetic graphs.
9. [judgment] Option (b) is clean, fully symmetric, zero-cost, and natively scales across real and synthetic size checkpoints.
10. [judgment] Option (c) adds pre-computation API cost and synthetic definition bias for minimal gain over modern LLM parametric memory.
11. [judgment] Recommendation: Adopt Option (b) (parametric evaluation with domain-prefixed concept names, e.g. "Domain: CS/ML | Concept: X").
12. [judgment] Confidence: High (90%). Evidence that would change it: adviser mandate requiring grounded RAG text, or failure on pilot accuracy.
```

---

## 2. Part A: What the Repo Already Says (No Network)

All citations below reference `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md` and `docs/rrl/catalogue.md`.

### A1. Node / Concept Definition: Name Only or Name Plus Text?
**Finding:** The repo defines a node exclusively as a concept name / entity identifier, never as a name plus text body.
- *Citation:* Thesis Chapter 1, Section 1.6 (*Definition of Terms*), line 70:
  > `"Node (Vertex): A single unit of data in a graph, representing a concept, entity, or topic."` [repo]
- *Citation:* Thesis Chapter 3, Section 3.3.2 (*Synthetic/Unlabeled Data*), line 208:
  > `"additional concept sets are generated using an LLM prompted to produce a large list of plausible, distinct concept names within a defined subject domain..."` [repo]
- *Silence Note:* There is no mention anywhere in Chapters 1–3 of an attribute, document, or textual payload attached to a graph node.

### A2. Final LLM Relationship-Judgment Call: Structure and Granularity
**Finding:** The final decision step is specified as an LLM prompt between the new concept and candidate nodes, evaluated either pair-by-pair or against shortlisted candidates.
- *Citation:* Thesis Chapter 3, Section 3.2.6 (*The Shared Decision Step*), line 190:
  > `"Across all four strategies, once a shortlist of candidate existing nodes has been produced, a single shared mechanism determines the final relationship: an LLM is prompted with the new concept and each shortlisted candidate, and asked to determine whether a relationship exists and, if so, its type."` [repo]
- *Citation:* Thesis Chapter 3, Section 3.2.2 (*Strategy A: Brute-Force Comparison*), line 174:
  > `"For a new candidate concept, the system queries an LLM to determine whether a relationship exists between the new concept and every single existing node in the graph, one at a time."` [repo]
- *Granularity Note:* Strategy A explicitly states `"one at a time"` (pairwise calls). For Strategies B, C, and D, Section 3.2.6 is slightly ambiguous on whether candidates are judged individually in separate prompts or grouped into a single multi-candidate prompt; however, Section 1.1 (line 15) cites Funk et al.'s prompt counts as 22 to 50 prompts per insertion, implying individual pair prompts.

### A3. What Strategies 2, 3, and 4 Embed or Partition On
**Finding:** Strategies 2 (threshold) and 3 (ANN) embed the candidate concept's representation directly; Strategy 4 partitions existing nodes into bounded buckets based on proximity/clustering.
- *Citation:* Thesis Chapter 3, Section 3.2.3 (*Strategy B*), line 178:
  > `"This strategy first computes a vector embedding for the new candidate concept, then computes cosine similarity between this embedding and the pre-computed embeddings of every existing node in the graph."` [repo]
- *Citation:* Thesis Chapter 3, Section 3.2.4 (*Strategy C*), line 182:
  > `"This strategy also relies on vector embeddings, but rather than filtering by a fixed similarity value (as in Strategy B), it retrieves a fixed number of the most similar existing nodes using an approximate nearest-neighbor index."` [repo]
- *Citation:* Thesis Chapter 3, Section 3.2.5 (*Strategy D*), line 186:
  > `"This strategy organizes existing nodes into size-bounded groups ('buckets'), such that inserting a new node only ever requires comparing it against the members of one bounded bucket, rather than the whole graph."` [repo]
- *Silence Note:* The text does not explicitly state what string is fed to the embedding model (e.g. `embedding_model.encode(concept_name)` vs. `embedding_model.encode(concept_description)`). Given A1, only the concept name exists.

### A4. Synthetic Large-n Data Specification
**Finding:** Synthetic data is explicitly specified as a generated list of concept names, with zero auxiliary text.
- *Citation:* Thesis Chapter 3, Section 3.3.2 (*Synthetic/Unlabeled Data*), line 208:
  > `"additional concept sets are generated using an LLM prompted to produce a large list of plausible, distinct concept names within a defined subject domain (consistent with the general domain of the DSA graph, i.e., computer science and related technical fields..."` [repo]
- *Citation:* Decision Log `[D-05]`, line 66:
  > `"generate LLM-produced concept name lists (domain: computer science, for topical continuity with DSA) for the large-n range (toward 2000 nodes) where no real data exists."` [repo]

### A5. Mentions of "Source Text" and the "Build Phase"
**Finding:** In the thesis itself, "source text" and "build phase" refer exclusively to the *prior literature's* initial batch graph extraction from raw documents, which this study explicitly scopes out.
- *Citation:* Thesis Chapter 1, Section 1.1 (*Background*), line 11:
  > `"LLMs can be prompted to read unstructured text and extract candidate concepts and relationships automatically... where the overall process typically follows three stages: first, defining what kinds of concepts and relationships are relevant... second, extracting candidate concepts and relationships from source text (knowledge extraction)..."` [repo]
- *Citation:* Thesis Chapter 1, Section 1.5 (*Scope and Limitations*), line 60:
  > `"This study is limited to the incremental insertion phase of knowledge graph construction — the process of adding one new node to an already-existing graph. It does not address the initial batch-construction process in depth beyond what is necessary to produce a starting graph..."` [repo]
- *Citation:* Catalogue `docs/rrl/catalogue.md`, entry #2 (line 6):
  > `"Establishes the 'build phase' is a mature, reviewed area (28 studies); explicitly does not cover incremental single-node insertion as a studied problem"` [repo]
- *Context of D-17:* Decision `[D-17]` used the phrase "build-phase source text" because early APC prompts assumed `concept_descriptions/` was intended as raw text for an LLM to read during evaluation. In reality, the thesis methodology has no document-reading extraction phase.

### A6. How ACE (Catalogue Entry #9) Supplied Text to Its Judgments
**Finding:** In the ACE paper (Aytekin & Saygın 2024), gold-standard graphs were curated via pairwise ranking and expert adjudication. The LLM baselines tested in ACE were prompted with concept names (plus Wikipedia RAG in one baseline).
- *Citation:* Catalogue `docs/rrl/catalogue.md`, entry #9 (line 13):
  > `"Aytekin & Saygın... embedding-ranked, human-adjudicated, transitive-edge pruning... LLM-vs-embedding precision/recall trade-off table (GPT-4o-mini+RAG: 87.23P/61.11R vs. their scorer: 46.13P/100R); released gold graphs (Metacademy 141 nodes, DSA 29 nodes); self-admits 'no ground truth' evaluation weakness"` [repo]
- *Citation:* Thesis Chapter 2, Section 2.2.5 (line 142):
  > `"Aytekin and Saygın [6] directly compare their embedding-based scoring approach against zero-shot and retrieval-augmented LLM baselines (GPT-4o-mini, LLaMA 3) on the prerequisite-detection task itself..."` [repo]

---

## 3. Part B: Is CS/ML Concept Text Already Somewhere in the Repo?

### B1. Git Archaeology and Provenance of `repositories/dataset/EKG-Dataset/`
- **Repo Nature:** `repositories/dataset/EKG-Dataset/` is an independent, non-shallow Git clone of `https://github.com/cemaytekin/EKG-Dataset.git` (branch `main`, commit `74089e2`). [repo]
- **Commit History Analysis:**
  - In commit `4c2ab1c` (Feb 22, 2023), the author deleted `data-structures-algorithm-concepts.zip`.
  - In commit `7049aec` (Feb 22, 2023), the author deleted `machine-learning-concepts.zip`.
  - In commit `ec5768d`, the file `ds_concept_direct_preqs_real_replaced.txt` was renamed to `DSA_gold_standard_MEKG.txt`.
  - In commit `8ae3074`, the file `ml_concept_direct_merged.txt` was renamed to `metacademy_gold_standard_MEKG.txt`.
- **Examination of Deleted Zip Files:**
  - Using `git show 4c2ab1c~1:data-structures-algorithm-concepts.zip` and `git show 7049aec~1:machine-learning-concepts.zip`, the archive contents were extracted and examined:
    - `data-structures-algorithm-concepts.zip`: Contained 29 text files (e.g. `linked_list.txt`, `pointer.txt`).
    - `machine-learning-concepts.zip`: Contained 141 text files (e.g. `loss_function.txt`, `backpropagation.txt`).
  - **Contents of these files:** They are **NOT textual concept descriptions**. Each file contains pairwise numerical scores against other concepts (e.g. `linked_list breadth_first_search 0.0`, `loss_function adaboost 0`).
- **Conclusion:** **Zero expository text files exist anywhere in the dataset repository or its entire Git history.** The `.txt` extension on concept names in the 10 example MEKG files was simply an artifact of the author referencing these numerical score files during graph generation. [repo]
- **Upstream Sync:** `git fetch --all` confirmed local `main` is identical to `origin/main` at GitHub. No tags, alternative branches, or unmerged stashes exist upstream. [repo, net]

---

## 4. Part C: Feasibility Sample for Option (a) (External Text)

### C1. Metacademy Official Content Repository (`metacademy-content`)
- **Location:** GitHub repository `https://github.com/metacademy/metacademy-content` (created April 2013, last pushed May 2017). [net]
- **License:** Creative Commons Attribution-ShareAlike 3.0 United States License (`CC-BY-SA 3.0`). [net]
- **Format:** Directory structure containing 393 concepts. Each concept folder has:
  - `title.txt`: Human-readable title.
  - `summary.txt`: A concise 1-paragraph summary (average ~300 characters, ~40–60 words).
  - `dependencies.txt`: Prerequisite concept IDs.
- **Coverage of Metacademy Gold Standard (141 concepts):**
  - **117 concepts (83.0%)** match directly or via simple punctuation normalization (`jensen's_inequality` $\to$ `jensens_inequality`). [net]
  - **24 concepts (17.0%)** are missing or use structural plural/synonym naming in the repo (e.g. `covariance_matrix` is `covariance_matrices`, `adaboost` is `ada_boost`, `convolutional_neural_network` is `convolutional_nets`). [net]
- **Coverage of DSA Gold Standard (29 concepts):**
  - **Only 1 concept** (`asymptotic_complexity`) exists in `metacademy-content`.
  - **28 concepts (96.6%) are absent**, because Metacademy was strictly a machine learning/statistics/math site. [net]

### C2. Deterministic Sample Audit against Wikipedia REST Summary API
Sample selection:
- DSA: Every 3rd concept sorted alphabetically ($n=10$: indices 0, 3, 6, 9, 12, 15, 18, 21, 24, 27).
- Metacademy: Every 7th concept sorted alphabetically ($n=21$: indices 0, 7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84, 91, 98, 105, 112, 119, 126, 133, 140).

Endpoint used: `https://en.wikipedia.org/api/rest_v1/page/summary/{title}` with rate limiting. [net]

#### DSA Sample Results (10 concepts)
| Concept | Title Queried | Status | Resolved Title | Summary Length |
|---|---|---|---|---|
| `asymptotic_complexity` | `asymptotic complexity` | redirect | Asymptotic computational complexity | 254 chars |
| `bellman_ford_algorithm` | `bellman ford algorithm` | none (404) | *Requires "Bellman–Ford algorithm" (en-dash)* | 641 chars (manual) |
| `bloom_filter` | `bloom filter` | exact | Bloom filter | 456 chars |
| `dijkstra_algorithm` | `dijkstra algorithm` | redirect | Dijkstra's algorithm | 251 chars |
| `heap` | `heap` | disambiguation | *Requires "Heap (data structure)"* | 345 chars (manual) |
| `minimum_spanning_tree` | `minimum spanning tree` | exact | Minimum spanning tree | 500 chars |
| `quicksort` | `quicksort` | exact | Quicksort | 327 chars |
| `red_black_tree` | `red black tree` | redirect | Red–black tree | 305 chars |
| `stirling's_approximation` | `stirling's approximation` | exact | Stirling's approximation | 284 chars |
| `tree` | `tree` | disambiguation | *Requires "Tree (data structure)"* | 621 chars (manual) |

*DSA Summary:* 4 exact (40%), 3 auto-redirect (30%), 2 disambiguation (20%), 1 404 dash-issue (10%). With manual variant resolution, 10/10 (100%) match.

#### Metacademy Sample Results (21 concepts)
| Concept | Title Queried | Status | Resolved Title | Summary Length |
|---|---|---|---|---|
| `adaboost` | `adaboost` | exact | AdaBoost | 522 chars |
| `bayesian_linear_regression` | `bayesian linear regression` | exact | Bayesian linear regression | 724 chars |
| `binomial_distribution` | `binomial distribution` | exact | Binomial distribution | 634 chars |
| `conditional_distributions` | `conditional distributions` | none (404) | *Requires "Conditional probability distribution"* | 815 chars (manual) |
| `convolutional_neural_network` | `convolutional neural network` | exact | Convolutional neural network | 479 chars |
| `deep_belief_networks` | `deep belief networks` | none (404) | *Requires "Deep belief network" (singular)* | 256 chars (manual) |
| `entropy` | `entropy` | exact | Entropy | 539 chars |
| `forward_backward_algorithm` | `forward backward algorithm` | none (404) | *Requires "Forward–backward algorithm" (en-dash)* | 611 chars (manual) |
| `gaussian_process_regression` | `gaussian process regression` | redirect | Kriging | 594 chars |
| `hamiltonian_monte_carlo` | `hamiltonian monte carlo` | none (404) | *Requires "Hamiltonian Monte Carlo" (capitalized)* | 334 chars (manual) |
| `jensen's_inequality` | `jensen's inequality` | exact | Jensen's inequality | 601 chars |
| `kl_divergence` | `kl divergence` | none (404) | *Requires "Kullback–Leibler divergence"* | 262 chars (manual) |
| `linear_dynamical_systems` | `linear dynamical systems` | none (404) | *Requires "Linear dynamical system" (singular)* | 474 chars (manual) |
| `map_parameter_estimation` | `map parameter estimation` | none (404) | *Requires "Maximum a posteriori estimation"* | 507 chars (manual) |
| `matrix_transpose` | `matrix transpose` | redirect | Transpose | 237 chars |
| `multinomial_distribution` | `multinomial distribution` | exact | Multinomial distribution | 482 chars |
| `orthonormal_bases` | `orthonormal bases` | redirect | Orthonormal basis | 697 chars |
| `principal_component_analysis` | `principal component analysis` | exact | Principal component analysis | 167 chars |
| `recurrent_neural_networks` | `recurrent neural networks` | redirect | Recurrent neural network | 484 chars |
| `student-t_distribution` | `student-t distribution` | redirect | Student's t-distribution | 217 chars |
| `viterbi_algorithm` | `viterbi algorithm` | exact | Viterbi algorithm | 479 chars |

*Metacademy Summary:* 8 exact (38.1%), 6 auto-redirect (28.6%), 7 404s (33.3%). All 7 404s resolved successfully once manual variants (singularization, hyphenation, or expansion) were applied.

### C3. Extrapolation across all 170 Concepts
- **Direct Naive Match Rate (spaces for underscores):** ~65% to 70%.
- **Manual Title Curation Required:** ~30% to 35% (~50–60 concepts out of 170) would require manual title aliases (e.g. fixing en-dashes `Bellman–Ford`, handling acronyms `KL divergence` $\to$ `Kullback–Leibler`, singularizing `deep belief networks`, and appending disambiguation tags `(data structure)` for generic words like `tree`, `stack`, `heap`, `graph`, `queue`).
- **Text Length Variability:** Wikipedia lead summaries range from 167 characters (`PCA`) to 815 characters (`conditional probability distribution`), averaging ~480 characters.
- **Effort Estimate:** Fetching, mapping, verifying, and packaging 170 Wikipedia descriptions would require ~1–2 hours of manual alias mapping and pipeline verification.

---

## 4. Part D: Name Audit for Option (b) (No Network)

All 170 distinct concept names across `DSA_gold_standard_MEKG.txt` (29) and `metacademy_gold_standard_MEKG.txt` (141) were audited. [judgment]

### Classification Definitions
- **Clear:** Unambiguous technical term in CS/ML with essentially no competing common meanings.
- **Needs-Domain-Hint:** Common English word or broad scientific term that becomes completely unambiguous once the domain ("Computer Science / Data Structures" or "Machine Learning / Statistics / Linear Algebra") is prefixed.
- **Ambiguous-Even-With-Hint:** Has multiple distinct meanings even within the specified domain.

### Summary Counts
| Graph | Total Nodes | Clear | Needs-Domain-Hint | Ambiguous-Even-With-Hint |
|---|---|---|---|---|
| **DSA Gold Standard** | 29 | 22 (75.9%) | 7 (24.1%) | 0 (0.0%) |
| **Metacademy Gold Standard** | 141 | 130 (92.2%) | 11 (7.8%) | 0 (0.0%) |
| **TOTAL** | **170** | **152 (89.4%)** | **18 (10.6%)** | **0 (0.0%)** |

**Zero concepts out of 170 are ambiguous once a domain hint is provided.**

### Full Listing of Non-Clear Names (18 total)

#### DSA Graph (7 concepts needing domain hint)
1. `graph` — Common word (charts/plots); needs hint: "Data Structures & Algorithms: graph (nodes and edges)".
2. `heap` — Common word (pile of objects); needs hint: "Data Structures: binary heap priority queue".
3. `pointer` — Common word (pointing device/dog); needs hint: "Computer Science: memory pointer".
4. `queue` — Common word (waiting line); needs hint: "Data Structures: FIFO queue".
5. `recursion` — General linguistic/mathematical term; needs hint: "Computer Science: recursive functions/call stack".
6. `stack` — Common word (stack of plates/pancakes); needs hint: "Data Structures: LIFO stack".
7. `tree` — Common word (biological plant); needs hint: "Data Structures: hierarchical tree structure".

#### Metacademy Graph (11 concepts needing domain hint)
1. `bases` — Common word (baseball, chemical bases); needs hint: "Linear Algebra: basis vectors".
2. `covariance` — Shared with general physics/finance; needs hint: "Statistics: covariance".
3. `determinant` — Common word (determining factor); needs hint: "Linear Algebra: matrix determinant".
4. `dot_product` — Needs hint: "Linear Algebra / Vector operations".
5. `entropy` — Major thermodynamic concept in physics; needs hint: "Information Theory / Machine Learning: information entropy".
6. `expected_value` — Broad probabilistic concept; needs hint: "Probability Theory: expectation".
7. `generalization` — Common psychological/colloquial word; needs hint: "Machine Learning: generalization to unseen data".
8. `gradient` — Common word (slope/incline in geography); needs hint: "Multivariate Calculus / Optimization: gradient vector".
9. `probability` — Broad mathematical and philosophical concept; needs hint: "Mathematics: probability theory".
10. `subspaces` — Needs hint: "Linear Algebra: vector subspaces".
11. `vector` — Biology (disease vector) vs physics vs math; needs hint: "Linear Algebra: numerical vector".

---

## 5. Part E: Implications and Comparison of Options

### Evaluation Matrix

| Criterion | Option (a): External Text (Wikipedia / Metacademy) | Option (b): Names Only (with Domain Hint) | Option (c): Up-front LLM Definitions | Split Design: (a)/(c) on Accuracy, (b) on Sweep |
|---|---|---|---|---|
| **(i) Comparability across Size Sweep (29/141 $\to$ 2000)** | **Poor.** Real nodes would carry 300–800 char texts; synthetic large-$n$ nodes (D-05) have only names. Creates an artificial distribution shift across the $n=141$ boundary. | **Excellent.** 100% symmetric. Real and synthetic nodes both carry identical structural shape (`Domain + Concept Name`). Cost curves reflect pure algorithm scaling. | **Moderate.** Synthetic nodes would need 2,000 generated definitions. Token costs scale with definition generation up front. | **Poor.** Evaluation metrics would test two completely different prompt types (long text on gold tests vs. names on sweep). |
| **(ii) Accuracy Evaluation against Gold Standards** | High precision expected, but variable text length introduces prompt noise and RAG-like context confounding. | High precision expected on modern LLMs (GPT-4o, Claude 3.5, Gemini 1.5/2.0) which excel at textbook CS/ML concepts without external definitions. | High precision, but definitions are generated by the same LLM family evaluating them, risking hallucination circularity. | Asymmetric: accuracy is measured with text, while cost is measured without text. Hard to defend at thesis defense. |
| **(iii) What Strategies 2–4 Embed** | Embeds multi-sentence text paragraphs (average ~500 chars). | Embeds concept name string with domain hint (e.g. `"Data Structures and Algorithms: bloom_filter"`). Clean, compact, highly effective for embedding models. | Embeds 1–2 sentence synthetic definitions. | Inconsistent embedding dimensionality or semantic space across real vs synthetic sweeps. |
| **(iv) In-Memory Node Shape (INFRA-001/002)** | Node must store: `name: str`, `domain: str`, `text: str`, `embedding: ndarray`. | Node stores: `name: str`, `domain: str`, `embedding: ndarray`. (Minimal, clean, fast). | Node stores: `name: str`, `domain: str`, `text: str`, `embedding: ndarray`. | Node must support optional `text` field, creating branching logic in harness. |
| **(v) Thesis Sections Needing Revision** | **Substantial.** Ch. 3 §3.3.1, §3.3.2, §3.2.6 must formally document the external text corpus, licenses, and fetch methodology. | **Minimal / None.** Matches Chapter 3 as written (§3.2.2, §3.2.6, §3.3.2 describe prompting with concept names). Only needs minor clarification in §3.2.6. | **Moderate.** Ch. 3 §3.3.2 must define the definition-generation prompt and validation protocol. | **Substantial.** Must explain and justify the methodological split between accuracy and cost protocols. |
| **(vi) Added Work & API Spend** | High manual curation (~50–60 aliases); web fetch harness needed. $0 API spend. | **Zero added work.** No external scraping, no alias curation, $0 API spend. | High API spend: must generate 2,000 definitions for synthetic nodes + prompt tuning. | High implementation effort; two parallel harnesses required. |

---

## 6. Recommendation

**Recommended Option:** **Option (b) — Concept Names with Domain Context Prefix**
`e.g., prompt LLM with: "Domain: Data Structures & Algorithms | Concept: dijkstra_algorithm"`

- **Confidence Level:** **High (90%)**
- **Rationale:**
  1. **Fidelity to Thesis Methodology:** As documented in Part A, Chapters 1–3 of the thesis were written from the ground up as a pure CS algorithmic study of candidate narrowing for *concept-node insertion*, not text-chunk document summarization (which is what EraRAG did). The thesis repeatedly specifies nodes as concept names and mentions no textual payload.
  2. **Experimental Hygiene & Symmetry:** In a complexity scaling study, keeping the node payload strictly identical across real ($n=29, 141$) and synthetic ($n=50 \dots 2000$) checkpoints is essential. If real nodes carry 500 characters of human-written text while synthetic nodes carry 20 characters of name strings, any change in wall-clock time or token consumption at $n > 141$ will be confounded by text length disparity rather than candidate narrowing efficiency.
  3. **Zero Ambiguity:** As shown in Part D, 89.4% of concepts are unambiguous technical terms (`bloom_filter`, `quicksort`, `backpropagation`). The remaining 10.6% (`heap`, `tree`, `stack`, `vector`) become 100% unambiguous with a simple domain hint. Modern foundation models possess extensive parametric mastery of these textbook subjects.
- **Evidence That Would Change This Recommendation:**
  1. If Luke's thesis adviser explicitly mandates that node insertion *must* operate over grounded textual documents or literature extracts.
  2. If a small preliminary pilot trial reveals that zero-shot LLM relationship judgments on concept names fail to achieve acceptable accuracy against the gold-standard graph.

---

## 7. Stale or Contradictory Statements Found

1. **`docs/context/complete-context.md` (Line 76):** States `"This repo is cemaytekin/EKG-Dataset, cloned from the authors..."`. Contradiction: This repository is `lukexodus/llm-graph-insertion-complexity`, and the dataset is located in the subdirectory `repositories/dataset/EKG-Dataset/`.
2. **`docs/context/complete-context.md` (Line 98):** Refers to `"Four *.csv files (0-100.csv etc.)"`. Contradiction: There are 10 CSV files (`0-100.csv` to `900-1000.csv`), as verified in DATA-001 and documented in `data-formats.md`.
3. **`docs/context/complete-context.md` (Line 101–103):** States `concept_descriptions/` is `"not yet inspected at all... likely needed as source text for the build phase"`. Contradiction: Inspected in DATA-001; contains elementary school math with 0% overlap with DSA/Metacademy; ruled out in `[D-17]`.
4. **`docs/context/complete-context.md` (Line 170):** Lists `DATA-001` as open. Contradiction: `DATA-001` and `DATA-002` are both complete and logged in `docs/tasks/status.md`.
5. **Thesis Section 3.3.1 (Lines 198, 200):** States `label 1` means `source is prerequisite of target`. Contradiction: Empirically proven in DATA-001 and logged in `[D-15]` that `label 1` represents `target is prerequisite of source` (`concept1 requires concept2`).

---

## 8. Could Not Check, and Why

1. **Wikipedia Rate-Limit on Full 170 Concepts:** Full scraping of all 170 Wikipedia summaries was intentionally avoided per the task prompt instructions ("Don't fetch all 170. Keep to about 100 requests... sequential..."). The deterministic sample ($n=31$) provided sufficient statistical signal to extrapolate coverage and failure modes.
2. **Alternative Closed/Paywalled Educational KG Repositories:** No paid or access-restricted educational datasets were searched, as the study explicitly relies on open, public gold standards per `[D-04]`.
