# Verification Report: DATA-001 — Independent Dataset and File Formats Verification

- **Task ID:** DATA-001
- **Agent:** Gemini (Antigravity)
- **Date:** 2026-10-02
- **Status:** Complete / Verified

---

## 1. Executive Summary

This report delivers the results of an exhaustive, full-file programmatic verification of every claim and open question in [`docs/context/data-formats.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/data-formats.md), as specified by task DATA-001.

All primary data files located under `repositories/dataset/EKG-Dataset/` were inspected and verified against the assumptions established by the APC AI. Key findings include:

1. **DSA Gold Standard (`DSA_gold_standard_MEKG.txt`)**: Confirmed semicolon-delimited (`concept1;concept2;label`). Exactly 29 distinct concept nodes. 841 lines total. No internal semicolons in concept names. Contains exactly one duplicated pair and one missing pair, plus 29 self-loops (all labeled `0`).
2. **Metacademy Gold Standard (`metacademy_gold_standard_MEKG.txt`)**: Confirmed strictly space-delimited with 3 fields per line across all 19,740 lines. Exactly 141 distinct concept nodes. **Crucially: zero concept names contain whitespace** (all multi-word concepts use underscores or hyphens), resolving the primary ambiguity concern flagged in `data-formats.md`. Exactly $141 \times 140 = 19,740$ pairs (no self-loops).
3. **Ten Example MEKG Files (`MEKG_with*.txt`)**: **All 10 files follow the semicolon-delimited format** (like DSA), NOT space-delimited. However, **every concept name inside all 10 files includes an explicit `.txt` filename extension** (e.g. `hash_table.txt;asymptotic_complexity.txt;0`), which requires normalization. Furthermore, 7 of the 10 files contain an extra underscore in their filenames (e.g. `MEKG_with_6_nodes(DS).txt`).
4. **Column Semantic Inversion in DSA / MEKG**: A critical semantic finding was discovered regarding prerequisite directionality: in both `DSA_gold_standard_MEKG.txt` and `metacademy_gold_standard_MEKG.txt`, `concept1;concept2;1` signifies that **`concept2` is a prerequisite of `concept1`** (i.e. target/right column is the prerequisite required by source/left column, or `source -> requires -> target`), contradicting the description in `data-formats.md` and Chapter 3 Section 3.3.1 which stated "source is a prerequisite of target".
5. **`concept_descriptions/` Folder**: Contains 153 files (152 non-empty `.txt` files + 1 empty 1-byte artifact file named `files`). These files are long-form expository textbooks/summaries of **elementary and high school mathematics** (fractions, arithmetic, geometry), matching the Crowdsourced Study / CSR experiment in Section 6.2 of the ACE paper. They have **zero overlap** with DSA, Metacademy, or the 10 MEKG files. Therefore, they **cannot** serve as build-phase source text for DSA or Metacademy concept extraction.
6. **CSV Files (`0-100.csv` to `900-1000.csv`)**: 10 CSV files exist in total (not just 4). They represent a single master dataset of 999 student A-B testing pairs ranked in descending order of `CSR_score` (from 29.4010 down to 5.8960), partitioned into sequential 100-row chunks.

---

## 2. Detailed Verification by Item

### 2.1 DSA File (`DSA_gold_standard_MEKG.txt`)

- **Total lines:** 841 lines.
- **Delimiter:** Strictly semicolon (`;`). Every line has exactly 3 fields (`part1;part2;part3`).
- **Delimiter-collision test:** Confirmed that no concept name contains a semicolon.
- **Special characters in names:** Confirmed `stirling's_approximation` contains an apostrophe without quoting or escaping; parsed without issue.
- **Node count & set:** Exactly 29 distinct concepts. Matches the 29 concept names listed in `data-formats.md`.
- **Labels:** Strictly binary: 55 lines labeled `'1'`, 786 lines labeled `'0'`.
- **Structural anomalies found:**
  - $29 \times 29 = 841$ expected lines for a complete Cartesian product with self-loops.
  - Self-loops: Exactly 29 self-loops (`concept;concept;0`), all with label `0`.
  - Duplication & Missing pair: Line 251 and Line 252 are identical duplicates: `binary_search_tree;recursion;1`. The pair `('binary_search_tree', 'asymptotic_complexity')` is missing from the file. Total distinct pairs represented: 840.

### 2.2 Metacademy File (`metacademy_gold_standard_MEKG.txt`)

- **Total lines:** 19,740 lines.
- **Delimiter:** Strictly single space (` `). Every line splits into exactly 3 fields via `line.split(' ')`.
- **Whitespace / delimiter-collision test:** **Zero lines contain more than 2 spaces.** No concept name contains a literal space; multi-word concepts consistently use underscores (`_`) or hyphens (`-`). Naive space-splitting is completely unambiguous across the entire 19,740 lines.
- **Node count:** Exactly 141 distinct concepts.
- **Self-loops:** 0 self-loops exist. All pairs are directed distinct concept pairs: $141 \times 140 = 19,740$ unique pairs (a complete directed Cartesian product without self-loops).
- **Labels:** 318 lines with label `'1'`, 19,422 lines with label `'0'`.
- **Full list of 141 concept names:**
  `adaboost`, `akaike_information_criterion`, `backpropagation`, `bagging`, `bases`, `baum-welch_algorithm`, `bayes_theorem`, `bayesian_linear_regression`, `bayesian_model_comparison`, `bayesian_networks`, `bayesian_parameter_estimation`, `beta_distribution`, `bias-variance_decomposition`, `binary_linear_classifier`, `binomial_distribution`, `boltzmann_machines`, `central_limit_theorem`, `chain_rule`, `change_of_basis`, `chow-liu_trees`, `computations_on_multivariate_gaussians`, `conditional_distributions`, `conditional_independence`, `conditional_probability`, `conditional_random_fields`, `convex_functions`, `convex_optimization`, `convex_sets`, `convolutional_neural_network`, `covariance`, `covariance_matrix`, `cross_validation`, `cumulative_distribution_function`, `curse_of_dimensionality`, `decision_tree`, `deep_belief_networks`, `determinant`, `dirichlet_distribution`, `dirichlet_process`, `dot_product`, `early_stopping`, `eigenvalues_and_eigenvectors`, `entropy`, `expectation_maximization_algorithm`, `expected_value`, `f_measure`, `factor_analysis`, `factor_graphs`, `fisher's_linear_discriminant`, `forward_backward_algorithm`, `four_fundamental_subspaces`, `functions_of_several_variables`, `gamma_distribution`, `gamma_function`, `gaussian_distribution`, `gaussian_elimination`, `gaussian_process_regression`, `gaussian_processes`, `generalization`, `generalized_linear_models`, `gibbs_sampling`, `gradient`, `gradient_descent`, `hamiltonian_monte_carlo`, `heavy-tailed_distributions`, `hidden_markov_model`, `hopfield_networks`, `importance_sampling`, `independent_component_analysis`, `independent_events`, `jensen's_inequality`, `k-means`, `k-means++`, `k_nearest_neighbors`, `kalman_filter`, `kernel_trick`, `kkt_conditions`, `kl_divergence`, `lagrange_duality`, `lagrange_multipliers`, `lasso_regression`, `latent_dirichlet_allocation`, `latent_semantic_analysis`, `linear_approximation`, `linear_dynamical_systems`, `linear_least_squares`, `linear_regression`, `linear_systems_as_matrices`, `linear_transformations_as_matrices`, `logistic_regression`, `loss_function`, `map_parameter_estimation`, `markov_chain`, `markov_chain_monte_carlo`, `markov_models`, `markov_random_field`, `matrix_inverse`, `matrix_multiplication`, `matrix_transpose`, `maximum_likelihood`, `metropolis-hastings_algorithm`, `mixture_of_gaussians_models`, `monte_carlo_estimation`, `multidimensional_scaling`, `multinomial_coefficients`, `multinomial_distribution`, `multiple_integrals`, `multivariate_gaussian_distribution`, `naive_bayes`, `neural_network`, `optimization_problems`, `orthogonal_subspaces`, `orthonormal_bases`, `partial_derivative`, `particle_filter`, `perceptron_algorithm`, `poisson_distribution`, `positive_definite_matrices`, `precision_and_recall`, `principal_component_analysis`, `probabilistic_latent_semantic_analysis`, `probability`, `probit_regression`, `projection_onto_a_subspace`, `random_forest`, `random_variable`, `recurrent_neural_networks`, `restricted_boltzmann_machines`, `ridge_regression`, `singular_value_decomposition`, `softmax_regression`, `spectral_decomposition`, `stochastic_gradient_descent`, `student-t_distribution`, `subspaces`, `support_vector_machine`, `variational_bayes`, `vc_dimension`, `vector`, `vector_spaces`, `viterbi_algorithm`.

### 2.3 The Ten Example MEKG Files

All 10 example files were inspected directly.

1. **Exact Filenames in Repo:**
   - `MEKG_with_6_nodes(DS).txt` (note: `with_6_nodes`, not `with6nodes`)
   - `MEKG_with7nodes.txt` (note: no underscores around `7`)
   - `MEKG_with_8_nodes(DS3).txt`
   - `MEKG_with_8_nodes(DS4).txt`
   - `MEKG_with_8_nodes(logic).txt`
   - `MEKG_with_10_nodes(DS1).txt`
   - `MEKG_with_10_nodes(DS2).txt`
   - `MEKG_with_18_nodes(ML).txt`
   - `MEKG_with_21_nodes(ML).txt`
   - `MEKG_with_35_nodes(ML1).txt`
2. **Format & Delimiter:**
   - **All 10 files are semicolon-delimited** (`part1;part2;part3`), exactly like DSA. None are space-delimited.
   - Every line has exactly 3 fields. No delimiter collisions or internal semicolons.
3. **Concept Name Extension Quirk (`.txt` in node names):**
   - **Crucial finding:** In all 10 files, every concept name has a `.txt` suffix appended to it (e.g., `hash_table.txt;asymptotic_complexity.txt;0`).
   - Any corpus loader implementing INFRA-003 **must strip `.txt`** from concept names to normalize them against DSA/Metacademy concept names.
4. **Self-loops and Label Counts:**
   - Every file contains $N \times N$ lines representing the full Cartesian product, including $N$ self-loops (`concept;concept;0`).
   - All self-loops have label `'0'`.
   - Summary table:

| Filename | Lines ($N^2$) | Nodes ($N$) | Delimiter | Label '1' | Label '0' | Self-loops (all '0') |
|---|---|---|---|---|---|---|
| `MEKG_with_6_nodes(DS).txt` | 36 | 6 | `;` | 7 | 29 | 6 |
| `MEKG_with7nodes.txt` | 49 | 7 | `;` | 16 | 33 | 7 |
| `MEKG_with_8_nodes(DS3).txt` | 64 | 8 | `;` | 18 | 46 | 8 |
| `MEKG_with_8_nodes(DS4).txt` | 64 | 8 | `;` | 23 | 41 | 8 |
| `MEKG_with_8_nodes(logic).txt` | 64 | 8 | `;` | 15 | 49 | 8 |
| `MEKG_with_10_nodes(DS1).txt` | 100 | 10 | `;` | 29 | 71 | 10 |
| `MEKG_with_10_nodes(DS2).txt` | 100 | 10 | `;` | 19 | 81 | 10 |
| `MEKG_with_18_nodes(ML).txt` | 324 | 18 | `;` | 76 | 248 | 18 |
| `MEKG_with_21_nodes(ML).txt` | 441 | 21 | `;` | 138 | 303 | 21 |
| `MEKG_with_35_nodes(ML1).txt` | 1225 | 35 | `;` | 244 | 981 | 35 |

### 2.4 Critical Finding: Directionality / Column Semantics in Dataset

In `data-formats.md` and Chapter 3 Section 3.3.1, it was assumed:
> `source_concept;target_concept;label`: `1` = source is a prerequisite of target.

**Direct inspection of actual concept pairs proves this is inverted:**
- In `DSA_gold_standard_MEKG.txt`:
  - `dijkstra_algorithm;graph;1` (and `graph;dijkstra_algorithm;0`): A student must know graphs *before* Dijkstra's algorithm. Hence, `graph` (column 2) is the prerequisite for `dijkstra_algorithm` (column 1).
  - `quicksort;sorting_algorithm;1` (and `sorting_algorithm;quicksort;0`): `sorting_algorithm` is the prerequisite for `quicksort`.
  - `recursive_backtracking;recursion;1`: `recursion` is the prerequisite for `recursive_backtracking`.
- In `metacademy_gold_standard_MEKG.txt`:
  - `backpropagation chain_rule 1`: `chain_rule` (column 2) is the prerequisite for `backpropagation` (column 1).
  - `gradient_descent gradient 1`: `gradient` (column 2) is the prerequisite for `gradient_descent` (column 1).
- In `MEKG_with_6_nodes(DS).txt`:
  - `asymptotic_complexity.txt;hash_table.txt;1`: Here, column 2 is `hash_table.txt` and column 1 is `asymptotic_complexity.txt`. In fact, comparing `MEKG_with_6_nodes(DS).txt` directly against `DSA_gold_standard_MEKG.txt` shows that the column ordering in the example MEKG file was generated with the reverse pair ordering compared to DSA!

**Recommendation for INFRA-001/003:** The graph model and loader must standardize and explicitly document directed edge semantics as:
- Either directed edge `(u, v)` represents `u requires v` (prerequisite), OR
- Directed edge `(u, v)` represents `u is_prerequisite_of v`.
Since column 1 requires column 2 in the gold standard files, naive loaders assuming `col1 is prerequisite of col2` will invert all graph edges.

### 2.5 `concept_descriptions/` Folder Inspection & Sufficiency Assessment

- **File count:** 153 total directory entries:
  - 152 `.txt` files containing expository concept text. Average length: 3,013 characters (~500–600 words each).
  - 1 stray file named `files` (1 byte, contains a newline `\n`), likely an artifact from an author script.
- **Content domain:** School-level mathematics topics (e.g. `Adding_and_Subtracting_Fractions.txt`, `BIDMAS.txt`, `Angles_in_Polygons.txt`, `Area_of_Simple_Shapes.txt`).
- **Cross-reference with paper:** These 152 concepts are the exact concepts used in Section 6.2 ("Crowdsourced Evaluation") and correspond to the concepts tested in the 10 CSV files (`0-100.csv` to `900-1000.csv`).
- **Overlap with DSA / Metacademy / MEKG:** **0% overlap.** None of the 29 DSA concepts, none of the 141 Metacademy concepts, and none of the 88 distinct concepts in the 10 MEKG files appear in `concept_descriptions/`.
- **Sufficiency Assessment:**
  - **Verdict:** **INSUFFICIENT** as source text for DSA or Metacademy graph construction.
  - **Rationale:** Because this folder contains exclusively school mathematics curriculum articles, an LLM reading these texts will never encounter "dijkstra_algorithm", "avl_tree", "support_vector_machine", or any concept from the gold-standard evaluation graphs.
  - **Action Required:** For the build/insertion phase on DSA and Metacademy, either:
    1. Concept definitions must be generated or fetched from an external corpus (e.g., Metacademy article summaries, Wikipedia concept lead sections, or standard textbook passages), OR
    2. Prompt templates must supply the concept names directly and prompt the LLM's parametric knowledge (e.g., asking whether Concept A is a prerequisite of Concept B based on general domain knowledge).

### 2.6 The CSV Files (`0-100.csv` to `900-1000.csv`)

- **Files present:** 10 files in total: `0-100.csv`, `100-200.csv`, `200-300.csv`, `300-400.csv`, `400-500.csv`, `500-600.csv`, `600-700.csv`, `700-800.csv`, `800-900.csv`, `900-1000.csv`.
- **Row count:** Files `0-100` through `800-900` have exactly 100 rows each. `900-1000.csv` has 99 rows. Total: 999 rows.
- **Bucketing scheme confirmed:** The naming denotes **row index ranks** of concept pairs sorted strictly in descending order of `CSR_score`:
  - `0-100.csv`: CSR scores 29.4010 down to 16.4704 (rows 1–100)
  - `100-200.csv`: CSR scores 16.4553 down to 13.8400 (rows 101–200)
  - `200-300.csv`: CSR scores 13.8300 down to 12.0918 (rows 201–300)
  - `...`
  - `900-1000.csv`: CSR scores 6.7575 down to 5.8960 (rows 901–999)
- **Conclusion:** Confirms the APC AI's negative finding. These are strictly tabular experimental results from ACE's crowdsourced A-B testing on school math concepts, partitioned by rank order. They are not graph topology files.

---

## 3. Discrepancies and Corrections to Shared Context

| Item | Prior Documentation Assumption | Verified Reality | Impact / Action |
|---|---|---|---|
| **MEKG example file delimiter** | Assumed unknown, possibly space or semicolon | **All 10 files use semicolons (`;`)** | Shared parser can parse both DSA and all 10 MEKG files. |
| **MEKG concept names** | Assumed clean concept strings | **All concept names in all 10 MEKG files end in `.txt`** | Loader must strip `.txt` extension from node identifiers. |
| **MEKG file names** | Assumed e.g. `MEKG_with6nodes(DS).txt` | Filenames have underscores: `MEKG_with_6_nodes(DS).txt` (7 of 10 differ) | Correct filenames in docs and loader paths. |
| **Metacademy space collision** | Flagged as risk of literal spaces inside concept names | **Zero concept names contain spaces** across all 19,740 lines | Simple `line.split(' ')` is 100% safe. |
| **Edge direction semantics** | Assumed `source;target;1` = source is prerequisite of target | **`concept1;concept2;1` = concept2 is prerequisite of concept1** (`concept1 requires concept2`) | High priority for INFRA-001/003 loader edge construction. |
| **`concept_descriptions/`** | Assumed candidate source text for build phase | Contains school math articles only; 0% overlap with DSA / Metacademy | Build phase cannot use this folder for gold standard concepts. |
| **CSV files** | Listed as 4 files (`0-100` to `300-400`), bucketing unverified | **10 files exist (`0-100` to `900-1000`)**, strictly partitioned by CSR score rank order (rows 1 to 999) | Confirmed non-graph data; update documentation. |

---

## 4. Updates Applied to Repository

1. **Updated `docs/context/data-formats.md`**: Upgraded verification status to fully verified, updated delimiter and node name findings, added directionality notice, and updated CSV and `concept_descriptions` findings.
2. **Added to `docs/decisions/decision-log.md`**: Added entries recording:
   - `[D-15]`: Prerequisite edge directionality in gold-standard files (`col1 requires col2`).
   - `[D-16]`: Semicolon delimiter and `.txt` suffix convention in example MEKG files.
   - `[D-17]`: `concept_descriptions/` scope mismatch and necessity for alternative build-phase text source.
3. **Updated `docs/tasks/status.md`**: Marked DATA-001 as `done` and linked to this report.
