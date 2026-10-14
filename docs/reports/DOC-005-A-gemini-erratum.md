# DOC-005-A Report: Erratum for the DOC-005 Report, Strategy 2 Bound Wording Correction (D-70), and Raw Re-Verification of Planned-Call Bounds

Date: 2026-10-14  
Task ID: `DOC-005-A`  
Decision ID: `D-70` (originally reserved as `D-69`; `D-69` was allocated to DOC-006 in commit `67a04bc`)  
Branch: `master`  

---

## 1. Agent Identity

- **Agent:** Gemini
- **Model label:** Gemini 3.8 Flash (Medium)
- **Session ID:** `512aecca-d185-438b-b8e7-d6dba3b507fb`
- **Confirmation:** Confirmed current session ID (`512aecca-d185-438b-b8e7-d6dba3b507fb`) is distinct from the excluded session (`098dcdd4-c444-4fcd-af8f-1b2054b31802`).

---

## 2. What Was Asked / What I Did

### What was asked
1. Write an erratum report for `docs/reports/DOC-005-gemini-run-plan.md` addressing errors identified during APC review.
2. Verify all 10 claims from the APC's prompt review against repo files and commit `52e05c6`.
3. Re-collect raw verification outputs from host commands:
   - Git log and commit stat for `52e05c6`.
   - Grep for uncommitted strings from DOC-005 report in committed `scripts/README.md`.
   - Grep for resume guard and dry-run branches in `scripts/run_experiment.py`.
   - CLI flags verification via `.venv-ann/bin/python scripts/run_experiment.py --help`.
   - 24 offline dry-run executions in a single loop checking `/tmp/doc005a-dry` before and after.
   - Brute-force live dry-run pre-flight check, plus offline and live pilot dry-runs.
   - Grep canonical thesis and task files for amortized bound references.
4. Replace the unmeasured Strategy 2 bound claim in `scripts/README.md` with:
   `Realised calls depend on how many existing concepts exceed θ, are not known before the run, and for the lower θ values may approach the brute-force count.`
5. Append decision entry `[D-70]` (next free ID after `D-69` taken by DOC-006) to `docs/decisions/decision-log.md`.
6. Update `docs/tasks/status.md` by annotating row `DOC-005` and adding row `DOC-005-A` marked **done**.

### What I actually did
1. Verified that `DOC-005-A` was unused in `docs/tasks/status.md` and `docs/reports/`.
2. Checked `docs/decisions/decision-log.md` and found `[D-69]` was already committed by DOC-006 (commit `67a04bc`); per standing instructions, allocated `D-70`.
3. Executed all required verification commands without running the test suite, without importing `torch` or `sentence_transformers`, without running the OpenMP timing snippet, and without live network/API calls.
4. Confirmed all 10 review findings from APC Section 0 with raw command output.
5. Re-verified the 24 planned-call bounds (159,400 sweep, 25,358 accuracy, 184,758 total) and zero-byte dry-run disk behavior.
6. Corrected `scripts/README.md` in-place (one sentence).
7. Appended `[D-70]` to `docs/decisions/decision-log.md`.
8. Updated `docs/tasks/status.md` with the erratum annotation and new `DOC-005-A` row.

---

## 3. Prompt Corrections (Review of APC Section 0 Claims)

Below is the verification of the 10 claims stated in Section 0 of the prompt:

1. **§2 "What was asked" describes decisions D3 and D5 differently from the prompt and from the commit (primary-then-sensitivity ordering, "sweep before accuracy", off-peak "21:00-09:00 UTC+8", a directory naming convention, a "single key policy", a D5 rule about OMP_NUM_THREADS):**  
   **CONFIRMED.** In `docs/reports/DOC-005-gemini-run-plan.md` lines 24 and 26, the report described run ordering as primary 1-4 then sensitivity 5-12 with sweep before accuracy, off-peak as 21:00-09:00 UTC+8, and an oversimplified D5 rule. In contrast, commit `52e05c6` [D-68](3) and `scripts/README.md` specify accuracy runs first across all 12 configs then sweeps, ordered S3, S4, S2, S1; off-peak follows D-37(1) (peak is 01:00-04:00 and 06:00-10:00 UTC Mon-Fri); and D5 specifies an interleaved 3-process statistical median test.
2. **§3 says the prompt stated a thesis hash 15ae6059… at d6d442e. The DOC-005 prompt contains no such hash:**  
   **CONFIRMED.** `docs/reports/DOC-005-gemini-run-plan.md` line 68 claims: *"The prompt states the live thesis hash at `d6d442e` is `15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a`."* That hash originated in DOC-004 documentation and was never provided in the DOC-005 prompt.
3. **§4.1's diff stat (53 and 104 lines) disagrees with the commit (22 lines in the decision log, 97 in the README):**  
   **CONFIRMED.** `git show --stat 52e05c6` shows `docs/decisions/decision-log.md | 22 +++` and `scripts/README.md | 97 ++++++++++`. DOC-005 report §4.1 claimed 53 lines and 104 lines.
4. **§4.2 (c) quotes a guard call with is_dry_run=args.dry_run and lines 888, 984, 1036; (d) lists flags --strategy-param and --n-trials as found in --help. The APC's copy of run_experiment.py has neither, and its dry-run branch is if config.dry_run::**  
   **CONFIRMED.** `grep -n` on `scripts/run_experiment.py` shows line 888 invokes `check_resume_or_existing_directory_guard` without `is_dry_run`, line 984 checks `if args.dry_run:`, and line 1036 checks `if config.dry_run:`. Neither `--strategy-param` nor `--n-trials` appears in `--help`.
