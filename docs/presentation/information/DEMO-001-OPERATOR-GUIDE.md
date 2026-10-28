# DEMO-001 — Operator Guide

How to run and operate the defense demo (`scripts/demo_trial.py`). The demo is
offline and deterministic: it replays real recorded PILOT-001 answers. No API
key, no network, and no model download are used at demo time.

For the implementation and verification record, see
[`docs/reports/DEMO-001-claude-code-defense-demo-trial.md`](../../reports/DEMO-001-claude-code-defense-demo-trial.md).
For a one-paragraph summary, see the "Defense Demo" section of
[`scripts/README.md`](../../../scripts/README.md).

---

## 1. Before the defense: one-time setup

Run from the repository root.

1. **Use the pinned environment.** The demo needs `sentence-transformers`
   6.1.0, `faiss-cpu` 1.15.1, and the cached `all-MiniLM-L6-v2` model at the
   pinned revision. On this machine that is `.venv-ann/`.
2. **Confirm the pilot cache is present:**
   `results/pilot/20261007_053743Z/raw_calls.jsonl` and `summary.json`.
3. **Confirm the dataset clone is present:**
   `repositories/dataset/EKG-Dataset/` (ignored by git, so it is not in a fresh
   worktree; the main checkout has it).
4. **Run the pre-flight check.** This loads the corpus, validates the cache and
   provenance, checks the node, and loads the embedder. It does not run a trial.

```bash
.venv-ann/bin/python scripts/demo_trial.py --check
```

Expected: five `OK` lines, exit 0. If the embedder line fails, fix the
environment before the defense; the demo never downloads the model.

5. **Rehearse once end-to-end.** Do this while online or offline; the demo sets
   `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.

```bash
.venv-ann/bin/python scripts/demo_trial.py --no-color | less
```

6. **Record the smoke evidence.** Optional but useful:

```bash
.venv-ann/bin/python scripts/demo_trial.py --check
.venv-ann/bin/python scripts/demo_trial.py --no-color --json /tmp/demo.json
```

`--json` refuses to overwrite an existing file and refuses any path under
`results/`.

---

## 2. The default run

```bash
.venv-ann/bin/python scripts/demo_trial.py
```

What it does: one leave-one-out insertion on the DSA corpus. The held-out
concept is `binary_search_tree` by default. The existing graph is 28 concepts
and 47 edges; the full gold graph is 29 concepts and 54 edges.

The transcript has three phases:

| Phase | What the panel sees |
|---|---|
| **BEFORE** | The research question, corpus, hidden gold neighbourhood, the shared decision prompt, the four strategies and the cost formula. |
| **WHILE** | Per strategy: setup time, shortlist size and narrowing, candidate ranking, sampled decision calls with exact prompts, recorded answers, calls, recorded model latency, tokens, cost, and graph update. |
| **AFTER** | Gold neighbourhood revealed, TP/FP/FN edges, missed-edge causes, precision/recall/F1, shortlist recall, cross-strategy tables, takeaways and limitations. |

Metric tags: `[LIVE]` measured now, `[PILOT]` recorded on 2026-10-07, `[CALC]`
derived from recorded values, `[GOLD]` ground truth shown only in AFTER.

Expected default result (P8, reproduced by the test suite):

| strategy | shortlist | calls | F1 | TP/FP/FN |
|---|---:|---:|---:|---:|
| S1 brute force | 28/28 | 28 | .667 | 4/1/3 |
| S2 embedding threshold (θ=.6) | 1/28 | 1 | .250 | 1/0/6 |
| S3 ANN retrieval (k=10) | 10/28 | 10 | .727 | 4/0/3 |
| S4 bounded bucket (5..10) | 9/28 | 9 | .250 | 1/0/6 |

Runtime: about 7–10 seconds including model load on this machine; process wall
about 8–11 seconds. Well under 30 seconds.

---

## 3. Flags you are likely to use

```bash
# One strategy or a subset, always printed in S1-S4 order
.venv-ann/bin/python scripts/demo_trial.py --strategies s1,s3

# A different held-out node (must exist in DSA)
.venv-ann/bin/python scripts/demo_trial.py --node graph

# Show every decision call (brute force has 28)
.venv-ann/bin/python scripts/demo_trial.py --show-all-calls

# Plain ASCII (useful if the projector/font lacks box-drawing glyphs)
.venv-ann/bin/python scripts/demo_trial.py --ascii

# Wait for Enter between BEFORE, WHILE and AFTER
.venv-ann/bin/python scripts/demo_trial.py --pause

# Disable colour explicitly, or set NO_COLOR
.venv-ann/bin/python scripts/demo_trial.py --no-color

# Use a different pilot directory (resolved against the repo root)
.venv-ann/bin/python scripts/demo_trial.py --pilot-dir results/pilot/20261007_053743Z

# Machine-readable report (must be outside results/ and must not already exist)
.venv-ann/bin/python scripts/demo_trial.py --json /tmp/demo.json

# Show a Python traceback on failure (debugging only)
.venv-ann/bin/python scripts/demo_trial.py --traceback
```

Colour appears only when stdout is a TTY and neither `--no-color` nor
`NO_COLOR` is set. Piped output is plain automatically.

### Suggested defense presentation

1. Run `--check` first, on screen, so the panel sees the provenance and cache
   fingerprint pass.
2. Run the default command with `--pause` if you want to talk between phases.
3. During WHILE, point at the shortlist size and call count; do not read every
   call. `--show-all-calls` is for Q&A, not the main run.
4. During AFTER, point at shortlist recall first, then F1. The story is
   two-stage: narrowing decides what the model is allowed to see; the shared
   decision step decides the edges.
5. Use `--strategies s1,s3` if time is short; it keeps the strongest contrast.

### Useful Q&A counter-nodes

The default node is favourable to narrowing (`binary_search_tree` ranks 5th of
29 by `F1(S3) - F1(S1)`). If a panelist asks for a counterexample:

```bash
# Brute force clearly beats S3: S1 F1 1.000 vs S3 F1 0.000
.venv-ann/bin/python scripts/demo_trial.py --node bellman_ford_algorithm --strategies s1,s3

