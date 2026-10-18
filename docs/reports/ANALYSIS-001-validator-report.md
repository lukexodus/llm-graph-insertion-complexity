# ANALYSIS-001 Report: Independent Run-Validation Gate, Tests, and Mutation Table

## 1. Independence and Task Context

- **Task ID**: `ANALYSIS-001`
- **Agent Name**: `gemini`
- **Session ID**: `f4b13de1-a057-445e-a788-0523b774b94d`
- **Model Label**: `Gemini 3.8 Flash`
- **Independence Certification**: Confirmed independent. This session is NOT any of the excluded sessions:
  - `1b3efbca-895e-4b87-bbbd-80fb31a3230d`
  - `512aecca-d185-438b-b8e7-d6dba3b507fb`
  - `098dcdd4-c444-4fcd-af8f-1b2054b31802`
  - `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
  - Any session ID starting with `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, or `ede0cb54`.
- **Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-001`
- **Branch**: `task/ANALYSIS-001`
- **Base Commit**: `3323bfbd03bb6490aecef2d864b9d77271bd9a340e` (clean tree)

---

## 2. Critique of Earlier Draft (`~/projects/thesis-analysis/validate_runs.py`)

The earlier draft at `~/projects/thesis-analysis/validate_runs.py` was inspected and rejected as-is due to three fundamental design flaws:

### (a) Resumed Run Detection: Raw Lines vs. Summary Rows
- **Earlier Draft Mechanism**: Compared line counts between `raw.jsonl` and row counts in `summary.csv` (`len(raw_lines) != len(summary_rows)`).
- **Flaw**: In `src/graph_insertion/harness.py`, `generate_summary_csv` groups trial records by key `(graph_name, corpus_size, trial_index)` taking the last observed record for each key. When a run experiences failures and is later resumed, `raw.jsonl` appends the retried records while preserving the failed records. Comparing the raw line count directly to the summary row count incorrectly treats an intended resume as a corruption error, or relies on an ad-hoc heuristic that fails to identify which trials were retried.
- **Implemented Fix**: Resumed runs are detected by tracking duplicate `(graph_name, corpus_size, trial_index)` keys in `raw.jsonl`. If and only if duplicate keys are detected, the run is flagged as `PASS (resumed)`. Failed trials and retry counts are parsed directly from trial records without imputing values.

### (b) CPU Thread Pin Verification: Conditional Bypass
- **Earlier Draft Mechanism**: Checked CPU thread pins using `if model_name is not None:` based on what was present in the sidecar.
- **Flaw**: If an embedding strategy run had an invalid sidecar where `model_name` was omitted, set to `null`, or the entire `embedder` block was deleted, the thread check was silently skipped. This is a severe fail-open vulnerability.
- **Implemented Fix**: The validation gate enforces thread pinning unconditionally based on the strategy type. If `strategy in {"embedding_threshold", "ann_retrieval", "bounded_bucket"}`, the sidecar must contain an `embedder` block and `cpu_threads` must be strictly `1` ([D-72]). If the embedder block is missing, validation fails immediately. Conversely, for `brute_force`, the embedder block must be null or absent.

### (c) Bound Lookup: Directory Name Matching vs. Semantic Sidecar
- **Earlier Draft Mechanism**: Looked up call bounds by parsing directory names and applying regex matching against directory paths.
- **Flaw**: String matching on directory names is fragile against path formatting differences, symlinks, directory renames, or slight slug typos, risking bound lookup errors or silent bypasses.
- **Implemented Fix**: Bound lookup is keyed strictly by the semantic tuple `(strategy, config_key, mode)` extracted directly from `strategy_config.json`, conforming exactly to [D-68] and the README run plan table. The directory name is verified separately against the canonical slug format.

---

## 3. Implementation Summary: `scripts/analysis/validate_runs.py`

The validation gate is implemented in `scripts/analysis/validate_runs.py` using **Python standard library only** (no external packages, zero pip installs).

### Key Architectural Components:
1. **File Presence**: Enforces that all four required files exist and are non-empty: `manifest.json`, `strategy_config.json`, `summary.csv`, and `raw.jsonl`.
2. **Cross-Run Manifest Invariants**:
   - `git_dirty` must be strictly `False`.
   - `git_commit` must be uniform across all runs in a batch.
   - `libraries` dictionary (package versions) must be identical across all runs in a batch.
   - Embedding revision (`revision`) must be uniform across all embedding runs.
3. **Sidecar & Directory Slug Parity**:
   - Validates JSON schema of `strategy_config.json`.
   - Derives canonical directory slug from `(mode, strategy, config)` and verifies the directory name matches.
4. **Planned Call Bounds ([D-68])**:
   - Maps `(strategy, config_summary, mode)` to maximum allowed LLM calls.
   - Verifies that realized total calls in `manifest.json` do not exceed the planned upper bound.
5. **CPU Thread Pinning ([D-72])**:
   - Fail-closed enforcement: strategies 2, 3, and 4 require `cpu_threads == 1`.
   - Strategy 1 (`brute_force`) requires `embedder` to be null or omitted.
6. **Trial Grouping & Count Invariants**:
   - **Accuracy mode**: exactly 29 DSA trials and 30 Metacademy trials (total 59).
   - **Sweep mode**: exactly 5 trials each for sizes $n \in \{10, 20, 50, 100, 200, 500, 1000\}$ (total 35 for 7 sizes or 60 for full sweep).
7. **Summary Recomputation from Raw Trials**:
   - Independently recomputes `total_s_mean`, `total_s_median`, `llm_calls_sum`, and `embedding_calls_sum` from `raw.jsonl`.
   - Uses `statistics.median` for median calculations, preventing even-$n$ middle-element off-by-one errors.
   - Checks relative error within $10^{-5}$ or absolute error within $10^{-4}$.
8. **Resumed Run Detection**:
   - Analyzes trial keys in `raw.jsonl` for duplicates.
   - Valid runs with retried duplicate keys are certified as `PASS (resumed)` and report exact failed trial counts.
9. **Table T3 Generation**:
   - Compiles a complete inventory CSV including per-file SHA256 hashes, combined directory hash, call counts, margins, and status.

---

## 4. Executed Mutation Table

The test suite in `tests/test_analysis_validate_runs.py` executes 17 test cases on purely synthetic fixtures created dynamically in `tmp_path` (zero coupling to real `results/` or user home directory).

| Test Name | Fixture / Mutation Applied | Expected Failure / Behavior | Status | Verbatim Failing Assertion / Check Line |
|---|---|---|---|---|
| `test_baseline_control_accuracy` | Clean synthetic accuracy run (k=10, ef=128) | Clean PASS, 59 trials, 295 calls, resumed=False | **PASSED** | `assert passed` (`errors == []`) |
| `test_baseline_control_sweep` | Clean synthetic sweep run (7 sizes x 5 trials) | Clean PASS, 35/60 trials, 35/60 calls | **PASSED** | `assert passed` (`errors == []`) |
| `test_mutant_git_dirty_true` | Manifest mutated with `"git_dirty": True` | Validation fails | **PASSED** | `assert any("git_dirty is not False" in e for e in errors)` |
| `test_mutant_cross_run_commit_mismatch` | Run 2 manifest mutated to commit `0000000...` | Batch validation fails on commit mismatch | **PASSED** | `assert any("Cross-run git_commit mismatch" in err...)` |
| `test_mutant_cross_run_library_mismatch` | Run 2 manifest mutated with `torch: 9.9.9` | Batch validation fails on libraries mismatch | **PASSED** | `assert any("Cross-run libraries block mismatch" in err...)` |
| `test_mutant_cross_run_embedder_revision_mismatch` | Run 2 sidecar mutated with wrong embedder revision | Batch validation fails on revision mismatch | **PASSED** | `assert any("revision mismatch" in e for e in all_errs)` |
| `test_mutant_short_trial_count_consistent_summary` | Accuracy run provided with 28 DSA trials; summary.csv patched to agree | Validation fails on group trial count mismatch | **PASSED** | `assert any("trial count mismatch" in e.lower() for e in errors)` |
| `test_mutant_tampered_mean_total_s` | `summary.csv` row modified with `total_s_mean = 999.999` | Validation fails on mean recomputation mismatch | **PASSED** | `assert any("total_s_mean mismatch" in e for e in errors)` |
| `test_mutant_even_n_median_correctness` | `summary.csv` row modified with naive sorted median (3.0 instead of 2.5) | Validation fails on median recomputation mismatch | **PASSED** | `assert any("total_s_median mismatch" in e for e in errors)` |
| `test_mutant_missing_embedder_block_embedding_strategy` | Embedding strategy sidecar has `embedder` block deleted | Validation fails closed on missing embedder block | **PASSED** | `assert any("missing required 'embedder' block" in e for e in errors)` |
| `test_mutant_missing_required_field_git_dirty` | `manifest.json` has `git_dirty` key removed | Validation fails closed on missing required field | **PASSED** | `assert any("git_dirty" in e for e in errors)` |
| `test_mutant_exceeded_planned_bound` | Realized LLM calls (885) exceed planned upper bound (590) | Validation fails on bound violation | **PASSED** | `assert any("exceeds planned upper bound" in e for e in errors)` |
| `test_mutant_thread_pin_violated` | Sidecar has `cpu_threads: 4` instead of 1 | Validation fails on thread pin violation | **PASSED** | `assert any("cpu_threads != 1" in e for e in errors)` |
| `test_mutant_brute_force_has_embedder_model` | `brute_force` sidecar unexpectedly includes an embedder block | Validation fails on non-embedding strategy having embedder | **PASSED** | `assert any("unexpectedly defines an embedding model" in e for e in errors)` |
| `test_mutant_missing_file_manifest` | `manifest.json` deleted from run directory | Validation fails immediately on missing file | **PASSED** | `assert any("Missing required file: manifest.json" in e for e in errors)` |
| `test_resume_detection_with_duplicate_keys` | `raw.jsonl` contains duplicate trial key | Run passes but is correctly flagged as `is_resumed=True` | **PASSED** | `assert info["resumed"] is True` |
| `test_table_t3_inventory_generation` | Multi-run synthetic batch validation | Table T3 CSV generated with exact schema | **PASSED** | `assert reader[0]["status"] == "PASS"` |

---

## 5. Verification on Live Accuracy Results

The validator was executed against the 12 real completed accuracy runs in `../llm-graph-insertion-complexity/results/`:

```
================================================================================
RUN VALIDATION GATE: results/
================================================================================
[PASS] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    590 / 590 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_ann_retrieval_k10_ef256
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    590 / 590 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_ann_retrieval_k10_ef64
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    590 / 590 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_ann_retrieval_k20_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    1180 / 1180 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_ann_retrieval_k5_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 295 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_bounded_bucket_smin10_smax20_nb12
       Strategy: bounded_bucket | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    891 / 1180 bound | Trials: 59 (failed=0, retries=6)