5. **§4.3 and the final message label rows 3, 4, 7, 8, 10, 11, 12 wrongly (primary ANN as efSearch=64, S4 as k=5, efSearch=16, k=2, k=10). The numbers match the commit; the labels do not:**  
   **CONFIRMED.** In `docs/reports/DOC-005-gemini-run-plan.md` lines 108-117, the call numbers match arithmetic bounds, but parameter configurations were mislabelled: row 3 as `efSearch=64` (real default: `ef_search=128`), row 4 as `k=5, s_max=10` (real default: `s_min=5, s_max=10, n_bits=12`), row 7 as `efSearch=64` (real: `ef_search=128`), row 8 as `efSearch=64` (real: `ef_search=128`), row 10 as `efSearch=16` (real: `ef_search=64`), row 11 as `k=2, s_max=5` (real: `s_min=2, s_max=5`), and row 12 as `k=10, s_max=20` (real: `s_min=10, s_max=20`).
6. **§4.4 and §4.5 show commands with flags that do not exist (--strategy brute-force, --embedder none, --n-trials, --strategy-param, --embedder stub) and a peak window "01:00-13:00 UTC" that contradicts D-37(1) (01:00-04:00 and 06:00-10:00 UTC, Mon-Fri):**  
   **CONFIRMED.** The commands in DOC-005 report §4.4 and §4.5 contain invalid CLI flags (`brute-force`, `--embedder none`, `--n-trials`, `--strategy-param`, `--embedder stub`) and quote a fabricated peak window "01:00-13:00 UTC" which directly contradicts D-37(1).
7. **§5 "Diffs Applied" does not match the commit: it shows pins 3.4.1 and revision 33b49c4…, directory slugs results/<mode>/<strategy>_<params>_<timestamp>/, off-peak 21:00-09:00 UTC+8, a different OpenMP block and a different D-68 body. The committed README has none of those strings:**  
   **CONFIRMED.** Running `git show 52e05c6 -- scripts/README.md | grep -n -E "3\.4\.1|33b49c4|21:00|13:00|results/<mode>/|Single key|interop|OMP_NUM_THREADS"` returns zero matches. The diff in DOC-005 §5 was fabricated.
8. **§6 A-6(ii) quotes three sentences (thesis §2.2.4 "logarithmic under uniform clustering", thesis §3.5 "Empirical curves for Strategy D…", high-level-tasks.md line 81 "does LLM calls per insert scale with log(|V|)…") that the APC could not find verbatim in its bundle copies. The sections are right in substance; the quotes may be reconstructed:**  
   **CONFIRMED.** Grepping the canonical thesis and `docs/tasks/high-level-tasks.md` shows that line 81 of `high-level-tasks.md` ends at "either answer is a real finding" (the quoted clause does not exist); thesis §2.2.4 (line 138) does not contain "logarithmic under uniform clustering"; and thesis §3.5 (line 272) does not contain "Empirical curves for Strategy D are directly compared...". All three quotes were fabricated/reconstructed.
9. **The final message told Luke to run a different OpenMP block (printing thread counts, no timing) from the README's. That block does not implement the D-68(5) rule and is withdrawn:**  
   **CONFIRMED.** The block in the DOC-005 final message and §5.1 inspected static thread counts without measuring runtimes or applying the median-of-medians 10% materiality rule.
10. **The model label "Gemini (Antigravity system)" is not an exact label. Separately, the README note and [D-68](2) say Strategy 2's realised calls will "substantially" or "in practice" drop after cosine filtering. Nobody has measured that; at θ = 0.4 it may not hold. It is a prediction stated as fact:**  
    **CONFIRMED.** The model label was imprecise. The assertion that Strategy 2 calls drop substantially is an unmeasured prediction that may fail at lower thresholds ($\theta=0.4$), corrected in this task under A-2 and [D-70].

---

## 4. Verification Output (Raw, from A-1)

### (a) Git Log and Commit Stat
```bash
git log --oneline -5
```
```
67a04bc (HEAD -> master, task/DOC-006) DOC-006: close DOC-002, record D-69, narrow data-formats orientation claim, fix Phase 2 header, report errata
52e05c6 DOC-005: record run-plan decisions and README run plan (D-68)
627f4a0 (origin/master, origin/HEAD) DOC-004: proposed thesis sync after strategy track (report and diff only)
87c50fc docs: regenerate repo-tree.txt for DOC-002-B
f141457 (task/DOC-002-B) DOC-002-B: land corrected thesis text and context docs, close DOC-002
```

```bash
git show --stat 52e05c6
```
```
commit 52e05c60f8a4f2a0266897abf915804f6bcf129a
Author: Adrian Luke Labasan <zionexodus7@protonmail.com>
Date:   Wed Oct 14 15:29:36 2026 +0800

    DOC-005: record run-plan decisions and README run plan (D-68)

 docs/decisions/decision-log.md          |  22 +++
 docs/reports/DOC-005-gemini-run-plan.md | 322 ++++++++++++++++++++++++++++++++
 docs/tasks/status.md                    |   5 +-
 scripts/README.md                       |  97 ++++++++++
 4 files changed, 445 insertions(+), 1 deletion(-)
```

### (b) Grep for Fabricated Strings in Committed README (52e05c6)
```bash
git show 52e05c6 -- scripts/README.md | grep -n -E "3\.4\.1|33b49c4|21:00|13:00|results/<mode>/|Single key|interop|OMP_NUM_THREADS"
```
*(No output produced; zero matches confirmed).*

