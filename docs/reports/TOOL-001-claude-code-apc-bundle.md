# Task Report: TOOL-001 APC Bundle Script Rework

**Date:** 2026-10-09  
**Agent:** Gemini (reporting under requested task artifact name `TOOL-001-claude-code-apc-bundle.md`)  
**Task ID:** TOOL-001  

---

## 1. Script Location

- **Previous location:** `apc-bundle.sh` (at repo root, untracked in git).
- **Relocation method:** Plain `mv` (not `git mv`, because `apc-bundle.sh` was untracked: `?? apc-bundle.sh` in `git status`).
- **Current location:** `scripts/apc-bundle.sh`.

---

## 2. Command Outputs

### 2.1 `scripts/apc-bundle.sh --list strat`

```
    8928  AGENTS.md
   11110  docs/context/complete-context.md
    6116  docs/context/data-formats.md
   14161  docs/context/strategy-interface.md
    3693  docs/context/apc-handoff-template.md
   61185  docs/decisions/decision-log.md
   25119  docs/tasks/status.md
     447  pyproject.toml
    4396  src/graph_insertion/strategies/null.py
   32639  tests/test_strategy_interface.py
   33443  tests/test_null_strategy.py
    7145  docs/rrl/catalogue.md
```

### 2.2 `scripts/apc-bundle.sh --list full`

```
    8928  AGENTS.md
   11110  docs/context/complete-context.md
    6116  docs/context/data-formats.md
   14161  docs/context/strategy-interface.md
    3693  docs/context/apc-handoff-template.md
   61185  docs/decisions/decision-log.md
   25119  docs/tasks/status.md
     447  pyproject.toml
    4396  src/graph_insertion/strategies/null.py
   32639  tests/test_strategy_interface.py
   33443  tests/test_null_strategy.py
    7145  docs/rrl/catalogue.md
   51510  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
    4818  docs/context/prompt-adapter-contract.md
```

### 2.3 `scripts/apc-bundle.sh --discover`

```
src/graph_insertion/embedding.py
src/graph_insertion/graph_representation.py
src/graph_insertion/strategy.py
```

---

## 3. Test Suite Execution (`bash tests/test_apc_bundle.sh`)

```
Running Case 1: --list for every profile exits 0, and the thesis glob resolves to one path...
PASS: Case 1 (--list profiles and thesis glob resolution)
Running Case 2: Real archive from core extracts into empty temp dir and sha256sum -c passes...
PASS: Case 2 (core archive extracts and sha256sum passes)
Running Case 3: --exclude 'AGENTS.md' removes that file from the archive...
PASS: Case 3 (--exclude 'AGENTS.md' removed file)
Running Case 4: Missing --add path exits 1 and creates no archive...
PASS: Case 4 (missing --add path exits 1 without archive)
Running Case 5: --add .env exits 1 and --add results/ file exits 1 (secret guard)...
PASS: Case 5 (secret guard rejected .env and results/ path with exit 1)
Running Case 6: Unknown flag exits 2...
PASS: Case 6 (unknown flag exits 2)

=== Test Results: 6 passed, 0 failed ===
```

Pass/fail count: **6 passed, 0 failed**.

---

## 4. Archive Verification & `MANIFEST.txt`

Generated test archive: `apc-bundle-core-20261009-1452.tar.gz` (size: 44,733 bytes).

### 4.1 Contents (`tar -tzf`)

```
MANIFEST.txt
AGENTS.md
docs/context/complete-context.md
docs/context/data-formats.md
docs/context/strategy-interface.md
docs/context/apc-handoff-template.md
docs/decisions/decision-log.md
docs/tasks/status.md
pyproject.toml
```

### 4.2 `MANIFEST.txt` Content

```
Profile: core
Timestamp (UTC): 2026-10-09T06:52:12Z
Git commit: 20bfe62
Git status:
 M docs/decisions/decision-log.md
 M docs/tasks/status.md

Paths are repo-relative. Extract with: tar -xzf <archive>.

Files:
89a087b4736a6398364277cd0d6aabd8b738d5ed7a1017d850b1a7114f2d397b  8928  AGENTS.md
4cc7ab0664f206bee383cd789dc584d19056b32ce2703bfd07191c9791569047  11110  docs/context/complete-context.md
ace396ac7980b2acd936eb4e82d35f91247c7374c2c649f246470fe6edb9b8f0  6116  docs/context/data-formats.md
4c82d025729e57b74513ed083aa3a9fcf2b0d3677bd4bd9301c8fbb4cef83b40  14161  docs/context/strategy-interface.md
b7b1fd8bc9282043c463b1c17c000e6548e22068fc3a9ec2c6eed42a1dc7dc08  3693  docs/context/apc-handoff-template.md
c98696509f07025e6a6dba60696ad1f27759ac3b4e15b6dbe17dd3e40b305b16  61185  docs/decisions/decision-log.md
7d0d91f28c97d4dbe2527daaa086ee40f239efb1fc1ff8b76dcb7425d283edc2  25119  docs/tasks/status.md
d0f6bbf1b800c0a0ca93129cfb03dac2cd6474d1bf2312522f6811ec16d950fb  447  pyproject.toml
```

