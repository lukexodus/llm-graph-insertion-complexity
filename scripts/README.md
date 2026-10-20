# APC Bundle Tool (`scripts/apc-bundle.sh`)

`scripts/apc-bundle.sh` is an archive packager for uploading repository files to an external **APC** (Advisor / Planner / Controller) AI chat session.

Because the external APC has **no direct filesystem access** and **no persistent memory** across sessions, this tool packages all necessary context, documentation, and code into a self-describing, repo-relative, verified archive.

---

## Quick Start

Always execute the script from the **repository root**:

```bash
# 1. Preview default bundle ('core') and file sizes without creating an archive
./scripts/apc-bundle.sh --list

# 2. Package the default 'core' bundle
./scripts/apc-bundle.sh

# 3. Package the 'strat' profile with an ad hoc file
./scripts/apc-bundle.sh strat --add src/graph_insertion/strategy.py

# 4. Discover code files defining core symbols
./scripts/apc-bundle.sh --discover
```

---

## Built-In Profiles

The script provides 5 standard profiles. If no profile is specified, it defaults to `core`.

| Profile | Purpose | Included Files |
| :--- | :--- | :--- |
| `core` *(default)* | Operational context & tracking | `AGENTS.md`, `docs/context/complete-context.md`, `docs/context/data-formats.md`, `docs/context/strategy-interface.md`, `docs/context/apc-handoff-template.md`, `docs/context/apc-bundle-quickref.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `pyproject.toml` |
| `strat` | Strategy review & testing | All of `core`, plus `src/graph_insertion/strategies/null.py`, `tests/test_strategy_interface.py`, `tests/test_null_strategy.py`, `docs/rrl/catalogue.md` |
| `strat-design` | Methodology & thesis text | All of `strat`, plus the thesis document (`docs/thesis/*.md`) |
| `fix` | Interface contracts & fixes | All of `core`, plus `docs/context/prompt-adapter-contract.md` |
| `full` | Complete snapshot | Union of all profiles above (de-duplicated) |

### The "Comment-Out" Workflow
Each profile is declared as a bash array directly inside [`scripts/apc-bundle.sh`](apc-bundle.sh). You can comment out or uncomment lines directly within those arrays before running the script to fine-tune your upload bundle.

---

## Command Line Options

```text
Usage: scripts/apc-bundle.sh [PROFILE] [OPTIONS]
```

### Options Reference

- **`[PROFILE]`** *(positional)*: Name of the profile to package (`core`, `strat`, `strat-design`, `fix`, `full`). Defaults to `core`.
- **`--list`**: Prints all resolved files and their sizes in bytes to `stdout` and exits `0` without creating an archive.
- **`--tokens`**: Computes and prints estimated token count of resolved files in the bundle (~1 token per 4 chars) and exits `0` without creating an archive.
- **`--discover`**: Searches `src/` for definitions of core symbols (`Shortlist`, `MeteredEmbedder`, `ConceptGraph`, `FakeEmbedder`, `embed_text`, `insert_node`, `candidate_upper_bound`) and prints matching files. Does not modify or create an archive.
- **`--add PATH`** *(repeatable)*: Adds an ad hoc file to the bundle. Path must exist, be a regular file, and pass secret guards.
- **`--exclude GLOB`** *(repeatable)*: Excludes files matching a glob or filename from the bundle (e.g. `--exclude 'AGENTS.md'` or `--exclude '*.py'`).
- **`--with-reports`**: Appends uncommented report paths from `OPTIONAL_REPORTS` in `scripts/apc-bundle.sh`.
- **`-h, --help`**: Displays CLI help and exits `0`.

---

## Safety & Secret Guards

Before anything is written, the script enforces strict validation checks. Any failure causes the script to abort with **exit code 1**, listing **all** offending paths:

1. **Missing Files:** Every resolved file must exist and be a regular file on disk.
2. **Secret Detection:** Rejects any path or file matching:
   - `.env*`
   - `*.key`
   - `*.pem`
   - `*secret*`, `*token*`, `*credential*` (case-insensitive)
3. **Forbidden Directories:** Rejects any path under:
   - `results/`
   - `repositories/`
   - `.git/`
   - `.venv/`
   - `node_modules/`
4. **Thesis Check:** Warns on `stderr` if the thesis file exceeds 300 KB.

---

## Archive Output & `MANIFEST.txt`

When executed, the script creates a gzipped tar archive in the current working directory:

```text
apc-bundle-<profile>-<YYYYmmdd-HHMM>.tar.gz
```

### Archive Structure
- All files are stored with **repo-relative paths** (e.g., `docs/context/complete-context.md`).
- A `MANIFEST.txt` file is placed at the root of the archive.

### Manifest Content
`MANIFEST.txt` contains self-describing audit metadata:
- Profile name
- UTC timestamp of creation
- Short git commit hash (`git rev-parse --short HEAD`)
- Working tree status (`git status --porcelain` restricted to bundled files)
- Checksum table: `<sha256>  <size_in_bytes>  <repo_relative_path>`
- Extraction and verification instructions.

---

## Verifying and Extracting Archives

### Extraction
To extract into an existing directory preserving relative paths:
```bash
tar -xzf apc-bundle-core-20261009-1452.tar.gz
```

### Checksum Verification
To verify file integrity against `MANIFEST.txt`:
```bash
awk '/^[0-9a-f]{64}/ {print $1 "  " $3}' MANIFEST.txt | sha256sum -c -
```

---

## Running Automated Tests

The tool includes a standalone test suite in [`tests/test_apc_bundle.sh`](../tests/test_apc_bundle.sh) covering all profiles, glob resolutions, exclusion filters, secret guards, and archive extractions:

```bash
bash tests/test_apc_bundle.sh
```

---

## Common Recipes

### 1. Preparing an upload for an APC session on strategy design
```bash
./scripts/apc-bundle.sh strat-design
```

### 2. Including strategy implementation and embedding modules
```bash
./scripts/apc-bundle.sh strat \
  --add src/graph_insertion/strategy.py \
  --add src/graph_insertion/embedding.py
```

### 3. Sharing the core docs without `AGENTS.md`
```bash
./scripts/apc-bundle.sh core --exclude 'AGENTS.md'
```

### 4. Inspecting what will be bundled before writing to disk
```bash
./scripts/apc-bundle.sh full --list
```

---

## Experiment Runner CLI (`scripts/run_experiment.py`)

`scripts/run_experiment.py` executes accuracy (leave-one-out on DSA and Metacademy) and cost-scaling sweep (D-35 matrix: sizes `50 100 200 500 1000 2000` × 10 trials) benchmarks across all registered candidate-narrowing strategies.

### Registered Strategies & CLI Flags

- **`--strategy {null,stub,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}`**: Strategy to evaluate (default: `null`). Derived from `graph_insertion.strategies.registry.STRATEGY_FACTORIES`.
- **`-k, --k INT`**: Candidate shortlist size $k$ (`null`, `stub`, `ann_retrieval`). Defaults to `None` (resolves to `1` for `null`, `5` for `stub`, `10` for `ann_retrieval`).
- **`--theta FLOAT`**: Cosine similarity threshold $\theta$ (`embedding_threshold` only; default `0.6`).
- **`--ef-search INT`**: FAISS HNSW `efSearch` query depth (`ann_retrieval` only; default `128`).
- **`--s-min INT`**: Minimum segment size $s_{\min}$ (`bounded_bucket` only; default `5`).
- **`--s-max INT`**: Maximum segment size $s_{\max}$ (`bounded_bucket` only; default `10`).
- **`--n-bits INT`**: Number of LSH hyperplanes $n_{\text{bits}}$ (`bounded_bucket` only; default `12`).
- **`--embedder {fake,minilm}`**: Embedding backend (default: `fake`). Live runs (`--live`) for any strategy with `uses_embeddings=True` (`embedding_threshold`, `ann_retrieval`, `bounded_bucket`) require `--embedder minilm` (pinned local `sentence-transformers` `all-MiniLM-L6-v2` on CPU per [D-35](4)); `--embedder fake` is refused with exit code `1`. Non-embedding strategies (`null`, `stub`, `brute_force`) ignore `--embedder`.
- **Applicability & Range Validation**: Passing a strategy-specific flag to a strategy that does not accept it (e.g., `--theta` with `ann_retrieval`, `--s-max` with `brute_force`, `-k` with `bounded_bucket`) is rejected as a CLI usage error (`parser.error`, exit code `2`). Out-of-range parameter values raise the strategy's `ValueError`, printed as `ERROR: ...` with exit code `1` (no traceback).

### Deterministic Default Run Directories & Configuration Sidecar

- When neither `--output-dir` nor `--run-id` is passed, the default output directory is `results/<mode>_<strategy>` (for `brute_force` at seed 42) or `results/<mode>_<strategy>_<slug>`, where `<slug>` encodes the strategy's keyed `config()` fields in fixed order (`_seed<seed>` is appended when `--seed != 42` for strategies with a seed). Explicit `--output-dir` or `--run-id` takes precedence unchanged.
- `--dry-run` (both offline and `--live --dry-run`) prints the plan and resolved output directory without creating the output directory or any file on disk.
- On a real run (`--confirm`) into a fresh directory, `<output_dir>/strategy_config.json` (containing `{"strategy", "config", "embedder", "mode", "command_line_params"}`) is written immediately after `manifest.json` and before the first trial begins, preserving clean `git_dirty` status in `manifest.json` while remaining crash-safe before trial execution.
- On `--resume` (with an existing sidecar) or any run into an existing directory containing `raw.jsonl`, the CLI compares `strategy`, `config`, `mode`, and the `embedder` identity block (`type`, `model_name`, `dim`, `revision`, and installed `sentence_transformers_version` for `minilm`; `type`, `dim`, and `seed` for `fake`) in `strategy_config.json` with the current configuration and refuses with exit code `1` on mismatch. Older sidecars without `sentence_transformers_version` emit a single warning for that missing key and proceed; older directories containing `raw.jsonl` without `strategy_config.json` emit a warning to `stderr` and proceed without overwriting.
- **Live Embedding Runs & Offline Smoke Rule ([D-67])**: A one-time model download is required before any live embedding run (`pip install -e ".[embed]"`, then construct `MiniLMEmbedder()` once to cache the pinned `all-MiniLM-L6-v2` snapshot). Because default run directories (`results/<mode>_<strategy>_<slug>`) do not encode the embedder backend and the resume/existing-directory guard refuses an embedder mismatch, any offline smoke run of an embedding strategy using `--embedder fake` must pass an explicit `--output-dir` outside `results/` (for example `/tmp/...`), never the default directory that a subsequent live run will target. In addition, the OpenMP/PyTorch thread-count timing check (`docs/reports/INFRA-007-P-gemini.md` section 8.2) should be run once after the pins are in to verify single-threaded CPU embedding latency alongside FAISS.

### Primary & Sensitivity Run Table (D-35, D-46, D-47, D-55, D-58, D-59, D-62)

Note: `n_bits = 12` for `bounded_bucket` is fixed a priori ($2^{12} = 4096 > 2000$) and has **no** sensitivity runs ([D-62](1)).

| Role | Strategy | CLI Flags | Default Sweep Directory (`--mode sweep`) | Default Accuracy Directory (`--mode accuracy`) | D-35 Sweep Planned Calls Bound |
| :--- | :--- | :--- | :--- | :--- | ---: |
| **Primary (S1)** | `brute_force` | `--strategy brute_force` | `results/sweep_brute_force` | `results/accuracy_brute_force` | 38,500 |
| **Primary (S2)** | `embedding_threshold` | `--strategy embedding_threshold` *(θ=0.6)* | `results/sweep_embedding_threshold_theta0.6` | `results/accuracy_embedding_threshold_theta0.6` | 38,500 |
| **Primary (S3)** | `ann_retrieval` | `--strategy ann_retrieval` *(k=10, ef_search=128)* | `results/sweep_ann_retrieval_k10_ef128` | `results/accuracy_ann_retrieval_k10_ef128` | 600 |
| **Primary (S4)** | `bounded_bucket` | `--strategy bounded_bucket` *(s_min=5, s_max=10, n_bits=12)* | `results/sweep_bounded_bucket_smin5_smax10_nb12` | `results/accuracy_bounded_bucket_smin5_smax10_nb12` | 600 |
| **Sensitivity (S2)** | `embedding_threshold` | `--strategy embedding_threshold --theta 0.4` | `results/sweep_embedding_threshold_theta0.4` | `results/accuracy_embedding_threshold_theta0.4` | 38,500 |
| **Sensitivity (S2)** | `embedding_threshold` | `--strategy embedding_threshold --theta 0.5` | `results/sweep_embedding_threshold_theta0.5` | `results/accuracy_embedding_threshold_theta0.5` | 38,500 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval -k 5` *(ef_search=128)* | `results/sweep_ann_retrieval_k5_ef128` | `results/accuracy_ann_retrieval_k5_ef128` | 300 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval -k 20` *(ef_search=128)* | `results/sweep_ann_retrieval_k20_ef128` | `results/accuracy_ann_retrieval_k20_ef128` | 1,200 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval --ef-search 64` *(k=10)* | `results/sweep_ann_retrieval_k10_ef64` | `results/accuracy_ann_retrieval_k10_ef64` | 600 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval --ef-search 256` *(k=10)* | `results/sweep_ann_retrieval_k10_ef256` | `results/accuracy_ann_retrieval_k10_ef256` | 600 |
| **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 2 --s-max 5` *(n_bits=12)* | `results/sweep_bounded_bucket_smin2_smax5_nb12` | `results/accuracy_bounded_bucket_smin2_smax5_nb12` | 300 |
| **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 10 --s-max 20` *(n_bits=12)* | `results/sweep_bounded_bucket_smin10_smax20_nb12` | `results/accuracy_bounded_bucket_smin10_smax20_nb12` | 1,200 |

### Run plan (D-68)

#### 1. Total Runs and Verified Upper-Bound Calls (24 Runs)

Every one of the 12 configurations (4 primary + 8 sensitivity per the table above and [D-64](4)) is evaluated across **both** `--mode sweep` and `--mode accuracy` (24 distinct experimental runs). Synthetic concept names carry no ground-truth edges and isolate cost-scaling curves (thesis §3.3.2, RQ1); accuracy mode evaluates placement precision, recall, $F_1$, and candidate shortlist recall against gold-standard graphs (RQ2); evaluating both modes allows side-by-side comparison across all primary and sensitivity conditions (RQ3).

The table below summarizes the verified planned upper-bound LLM call counts per configuration for both modes (confirmed offline via `--dry-run`):

| Role | Strategy | CLI Flags | Sweep Upper Bound | Accuracy Upper Bound |
| :--- | :--- | :--- | ---: | ---: |
| **Primary (S1)** | `brute_force` | `--strategy brute_force` | 38,500 | 5,012 |
| **Primary (S2)** | `embedding_threshold` | `--strategy embedding_threshold` *(θ=0.6)* | 38,500 | 5,012 |
| **Primary (S3)** | `ann_retrieval` | `--strategy ann_retrieval` *(k=10, ef_search=128)* | 600 | 590 |
| **Primary (S4)** | `bounded_bucket` | `--strategy bounded_bucket` *(s_min=5, s_max=10, n_bits=12)* | 600 | 590 |
| **Sensitivity (S2)** | `embedding_threshold` | `--strategy embedding_threshold --theta 0.4` | 38,500 | 5,012 |
| **Sensitivity (S2)** | `embedding_threshold` | `--strategy embedding_threshold --theta 0.5` | 38,500 | 5,012 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval -k 5` *(ef_search=128)* | 300 | 295 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval -k 20` *(ef_search=128)* | 1,200 | 1,180 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval --ef-search 64` *(k=10)* | 600 | 590 |
| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval --ef-search 256` *(k=10)* | 600 | 590 |
| **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 2 --s-max 5` *(n_bits=12)* | 300 | 295 |
| **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 10 --s-max 20` *(n_bits=12)* | 1,200 | 1,180 |
| **Total** | | | **159,400** | **25,358** |

*Note on Strategy 2 bounds:* Strategy B does not cap candidate shortlists (`max_candidates` returns $n_{\text{existing}}$), so its bounds (38,500 sweep, 5,012 accuracy) represent theoretical worst-case guard ceilings. Realised calls depend on how many existing concepts exceed θ, are not known before the run, and for the lower θ values may approach the brute-force count.

Combined upper-bound total across all 24 runs: **184,758 LLM calls**.

#### 2. Run Order and Phasing

1. **Plumbing Pilot First:** Strategy 3 primary on DSA in accuracy mode, into an isolated throwaway output directory outside `results/`:
   ```bash
   .venv-ann/bin/python scripts/run_experiment.py \
     --mode accuracy \
     --strategy ann_retrieval \
     --corpus DSA \
     --embedder minilm \
     --live \
     --confirm \
     --output-dir /tmp/pilot-s3-dsa
   ```
   *Verified bound:* 29 trials (DSA graph), at most 10 candidates each = **290 LLM calls** (estimated ~4.8 min, ~$0.0070 USD). Output is plumbing verification only (exercising live API client, pins, MiniLM, and FAISS together); it is not part of benchmark results and no parameters may change because of it ([D-35](5)).
2. **OpenMP / PyTorch Thread Check:** Run the diagnostic benchmark below prior to executing any non-pilot live run of an embedding strategy (Strategies 2, 3, 4).
3. **Accuracy Runs First:** Execute all 12 accuracy configurations before any sweep runs, in order:
   - Strategy 3 (`ann_retrieval`, 5 configurations: primary, $k \in \{5, 20\}$, $\text{efSearch} \in \{64, 256\}$)
   - Strategy 4 (`bounded_bucket`, 3 configurations: primary, $(2, 5)$, $(10, 20)$)
   - Strategy 2 (`embedding_threshold`, 3 configurations: $\theta \in \{0.6, 0.5, 0.4\}$)
   - Strategy 1 (`brute_force`, primary)
   *Rationale:* Accuracy mode is computationally small (25,358 total calls max); cheap strategies run first so any API or budget issues surface early before launching long sweep runs (`docs/tasks/high-level-tasks.md` Phase 3 step 3).
4. **Sweep Runs Second:** Execute all 12 cost-scaling sweep configurations:
   - Strategy 3 (`ann_retrieval`, 5 configurations)
   - Strategy 4 (`bounded_bucket`, 3 configurations)
   - Strategy 2 (`embedding_threshold`, 3 configurations: $\theta \in \{0.6, 0.5, 0.4\}$)
   - Strategy 1 (`brute_force`, primary) last.
   *Rationale:* Strategy 2 is uncapped by design and may approach brute-force cost for $\theta = 0.4$; brute force is exact (38,500 calls, ~10.7 h) and has no dependency on the OpenMP check.

#### 3. Off-Peak Scheduling Rules

Per [D-37](1) (correcting [D-36](3)), DeepSeek peak hours are **01:00–04:00 UTC** and **06:00–10:00 UTC** Monday through Friday. All other times (weekends, weekdays 00:00–01:00, 04:00–06:00, and 10:00–24:00 UTC) are off-peak.
The CLI pre-flight guard assumes 1.0 s per call and strictly refuses live execution if the planned duration window intersects peak hours.
- A brute-force sweep run requires 38,500 calls (estimated 10.7 hours continuous). It must be launched **at or after 10:00 UTC (18:00 PHT)** on a weekday (which provides a 15-hour off-peak window until 01:00 UTC next day), or on a weekend.
- Strategy 2 sweeps (especially $\theta=0.4$) can approach the same duration and must follow the same scheduling window.

#### 4. OpenMP / PyTorch Thread Check Outcome & Pinning Policy (D-71, D-72)

`faiss.omp_set_num_threads(1)` is called by `ann_retrieval.py` to ensure deterministic index construction and queries. In the torch-first import order FAISS and PyTorch were observed to share one OpenMP thread setting ([D-71]); in the faiss-first order that real Strategy 3 runs use, no such coupling was observed ([D-73]). Whether a cross-strategy latency confound arose in real runs is unestablished.

The diagnostic benchmark specified below was executed on Luke's host environment under **INFRA-008** (`docs/reports/INFRA-008-gemini-openmp-timing-check.md`):

```bash
for mode in default omp1 default omp1 default omp1; do
.venv-ann/bin/python - "$mode" <<'EOF'
import sys, time, statistics as st
import torch, faiss
from graph_insertion.embedding_minilm import MiniLMEmbedder
mode = sys.argv[1]
emb = MiniLMEmbedder()
for i in range(20): emb.embed(f"warmup_{i}")
if mode == "omp1": faiss.omp_set_num_threads(1)
ts = []
for i in range(200):
    t0 = time.perf_counter(); emb.embed(f"concept_name_{i:04d}"); ts.append((time.perf_counter()-t0)*1000)
print(f"{mode:8s} torch_threads={torch.get_num_threads()} median={st.median(ts):.3f} ms p95={sorted(ts)[190]:.3f} ms")
EOF
done
```

**Observed Outcome & Materiality Determination ([D-71]):**
- `default`: `torch.get_num_threads() = 4`, condition median $M_{\text{default}} = 16.856$ ms, spread 1.810 ms.
- `omp1`: `torch.get_num_threads() = 1`, condition median $M_{\text{omp1}} = 24.362$ ms, spread 0.970 ms.
- Shift: $+7.506$ ms ($+44.53\%$, $> 10\%$ threshold and $> 1.810$ ms spread).
- Both pre-fixed criteria in [D-68](5) were triggered: the effect is declared **material**.

**Pinning Policy & Implementation ([D-72], INFRA-009):**
- PyTorch intra-op CPU threads are pinned to `CPU_THREAD_PIN = 1` for every execution constructing `MiniLMEmbedder` via `graph_insertion.cpu_threads.pin_cpu_threads(1)` called in `scripts/run_experiment.py`.
- Recorded in `strategy_config.json` sidecar embedder block as `"cpu_threads": 1`. Resume guard checks for matching `cpu_threads` in existing sidecars (legacy-tolerant).
- Consequence: Strategies 2, 3, and 4 all execute CPU inference single-threaded (~24 ms per embedding on the reference host), so embedding times are uniform across strategies and independent of import order (single-threaded by protocol).
- The diagnostic snippet does not need to be re-run.

---

## Operational Tooling

In addition to `apc-bundle.sh`, this directory provides workflow automation scripts that enforce the APC + Local Agent operational protocol:

### `task-worktree.sh` — Worktree Lifecycle Helper

Enforces worktree isolation when running multiple local agents or tasks in parallel.

```bash
# Create an isolated task worktree and branch
./scripts/task-worktree.sh start ANALYSIS-002

# Inspect active worktrees
./scripts/task-worktree.sh list

# Review status inside a worktree
./scripts/task-worktree.sh status ANALYSIS-002

# Generate clean git diff from a worktree
./scripts/task-worktree.sh diff ANALYSIS-002

# Validate worktree state before operator commit
./scripts/task-worktree.sh handoff ANALYSIS-002

# Clean up worktree after merge
./scripts/task-worktree.sh remove ANALYSIS-002
```

### `validate-report.py` — Report Linter & Verification

Verifies that local agent task reports conform to the required schema, match `docs/tasks/status.md`, link a patch file in `patch/`, and contain valid unified git diffs.

```bash
# Validate the most recently written report:
./scripts/validate-report.py

# Validate a specific report file:
./scripts/validate-report.py docs/reports/DATA-005-gemini-sample-extraction.md

# Validate with strict patch file enforcement:
./scripts/validate-report.py docs/reports/DATA-005-gemini-sample-extraction.md --require-patch

# Validate all reports in docs/reports/:
./scripts/validate-report.py --all
```

### `manage-decisions.py` — Decision ID Allocator & Log Inspector

Prevents decision ID collisions when multiple parallel worktrees operate concurrently.

```bash
# Show next available Decision ID:
./scripts/manage-decisions.py next

# List all recorded decision IDs:
./scripts/manage-decisions.py list

# Check if a specific ID is available:
./scripts/manage-decisions.py check --id 84

# Reserve an ID in decision-log.md for an upcoming task:
./scripts/manage-decisions.py reserve --title "Select evaluation benchmark configuration"
```


