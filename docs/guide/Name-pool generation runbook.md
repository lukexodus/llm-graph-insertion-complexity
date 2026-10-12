# Name-pool generation runbook (sharded, supervised)

Reissued by APC-A on 2026-10-12. It replaces the sequential Profile 24 runbook. It describes the procedure that produced the committed pool
(`np1w`, [D-65]) and how to rerun or resume it. Evidence tags: [Confirmed] = observed in the committed run's logs or caches;
[Inference] = reasoned, not observed; [Unverified] = not checked.

Goal: `data/synthetic/cs_concept_names.json`, at least 2100 valid names (DATA-004), through the claude-automator prompt-adapter, using
`scripts/name_pool_supervisor.py`, which launches N shard processes of `scripts/generate_name_pool.py`, rotates a shard onto a spare profile when its
account hits a usage limit, and builds and verifies the merged pool at the end.

## 1. What the committed run looked like

| Item | Value |
|---|---|
| Date | 2026-10-12, 03:41:40Z to 04:05:00Z (11:41 AM to 12:05 PM PH) |
| Code | detached `-gen` worktree at 21d8e12; adapter (claude-automator) `ba3a8a2`, clean tree |
| Shards | 3: `np1w-s1of3` (Profile 24), `np1w-s2of3` (Profile 25), `np1w-s3of3` (Profile 28); spares Profile 29, 30 |
| Model settings | `--adapter-model sonnet-5 --adapter-effort low --adapter-thinking off`; observed label "Sonnet 5 Low" on 73 of 73 calls |
| Calls | 73 (24 + 25 + 24), zero restarts, all shards exit 0 |
| Time | 22.9 minutes wall; per call mean 46.4 s, min 22.5 s, max 238.6 s (3 shards running at once) |
| Result | 2254 valid names (target 2600, floor 2100); `sha256_names` ad26b510...3487 |

Plan for roughly 25 to 35 minutes for a clean run of this size, longer if a profile hits a usage limit. Each call opens a headed Chromium window; do not
touch the windows or the clipboard while it runs.

## 2. Pre-flight checklist