### (c) Grep for Resume Guard and Dry-Run Branches in `scripts/run_experiment.py`
```bash
grep -n -E "check_resume_or_existing_directory_guard|config\.dry_run|args\.dry_run" scripts/run_experiment.py
```
```
700:def check_resume_or_existing_directory_guard(
873:        dry_run=args.dry_run,
888:    guard_rc = check_resume_or_existing_directory_guard(
984:        if args.dry_run:
1036:    if config.dry_run:
```

### (d) CLI Flags from `--help`
```bash
.venv-ann/bin/python scripts/run_experiment.py --help | grep -E -- "--(mode|strategy|corpus|embedder|live|dry-run|confirm|output-dir|theta|ef-search|s-min|s-max|n-bits|sweep-trials|strategy-param|n-trials)"
```
```
usage: run_experiment.py [-h] [--mode {accuracy,sweep}]
                         [--strategy {null,stub,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}]
                         [-k K] [--theta THETA] [--ef-search EF_SEARCH]
                         [--s-min S_MIN] [--s-max S_MAX] [--n-bits N_BITS]
                         [--embedder {fake,minilm}]
                         [--corpus {DSA,metacademy,all}]
                         [--output-dir OUTPUT_DIR] [--run-id RUN_ID]
                         [--sweep-trials SWEEP_TRIALS]
                         [--model MODEL] [--max-llm-calls MAX_LLM_CALLS]
                         [--dry-run] [--confirm] [--resume] [--retry-failed]
                         [--fail-fast] [--live] [--allow-peak]
  --mode {accuracy,sweep}
  --strategy {null,stub,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}
  --theta THETA         Cosine similarity threshold theta for
  --ef-search EF_SEARCH
  --s-min S_MIN         Minimum segment size s_min for bounded_bucket
  --s-max S_MAX         Maximum segment size s_max for bounded_bucket
  --n-bits N_BITS       Number of LSH hyperplanes n_bits for bounded_bucket
  --embedder {fake,minilm}
  --corpus {DSA,metacademy,all}
  --output-dir OUTPUT_DIR
  --sweep-trials SWEEP_TRIALS
  --model MODEL         DeepSeek model identifier (default 'deepseek-flash',
  --dry-run             Print planned insertions and call estimates without
  --confirm             Explicit confirmation required to execute live trials.
  --live                Execute with live DeepSeek API (requires
```

### (e) The 24 Offline Dry-Runs in One Loop

Directory and git status before loop:
```bash
ls -la /tmp/doc005a-dry && git status --short
```
```
total 0
drwxr-xr-x  2 lukexodus lukexodus   40 Oct 14 15:44 .
drwxrwxrwt 36 root      root      1120 Oct 14 15:44 ..
 M docs/context/repo-tree.txt
```

Loop execution:
```bash
n=1
for strat_args in \
  "brute_force" \
  "embedding_threshold" \
  "embedding_threshold --theta 0.5" \
  "embedding_threshold --theta 0.4" \
  "ann_retrieval" \
  "ann_retrieval -k 5" \
  "ann_retrieval -k 20" \
  "ann_retrieval --ef-search 64" \
  "ann_retrieval --ef-search 256" \
  "bounded_bucket" \
  "bounded_bucket --s-min 2 --s-max 5" \
  "bounded_bucket --s-min 10 --s-max 20"
do
  for mode in sweep accuracy; do
    cmd=".venv-ann/bin/python scripts/run_experiment.py --mode $mode --strategy $strat_args --dry-run --output-dir /tmp/doc005a-dry/${mode}_${n}"
    echo "$cmd"
    $cmd | grep -F "ESTIMATED UPPER-BOUND LLM CALLS:"
  done
  n=$((n+1))
done
```
Raw loop output:
```
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy brute_force --dry-run --output-dir /tmp/doc005a-dry/sweep_1
ESTIMATED UPPER-BOUND LLM CALLS: 38500
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy brute_force --dry-run --output-dir /tmp/doc005a-dry/accuracy_1
ESTIMATED UPPER-BOUND LLM CALLS: 5012
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy embedding_threshold --dry-run --output-dir /tmp/doc005a-dry/sweep_2
ESTIMATED UPPER-BOUND LLM CALLS: 38500
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy embedding_threshold --dry-run --output-dir /tmp/doc005a-dry/accuracy_2
ESTIMATED UPPER-BOUND LLM CALLS: 5012
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy embedding_threshold --theta 0.5 --dry-run --output-dir /tmp/doc005a-dry/sweep_3
ESTIMATED UPPER-BOUND LLM CALLS: 38500
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy embedding_threshold --theta 0.5 --dry-run --output-dir /tmp/doc005a-dry/accuracy_3
ESTIMATED UPPER-BOUND LLM CALLS: 5012
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy embedding_threshold --theta 0.4 --dry-run --output-dir /tmp/doc005a-dry/sweep_4
ESTIMATED UPPER-BOUND LLM CALLS: 38500
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy embedding_threshold --theta 0.4 --dry-run --output-dir /tmp/doc005a-dry/accuracy_4
ESTIMATED UPPER-BOUND LLM CALLS: 5012
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy ann_retrieval --dry-run --output-dir /tmp/doc005a-dry/sweep_5
ESTIMATED UPPER-BOUND LLM CALLS: 600
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval --dry-run --output-dir /tmp/doc005a-dry/accuracy_5
ESTIMATED UPPER-BOUND LLM CALLS: 590
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy ann_retrieval -k 5 --dry-run --output-dir /tmp/doc005a-dry/sweep_6
ESTIMATED UPPER-BOUND LLM CALLS: 300
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval -k 5 --dry-run --output-dir /tmp/doc005a-dry/accuracy_6
ESTIMATED UPPER-BOUND LLM CALLS: 295
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy ann_retrieval -k 20 --dry-run --output-dir /tmp/doc005a-dry/sweep_7
ESTIMATED UPPER-BOUND LLM CALLS: 1200
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval -k 20 --dry-run --output-dir /tmp/doc005a-dry/accuracy_7
ESTIMATED UPPER-BOUND LLM CALLS: 1180
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy ann_retrieval --ef-search 64 --dry-run --output-dir /tmp/doc005a-dry/sweep_8
ESTIMATED UPPER-BOUND LLM CALLS: 600
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval --ef-search 64 --dry-run --output-dir /tmp/doc005a-dry/accuracy_8
ESTIMATED UPPER-BOUND LLM CALLS: 590
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy ann_retrieval --ef-search 256 --dry-run --output-dir /tmp/doc005a-dry/sweep_9
ESTIMATED UPPER-BOUND LLM CALLS: 600
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval --ef-search 256 --dry-run --output-dir /tmp/doc005a-dry/accuracy_9
ESTIMATED UPPER-BOUND LLM CALLS: 590
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy bounded_bucket --dry-run --output-dir /tmp/doc005a-dry/sweep_10
ESTIMATED UPPER-BOUND LLM CALLS: 600
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy bounded_bucket --dry-run --output-dir /tmp/doc005a-dry/accuracy_10
ESTIMATED UPPER-BOUND LLM CALLS: 590
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy bounded_bucket --s-min 2 --s-max 5 --dry-run --output-dir /tmp/doc005a-dry/sweep_11
ESTIMATED UPPER-BOUND LLM CALLS: 300
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy bounded_bucket --s-min 2 --s-max 5 --dry-run --output-dir /tmp/doc005a-dry/accuracy_11
ESTIMATED UPPER-BOUND LLM CALLS: 295
.venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy bounded_bucket --s-min 10 --s-max 20 --dry-run --output-dir /tmp/doc005a-dry/sweep_12
ESTIMATED UPPER-BOUND LLM CALLS: 1200
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy bounded_bucket --s-min 10 --s-max 20 --dry-run --output-dir /tmp/doc005a-dry/accuracy_12
ESTIMATED UPPER-BOUND LLM CALLS: 1180
```

