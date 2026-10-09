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
| `core` *(default)* | Operational context & tracking | `AGENTS.md`, `docs/context/complete-context.md`, `docs/context/data-formats.md`, `docs/context/strategy-interface.md`, `docs/context/apc-handoff-template.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `pyproject.toml` |
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
