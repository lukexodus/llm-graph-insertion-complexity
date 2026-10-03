# Data Formats — Settled Findings

**Status: FULLY VERIFIED.** All claims in this document have been independently
verified against the complete raw files in `repositories/dataset/EKG-Dataset/` by
Gemini under task **DATA-001** (see `docs/reports/DATA-001-gemini-verify-file-formats.md`
for full details and code-level verification logs).

---

## `DSA_gold_standard_MEKG.txt`

- **Format:** semicolon-delimited triples, one per line: `concept1;concept2;label`
- **Directionality / Semantics (CRITICAL):** `label = 1` means **`concept2` is a prerequisite of `concept1`** (i.e. `concept1` requires `concept2`, e.g., `dijkstra_algorithm;graph;1`, `quicksort;sorting_algorithm;1`, `recursive_backtracking;recursion;1`). Naive reading as `concept1 is prerequisite of concept2` inverts all graph edges. `0` indicates no direct prerequisite relationship.
- **Coverage:** fully-enumerated pairwise judgment set — 841 lines total.
  - Contains exactly 29 self-loops (`concept;concept;0`), all labeled `0`.
  - Exactly one duplicate pair: `binary_search_tree;recursion;1` appears twice (lines 251 and 252).
  - Exactly one missing pair: `('binary_search_tree', 'asymptotic_complexity')` is omitted.
  - Distinct pairs represented: 840.
- **Node count:** exactly 29 distinct concept names:
  `asymptotic_complexity`, `avl_tree`, `b_tree`, `bellman_ford_algorithm`,
  `binary_search`, `binary_search_tree`, `bloom_filter`, `breadth_first_search`,
  `depth_first_search`, `dijkstra_algorithm`, `graph`, `hash_table`, `heap`,
  `linked_list`, `merge_sort`, `minimum_spanning_tree`, `pointer`, `queue`,
  `quicksort`, `recursion`, `recursive_backtracking`, `red_black_tree`,
  `sorting_algorithm`, `stack`, `stirling's_approximation`,
  `strongly_connected_component`, `topological_sort`, `tree`, `trie`.
- **Delimiter / Quoting:** strictly semicolon-delimited. No concept name contains a semicolon. Apostrophe in `stirling's_approximation` is unquoted and parses cleanly.

## `metacademy_gold_standard_MEKG.txt`

- **Format:** **space-delimited** triples, one per line: `concept1 concept2 label`
  (exactly 2 spaces / 3 tokens per line across all 19,740 lines).
- **Directionality / Semantics:** same convention as DSA: `1` means **`concept2` is a prerequisite of `concept1`** (e.g., `backpropagation chain_rule 1`, `gradient_descent gradient 1`).
- **Whitespace / Delimiter collision:** **VERIFIED SAFE.** Zero concept names contain spaces (multi-word concepts use underscores or hyphens). Naive `line.split(' ')` is 100% reliable.
- **Coverage:** $141 \times 140 = 19,740$ lines. Complete directed Cartesian product without self-loops (0 self-loops exist).
  - 318 edges labeled `1`; 19,422 pairs labeled `0`.
- **Node count:** exactly 141 distinct concepts (full list documented in `docs/reports/DATA-001-gemini-verify-file-formats.md`).

## `0-100.csv` through `900-1000.csv` (10 files total)

- **NEGATIVE FINDING — NOT graph data at any size; NOT usable for cost-scaling sweep.**
- **File inventory:** exactly 10 CSV files exist in the repo: `0-100.csv`, `100-200.csv`, `200-300.csv`, `300-400.csv`, `400-500.csv`, `500-600.csv`, `600-700.csv`, `700-800.csv`, `800-900.csv`, and `900-1000.csv`.
- **Content:** crowdsourced A-B test experimental data comparing student performance on prerequisite pairs from school mathematics (columns: `Concept1`, `Concept2`, student group IDs/success, `TGoutperforms`, `CSR_score`).
- **Bucketing scheme confirmed:** rows represent concept pairs sorted descending by `CSR_score` (from 29.4010 down to 5.8960 across 999 total rows). The file naming designates the row index range (1–100, 101–200, ..., 901–999).

## Example MEKG Files (10 files in repo)

Ten files confirmed present in `repositories/dataset/EKG-Dataset/`:
- `MEKG_with_6_nodes(DS).txt`
- `MEKG_with7nodes.txt`
- `MEKG_with_8_nodes(DS3).txt`
- `MEKG_with_8_nodes(DS4).txt`
- `MEKG_with_8_nodes(logic).txt`
- `MEKG_with_10_nodes(DS1).txt`
- `MEKG_with_10_nodes(DS2).txt`
- `MEKG_with_18_nodes(ML).txt`
- `MEKG_with_21_nodes(ML).txt`
- `MEKG_with_35_nodes(ML1).txt`

*(Note exact filenames: 7 of the 10 files contain `with_<n>_nodes` with underscores).*

- **Format:** **All 10 files are semicolon-delimited (`;`)**, matching DSA. None are space-delimited.
- **Concept Name Extension Quirk (CRITICAL):** in all 10 files, every concept name has a `.txt` filename suffix attached (e.g. `hash_table.txt;asymptotic_complexity.txt;0`). Loaders must strip `.txt` from node names when parsing.
- **Coverage:** each file contains $N \times N$ lines (full Cartesian product including $N$ self-loops, all labeled `0`).
- **Concept name edge case:** `Godel's_completeness_theorem.txt` in `MEKG_with_8_nodes(logic).txt` contains an apostrophe without quoting; parses cleanly.

## `concept_descriptions/` Folder

- **Contents:** 153 files (152 expository text files averaging ~3,000 characters each + 1 stray 1-byte file named `files`).
- **Domain:** School-level mathematics (fractions, decimals, basic geometry, BIDMAS). These match the 105 concepts evaluated in the CSV files.
- **Overlap with evaluation graphs:** **0% overlap** with DSA (29 nodes), Metacademy (141 nodes), or the 10 MEKG example files.
- **Sufficiency Assessment:** **INSUFFICIENT** as source text for DSA or Metacademy concept extraction. An LLM cannot extract computer science or advanced machine learning concepts from elementary school math articles. Build-phase text must be sourced externally or queried via parametric knowledge prompts.