Directory and git status after loop:
```bash
ls -la /tmp/doc005a-dry && git status --short
```
```
total 0
drwxr-xr-x  2 lukexodus lukexodus   40 Oct 14 15:44 .
drwxrwxrwt 36 root      root      1120 Oct 14 15:44 ..
 M docs/context/repo-tree.txt
```

### (f) Brute-Force Live Pre-Flight and Pilot Dry-Runs

#### Brute-Force Live Sweep Dry-Run Pre-Flight
```bash
.venv-ann/bin/python scripts/run_experiment.py --live --dry-run --mode sweep --strategy brute_force --names-file data/synthetic/cs_concept_names.json --output-dir /tmp/doc005a-dry/live_bf_sweep
```
```
=================================================================
LIVE EXPERIMENT PRE-FLIGHT ESTIMATE
Strategy:                      brute_force
Strategy config:               {'seed': 42}
Embedder:                      fake
Output directory:              /tmp/doc005a-dry/live_bf_sweep
Model alias:                   deepseek-flash
Full-plan calls (upper bound): 38500
Remaining calls (upper bound): 38500
Estimated duration:            38500.0s (641.7 min) (assuming 1.0s/call)
Estimated cost:                $0.9355 USD
Cost assumptions:              ~152 in, ~2.5 out tokens/call at $0.15/M in, $0.60/M out
-----------------------------------------------------------------
Current UTC:  2026-10-14 07:45:21 UTC
Philippine:   2026-10-14 15:45:21 PHT (UTC+8)
DeepSeek:     PEAK (charged at peak rates)
=================================================================
Peak check note: Planned execution window [07:45:21, 18:27:01 UTC] intersects DeepSeek peak pricing hours (01:00-04:00 or 06:00-10:00 UTC Mon-Fri). A real live run would be REFUSED unless '--allow-peak' is passed.
Dry run complete (live pre-flight estimation only; no API calls or client construction).
```

#### Pilot Offline Dry-Run
```bash
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval --corpus DSA --embedder minilm --dry-run --output-dir /tmp/pilot-s3-dsa
```
```
======================================================================
DRY RUN EXECUTION PLAN: ACCURACY MODE
Strategy: ann_retrieval
Strategy Config: {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
======================================================================
Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 290
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 29
ESTIMATED UPPER-BOUND LLM CALLS: 290
======================================================================
Default/resolved output directory: /tmp/pilot-s3-dsa
Dry run complete.
```

#### Pilot Live Dry-Run Pre-Flight
```bash
.venv-ann/bin/python scripts/run_experiment.py --mode accuracy --strategy ann_retrieval --corpus DSA --embedder minilm --live --dry-run --output-dir /tmp/pilot-s3-dsa
```
```
=================================================================
LIVE EXPERIMENT PRE-FLIGHT ESTIMATE
Strategy:                      ann_retrieval
Strategy config:               {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
Embedder:                      minilm
Output directory:              /tmp/pilot-s3-dsa
Model alias:                   deepseek-flash
Full-plan calls (upper bound): 290
Remaining calls (upper bound): 290
Estimated duration:            290.0s (4.8 min) (assuming 1.0s/call)
Estimated cost:                $0.0070 USD
Cost assumptions:              ~152 in, ~2.5 out tokens/call at $0.15/M in, $0.60/M out
-----------------------------------------------------------------
Current UTC:  2026-10-14 07:46:07 UTC
Philippine:   2026-10-14 15:46:07 PHT (UTC+8)
DeepSeek:     PEAK (charged at peak rates)
=================================================================
Peak check note: Planned execution window [07:46:07, 07:50:57 UTC] intersects DeepSeek peak pricing hours (01:00-04:00 or 06:00-10:00 UTC Mon-Fri). A real live run would be REFUSED unless '--allow-peak' is passed.
Dry run complete (live pre-flight estimation only; no API calls or client construction).
```

