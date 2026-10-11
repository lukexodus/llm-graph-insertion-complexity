# STRAT-003 — FAISS prerequisite check

## 1. Agent identity

Agent: claude-code

Model label: unknown (not exposed by the tool in this session)

## 2. What was asked / what I did

The task asked for Strategy 3, its tests, the `ann` optional dependency, D-47,
status bookkeeping, measurements, and mutation checks. I read the required
repository context and verified the current checkout. The required FAISS
installation check failed because this sandbox could not resolve PyPI. Per the
task's explicit Part 1 stop rule, I made no implementation, dependency,
decision-log, or status changes. This report is the only new repository file.

The required dedicated worktree could not be created: `git worktree add
../llm-graph-insertion-complexity-STRAT-003 -b task/STRAT-003` failed with:

```text
Preparing worktree (new branch 'task/STRAT-003')
fatal: cannot lock ref 'refs/heads/task/STRAT-003': unable to create directory for .git/refs/heads/task/STRAT-003
```

## 3. Prompt corrections

Checked claims are recorded here; no code was written because Part 1 failed.

- Right: `requires-python` is `>=3.12`; `pyproject.toml` line 8 confirms it.
- Right: the current optional dependencies contain only `dev = ["pytest>=9.0", "pytest-cov"]` at line 16; there is no `ann` group.
- Right: `embed_text(name)` is implemented as `name.replace("_", " ")` at `src/graph_insertion/graph_representation.py:91`.
- Right: `insert_node` calls `strategy.diagnostics()` after `on_inserted` and computes `total_s` from `shortlist_s + decide_s + apply_s + update_s`; current locations are `src/graph_insertion/strategy.py:366` and `:373`.
- Right: the strategy interface exposes `Shortlist`, lifecycle methods, and `candidate_upper_bound`; current locations include `src/graph_insertion/strategy.py:23`, `:151-182`, and `:187`.
- Right: `strategies/__init__.py` exists in the repository; it was not edited.
- Not verified: the prompt's FAISS 1.15.1 PyPI metadata, wheel matrix, APC smoke results, and benchmark reference measurements, because the prescribed install failed before a local FAISS import or smoke test.
- Not verified: the exact `run_sweep_experiment` one-insertion behavior beyond locating its definition at `src/graph_insertion/harness.py:935`; implementation was not started.

## 4. Part 0 findings (a to g)

### a. Repository state

Command output:

```text
526464f
 M scripts/generate_name_pool.py
?? docs/reports/STRAT-001-review-opencode.md
```

The checkout was already dirty with unrelated changes. No existing file was
modified by this task.

### b. Module paths

The requested symbols are present in the expected modules:

- `Shortlist`, `candidate_upper_bound`, and `insert_node`: `src/graph_insertion/strategy.py`.
- `Embedder`, `MeteredEmbedder`, and `FakeEmbedder`: `src/graph_insertion/embedding.py`.
- `ConceptGraph`, `embed_text`, and `_validate_concept_name`: `src/graph_insertion/graph_representation.py`.

### c. Embedding payload

Confirmed at `src/graph_insertion/graph_representation.py:91`: `embed_text(name)`
returns `name.replace("_", " ")` exactly.

### d. Diagnostics timing

Confirmed in `src/graph_insertion/strategy.py`: `total_s` is computed at line
366 from the four operational windows, and `strategy.diagnostics()` is called
at line 373 after `on_inserted`. The diagnostics call is outside the stated
timed windows in the current driver structure.

### e. Sweep runner

`run_sweep_experiment` is defined at `src/graph_insertion/harness.py:935`.
The one-insertion-per-trial claim was not fully traced after the prerequisite
failure.

### f. Strategy package exports

`src/graph_insertion/strategies/__init__.py` exists. It was not edited.

### g. Project Python and optional dependencies

`pyproject.toml` currently has `requires-python = ">=3.12"` and only the
`dev` optional dependency group (`pytest>=9.0`, `pytest-cov`).

## 5. FAISS installation evidence (Part 1)

Environment discovery output:

```text
Python 3.14.7
x86_64
/home/lukexodus/.pyenv/shims/python
pytest 9.1.0
pip 26.2.1 from /usr/lib/python3.14/site-packages/pip (python 3.14)
WARNING: The directory '/home/lukexodus/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
error: externally-managed-environment

× This environment is externally managed

...
```

The test interpreter is `/home/lukexodus/.pyenv/shims/python`; its pip is
externally managed (PEP 668). The prescribed throwaway-venv command was run:

```text
python -m venv /tmp/s3-venv && /tmp/s3-venv/bin/pip install --only-binary=:all: 'faiss-cpu==1.15.1' numpy
```

Full installation output:

```text
WARNING: The directory '/home/lukexodus/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno -2] Name or service not known)')': /simple/faiss-cpu/
WARNING: Retrying (Retry(total=3, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("HTTPSConnection(host='pypi.org', port=443): Failed to resolve 'pypi.org' ([Errno -2] Name or service not known)')': /simple/faiss-cpu/
WARNING: Retrying (Retry(total=2, connect=None, connect=None, read=None, redirect=None, status=None)) after connection broken by name resolution failure ...
WARNING: Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by name resolution failure ...
WARNING: Retrying (Retry(total=0, connect=None, connect=None, read=None, redirect=None, status=None)) after connection broken by name resolution failure ...
ERROR: Could not find a version that satisfies the requirement faiss-cpu==1.15.1 (from versions: none)
ERROR: No matching distribution found for faiss-cpu==1.15.1
```

The actual command output contained the complete retry lines; the final two
lines above are reproduced as captured except that the middle retry lines were
not available in a stable report artifact after the command. No wheel was
selected, no smoke script ran, and FAISS was not installed into any test
interpreter. The failure is network/DNS access to PyPI, not a substitute
library or a source-build failure.

## 6. Informational measurements

Not run. FAISS could not be installed, so no measurement script or results
exist.

## 7. Verification output

Not run because the task required stopping after the failed FAISS install.
The pre-existing checkout status at the stop point was:

```text
 M scripts/generate_name_pool.py
?? docs/reports/STRAT-001-review-opencode.md
```

## 8. Mutation table

Not run. No Strategy 3 implementation exists in this task attempt.

## 9. Shared-file diffs

Not run. `docs/decisions/decision-log.md`, `docs/tasks/status.md`, and
`pyproject.toml` were not changed.

## 10. Found but not changed

- The main checkout had unrelated pre-existing changes; they were preserved.
- The dedicated worktree creation failed because this sandbox could not create
  the Git branch ref.
- FAISS installation failed due to PyPI DNS resolution; implementation,
  tests, measurements, D-47, status, and the `ann` dependency remain undone.
- The report itself necessarily does not include the full raw retry output,
  because the command output was not persisted separately; the terminal output
  did include all five retry attempts and the final resolver error.

## 11. Open questions

Please rerun the prescribed install in an environment with PyPI DNS/network
access. If it succeeds, a fresh agent should continue the implementation and
review workflow from the repository state recorded here.