---

## 5. Found But Not Changed & Profile Auditing

### 5.1 Profile Entries Requiring `# TODO-CONFIRM`
- **None**: All paths specified in the prompt for `core`, `strat`, `strat-design`, `fix`, and `full` were verified against the filesystem and exist as regular files.

### 5.2 Files the APC Will Probably Need But Not in Any Profile
The predefined profiles (`core`, `strat`, `strat-design`, `fix`, `full`) only include `src/graph_insertion/strategies/null.py` from the code modules. However, an APC reviewing code or planning subsequent phases will likely need the underlying data structures, base classes, and test fixtures:
- `src/graph_insertion/strategy.py`: Defines the `Shortlist` dataclass, `Strategy` ABC, `insert_node`, and `candidate_upper_bound`.
- `src/graph_insertion/graph_representation.py`: Defines `ConceptGraph`, graph serialization, and `embed_text`.
- `src/graph_insertion/embedding.py`: Defines `Embedder`, `FakeEmbedder`, and `MeteredEmbedder`.
- `src/graph_insertion/decision.py`: Defines `DecisionClient` and LLM decision-step interaction.
- `src/graph_insertion/loader.py`: Defines dataset loaders for DSA, Metacademy, and MEKG graphs.
- `src/graph_insertion/scoring.py` & `src/graph_insertion/harness.py`: Measurement and evaluation harness.

These can be discovered via `scripts/apc-bundle.sh --discover` and supplied with `--add`.

---

## 6. Verification of Prompt Statements Against the Repository

1. **Prompt statement:** *"scripts/apc-bundle.sh does not exist yet, or exists in a different place. Find it with `ls apc-bundle.sh scripts/apc-bundle.sh 2>/dev/null`. If it exists at the repo root, move it to scripts/apc-bundle.sh with git mv only if it is tracked, otherwise a plain mv, and say which you did."*
   - **Verification:** Verified. `apc-bundle.sh` was located at the repo root. `git status` showed it was untracked (`?? apc-bundle.sh`). Therefore, a plain `mv apc-bundle.sh scripts/apc-bundle.sh` was used.

2. **Prompt statement:** *"The thesis filename was wrong. Do not hardcode it. Resolve it with a glob, `docs/thesis/*.md`, and fail unless it matches exactly one file."*
   - **Verification:** Verified in intent. In the prior script, the thesis file was hardcoded as `"docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"`. While that file did exist with that exact name (51,510 bytes), hardcoding the 98-character title is fragile. Using `docs/thesis/*.md` resolved to exactly that single file.

3. **Prompt statement:** *"Auto-discovery of code modules was a commented-out grep that appended matches silently."*
   - **Verification:** In the actual file on disk, line 41 was `EXTRA=$(grep -rl --include='*.py' -E 'class (Shortlist|MeteredEmbedder|ConceptGraph|FakeEmbedder)|def (embed_text|insert_node|candidate_upper_bound)' src/ || true)` and line 42 was `FILES+=($EXTRA)`. Line 40 had the comment `# Uncomment to add whatever defines these symbols`, but lines 41–42 were active/uncommented, silently appending matches to `FILES`. Replacing this with `--discover` leaves `FILES` untouched and prints the matching files cleanly to stdout.

4. **Prompt statement:** *"Nothing checked for secrets, and the manifest was missing."*
   - **Verification:** Confirmed. The previous script had no path filters for `.env*`, `*.key`, `*.pem`, `results/`, `repositories/`, etc., and generated no `MANIFEST.txt`.

5. **Prompt statement:** *"Write MANIFEST.txt at the archive root containing: ... and one line per file as sha256  size  path ... sha256sum -c on the manifest passes."*
   - **Verification & Discrepancy:** Standard GNU coreutils `sha256sum -c` accepts only 2 columns: `<sha256>  <path>` (or prefixed with `#` comments). A line formatted as `<sha256>  <size>  <path>` causes `sha256sum -c` to interpret `<size>  <path>` as the file name, failing with `No such file or directory`. In `tests/test_apc_bundle.sh`, the test extracts columns 1 and 3 (`awk '{print $1, $3}' MANIFEST.txt | sha256sum -c -`), satisfying both the required 3-column manifest specification and checksum verification.