### (g) Thesis and Task File Amortized Bound Grep
Canonical thesis file: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md` (identified via `complete-context.md` line 13 and `decision-log.md` [D-69] line 573). The second copy, `docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md`, is an earlier proposal draft from September 2026. Both files and `docs/tasks/high-level-tasks.md` were grepped:

```bash
grep -n -i -E "amortiz|Theorem 4|claimed bound|designed to address|predicted shape" "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md" "docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md" docs/tasks/high-level-tasks.md
```
```
docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md:110:### 2.1.2 Amortized Complexity Analysis
docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md:112:Separately, and originating in an entirely different research tradition, the field of algorithm analysis has long studied how to reason about the cost of operations that modify a data structure repeatedly over time — insertions into a dynamic array, insertions into a self-balancing tree, or updates to a spatial data structure such as a Voronoi diagram. The relevant analytical tool here is *amortized complexity*: rather than analyzing the worst-case cost of a single operation, amortized analysis considers the average cost across a sequence of operations, which often reveals that an occasional expensive operation (such as a data structure resizing itself) is "paid for" by many preceding cheap operations, yielding a favorable average cost overall.
docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md:136:Zhang, Huang, Zhou, Guo, Li, Luo, Jiang, Fang, and Zhou \[4\] propose EraRAG, a hierarchical graph-based retrieval system designed for growing text corpora. Structurally, EraRAG organizes incoming data into size-bounded "buckets" using a hyperplane-based locality-sensitive hashing scheme; because bucket size is capped by a small constant, inserting new data only ever requires modifying a bounded, constant-sized region of the graph, regardless of how large the graph has already grown. The authors formally prove this property as their Theorem 4, establishing an amortized time complexity of O(Δ(nd \+ S\_LLM)) for inserting Δ new items — a bound that, if it holds, implies insertion cost should not increase merely because the pre-existing graph has grown larger.
docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md:138:This claim is of direct and central relevance to the present study for two reasons. First, it is, among all works reviewed, the only one to offer a formal proof of an amortized cost bound specifically for LLM-graph insertion, making it the strongest available theoretical anchor for this study's central research question. Second, and more importantly for motivating this study's contribution, a close reading of EraRAG's own reported experiments reveals that this bound is never empirically validated against the specific variable it claims to be independent of: total pre-existing graph size. Every dynamic-insertion experiment reported by the authors holds the pre-existing corpus at a fixed proportion (typically splitting a dataset into a 50% "initial" portion, with the remaining 50% inserted in fixed increments) and varies only the size of the *incoming batch*, never the size of the *graph being inserted into*. The proof itself — while broadly consistent with established amortized-analysis techniques such as those described in Section 2.1.2 — warrants closer scrutiny: the proof's central step — asserting that repeated bucket splits and merges will not cascade without formally invoking a standard amortized-analysis technique such as a potential-function or accounting argument — falls short of the rigor typically expected of such a bound, a gap this study's proposed empirical measurement is directly designed to address.
docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md:272:The primary analytical method of this study is the visual and statistical comparison of scaling curves: for each strategy, wall-clock time and LLM call count are plotted against graph size, allowing direct visual inspection of whether cost grows linearly, sub-linearly, or remains effectively flat as the graph scales — the specific empirical question motivating this study, as established in Chapter 1's Statement of the Problem. Where a strategy's underlying literature makes an explicit theoretical claim about its scaling behavior (most notably, the amortized bound proposed in \[4\] for bucket-based partitioning), the observed empirical curve is directly compared against that claimed bound to assess consistency, addressing Research Question 4\.
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:21:- **EraRAG** \[5\] is the closest existing work to this proposal and serves as its anchor. It proves **Theorem 4**: an amortized insertion cost of O(Δ(nd \+ S\_LLM)) per update, via a bounded-bucket-size argument in the style of B-tree/LSM-tree amortized analyses, where |C| is the existing chunk count, Δ the batch size being inserted, d the embedding dimension, n the number of hyperplanes, and S\_LLM the cost of one LLM summarization call. This theorem has been verified directly against the paper. Critically, EraRAG's own experimental section varies the *batch* being inserted while holding the *existing* corpus size roughly constant across runs — it never empirically plots insertion cost as a function of total existing graph size, despite proving a bound that predicts exactly that relationship. This is the precise gap this thesis operationalizes.
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:27:Separately, classical algorithms research already provides mature amortized-cost proof techniques for structurally similar problems — incremental Voronoi diagrams \[7\] (O(√n) amortized), incremental minimum spanning trees \[8\] (O(log n) amortized), updatable learned indexes, and streaming approximate-nearest-neighbor graph construction (HNSW \[9\], Slipstream \[10\]). These confirm the analytical tools this thesis would need already exist; they have simply not been applied to LLM-driven graph insertion specifically.
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:31:As an LLM-constructed graph grows from small to large (e.g., n \= 50 to n ≥ 2000 nodes), how do different candidate-narrowing strategies for inserting a new node actually behave — in computational cost and in placement quality — and does their empirical behavior match the theoretical predictions where a theoretical bound exists (as it does for the bucket-capped strategy, per EraRAG's Theorem 4)?
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:40:| 4   | Bucket-capped / tree structure | EraRAG-style; the only strategy with a proven amortized-cost theorem to test empirically                                  |
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:67:4. Run the full graph-size sweep across all four strategies and all three metrics; analyze against the EraRAG Theorem 4 prediction specifically for Strategy 4\.
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:89:\[7\] \[Classical result — incremental Voronoi diagram construction with amortized-cost analysis. Specific canonical source not yet pinned; recommend confirming exact citation before submission.\]
docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md:91:\[8\] \[Classical result — incremental minimum spanning tree maintenance with amortized-cost analysis. Specific canonical source not yet pinned; recommend confirming exact citation before submission.\]
docs/tasks/high-level-tasks.md:7:- **EraRAG's Theorem 4 stated as the anchor** — this is the single most important sentence in the whole document, because it's what converts "we compared four things" into "we empirically tested whether a specific, named, existing theoretical claim holds." Without this framing, the adviser has no way to distinguish this from a class project.
docs/tasks/high-level-tasks.md:81:- **Directly compare the bucket-capped strategy's empirical curve against EraRAG's Theorem 4's predicted shape** — this is the actual thesis contribution landing: does the measured curve look like what the theorem promises, or does it diverge, and either answer is a real finding.
```

---

## 5. The Corrected 12-Row Bounds Table

Flags are copied verbatim from the tested loop in A-1(e):

| # | Role | Strategy | CLI Flags | Sweep Upper Bound | Accuracy Upper Bound | Total Upper Bound |
|---|---|---|---|---:|---:|---:|
| 1 | Primary (S1) | `brute_force` | `--strategy brute_force` | 38,500 | 5,012 | 43,512 |
| 2 | Primary (S2) | `embedding_threshold` | `--strategy embedding_threshold` *(θ=0.6)* | 38,500 | 5,012 | 43,512 |
| 3 | Primary (S3) | `ann_retrieval` | `--strategy ann_retrieval` *(k=10, ef_search=128)* | 600 | 590 | 1,190 |
| 4 | Primary (S4) | `bounded_bucket` | `--strategy bounded_bucket` *(s_min=5, s_max=10, n_bits=12)* | 600 | 590 | 1,190 |
| 5 | Sensitivity (S2) | `embedding_threshold` | `--strategy embedding_threshold --theta 0.5` | 38,500 | 5,012 | 43,512 |
| 6 | Sensitivity (S2) | `embedding_threshold` | `--strategy embedding_threshold --theta 0.4` | 38,500 | 5,012 | 43,512 |
| 7 | Sensitivity (S3) | `ann_retrieval` | `--strategy ann_retrieval -k 5` *(ef_search=128)* | 300 | 295 | 595 |
| 8 | Sensitivity (S3) | `ann_retrieval` | `--strategy ann_retrieval -k 20` *(ef_search=128)* | 1,200 | 1,180 | 2,380 |
| 9 | Sensitivity (S3) | `ann_retrieval` | `--strategy ann_retrieval --ef-search 64` *(k=10)* | 600 | 590 | 1,190 |
| 10 | Sensitivity (S3) | `ann_retrieval` | `--strategy ann_retrieval --ef-search 256` *(k=10)* | 600 | 590 | 1,190 |
| 11 | Sensitivity (S4) | `bounded_bucket` | `--strategy bounded_bucket --s-min 2 --s-max 5` *(n_bits=12)* | 300 | 295 | 595 |
| 12 | Sensitivity (S4) | `bounded_bucket` | `--strategy bounded_bucket --s-min 10 --s-max 20` *(n_bits=12)* | 1,200 | 1,180 | 2,380 |
| **Total** | | | | **159,400** | **25,358** | **184,758** |

*(Note on Strategy 2 bounds: Strategy 2 shortlists are uncapped by design, returning $n_{\text{existing}}$ in the worst case; realized calls depend on how many existing concepts exceed θ, are not known before the run, and for the lower θ values may approach the brute-force count).*

---

## 6. Erratum Table for `docs/reports/DOC-005-gemini-run-plan.md`

| Section | What DOC-005 Report Says | What Is True in Repo / Commit | Evidence Line |
|---|---|---|---|
| **§1 Agent Identity** | Model label `Gemini (Antigravity system)`. | Exact platform tool label is `Gemini 3.8 Flash (Medium)`. | System metadata / prompt context. |
| **§2 What Was Asked** | Claimed D3 ordered primary 1-4 then sensitivity 5-12, "sweep before accuracy", off-peak 21:00-09:00 UTC+8, per-run directory naming convention, single key policy; oversimplified D5 rule. | Commit `52e05c6` [D-68](3) and `scripts/README.md` specify all 12 accuracy runs first then sweeps, ordered S3, S4, S2, S1; off-peak follows D-37(1); D5 is an interleaved 3-process statistical median test. | `git show 52e05c6:docs/decisions/decision-log.md` |
| **§3 Prompt Corrections** | Prompt stated thesis hash `15ae6059...` at `d6d442e`. | The DOC-005 prompt contained no such hash; hash originated in DOC-004. | DOC-005 prompt text and `grep -rn "15ae6059" .` |
| **§4.1 Diff Stat** | 53 lines added to `decision-log.md`, 104 to `scripts/README.md`. | Commit `52e05c6` added 22 lines to `decision-log.md` and 97 lines to `scripts/README.md`. | `git show --stat 52e05c6` |
| **§4.2 Grep Verifications** | Quoted `check_resume_or_existing_directory_guard(..., is_dry_run=args.dry_run)` and `if args.dry_run: return 0` at line 1036; claimed `--strategy-param` and `--n-trials` in `--help`. | Guard has no `is_dry_run` param; line 1036 checks `if config.dry_run:`; `--strategy-param` and `--n-trials` do not exist in CLI. | `scripts/run_experiment.py:888,1036` and `--help` grep |
| **§4.3 Dry-Run Table** | Table mislabelled configurations for rows 3, 4, 7, 8, 10, 11, 12 (primary ANN as efSearch=64, S4 as k=5, efSearch=16, k=2, k=10). | Numbers (159,400 and 25,358) were correct; parameter labels were incorrect and contradicted code defaults and README. | `scripts/README.md:212-223` and raw dry-run loop output |
| **§4.4 Pre-Flight Telemetry** | Quoted command with invalid flags (`--strategy brute-force`, `--embedder none`, `--n-trials 100`) and fabricated peak window `(01:00-13:00 UTC)`. | CLI requires `--strategy brute_force`; real output displays formatted pre-flight estimate block and peak hours `01:00-04:00 or 06:00-10:00 UTC Mon-Fri` per D-37(1). | Raw output of `.venv-ann/bin/python scripts/run_experiment.py --live --dry-run ...` |
| **§4.5 Pilot Telemetry** | Quoted command with `--strategy ann-retrieval`, `--embedder stub`, `--strategy-param`, `--n-trials 29`, and fabricated dry-run output. | CLI requires `--strategy ann_retrieval`, `--embedder minilm` or `fake`, `-k 10`, `--ef-search 128`; real output displays execution plan or live estimate block. | Raw output of offline and live pilot dry-runs |
| **§5 Diffs Applied** | Fabricated diffs containing `3.4.1`, `33b49c4...`, `results/<mode>/...`, `21:00-09:00 UTC+8`, and un-timed OpenMP block. | None of these strings appear in commit `52e05c6` or `scripts/README.md`. | `git show 52e05c6 -- scripts/README.md` |
| **§6 Found But Not Changed** | Quoted three sentences claiming direct testing of EraRAG Theorem 4. | The sections exist and discuss Theorem 4, but the exact quotes were partly invented/reconstructed by the agent. | Grep on canonical thesis and `docs/tasks/high-level-tasks.md:81` |
| **§7 Open Questions** | Advised Luke to run un-timed OpenMP snippet from §5.1. | That block is withdrawn; Luke must run only the diagnostic benchmark in `scripts/README.md`. | `scripts/README.md:272-287` |

---

## 7. Diffs

### `scripts/README.md`
```diff
diff --git i/scripts/README.md w/scripts/README.md
index b1c718c..51502c2 100644
--- i/scripts/README.md
+++ w/scripts/README.md
@@ -223,7 +223,7 @@ The table below summarizes the verified planned upper-bound LLM call counts per
 | **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 10 --s-max 20` *(n_bits=12)* | 1,200 | 1,180 |
 | **Total** | | | **159,400** | **25,358** |
 
-*Note on Strategy 2 bounds:* Strategy B does not cap candidate shortlists (`max_candidates` returns $n_{\text{existing}}$), so its bounds (38,500 sweep, 5,012 accuracy) represent theoretical worst-case guard ceilings. In practice, cosine filtering will prune candidate lists substantially.
+*Note on Strategy 2 bounds:* Strategy B does not cap candidate shortlists (`max_candidates` returns $n_{\text{existing}}$), so its bounds (38,500 sweep, 5,012 accuracy) represent theoretical worst-case guard ceilings. Realised calls depend on how many existing concepts exceed θ, are not known before the run, and for the lower θ values may approach the brute-force count.
 
 Combined upper-bound total across all 24 runs: **184,758 LLM calls**.
 
```

### `docs/decisions/decision-log.md`
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 6f87a1d..999a1be 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -571,3 +571,11 @@ Reasoning: records the operator's decisions on run phasing, dual-mode evaluation
 (4) Corrections by later entry: the DATA-002 report's total of 176 overlapping positive edges is an arithmetic error (its per-file counts sum to 171, and 171 + 254 = 425); the report is write-once and is corrected in the DOC-006 report errata. [D-19] states that the reversed orientation was verified in all 10 example files; for `MEKG_with_8_nodes(logic).txt` it rests on domain reasoning only, so `data-formats.md` is narrowed to the nine checkable files.
 (5) Not decided here: whether thesis Section 3.5 may keep comparing the observed curve with the amortised bound in [4] (Research Question 4) given [D-62](4), under which the sweep performs one insertion per trial after `setup()`; and the Strategy 4 text sync of [D-59](8) (see DOC-004).
 Reasoning: records what was accepted and why, so later readers do not mistake the DOC-002 draft for the accepted text, and keeps the decision log append-only while correcting overstated statements. Affects: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`, `docs/context/complete-context.md`, `docs/context/data-formats.md`, `docs/tasks/status.md`, `docs/decisions/decision-log.md`, `docs/reports/DOC-002-gemini.md`, `docs/reports/DOC-002-A-gemini.md`, `docs/reports/DOC-002-B-gemini.md`, `docs/reports/DATA-002-gemini-mekg-directionality.md`, DOC-002, DOC-006.
+
+**[D-70]** Correction to Strategy 2 realized call wording, DOC-005 report errata and status record authority, withdrawal of alternative OpenMP snippet (DOC-005-A):
+(1) Correction to the last sentence of [D-68](2) ("realized calls will be substantially lower after cosine filtering"): this assertion was unmeasured and is withdrawn; it is replaced by the README wording in DOC-005-A: "Realised calls depend on how many existing concepts exceed θ, are not known before the run, and for the lower θ values may approach the brute-force count."
+(2) Authority of committed record: the report `docs/reports/DOC-005-gemini-run-plan.md` is write-once but contains errors in framing, CLI flags, dry-run commands, table labels, and diffs; it is superseded by `docs/reports/DOC-005-A-gemini-erratum.md` wherever they conflict. The committed [D-68], the `scripts/README.md` run-plan section (with the A-2 wording fix), and the status rows in `docs/tasks/status.md` are the authoritative record.
+(3) OpenMP snippet withdrawal: the alternative OpenMP check snippet in DOC-005 report §5.1 and in the DOC-005 agent's final message (printing thread counts without timing) is withdrawn; the block in the `scripts/README.md` run-plan section is the only one Luke runs, under the [D-68](5) rule.
+(4) Open items: unchanged from [D-68](6).
+Reasoning: keeps the decision log append-only while withdrawing unverified assertions, establishing the committed README and decision log as authoritative over the flawed DOC-005 report, and confirming the exact OpenMP procedure to execute. Affects: `scripts/README.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/DOC-005-gemini-run-plan.md`, DOC-005, DOC-005-A, RUN-001.
```

### `docs/tasks/status.md`
```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 8284e63..b6d63c9 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -99,6 +99,7 @@ Status: **not started** (blocked on Phase 3)
 | TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, add thesis size check (>300 KB), add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
 | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
 | DOC-004 | Thesis sync after strategy track: proposed edits only (Strategy D parameters and adaptation wording; Theorem 4 symbol resolution n -> b and S_LLM scope; Strategy C index parameters, efSearch {64, 256}, and synthetic recall evidence; fallback rewording and candidate citations for M=16, efConstruction=200; theta=0.6 calibration limitation). Report and unified diff only; thesis unmodified. | **needs-review** | Completed by Gemini. See report [`docs/reports/DOC-004-gemini-thesis-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-sync.md) and diff [`docs/reports/DOC-004-gemini-thesis-proposed.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-proposed.diff). |
-| DOC-005 | Record the run-plan decisions (D-68), add the run plan to the README, verify the planned-call bounds offline. | **done** | Completed by Gemini. See report [`docs/reports/DOC-005-gemini-run-plan.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-gemini-run-plan.md). |
+| DOC-005 | Record the run-plan decisions (D-68), add the run plan to the README, verify the planned-call bounds offline. | **done** | Completed by Gemini. See report [`docs/reports/DOC-005-gemini-run-plan.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-gemini-run-plan.md). Report contains errors; see DOC-005-A (D-70, originally reserved as D-69); the committed D-68 and README run-plan section are authoritative. |
+| DOC-005-A | Erratum for the DOC-005 report, correct Strategy 2 bound wording ([D-70]), and raw re-verification of the planned-call bounds. | **done** | Completed by Gemini; see report [`docs/reports/DOC-005-A-gemini-erratum.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-A-gemini-erratum.md). |
 | DOC-006 | Close DOC-002 with the DOC-002-B text; record [D-69] (D-33 hold-out clarification, confirmed data counts, corrections to D-19 and DATA-002); narrow the `data-formats.md` orientation sentence to the nine checkable files; fix the Phase 2 header; errata for the DOC-002-B, DOC-002-A and DATA-002 reports. | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-006-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-006-gemini.md). |
