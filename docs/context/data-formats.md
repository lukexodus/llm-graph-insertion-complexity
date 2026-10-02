# Data Formats — Settled Findings

**Status: PARTIALLY VERIFIED.** The findings below come from direct inspection of
uploaded file excerpts by the APC AI (head/tail only for the large file, for cost
reasons) — not from a full read, and not yet independently re-verified by a local
agent with full filesystem access. **Task DATA-001 (see
`docs/tasks/status.md`) asks a local agent to independently re-verify every claim
below against the full files before any loader code is written against them.**
Do not treat this document as ground truth until DATA-001 reports back. Do not
re-investigate these files from scratch without reading this document first —
that would duplicate work DATA-001 is already doing.

---

## `DSA_gold_standard_MEKG.txt`

- **Format:** semicolon-delimited triples, one per line: `source_concept;target_concept;label`
- **`label`:** `1` = source is a prerequisite of target; `0` = not a prerequisite
- **Coverage:** fully-enumerated pairwise judgment set — a row exists for (nearly)
  every ordered pair of concepts, not just the positive edges. Verified by direct
  read of the complete file content (user pasted full contents in chat).
- **Node count:** approximately 29 distinct concept names, matching the paper's
  stated DSA graph size. Concepts include: `linked_list`, `graph`, `queue`,
  `stack`, `tree`, `heap`, `pointer`, `recursion`, `binary_search_tree`,
  `red_black_tree`, `avl_tree`, `b_tree`, `trie`, `hash_table`, `bloom_filter`,
  `depth_first_search`, `breadth_first_search`, `dijkstra_algorithm`,
  `bellman_ford_algorithm`, `minimum_spanning_tree`, `strongly_connected_component`,
  `topological_sort`, `merge_sort`, `quicksort`, `sorting_algorithm`,
  `binary_search`, `asymptotic_complexity`, `recursive_backtracking`,
  `stirling's_approximation`.
- **Quoting:** at least one concept name contains an apostrophe
  (`stirling's_approximation`) but no quote-escaping was observed around it in the
  semicolon-delimited format — the apostrophe appears to sit directly in the field.
  **DATA-001 should confirm the full file has no delimiter-collision edge cases**
  (e.g., a concept name that itself contains a semicolon, which would break naive
  split-on-`;` parsing).

## `metacademy_gold_standard_MEKG.txt`

- **Format:** **space-delimited** triples, one per line: `source_concept target_concept label`
  — NOT semicolon-delimited like DSA. This is a real format difference between
  the two gold-standard files; a loader cannot assume one format covers both.
- **`label`:** same `0`/`1` convention as DSA (inferred from identical structure;
  not independently confirmed by reading the paper's label semantics for this
  specific file — DATA-001 should confirm).
- **Coverage:** same fully-enumerated pairwise style as DSA — file is 19,740
  lines, overwhelmingly `0`, consistent with an all-pairs judgment set rather
  than a sparse edge list.
- **IMPORTANT CORRECTION TO THESIS TEXT:** Chapter 3 (Section 1.1 background,
  written before this file was inspected) states that the Metacademy file has
  "transitive edges removed" per the ACE paper's own prose (Aytekin & Saygın,
  2024, Section 6.3: *"We remove the transitive edges from the Metacademy graph,
  turning it into a MEKG"*). That prose describes how the AUTHORS constructed
  their experimental graph, but the actual released file, as inspected, still
  has the all-pairs enumerated structure — the "transitivity removal" appears to
  have already happened upstream (baked into which pairs get a `1` vs `0`), not
  to mean the file itself is a sparse edge list. **This is a meaningful
  correction and should be reflected in any thesis-text edits going forward.**
- **Node count:** 141 distinct concepts expected per the paper (Machine Learning,
  Statistics, Linear Algebra). Head of file shows concepts like `loss_function`,
  `adaboost`, `akaike_information_criterion`, `backpropagation`, `bagging`,
  `baum-welch_algorithm`, `bayes_theorem`, `bayesian_linear_regression`,
  `convex_optimization`, `kalman_filter`, `kl_divergence`, `factor_graphs`, etc.
  **Full enumeration of all 141 node names was NOT performed** (cost-efficiency
  constraint — only head/tail of the 19,740-line file was read). DATA-001 should
  produce the full node list.
