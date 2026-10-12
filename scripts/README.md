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