- [ ] Each profile you pass: account-level "Generate memory from chats" is off and there are no custom instructions (checked by hand; the tooling does not verify this).
- [ ] Single-profile smoke test passed on each profile at the current adapter version (section 3), returning the expected text, tier 2 and "Sonnet 5 Low".
- [ ] Automator tree is clean: `git -C ~/projects/claude-automator status --porcelain` prints nothing, so the recorded adapter version has no `-dirty`.
- [ ] Nothing else uses these profiles (claude-accounts TUI, another prompt-adapter run, your own browser window).
- [ ] `free -h` shows at least 6 GiB available (this is the APC's threshold, not a measured limit) and `df -h /tmp` shows free space; `/tmp` is tmpfs on this machine, so profile copies there use RAM [Inference].
- [ ] The laptop will not suspend or lock for the next hour; run inside `tmux`.

## 3. Smoke test (one profile, a few seconds of quota)

```bash
echo '{"prompt":"Reply with exactly: OK","profile":"Profile 24","model":"sonnet-5","effort":"low","thinking":false,"web_search":false,"memory":false,"headless":false,"timeout_s":120}' \
  | uv run --project /home/lukexodus/projects/claude-automator/apps/prompt-adapter prompt-adapter 2>/dev/null
```

Check in the JSON: `"text": "OK"`, `"tier": 2`, `"model_observed": "Sonnet 5 Low"`, `"thinking_requested": false`, `adapter.version` without `-dirty`.
Do not redirect the output into a file inside the repo (the stderr log contains chat URLs). Earlier smoke runs showed a profile returning another prompt's text at tier 1;
the adapter then still reported `ok: true`, so always check the text, not only `ok`.

## 4. Worktree and corpora

Generate from a clean detached worktree at the commit you reviewed. If the worktree already exists, move it:

```bash
cd ~/projects/llm-graph-insertion-complexity
git log --oneline -1 master
git diff --stat 7b36f95 master -- scripts/generate_name_pool.py scripts/name_pool_supervisor.py tests/stub_prompt_adapter.py   # expect no output unless those files changed on purpose
cd ../llm-graph-insertion-complexity-gen
git status --short            # must print nothing
git checkout --detach master
git log --oneline -1
```

If it does not exist: `git worktree add --detach ../llm-graph-insertion-complexity-gen master` from the main checkout.

The corpora under `repositories/` are not in git. The worktree needs them for the zero-overlap check, so link them and confirm all 12 are found:

```bash
cd ~/projects/llm-graph-insertion-complexity-gen
ln -s ~/projects/llm-graph-insertion-complexity/repositories repositories
ls repositories/dataset/EKG-Dataset | head -3
PYTHONPATH=src python - <<'EOF'
import graph_insertion
from graph_insertion.loader import discover_corpora
print(graph_insertion.__file__)   # must be under the -gen worktree
print(len(discover_corpora()))    # must print 12
EOF
```

`PYTHONPATH=src` is only needed for ad hoc imports like this one; the scripts put the worktree's `src/` on `sys.path` themselves.
Do not start a live run unless this prints 12.

## 5. Dry run, then live run

From the worktree root (the supervisor writes `results/datagen/...` relative to the current directory):

```bash
cd ~/projects/llm-graph-insertion-complexity-gen
CMD='uv run --project /home/lukexodus/projects/claude-automator/apps/prompt-adapter prompt-adapter'
python scripts/name_pool_supervisor.py --shards 3 \
  --profiles "Profile 24,Profile 25,Profile 28,Profile 29,Profile 30" \
  --run-id-prefix np1w --command "$CMD" \
  --adapter-model sonnet-5 --adapter-effort low --adapter-thinking off --dry-run
ls results/datagen
```

Check the plan: three shard commands with run IDs `np1w-s1of3` to `np1w-s3of3`, `--shard i/3`, `--adapter-model sonnet-5`, `--adapter-thinking off`; the first three
profiles are the shards and the rest are spares. `results/datagen` must contain no `np1w-s*` directory (an old `np1w-p24` directory from the sequential attempt is harmless).

The flags matter: `--adapter-thinking` defaults to `auto` and `--adapter-model` to `sonnet`, so pass both explicitly. Do not use the generator's own
`--shards` flags with `--dry-run` for planning; they are ignored unless `--print-shard-commands` is given.

Live run, same command with `--live --confirm` in place of `--dry-run`, in terminal 1:

```bash
python scripts/name_pool_supervisor.py --shards 3 \
  --profiles "Profile 24,Profile 25,Profile 28,Profile 29,Profile 30" \
  --run-id-prefix np1w --command "$CMD" \
  --adapter-model sonnet-5 --adapter-effort low --adapter-thinking off \
  --live --confirm
```

Ctrl+C stops all shards (supervisor exit 130) and keeps the caches. Afterwards check for leftover browsers: `pgrep -a chromium`.

## 6. Checks during the run (terminal 2)

Within the first minute, confirm the live shard commands carry the three flags (the supervisor's tests did not cover this until FIX-017); expect 9 lines:

```bash
cd ~/projects/llm-graph-insertion-complexity-gen
grep shard_launch results/datagen/np1w-supervisor/supervisor-log.jsonl | grep -o -e '--adapter-model [a-z0-9-]*' -e '--adapter-effort [a-z]*' -e '--adapter-thinking [a-z]*'
```

After each shard's first call (about two minutes, shards start 20 s apart), check the first record: right subfield, right profile, `thinking_requested` false, `model_requested` sonnet-5, clean adapter version.

```bash
for s in 1 2 3; do echo "== shard $s"; head -n 1 results/datagen/np1w-s${s}of3/raw_responses.jsonl | cut -c1-1500; done
python scripts/name_pool_supervisor.py --status --run-id-prefix np1w
free -h; df -h /tmp
```

## 7. Exit codes and what to do

Generator (one shard process):

| Exit | Meaning | What the supervisor does |
|---|---|---|
| 0 | shard reached its own target | marks it done |
| 3 | usage limit | restarts the shard on the next free profile |
| 7 | profile in use (adapter exit 15) | restarts on the next free profile after 60 s |
| 4, 5, 6, 1 | login or challenge needed, model mismatch, three consecutive failures, bad config | fatal: terminates all shards |

Exit 6 stays fatal on purpose (decision of 2026-10-11): rotating on repeated failures could hide a systematic prompt problem.

Supervisor: 0 done and verified; 1 fatal; 2 refused (no `--live --confirm`); 3 stalled (all profiles cooling past `--max-wait-s`, default 21600 s); 4 `--max-total-calls`
exceeded (default 600); 130 interrupted. The supervisor's exit 3 is not the generator's exit 3.

Reruns and resumes:
- The generator resumes each shard from its own cache (D-39(3)). Rerun the identical command (same `--run-id-prefix`, model, effort and thinking flags) so the pool records one configuration;
  mixed thinking settings across shards are refused at merge time.
- The cooldown table is in memory only. After a supervisor restart, rate-limited profiles are forgotten. Drop profiles that are still cooling from `--profiles`; `--status` shows them.
  The 18000 s default cooldown is an unverified operator assumption; the committed run never hit a rate limit, so it was not exercised.
- The adapter does not mark cooldowns and its exit-10 payload names no profile (RECON-parallel-2, agent-reported), so the supervisor's table is the only guard.
- Failover is a rotation of one run across accounts. It is opt-in behind `--live --confirm`.

## 8. When it finishes

The supervisor merges and verifies by itself and prints the pool path. To see the verification again:

```bash
python scripts/generate_name_pool.py --verify --merge-run-ids np1w-s1of3,np1w-s2of3,np1w-s3of3
```

Success prints `Pool verification PASSED: N valid names verified against 191 corpus concepts.` with N at least 2100. Then audit the caches (parse, count, prompt/subfield match, duplicates):

```bash
python3 - <<'EOF'
import json, itertools, collections
recs = []
for s in (1, 2, 3):
    for i, l in enumerate(open(f"results/datagen/np1w-s{s}of3/raw_responses.jsonl")):
        r = json.loads(l); recs.append((s, i + 1, r))
lens = collections.Counter(); sets = []
for s, i, r in recs:
    a = json.loads(r["response_text"])          # raises if a response is not JSON
    lens[len(a)] += 1; sets.append((r["subfield"], set(a)))
    assert f"subfield '{r['subfield'].replace('_', ' ')}'" in r["request_user"], (s, i)
    bm = r["backend_meta"]
    assert bm["thinking_requested"] is False and bm["tier"] == 2, (s, i)
print(len(recs), "records; array lengths", dict(lens))
print("max pairwise Jaccard", max(len(x & y) / len(x | y) for (_, x), (_, y) in itertools.combinations(sets, 2)))
EOF
sha256sum results/datagen/np1w-s*/raw_responses.jsonl    # compare with meta.sha256_raw_responses
```

Inspect the meta block (`observed_models` one label, `adapter_versions` one clean hash, `requested_thinking` false, `run_ids`, `drop_counts`, `n_valid`) and a 40-name sample
before committing. Send the outputs to the APC before committing the pool.

## 9. After the APC confirms: bring the results home

```bash
cd ~/projects/llm-graph-insertion-complexity
mkdir -p data/synthetic results/datagen
G=../llm-graph-insertion-complexity-gen
cp $G/data/synthetic/cs_concept_names.json data/synthetic/
cp -r $G/results/datagen/np1w-s1of3 $G/results/datagen/np1w-s2of3 $G/results/datagen/np1w-s3of3 $G/results/datagen/np1w-supervisor results/datagen/
sha256sum results/datagen/np1w-s*/raw_responses.jsonl
git add data/synthetic/cs_concept_names.json
git commit -m "DATA-004: add generated name pool" -- data/synthetic/cs_concept_names.json
```

`results/datagen/` is git-ignored but it is the reproducibility artifact: back the caches, `status.json` and `supervisor-log.jsonl` up outside the repo. The shard logs
(`shard-*.log`) can contain chat URLs; do not upload or commit them. Only after both copies are safe: `git worktree remove ../llm-graph-insertion-complexity-gen`.

## 10. Known properties of the committed pool (to state in Chapter 3)

- Responses are extracted from the page DOM (tier 2) and post-processed by the adapter: HTML to markdown, plus normalization of curly quotes to ASCII. They are not verbatim clipboard text.
- `token_usage` in the caches is all zeros because the web UI does not report tokens. It is not evidence about reasoning tokens. The per-call observed thinking state was not recorded.
- The pool (2254 names) is below the 2600 target because each shard stops at ceil(2600/3) = 867 valid names counted over its own cache, before cross-shard deduplication
  (542 exact duplicates were dropped at merge).
- 73 of 80 subfields were queried (indices 72 and 74 to 79 were never reached), so later-listed subfields are under-represented [Inference].
- The prompt asks for 1 to 4 word names but the validator accepts 1 to 5 (`generate_name_pool.py` line 634); three pool names have five words.
- Merged pool meta written before FIX-017 lists only the first profile per shard; after a mid-shard failover use the per-record `profile_used` in the caches and `supervisor-log.jsonl`.

## 11. Do not

- Run in the main checkout while it has uncommitted work, or point two runs at the same profiles.
- Change the model, effort, thinking flag or prompt version between reruns of the same run-id prefix.
- Edit the caches, the pool or the names by hand.
- Run live generation from anywhere other than your own shell.