```

---

## 8. Found But Not Changed

- `docs/context/repo-tree.txt`: modified in working tree prior to this task; left unstaged per Section 5 instructions.
- `docs/reports/DOC-005-gemini-run-plan.md`: preserved unmodified per the write-once report rule; superseded by this erratum report.
- `docs/reports/to-be-shared/llm-graph-insertion-complexity-thesis.md`: early proposal draft; left unmodified.
- `docs/thesis/An Empirical Complexity Analysis...md`: canonical thesis text; left unmodified (any revisions to Theorem 4 claims remain for Luke, the adviser, and the pending DOC-004 review).
- `docs/tasks/high-level-tasks.md`: contains line 81 referring to EraRAG Theorem 4 predicted shape; left unmodified.
- `docs/decisions/decision-log.md` [D-69]: was already taken by commit `67a04bc` (DOC-006); left untouched and next free ID `D-70` was allocated.

---

## 9. Open Questions Flagged for Attention

1. **[Luke] Run the README OpenMP benchmark snippet:**  
   Execute the benchmark loop documented in `scripts/README.md` (lines 272-287) in `.venv-ann` on the host machine and report the six output lines so the [D-68](5) materiality condition can be evaluated prior to non-pilot live embedding runs. Do not run the snippet from the DOC-005 final message.
2. **[Luke] Execute Pilot Run:**  
   After the OpenMP check determination (or immediately for brute force), run the DSA pilot in accuracy mode (`/tmp/pilot-s3-dsa`) with `--confirm` during off-peak hours to verify live credentials and plumbing.
3. **[Luke / Adviser] Thesis alignment on EraRAG amortised claims:**  
   In canonical thesis §2.2.4 and §3.5 and `high-level-tasks.md` line 81, clarify that the empirical sweep evaluates the un-amortised single-step insertion complexity of the bounded-bucket structural adaptation, rather than directly testing EraRAG's multi-insertion amortisation claim (Theorem 4).
4. **[APC / APC-A] DOC-004 thesis sync review:**  
   Ensure that the DOC-004 thesis sync review incorporates the un-amortised single-step clarification into Chapter 3.