# S2 returns an empty shortlist: no calls, no edges
.venv-ann/bin/python scripts/demo_trial.py --node graph --strategies s2
```

Both are genuine replay results from the same cache, not special cases.

---

## 4. What to say, and what not to say

Say:

- "The answers on screen are real recorded DeepSeek answers from PILOT-001 on
  2026-10-07, for exactly these prompts. The program looks them up instead of
  calling the API."
- "Narrowing, graph update, the decision step and scoring run live."
- "Latency, tokens and cost shown here are the recorded values, not
  measurements from this run."
- "This is one node, one trial. It illustrates the pipeline; the thesis
  evidence is the full runs."

Do not say:

- That the demo is making live API calls. It is not.
- That the shown latency is this machine's current latency. It is not.
- That the demo is a new empirical result or part of Chapter 4. It is not.
- That replay agreement proves the official runs agree. The official accuracy
  runs made their own live calls. Replay matches S2 and S3 exactly; S1 and S4
  each differ by one predicted edge from the 2026-10-18 accuracy records.

---

## 5. Exit codes and troubleshooting

| Exit | Meaning | What to do |
|---:|---|---|
| 0 | Success | Continue. |
| 2 | Usage error (bad/duplicate/unknown `--strategies`) | Use `s1`–`s4` or the canonical names. |
| 3 | Pilot cache/provenance failure | Restore the accepted PILOT-001 artifacts; do not edit the cache. The SHA-256 and prompt-version checks are fail-closed. |
| 4 | Corpus or node problem | Check `repositories/dataset/EKG-Dataset/`; use a node name from the DSA corpus. Close matches are printed. |
| 5 | Missing dependency or embedder | Use `.venv-ann`; the model must already be cached. The demo never downloads. |
| 6 | Internal consistency check failed | A production path, edge rebuild, label sum or subset invariant disagreed. Do not present the run; report it. |
| 7 | Refused `--json` path | Pick a new path outside `results/` whose parent exists. |

Common fixes:

- **`ModuleNotFoundError: sentence_transformers` or `faiss`** — run with
  `.venv-ann/bin/python`, not system Python.
- **Model load fails offline** — the cached MiniLM model is missing. Restore the
  cache; do not unset the offline variables to force a download during a
  defense.
- **Dataset not found** — the ignored `repositories/` clone is absent (common in
  a fresh worktree). Run from the main checkout or restore the clone.
- **`node ... is not in the DSA corpus`** — the hint lists close matches.
- **Output looks garbled on the projector** — add `--ascii`; if colour is
  distracting, add `--no-color`.
- **Output is too long for one screen** — use `--strategies s1,s3`, or page it:
  `... | less -R`.

---

## 6. What is verified, and what is not

Verified by the test suite and the DEMO-001 report:

- 812/812 prompts reproduce byte-exactly; cache SHA-256 is pinned.
- Default P8 table reproduced exactly.
- Offline run under `unshare -rn`; no API key read.
- Deterministic non-volatile JSON across two runs.
- No writes under `results/`; pilot artifact SHA unchanged.
- Formatter width <= 88 columns for every DSA node in both Unicode and ASCII.
- 51 new tests; full runnable suite 787 passed, 3 skipped.

Not verified or not claimed:

- The official accuracy-run decisions for S1/S4 are not identical to the pilot
  replay (one edge each). The demo is faithful to PILOT-001, not to the later
  live runs.
- The demo is not a re-run of the 24-run campaign, not a Chapter 4 result, and
  not evidence about amortised cost.
- It does not test a second corpus or a second held-out node simultaneously.

---

## 7. If the cache or prompt ever changes

The demo is deliberately fail-closed. If the PILOT-001 cache is re-recorded or
`decision.SYSTEM_PROMPT` changes, the run exits 3. Do not loosen the checks for
a defense. The correct path is:

1. Re-record and re-accept the pilot under a new task.
2. Update `PILOT_RAW_CALLS_SHA256` and `SYSTEM_PROMPT_SHA256` in
   `scripts/demo_trial.py`.
3. Update the regression values in `tests/test_demo_trial.py`.
4. Record a new decision entry; do not edit D-99 silently.

The current pins are:

- Cache SHA-256:
  `879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008`
- System prompt SHA-256:
  `32932d476b8cdac7026520cd9e1906a8cca9333d2945ad569fa8a7feb2b3d571`

---

## 8. Files involved

| File | Role |
|---|---|
| `scripts/demo_trial.py` | Demo implementation and CLI. |
| `tests/test_demo_trial.py` | 51 regression tests. |
| `docs/prompts/DEMO-001-PROMPT.md` | Original task prompt (archived). |
| `docs/reports/DEMO-001-claude-code-defense-demo-trial.md` | Full verification and evidence record. |
| `scripts/README.md` | One-paragraph command reference. |
| `docs/decisions/decision-log.md` | D-99: replay-only, fail-closed, tag semantics. |
| `docs/tasks/status.md` | DEMO-001 status row. |
| `results/pilot/20261007_053743Z/` | Recorded PILOT-001 cache and summary. |
