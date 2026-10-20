# APC Bundle Quick Reference

For the APC AI: `scripts/apc-bundle.sh` packages repo files into one
self-describing `.tar.gz` for upload. The APC has no filesystem access, so
when a task needs current file contents, ask Luke to run the commands below
and upload the resulting archive.

## Command

Run from the repo root:

```
./scripts/apc-bundle.sh [PROFILE] [OPTIONS]
```

Default profile is `core`.

## Profiles

| Profile | Adds beyond `core` |
| :--- | :--- |
| `core` | `AGENTS.md`, `docs/context/{complete-context,data-formats,strategy-interface,apc-handoff-template}.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `pyproject.toml` |
| `strat` | `core` + `src/graph_insertion/strategies/null.py`, strategy/interface tests, `docs/rrl/catalogue.md` |
| `strat-design` | `strat` + thesis (`docs/thesis/*.md`) |
| `fix` | `core` + `docs/context/prompt-adapter-contract.md` |
| `full` | Union of all above |

Profiles are bash arrays inside the script and can be edited (comment/uncomment lines) before running.

## Options

- `--list` — print resolved files + byte sizes, no archive (use to preview)
- `--tokens` — print estimated token count of resolved files (~1 token per 4 chars), no archive
- `--add PATH` — include an ad hoc file (repeat per file)
- `--exclude GLOB` — drop a file by path or filename (repeatable)
- `--with-reports` — include active `OPTIONAL_REPORTS` entries
- `--discover` — print `src/` files defining core symbols, no archive
- `-h, --help`

Examples:

```
./scripts/apc-bundle.sh --list
./scripts/apc-bundle.sh fix --add scripts/generate_name_pool.py
./scripts/apc-bundle.sh core --exclude 'AGENTS.md'
```

## Output

Creates `apc-bundle-<profile>-<YYYYmmdd-HHMM>.tar.gz` in the repo root. Files
keep repo-relative paths. A root `MANIFEST.txt` records profile, UTC
timestamp, short git commit, `git status` for bundled files, and a
`<sha256>  <size>  <path>` table.

## Safety

The script aborts (exit 1) listing all offenders if any path is missing, not
a regular file, or matches secret guards: `.env*`, `*.key`, `*.pem`,
`*secret*`, `*token*`, `*credential*`, or lives under `results/`,
`repositories/`, `.git/`, `.venv/`, `node_modules/`. It warns if the thesis
exceeds 300 KB.

## Verify after upload

```
tar -xzf <archive>
awk '/^[0-9a-f]{64}/ {print $1 "  " $3}' MANIFEST.txt | sha256sum -c -
```