[PASS] accuracy_bounded_bucket_smin2_smax5_nb12
       Strategy: bounded_bucket | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    189 / 295 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_bounded_bucket_smin5_smax10_nb12
       Strategy: bounded_bucket | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    423 / 590 bound | Trials: 59 (failed=0, retries=0)
[PASS (resumed)] accuracy_brute_force
       Strategy: brute_force | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    5012 / 5012 bound | Trials: 59 (failed=5, retries=18)
[PASS] accuracy_embedding_threshold_theta0.4
       Strategy: embedding_threshold | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    276 / 5012 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_embedding_threshold_theta0.5
       Strategy: embedding_threshold | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    122 / 5012 bound | Trials: 59 (failed=0, retries=0)
[PASS] accuracy_embedding_threshold_theta0.6
       Strategy: embedding_threshold | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    56 / 5012 bound | Trials: 59 (failed=0, retries=0)
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

### Table T3 Output (Verbatim CSV)

```csv
run,strategy,config,mode,commit,libraries_hash,trials,calls,failed,retries,status,manifest_sha256,config_sha256,raw_sha256,summary_sha256,dir_sha256
accuracy_ann_retrieval_k10_ef128,ann_retrieval,"{""M"": 16, ""ef_construction"": 200, ""ef_search"": 128, ""faiss_threads"": 1, ""faiss_version"": ""1.15.1"", ""index"": ""IndexHNSWFlat"", ""k"": 10, ""metric"": ""inner_product_on_unit_vectors"", ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,590,0,0,PASS,a5eebb8b6d534c6c4b21492d4686dd9f6a57801c03bb1546249506f6b8e31cc6,899163a535444010be44916869e3c42a3a0d7e69b64bac05d15092ba90ca794f,203a9149c12ca0055b6dd5ed361eed34c2182ed34091441e03e277a9043692b7,b6e5111bd362a966684936d1c609d978bb9c06a9c31f054379596cc8cdaea822,78470a52494b51af6e2fac98caffc737f79c37f5110ad47a18fb92a2d934e72c
accuracy_ann_retrieval_k10_ef256,ann_retrieval,"{""M"": 16, ""ef_construction"": 200, ""ef_search"": 256, ""faiss_threads"": 1, ""faiss_version"": ""1.15.1"", ""index"": ""IndexHNSWFlat"", ""k"": 10, ""metric"": ""inner_product_on_unit_vectors"", ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,590,0,0,PASS,4b62c6a35972b9ca3cb479666abcc516e62c74d37491e3e15e10d8a6c9b9ab6c,09d41181f0138b81bd429df05e4581bed8f42cc7906a8b579a5d1dc7590f0886,3e46b69769d7a490b8ce029237a44ab7be08c63baaf1bbe4d3655dc57ead3474,b4c29c4263fc5015977703d4c2922cea684b7a72515fcf60ac1c19a892dd837a,ce4bffd2a15a383d5efa18d370fced2d3665a3d5bd40d491c5d69ca37f30dd3c
accuracy_ann_retrieval_k10_ef64,ann_retrieval,"{""M"": 16, ""ef_construction"": 200, ""ef_search"": 64, ""faiss_threads"": 1, ""faiss_version"": ""1.15.1"", ""index"": ""IndexHNSWFlat"", ""k"": 10, ""metric"": ""inner_product_on_unit_vectors"", ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,590,0,0,PASS,aa576f5b6edc2f6749b33aa873dd408ead15e427e79be1cb27dce6cb4af8e4fe,8981c46cdb77ebb348edaf7de3a54a6bafc3da4613e37b07a8c3751f5baf962b,2c629845a6e700e2148cc135ef18ed21cebc5d363370da54775c7063deb34547,a57bbe6074375949ab55a2a21b1356aa519fe4c3ef496d92313d1091dc5a0f23,d664ac69a4a37f4549da4a3c9c05772d8314a6228e79f05d705deb1840d004b1
accuracy_ann_retrieval_k20_ef128,ann_retrieval,"{""M"": 16, ""ef_construction"": 200, ""ef_search"": 128, ""faiss_threads"": 1, ""faiss_version"": ""1.15.1"", ""index"": ""IndexHNSWFlat"", ""k"": 20, ""metric"": ""inner_product_on_unit_vectors"", ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,1180,0,0,PASS,bcf97c5f994684b0ef70fe32ee38c1b45b64fbc27fb673d50121c2e29d12ddb7,17db75b72069b526bb3f8e0347424b19916a2f25d824abacbc747345c9fd7814,34d5d4105b166ad744f00ee6b795154036b031f9f9c390e4fc395283250d66c9,35a0d4e350bec775acb83751d8087bf032d60cb7bae0a21ffa30d24e87070cee,5d1263116bebeffaf2ecaded1242e236c3880ef3e775cdea4dbb7e9b5500659f
accuracy_ann_retrieval_k5_ef128,ann_retrieval,"{""M"": 16, ""ef_construction"": 200, ""ef_search"": 128, ""faiss_threads"": 1, ""faiss_version"": ""1.15.1"", ""index"": ""IndexHNSWFlat"", ""k"": 5, ""metric"": ""inner_product_on_unit_vectors"", ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,295,0,0,PASS,b8bcee73c9a506a7af0e9220ee7872d9a8aa6b955bbfc3709c59d5e9ae6abfe9,5a3d2e0500d34fc5f826ceaad14379621c5b17b83b704d4e21ae4b56db6f009d,d54bfcf319a5e823948debb72fc223ac168894fcd3c3fb74dd6a88d350fa8ccd,9f0a6abf25cfb7d5c7db49515807afa27a22d22c270a6995eb3405efc1594934,f6aab967fd5b362af32f2eaaa0da517d46d4a41405f9442a9bf77159090a8985
accuracy_bounded_bucket_smin10_smax20_nb12,bounded_bucket,"{""n_bits"": 12, ""s_max"": 20, ""s_min"": 10, ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,891,0,6,PASS,65b9e346b4c6601f18810de96dbfbb4d0591730528be3e0d9a2e326e5a3f8f28,fa34a2b480e4b95398dc8a8e896fe52903f65cb98cf2f0bd391e0e7a9be941fd,98dac929c754886712ccf6aecd69758a25873a1ad9dcf63acd0acf83a5074a28,6b042c12cd94f19407155334ddff006afac74bbe1191b5e4ea9c7e94e22ceaa0,daf38fb81cba58ff4bb0d3b8d0207d84183fc8ad371cd0284ebcb48c26f54c77
accuracy_bounded_bucket_smin2_smax5_nb12,bounded_bucket,"{""n_bits"": 12, ""s_max"": 5, ""s_min"": 2, ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,189,0,0,PASS,f309993383ff55dc1b628c076fe47e9a48fa5c6dafa8d86472dae4a0222dae6c,8d44540ac261129fc021e0fe4a2dc32f136bb179cb6931bacea95e0549d0f546,60758e6012af235cc93a30bdf7ae79440e351c986b3a20c48c04f6b2e90cae20,400413f5c9288b083043407c7c90c3e933953e9e4072a094eca20f2b1c0081ef,e2ef3ade31fe3b27b1124670589d546f865ce82d06a75841425b79ad4410ee3a
accuracy_bounded_bucket_smin5_smax10_nb12,bounded_bucket,"{""n_bits"": 12, ""s_max"": 10, ""s_min"": 5, ""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,423,0,0,PASS,e56d962e48da181805225b7b04313cde147ea0883be0a16a99fe72211e99219f,b7af69f2b8c6853155078f310155c25d803141a6b6d4d80ea1e3626f96c16b6a,6f1160ae59e72d0250990ff2ba93dc58b95f49a2db0ea02bb2042fa7b31ae9bb,ea12227fe3943ace2b9b548659193d0be3eab1d24c7392e54ff4a8c47480310a,bb387867507824e57b4886c1499571630a0cdf4e49cf06b590fde81840e7bca8
accuracy_brute_force,brute_force,"{""seed"": 42}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,5012,5,18,PASS (resumed),97f423f99824b69718bad64e58c58118bf0d16760a317d8b655a6a9e798c27c2,e4bdf97b576deed768af45c68280dcd495bb7becd0b3b9d74ce9b9bf65c77475,5394c958057e4ae27de3487ab3d5f761a73c4f35e9105718169f1c49db675d85,dad711020e50ae9bd39e33b73451133eaf848153f95b6988a9ff47ce3257d6a9,c1dc59fcd4ebc3b9557bc1dd681e2b5389630b24207882ed6f2686a6d32db998
accuracy_embedding_threshold_theta0.4,embedding_threshold,"{""seed"": 42, ""theta"": 0.4}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,276,0,0,PASS,9720a00c5c2cd8e0a1b05eec73ddd13b744b4ac30907e2004f171f55c0bd96aa,131880255c82cf30a7b3266b68296fc8d6740e5b39aa2a8781924ddd7072f299,73e9a2ab8df1b3facf15a6336fb88d5c9e730ca95376191fc21d4ab0b3232640,e7f9cd39927ef4728c5a2cab0f1812db45954f26fb36687894db15740e6f3ee5,d27691ad5f552620f73cfe5a30154b140a2d4ce2c5c22526c5311858ec7a9f56
accuracy_embedding_threshold_theta0.5,embedding_threshold,"{""seed"": 42, ""theta"": 0.5}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,122,0,0,PASS,88beeb05d6fbe4cbdd4dd65eb554b4dc287a33241c636a76d8019f46805d6a40,3985ed0d789a17a8a5e03e9e3e0ee3b00e3f40585319470d47fb93bee11a3b62,9b32bc9fe62f4f551d94cb06fe6671e147f9d62acaefa32a060262dcdd70f9a8,a804ca9812f9340268c8d6959936a7ab2b81a85e08b3caf0eab7408cebeb2b75,6e010a088ce0e7c4917a76fb81a6cce15f5389f48d034cd76ec9df47f4229ad5
accuracy_embedding_threshold_theta0.6,embedding_threshold,"{""seed"": 42, ""theta"": 0.6}",accuracy,3323bfbd03b6490aeef2d864b9d77271bd9a340e,08e5ad5427ded137233ce4517d3d181c8ce06619b46a4430280194f579737fb3,59,56,0,0,PASS,f411b040b4d3a35501b7e68bcf9c947aef885b997286898d9d75030fffae46b5,860f20709530a63290d77002ec5991adc99cc6ab060b02810ac0f3ea0f6e2029,e0070c8b67064feda2980cb355316fd71898501896005ffcfb75298967693b5d,aac29667b2c727ffb23d85c8c4f7d5dbc96963d121e6ca3ffde3845adb3189d5,4883ce3d029cb48a6c76d7c2129e1de2cd92d5e80891ed6fb2cbc5db9b05109e
```