- **Quoting/delimiter-collision:** not checked in the head/tail excerpt.
  DATA-001 must check for concept names containing a literal space as part of
  the name itself (which would be ambiguous under space-delimiting) — this is a
  real risk specific to this file's format that does NOT apply to DSA's
  semicolon-delimited format.

## `0-100.csv`, `100-200.csv`, `200-300.csv`, `300-400.csv`

- **NEGATIVE FINDING — these are NOT graph data at any size, and are NOT usable
  as part of the cost-scaling size sweep.** An earlier working assumption (based
  on filenames alone, before inspection) guessed these might be graphs pre-binned
  by node count (e.g., "0-100" = a 100-node graph). **This guess was wrong and
  is retracted.**
- **Actual content, confirmed by direct read of `0-100.csv` header + 20 data rows:**
  crowdsourced / platform A-B-test data. Columns: `Concept1`, `Concept2`,
  `TreatmentGroupStudentIds`, `ControlGroupStudentIds`, `TreatmentGroupSuccess`,
  `ControlGroupSuccess`, `TreatmentGroupSize`, `ControlGroupSize`,
  `TGoutperforms`, `CSR_score`. This looks like raw experimental data comparing
  student success rates when concept pairs were taught in different orders —
  very likely the underlying data ACE's own CSR (Concept Space Reference)
  scoring method was derived from or validated against.
- **Best current guess at the `0-100` naming (UNCONFIRMED):** rows in this file
  have `CSR_score` values in the ~21–29 range, sorted descending from the file's
  start. The `0-100`/`100-200`/etc. naming most plausibly refers to a score-range
  or row-index bucket of this same underlying dataset, NOT a node count. This is
  a guess, not a verified fact — **DATA-001 should check the other three CSV
  files' score/row ranges to see if a consistent bucketing scheme emerges**, but
  this is low-priority (see below).
- **Implication for Section 3.3.2 (synthetic/cost-scaling data plan):** NONE of
  these four CSV files should be used to extend the graph-size sweep. The
  locked plan (ten example MEKG files for small-to-mid sizes, LLM-generated
  concept sets for large sizes) is UNAFFECTED by this finding and remains the
  plan. DATA-001 does not need to resolve the exact meaning of `0-100` etc.
  unless time permits — it is interesting context, not a blocker.

## Example MEKG files (small/mid-size real data for the cost-scaling sweep)

Ten files confirmed present in the repo via GitHub file listing (filenames
exactly as they appear in the repo, parentheses included):

- `MEKG_with6nodes(DS).txt`
- `MEKG_with7nodes.txt`
- `MEKG_with8nodes(DS3).txt`
- `MEKG_with8nodes(DS4).txt`
- `MEKG_with8nodes(logic).txt`
- `MEKG_with10nodes(DS1).txt`
- `MEKG_with10nodes(DS2).txt`
- `MEKG_with18nodes(ML).txt`
- `MEKG_with21nodes(ML).txt`
- `MEKG_with35nodes(ML1).txt`

**Correction to thesis Section 3.3.2:** earlier thesis drafting rounded this down
to "7 files at sizes 6, 7, 8, 10, 18, 21, 35." The actual repo has **10 files**,
with two files each at the 8-node and 10-node sizes (differentiated by domain
tag: DS3/DS4, DS1/DS2). This is MORE real data than the thesis currently
credits, which is a strictly positive correction, but the exact filenames and
count should be fixed in the thesis text.

**Internal format of these ten files: NOT YET INSPECTED.** Given they are named
identically in style to the DSA/Metacademy gold-standard files, the working
assumption is they follow one of the two confirmed formats above
(semicolon-delimited like DSA, or space-delimited like Metacademy) — but this
is an ASSUMPTION, not a verified fact. **DATA-001 must inspect at least two of
these ten files (one small, e.g. 6-node, one larger, e.g. 35-node) to confirm.**

## `concept_descriptions/` folder

Exists in the repo per the GitHub file listing and README description
("Concept descriptions are the concepts used in experiment in Section 6.2").
**Not yet inspected at all.** This folder likely contains the source text
descriptions needed to actually run the LLM-driven build phase against these
concepts (the gold-standard files only encode the TARGET graph structure, not
source text to extract from) — DATA-001 should determine whether this folder's
contents are sufficient as source material for the build phase, or whether
separate source text needs to be sourced/generated.
