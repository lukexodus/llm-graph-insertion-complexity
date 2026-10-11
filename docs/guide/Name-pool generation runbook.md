# Name-pool generation runbook (sequential, Profile 24)

Goal: produce `data/synthetic/cs_concept_names.json` (at least 2001 valid names, target 2600) through the claude-automator prompt-adapter, using the **accepted HEAD version** of `scripts/generate_name_pool.py`. Do not use the shard/merge code (DATA-006/FIX-013) for this run; it is under repair.

## 1. What to expect

| Item | Value |
|---|---|
| Calls per round | one per subfield (80 expected; the dry run prints the exact number) |
| Time per call | about 30-36 s, plus a 3 s pause |
| One round | roughly 50-60 minutes |
| Rounds needed | 1, maybe 2 (the run continues until 2600 valid names or `--max-calls`, default 400) |
| Browser | headed Chromium opens for every call; do not touch the windows |
| Interrupts | usage-limit stops (exit 3) are expected; the cache is written after every call, so a rerun resumes |

The dry run's "@ 20s/call" estimate is display-only and too low.

## 2. Pre-flight checklist (tick all before starting)

- [ ] Profile 24: account-level "Generate memory from chats" is off (confirmed by hand).
- [ ] Profile 24: no custom instructions (confirmed by hand).
- [ ] Smoke test at HEAD passed (done: `Sonnet 5.5 Low`, adapter `07fc977-dirty`).
- [ ] Nothing else is using Profile 24 (claude-accounts TUI, dashboard, another prompt-adapter run, your own browser window).
- [ ] The laptop will not suspend or lock for the next 1-2 hours.
- [ ] Run inside `tmux` (or `screen`) so closing the terminal does not kill the run.

## 3. Set up a clean worktree

Your main checkout has uncommitted DATA-006/FIX-013 changes, so generate from a clean detached worktree at HEAD.

```bash
cd ~/projects/llm-graph-insertion-complexity
git worktree add --detach ../llm-graph-insertion-complexity-gen HEAD
cd ../llm-graph-insertion-complexity-gen
git status --short        # must print nothing
```

The script puts its own `src/` first on `sys.path`, so it uses this worktree's code. Use the same Python environment you normally use for the repo.

## 4. Define the two variables (every terminal session)

```bash
export CLAUDE_AUTOMATOR_DIR=/home/lukexodus/projects/claude-automator
CMD='uv run --project /home/lukexodus/projects/claude-automator/apps/prompt-adapter prompt-adapter'
```

## 5. Dry run (no browser, no quota)

```bash
python scripts/generate_name_pool.py --backend command --command "$CMD" \
  --adapter-profile "Profile 24" --adapter-model sonnet --adapter-effort low \
  --run-id np1w-p24 --dry-run
```

Check that it shows: Command Backend, Adapter profile `Profile 24`, Adapter model `sonnet`, the memory-off reminder. Send me the output if anything looks different.

## 6. Live run

Use the **same** command with `--live --confirm` instead of `--dry-run`:

```bash
python scripts/generate_name_pool.py --backend command --command "$CMD" \
  --adapter-profile "Profile 24" --adapter-model sonnet --adapter-effort low \
  --run-id np1w-p24 --live --confirm
```

Rules:
- Always pass `--run-id np1w-p24`. Without it each rerun gets a timestamp ID and starts from an empty cache.
- Keep profile, model and effort identical on every rerun, so the pool records a single model label.
- Stopping with Ctrl+C is safe (the cache is appended after every call). Afterwards check for leftover browsers: `pgrep -a chromium`.

## 7. Exit codes and what to do

| Exit | Meaning | Action |
|---|---|---|
| 0 | Target reached; the pool was built | Go to section 8 |
| 3 | Usage limit (reset time is printed) | Wait for the reset, rerun the identical command |
| 4 | Login or challenge needed | Log in or clear the challenge on Profile 24 by hand, rerun |
| 5 | Model mismatch | Stop. Do not rerun blindly; run the smoke test and send me the output |
| 6 | Three consecutive failures (timeout, refusal, unparseable reply) | Read stderr, rerun once; if it repeats, stop and send me the log |
| 1 | Bad request or config error | Fix the command (missing `--adapter-profile`, `--command`) and rerun |

HEAD has no special code for a locked profile: if another process holds Profile 24, the failures count toward exit 6. Keep the profile free.

## 8. When it finishes

The run builds the pool by itself into `data/synthetic/cs_concept_names.json` (inside the worktree). Then:

```bash
python scripts/generate_name_pool.py --verify
```

Success prints `Pool verification PASSED: N valid names ...` with N at least 2001. Then inspect the pool:

```bash
python - <<'EOF'
import json, random
d = json.load(open("data/synthetic/cs_concept_names.json"))
m = d["meta"]
print(len(d["names"]), "names")
print(json.dumps({k: v for k, v in m.items() if k != "corpora_checked"}, indent=2))
print(random.sample(d["names"], 40))
EOF
```

Look for: one `observed_models` label (`Sonnet 5.5 Low`), one adapter version, sensible `drop_counts`, `n_valid` at least 2001, and names that look like CS concepts.

## 9. Send me before committing anything

1. The dry-run output.
2. The first few call lines and the last 30 lines of the live run (plus any warnings).
3. The verify output.
4. The printed meta block and the 40-name sample.

I will confirm before you commit the pool.

## 10. After I confirm: bring the results home

```bash
cd ~/projects/llm-graph-insertion-complexity
cp ../llm-graph-insertion-complexity-gen/data/synthetic/cs_concept_names.json data/synthetic/
cp -r ../llm-graph-insertion-complexity-gen/results/datagen/np1w-p24 results/datagen/
```

The cache directory is gitignored but it is the reproducibility artifact: back it up before removing the worktree. Commit the pool file on its own. Only after both copies are safe:

```bash
git worktree remove ../llm-graph-insertion-complexity-gen
```

Also delete the stray test directories in the main `results/datagen/` once `find results/datagen -type f` shows only `.lock` files.

## 11. Do not

- Run in the main checkout, or with the shard/merge flags.
- Use more than one profile, or change the model, effort or prompt mid-run.
- Edit the cache, the pool, or the names by hand.
- Run live calls from anywhere other than your own shell.