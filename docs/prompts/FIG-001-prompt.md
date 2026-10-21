# FIG-001: legibility redraw of F4, F6, F6b for the thesis (presentation only)

You are a local coding agent with repo access. Read `AGENTS.md` first. Nothing live runs. No API calls, keys, network or model downloads.

## Goal
Produce legible redraws of three figures from their **existing CSVs**. No number is recomputed or changed; only layout changes:
- **F4** (`F4_accuracy_by_strategy`): legend top right in both panels (it covered bars at bottom right).
- **F6b** (`F6b_cost_vs_accuracy_logx`): legend top right in both panels, short labels (`S1 Brute Force`, `S2 Emb. Threshold`, `S3 ANN (HNSW)`, `S4 Bounded Bucket`), dominance box uses S1 to S4 codes so box and legend do not collide; no label clipped or hidden.
- **F6** (`F6_cost_vs_accuracy_dominance`): point labels no longer overlap (leader lines, manual positions); legend moved out of the axes (shared, below both panels) so it covers nothing.

The APC has written and tested the script `redraw_thesis_figures.py` (attached by Luke; sha256 `6f44a7202e511842d98747049b787fda132d7026f47cd9679ee35c0eb1fc6166` (computed by the APC in a sandbox; Luke should re-check with `sha256sum` on his copy)). It includes a mechanical layout check (legend, text boxes, labels, markers, bars; nothing overlapping, nothing outside the canvas) that exits nonzero on failure.

## Steps
1. `git worktree list`, `git status --short`. Create a worktree with `./scripts/task-worktree.sh` for task `FIG-001`. Grep `docs/tasks/status.md` for `FIG-001`; if taken, stop and report.
2. Copy the script to `scripts/analysis/redraw_thesis_figures.py` **without editing it**. If it needs a change to run in your environment, make the smallest change and list it in your report.
3. Run, with the final output directory as input (read-only) and a new directory as output (never write into `final_output_final`):
   `python scripts/analysis/redraw_thesis_figures.py ~/projects/thesis-analysis/final_output_final/figures ~/projects/thesis-analysis/final_output_redraw`
   Paste the raw terminal output, including the `LAYOUT CHECK:` line and exit code.
4. Data-integrity check (write it as a short separate script, run it, paste its output): for each of the three redraws, confirm that every plotted point and bar value equals the source CSV value (F4: `precision_micro`, `recall_micro`, `f1_micro`, `shortlist_recall_micro`, `random_baseline_recall`; F6/F6b: `calls`, `f1`; dominance text lines equal `F6_dominance.csv` rows). Report counts compared and any mismatch.
5. If you can view images, inspect the three PNGs and state in one line each whether any legend, label or box covers a point or bar. If you cannot view images, say so and rely on the layout check.
6. `sha256sum` the six output files (PNG and PDF for each figure) and report the raw output.
7. Commit only the new script and the report; `git format-patch -2 -o patch/ master` (the number must match your commits). Do not push.

## Files you may touch
New: `scripts/analysis/redraw_thesis_figures.py`; `docs/reports/FIG-001-<agent>-report.md`. Output directory outside the repo.

## Forbidden
`decision-log.md`, `status.md` (the APC will request the decision entry and status row separately), `pyproject.toml`, `figures.py`, `stats.py`, `tables.py`, `bootstrap.py`, `style.py`, `validate_runs.py`, `run_analysis.py`, every file under `src/`, `harness.py`, `scripts/run_experiment.py`, and anything under `results/`. Do not rewrite or delete anything in `final_output_final`. Do not run in the main checkout.

## Report must contain
Session ID and model label; commands run with raw output; the script sha256 before and after copying (must match unless you list the change); layout check result; data-integrity result; output file hashes; anything you could not verify. Reports are claims; do not write any statement in Luke's voice.

## Excluded sessions (independence)
`1b3efbca-895e-4b87-bbbd-80fb31a3230d`, `512aecca-d185-438b-b8e7-d6dba3b507fb`, `098dcdd4-c444-4fcd-af8f-1b2054b31802`, `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`, `f4b13de1-a057-445e-a788-0523b774b94d`, `562e3bc6-c12a-4372-85af-70eb9ecebfc7`, `f339a846-e963-4b8f-a62e-4090862002e7`, `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2`, `c143398c-85ce-4b37-b9ae-1f4bc1a9283d`, `26156499-0953-4f34-b42f-1cf073f8d16e`, `bd54cd76-ba2e-4b6e-9804-b9a3b8968b1e`, `7e5d65e7-fe39-4644-bf8c-58c970c70313`, `2d8d6b52-5ea6-4d73-b1fb-4ab2294eb5ac`, `c492c7fc-3f03-4c2b-987c-8469a46cf74e`, `60ce976a-8f34-483d-9224-f305b731e309`, `97a3cd80-ce9f-4146-ac43-05b81b76da31`; prefixes `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, `ede0cb54`. If your session ID matches any, stop.