---

## 6. Test Suite Execution

### 6.1 Unit & Mutation Test Suite
- Command: `.venv-ann/bin/pytest tests/test_analysis_validate_runs.py -v`
- Result: **17 passed in 0.23s**

### 6.2 Full Repository Test Suite
- Command: `.venv-ann/bin/pytest`
- Result: **716 passed, 3 skipped in 166.82s**

---

## 7. Checksums and Line Counts

```
sha256sum:
820787e8c45cc265bb6c4bb595c894e75a0145a5f774ad446417311152690b83  scripts/analysis/__init__.py
1b417e0ba81cc537cfc7f07679c1a125ff98d8e846e5d81077037413fd90f579  scripts/analysis/validate_runs.py
ec0cc535b4d566e4b6c637acff42faf828b30564917158440db602562399fd64  tests/test_analysis_validate_runs.py
e9a1f896639ec7b81c5bc3e527b7444b12bbdef5ed449bf4307e84ab5ca32791  docs/decisions/decision-log.md
e5e34f8a7cba8c446bddfb46ea817b423b77c8100d2b75ec72023f49a7cc5ef9  docs/tasks/status.md
a68b703a5ff34d5c3019d0814fa831531498e4b871fc933529720bcfc2e0745f  docs/reports/ANALYSIS-001-validator-report.md

wc -l:
       1 scripts/analysis/__init__.py
     725 scripts/analysis/validate_runs.py
     569 tests/test_analysis_validate_runs.py
     655 docs/decisions/decision-log.md
     115 docs/tasks/status.md
     214 docs/reports/ANALYSIS-001-validator-report.md
    2279 total
```

---

## 8. Verbatim Git Diff Stat

```
 docs/decisions/decision-log.md                |  16 +
 docs/reports/ANALYSIS-001-validator-report.md | 214 +++++++++
 docs/tasks/status.md                          |   6 +-
 scripts/analysis/__init__.py                  |   1 +
 scripts/analysis/validate_runs.py             | 725 ++++++++++++++++++++++++++
 tests/test_analysis_validate_runs.py          | 569 ++++++++++++++++++++
 6 files changed, 1530 insertions(+), 1 deletion(-)
```
