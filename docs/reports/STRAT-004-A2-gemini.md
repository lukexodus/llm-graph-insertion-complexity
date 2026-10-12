# STRAT-004-A2: Close Three Test Gaps in Strategy 4 (`bounded_bucket`) & Relay Status

**Date:** 2026-10-12  
**Task ID:** `STRAT-004-A2`  
**Repo:** `llm-graph-insertion-complexity`  
**Base commit:** `21d8e12` (`STRAT-004-A: amend Strategy 4 decision record and tests after review (D-62)`)  
**Decision ID:** None (test-only task; `docs/decisions/decision-log.md` untouched)  

---

## 1. Identity & Independence Disclosure

- **Agent slug:** `gemini`
- **Model label:** Gemini 3.8 Flash
- **Session / Conversation ID:** `455d24de-0fbf-46a4-bbe1-9c839413cd7e`
- **Independence disclosure:**
  - This session is distinct from session `b8ab4203-d881-4c7d-8f76-db6a0b797a9c` (which executed the `STRAT-003` family: `STRAT-003`, `STRAT-003-R`, `STRAT-003-A`, `STRAT-003-B`).
  - This session is distinct from session `900404ed-8ba1-4026-9ef6-f04be8b69e63` (which executed `STRAT-004-R2`).
  - Disclosed per APC prompt instruction: Luke dispatched `STRAT-004-A2` into conversation `455d24de-0fbf-46a4-bbe1-9c839413cd7e` (the conversation that previously ran `STRAT-004-D`, `STRAT-004`, `STRAT-004-R`, and `STRAT-004-A`).

---

## 2. Baseline Capture (Pre-Edit)

### `git log --oneline -8`
```text
21d8e12 STRAT-004-A: amend Strategy 4 decision record and tests after review (D-62)
42890e9 FIX-016: make the dry-run planner use each strategy's own candidate bound
7b36f95 DATA-007: thesis-side supervisor for sharded name-pool generation (D-60)
7b52e0f STRAT-004: implement Strategy 4 bounded-bucket retrieval (D-59)
bd1e91f STRAT-003-B: close stale-cache hole in Strategy 2 and Strategy 3 shortlist() (D-58)
a532293 feat(scripts): auto-generate repo-tree.txt in apc-bundle and bundle docs
d9f7797 FIX-015: explicit adapter thinking control, results/datagen fixture repair (D-57)
6cd360a docs(guide): add sequential name-pool generation runbook
```

### `git status --short` (Pre-Edit)
```text
 M docs/context/repo-tree.txt
 M docs/tasks/status.md
?? docs/reports/STRAT-004-R-gemini.md
?? docs/reports/STRAT-004-R2-gemini.md
```

### SHA-256 and Line Counts (Pre-Edit)
- `53ed26166682f682b19c3624e97aed900474d480feeb0425c05f01e188844d40` (1689 lines) `tests/test_bounded_bucket_strategy.py`
- `c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af` (847 lines) `src/graph_insertion/strategies/bounded_bucket.py`

---

## 3. Prompt Corrections & Review of `STRAT-004-R2-gemini.md`

### Verification of Prompt Claims
1. **Base commit:** Accurate (`21d8e12`).
2. **Pre-edit test count:** Accurate (84 passed in `tests/test_bounded_bucket_strategy.py`, 583 passed / 3 skipped full suite).
3. **Pre-edit SHA-256 of test file:** Accurate (`53ed26166682f682b19c3624e97aed900474d480feeb0425c05f01e188844d40`).
4. **Mutants identified:** All three surviving mutants (`M-38`, `M-12` no-tie-break variant, `M-42`) were genuine and reproduced on the unedited tree in Step 1.

### Audit of `docs/reports/STRAT-004-R2-gemini.md`
`docs/reports/STRAT-004-R2-gemini.md` is present on disk (untracked). An audit against the real git history reveals:
- **Fabricated git log messages:** Lines 53–60 of `STRAT-004-R2-gemini.md` display commit subjects that do not match git history for `21d8e12`, `7b36f95`, `7b52e0f`, `bd1e91f`, and invent commit hashes and subjects for the older entries (`a532293 STRAT-003-A...`, `6aa3e84 STRAT-003...`, `1505cbe FIX-015...`). Real git log is shown in Section 2 above.
- **Fabricated `git show --stat 21d8e12`:** Lines 75–85 of `STRAT-004-R2-gemini.md` state `Author: Adrian Luke Labasan <lukexodus@gmail.com>` with 4 files changed including `patch/0001-...` and `356 insertions(+), 1 deletion(-)`. Real commit `21d8e12` has author `Luke <luke@localhost>`, 3 files changed, 284 insertions, and no patch commit.
- **Fabricated line numbers in Section 4:** R2 reported `setup()` at lines `235-350`, `shortlist()` at `360-460`, `on_inserted()` at `462-585`, and `diagnostics()` at `587-635`. In reality in `bounded_bucket.py`, `setup()` is at lines `368-530`, `shortlist()` is at `532-665`, `on_inserted()` is at `667-727`, and `diagnostics()` is at `768-847`.
- **Finding validity:** Despite those reporting discrepancies, R2's mutant identification (`M-38`, `M-12` no-tie-break, `M-42`) was technically correct and represented genuine gaps in `tests/test_bounded_bucket_strategy.py`.

---

## 4. Step 1: Reproduction of Surviving Mutants (Unedited Test Suite)

Ran against the unedited test file (`53ed26...`, 84 tests passing). All three mutants SURVIVED:

### M-38 (`shortlist()` scores segment offset `idx` instead of global `e.row`)
```diff
--- /home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/bounded_bucket.py
+++ /tmp/strat004a2-mut-M-38/graph_insertion/strategies/bounded_bucket.py
@@ -644,7 +644,7 @@
             self._last_shortlist_codes = ()
             return Shortlist(candidates=(), scores=())
 
-        rows = [e.row for e in filtered_entries]
+        rows = list(range(len(filtered_entries)))
         sub_mat = self._mat[rows]
         raw_scores = sub_mat @ q
```
**Result:** `SURVIVED (exit=0)` (84 passed in 1.76s).

### M-12 (No-tie-break variant: `paired.sort` by `(-score,)` without candidate name)
```diff
--- /home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/bounded_bucket.py
+++ /tmp/strat004a2-mut-M-12/graph_insertion/strategies/bounded_bucket.py
@@ -652,7 +652,7 @@
             (float(raw_scores[i]), filtered_entries[i].name, filtered_entries[i].code)
             for i in range(len(filtered_entries))
         ]
-        paired.sort(key=lambda item: (-item[0], item[1]))
+        paired.sort(key=lambda item: (-item[0],))
 
         candidates = tuple(name for _, name, _ in paired)
         scores = tuple(score for score, _, _ in paired)
```
**Result:** `SURVIVED (exit=0)` (84 passed in 1.80s).

### M-42 (`shortlist()` sets `_last_bucket_size_at_shortlist = 0`)
```diff
--- /home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/bounded_bucket.py
+++ /tmp/strat004a2-mut-M-42/graph_insertion/strategies/bounded_bucket.py
@@ -633,7 +633,7 @@
         self._last_bucket_gray_min = int(seg[0].gray)
         self._last_bucket_gray_max = int(seg[-1].gray)
         self._last_inside_bucket_span = bool(inside_span)
-        self._last_bucket_size_at_shortlist = len(seg)
+        self._last_bucket_size_at_shortlist = 0
         self._last_bucket_size = len(seg)
         self._last_code_existed_in_bucket = any(e.code == code for e in seg)
```
**Result:** `SURVIVED (exit=0)` (84 passed in 1.71s).

---

## 5. Step 3: Verification of Mutant Kills (Edited Test Suite)

Added `TestPostReviewScoringAndTies` (3 new tests, 87 total) to `tests/test_bounded_bucket_strategy.py`.
All 5 mutants (`M-38`, `M-12`, `M-42`, `A-01`, `A-02`) are KILLED:

1. **M-38:** `KILLED (exit=1)`
   ```text
   FAILED tests/test_bounded_bucket_strategy.py::TestPostReviewScoringAndTies::test_shortlist_scores_use_global_matrix_row_in_nonzero_segment_and_after_inserts
   ```
2. **M-12 (no-tie-break):** `KILLED (exit=1)`
   ```text
   FAILED tests/test_bounded_bucket_strategy.py::TestPostReviewScoringAndTies::test_shortlist_name_tiebreak_reorders_reverse_alphabetical_segment_entries
   ```
3. **M-42:** `KILLED (exit=1)`
   ```text
   FAILED tests/test_bounded_bucket_strategy.py::TestPostReviewScoringAndTies::test_bucket_size_at_shortlist_inside_span_gap_self_member_and_preserved_across_split
   ```
4. **A-01:** `KILLED (exit=1)`
   ```text
   FAILED tests/test_bounded_bucket_strategy.py::TestPostReviewAmendments::test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty
   ```
5. **A-02:** `KILLED (exit=1)`
   ```text
   FAILED tests/test_bounded_bucket_strategy.py::TestPostReviewAmendments::test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup
   ```

---

## 6. Verbatim `git diff` of `tests/test_bounded_bucket_strategy.py`

```diff
diff --git i/tests/test_bounded_bucket_strategy.py w/tests/test_bounded_bucket_strategy.py
index 2cb6593..171bd9a 100644
--- i/tests/test_bounded_bucket_strategy.py
+++ w/tests/test_bounded_bucket_strategy.py
@@ -1687,3 +1687,258 @@ class TestPostReviewAmendments:
         assert d_after_failed_setup["max_segment_size"] == 0
         assert d_after_failed_setup["mean_segment_size"] == 0.0
 
+
+class TestPostReviewScoringAndTies:
+    """Post-review tests closing M-38 (global row scoring), M-12 (tie-break), and M-42 (bucket_size_at_shortlist)."""
+
+    @staticmethod
+    def _cos_f64(a: np.ndarray, b: np.ndarray) -> float:
+        a64 = np.asarray(a, dtype=np.float64)
+        b64 = np.asarray(b, dtype=np.float64)
+        na = float(np.linalg.norm(a64))
+        nb = float(np.linalg.norm(b64))
+        return float(np.dot(a64 / na, b64 / nb))
+
+    def test_shortlist_scores_use_global_matrix_row_in_nonzero_segment_and_after_inserts(
+        self,
+    ) -> None:
+        """Proves shortlist() scores each candidate using its global matrix row e.row, not its 0..k-1 segment offset (kills M-38)."""
+        rng = np.random.default_rng(12345)
+        vecs: dict[str, np.ndarray] = {}
+        for i in range(18):
+            v = rng.standard_normal(16).astype(np.float32)
+            v /= float(np.linalg.norm(v))
+            vecs[f"node_{i:02d}"] = v
+
+        # Extra vectors for queries and sequential insertions whose names sort before "node_*"
+        for tag in ("q_batch", "aa_ins_1", "ab_ins_2", "ac_ins_3", "q_after_ins"):
+            v = rng.standard_normal(16).astype(np.float32)
+            v /= float(np.linalg.norm(v))
+            vecs[tag] = v
+
+        emb = ControllableEmbedder(vecs, dim=16)
+        g = ConceptGraph()
+        for i in range(18):
+            g.add_node(f"node_{i:02d}")
+
+        strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=6, seed=7)
+        strat.setup(g, emb)
+        assert len(strat._segments) >= 3
+
+        # 1. Batch setup() path: pick a query that lands in the last segment (bucket_id > 0)
+        last_seg = strat._segments[-1]
+        vecs["q_batch"] = vecs[last_seg[0].name].copy()
+        emb_batch = ControllableEmbedder(vecs, dim=16)
+        strat.setup(g, emb_batch)
+
+        sl = strat.shortlist("q_batch")
+        diag = strat.diagnostics()
+        home_idx = diag["bucket_id"]
+        assert home_idx is not None and home_idx == len(strat._segments) - 1 > 0
+        home_seg = strat._segments[home_idx]
+
+        # Precondition for killing M-38: global matrix row e.row differs from local segment offset idx
+        assert any(e.row != idx for idx, e in enumerate(home_seg))
+        assert len(sl.candidates) == len(home_seg) > 0
+        assert set(sl.candidates) == {e.name for e in home_seg}
+
+        for cand_name, score in zip(sl.candidates, sl.scores):
+            expected = self._cos_f64(vecs["q_batch"], vecs[cand_name])
+            assert abs(score - expected) < 1e-6, (
+                f"Candidate {cand_name} score {score} != expected cosine {expected}"
+            )
+
+        # 2. Post-on_inserted() path: append 3 nodes whose global rows are at the tail of _mat
+        for ins_idx, ins_name in enumerate(("aa_ins_1", "ab_ins_2", "ac_ins_3")):
+            # Aim at the last segment so the inserted nodes land in a non-zero segment
+            target_seg = strat._segments[-1]
+            v_ins = vecs[target_seg[ins_idx % len(target_seg)].name].copy()
+            vecs[ins_name] = v_ins
+            emb_batch.set_vector(ins_name, v_ins)
+
+            strat.shortlist(ins_name)
+            g.add_node(ins_name)
+            strat.on_inserted(ins_name, ())
+
+        # Find a non-zero segment containing at least one post-setup inserted node
+        target_seg_idx = None
+        for seg_i in range(len(strat._segments) - 1, 0, -1):
+            seg_names = {e.name for e in strat._segments[seg_i]}
+            if seg_names & {"aa_ins_1", "ab_ins_2", "ac_ins_3"}:
+                target_seg_idx = seg_i
+                break
+        assert target_seg_idx is not None and target_seg_idx > 0
+        post_seg = strat._segments[target_seg_idx]
+        assert any(e.row != idx for idx, e in enumerate(post_seg))
+
+        # Query that segment using a vector with the same Gray code as post_seg[0]
+        # and verify every candidate's score against independent float64 cosine
+        q_vec = vecs[post_seg[0].name].copy()
+        vecs["q_after_ins"] = q_vec
+        emb_batch.set_vector("q_after_ins", q_vec)
+
+        sl_post = strat.shortlist("q_after_ins")
+        assert strat.diagnostics()["bucket_id"] == target_seg_idx > 0
+        assert len(sl_post.candidates) == len(post_seg) > 0
+        assert set(sl_post.candidates) == {e.name for e in post_seg}
+        for cand_name, score in zip(sl_post.candidates, sl_post.scores):
+            expected = self._cos_f64(vecs["q_after_ins"], vecs[cand_name])
+            assert abs(score - expected) < 1e-6
+
+    def test_shortlist_name_tiebreak_reorders_reverse_alphabetical_segment_entries(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves shortlist() breaks equal-score ties by ascending name even when segment order is reverse-alphabetical (kills M-12 no-tie-break variant)."""
+        strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=4, seed=42)
+        # First 4 coordinates drive the 4 hyperplanes; 5th coordinate is orthogonal to all hyperplanes
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, 5, dtype=np.float64)
+        )
+
+        def vec5_for_gray(gray_rank: int, fifth: float) -> np.ndarray:
+            # Binary code corresponding to gray_rank: code = gray ^ (gray >> 1)
+            code = gray_rank ^ (gray_rank >> 1)
+            coords = [
+                1.0 if ((code >> (3 - b)) & 1) else -1.0 for b in range(4)
+            ] + [fifth]
+            return np.array(coords, dtype=np.float32)
+
+        # Case A: exact non-zero float32 score tie (all candidates have norm sqrt(5) and 5th coord 1.0)
+        # Assign gray ranks 1 < 2 < 3 to "z_first", "m_middle", "a_second" so segment order is reverse-alphabetical
+        vecs_nonzero = {
+            "z_first": vec5_for_gray(1, 1.0),
+            "m_middle": vec5_for_gray(2, 1.0),
+            "a_second": vec5_for_gray(3, 1.0),
+            "q_nonzero": np.array([-1.0, -1.0, -1.0, -1.0, 0.0], dtype=np.float32),
+        }
+        # Query purely along the 5th axis so dot product with each candidate is identically 1/sqrt(5)
+        vecs_nonzero["q_axis5"] = np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
+
+        g1 = ConceptGraph()
+        for name in ("z_first", "m_middle", "a_second"):
+            g1.add_node(name)
+        emb1 = ControllableEmbedder(vecs_nonzero, dim=5)
+        strat.setup(g1, emb1)
+
+        assert len(strat._segments) == 1
+        seg_entries = strat._segments[0]
+        # Precondition: segment entries have strictly increasing Gray rank and reverse-alphabetical names
+        assert [e.gray for e in seg_entries] == [1, 2, 3]
+        assert [e.name for e in seg_entries] == ["z_first", "m_middle", "a_second"]
+
+        sl_nonzero = strat.shortlist("q_axis5")
+        assert sl_nonzero.candidates == ("a_second", "m_middle", "z_first")
+        assert len(set(sl_nonzero.scores)) == 1
+        assert np.isclose(sl_nonzero.scores[0], 1.0 / np.sqrt(5.0), atol=1e-6)
+
+        # Case B: exact 0.0 float32 score tie (candidates have 5th coord 0.0, query is along 5th axis)
+        vecs_zero = {
+            "z_first": vec5_for_gray(1, 0.0),
+            "m_middle": vec5_for_gray(2, 0.0),
+            "a_second": vec5_for_gray(3, 0.0),
+            "q_axis5": np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32),
+        }
+        emb2 = ControllableEmbedder(vecs_zero, dim=5)
+        strat.setup(g1, emb2)
+        assert [e.name for e in strat._segments[0]] == ["z_first", "m_middle", "a_second"]
+
+        sl_zero = strat.shortlist("q_axis5")
+        assert sl_zero.candidates == ("a_second", "m_middle", "z_first")
+        assert sl_zero.scores == (0.0, 0.0, 0.0)
+
+    def test_bucket_size_at_shortlist_inside_span_gap_self_member_and_preserved_across_split(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves bucket_size_at_shortlist equals len(seg) >= 1 on inside-span, gap, and self-member queries and stays equal to pre-split size after a split in on_inserted() (kills M-42)."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+
+        # Build a 2-segment graph of 8 nodes:
+        # Segment 0 gets 4 nodes at gray ranks 1, 2, 3, 4; Segment 1 gets 4 nodes at gray ranks 10, 11, 12, 13
+        def vec4_for_gray(gray_rank: int) -> np.ndarray:
+            code = gray_rank ^ (gray_rank >> 1)
+            return TestMergeAndNeighbourRule._vec_for_code(code, 4)
+
+        vecs: dict[str, np.ndarray] = {}
+        g = ConceptGraph()
+        for g_rank in (1, 2, 3, 4, 10, 11, 12, 13):
+            name = f"n_{g_rank:02d}"
+            vecs[name] = vec4_for_gray(g_rank)
+            g.add_node(name)
+
+        vecs["q_inside"] = vec4_for_gray(2)  # inside Segment 0 span [1, 4]
+        vecs["q_gap_1"] = vec4_for_gray(5)   # in gap (4, 10), closer to Segment 0
+        vecs["q_gap_2"] = vec4_for_gray(6)   # in gap, will bring Segment 0 to size 6
+        vecs["q_split"] = vec4_for_gray(7)   # 7th node in Segment 0 -> triggers split (6 -> 7 -> 3 + 4)
+
+        emb = ControllableEmbedder(vecs, dim=4)
+        strat.setup(g, emb)
+        assert len(strat._segments) == 2
+        assert [len(s) for s in strat._segments] == [4, 4]
+
+        # 1. Inside-span query (not yet in graph)
+        strat.shortlist("q_inside")
+        d_in = strat.diagnostics()
+        seg_in = strat._segments[d_in["bucket_id"]]
+        seg_in_names = {e.name for e in seg_in}
+        assert d_in["inside_bucket_span"] is True
+        assert d_in["bucket_size_at_shortlist"] == len(seg_in) == 4 >= 1
+        assert d_in["bucket_size_at_shortlist"] == d_in["shortlist_size"] + (
+            1 if "q_inside" in seg_in_names else 0
+        )
+
+        # 2. Query where new_name is already a member of the segment (self-exclusion in shortlist_size)
+        strat.shortlist("n_02")
+        d_self = strat.diagnostics()
+        seg_self = strat._segments[d_self["bucket_id"]]
+        seg_self_names = {e.name for e in seg_self}
+        assert "n_02" in seg_self_names
+        assert d_self["bucket_size_at_shortlist"] == len(seg_self) == 4 >= 1
+        assert d_self["shortlist_size"] == 3
+        assert d_self["bucket_size_at_shortlist"] == d_self["shortlist_size"] + (
+            1 if "n_02" in seg_self_names else 0
+        )
+
+        # 3. Gap query (outside every segment span)
+        strat.shortlist("q_gap_1")
+        d_gap = strat.diagnostics()
+        seg_gap = strat._segments[d_gap["bucket_id"]]
+        seg_gap_names = {e.name for e in seg_gap}
+        assert d_gap["inside_bucket_span"] is False
+        assert d_gap["bucket_size_at_shortlist"] == len(seg_gap) == 4 >= 1
+        assert d_gap["bucket_size_at_shortlist"] == d_gap["shortlist_size"] + (
+            1 if "q_gap_1" in seg_gap_names else 0
+        )
+        g.add_node("q_gap_1")
+        strat.on_inserted("q_gap_1", ())
+        assert strat.diagnostics()["bucket_size_at_shortlist"] == 4
+        assert strat.diagnostics()["bucket_size"] == 5
+
+        # Insert a 6th node into Segment 0 so its size reaches s_max = 6
+        strat.shortlist("q_gap_2")
+        assert strat.diagnostics()["bucket_size_at_shortlist"] == 5
+        g.add_node("q_gap_2")
+        strat.on_inserted("q_gap_2", ())
+        assert strat.diagnostics()["bucket_size_at_shortlist"] == 5
+        assert strat.diagnostics()["bucket_size"] == 6
+        assert strat.diagnostics()["split_occurred"] is False
+
+        # 4. Query and insert 7th node into Segment 0 -> triggers split (6 + 1 = 7 -> 3 and 4)
+        strat.shortlist("q_split")
+        d_before_split = strat.diagnostics()
+        assert d_before_split["bucket_size_at_shortlist"] == 6
+        assert d_before_split["bucket_size"] == 6
+        assert d_before_split["shortlist_size"] == 6
+
+        g.add_node("q_split")
+        strat.on_inserted("q_split", ())
+        d_after_split = strat.diagnostics()
+        assert d_after_split["split_occurred"] is True
+        # bucket_size_at_shortlist MUST remain the pre-insert segment size (6),
+        # while bucket_size updates to the post-split home half size (4 for the right half containing q_split)
+        assert d_after_split["bucket_size_at_shortlist"] == 6
+        assert d_after_split["bucket_size"] == 4
+
```

---

## 7. Verbatim `git diff` of `docs/tasks/status.md`

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 4349689..9d8649c 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -48,8 +48,8 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 | --------- | ------------------------------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
 | STRAT-001 | Implement Strategy 1 (brute-force)         | **done**         | Implemented by Gemini; reviewed by opencode (ACCEPT WITH NOTES, report [`docs/reports/STRAT-001-review-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-review-opencode.md)); coverage gap closed under STRAT-001-A (report [`docs/reports/STRAT-001-A-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-A-claude-code.md)). Accepted at APC review 2026-10-11.                                    |
 | STRAT-002 | Implement Strategy 2 (embedding-threshold) | **done**         | Implemented by Gemini; reviewed and amended under D-50 (report [`docs/reports/STRAT-002-review-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-review-claude-code.md)); verified under STRAT-002-V (report [`docs/reports/STRAT-002-V-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-V-opencode.md)); one vacuous assertion strengthened under STRAT-003-A. Accepted at APC review 2026-10-11. |
-| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md).                                                                                                                                                                                                                                 |
-| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | **needs-review** | Implemented by Gemini (`BoundedBucketStrategy`, [D-59]; 82 strategy tests passing, 559 passed / 3 skipped full suite); reviewer to be assigned by APC. See report [`docs/reports/STRAT-004-gemini-bounded-bucket.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-004-gemini-bounded-bucket.md). |
+| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **done**         | Implemented by Gemini ([D-55]); reviewed under STRAT-003-R; amended under STRAT-003-A ([D-55] post-review note); stale-cache fix under STRAT-003-B ([D-58]); verified under STRAT-004-R. Accepted at APC review 2026-10-11. See reports `docs/reports/STRAT-003-gemini-ann-retrieval.md`, `docs/reports/STRAT-003-R-gemini.md`, `docs/reports/STRAT-003-A-gemini.md`, `docs/reports/STRAT-003-B-gemini.md`, `docs/reports/STRAT-004-R-gemini.md`. |
+| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | **done**         | Implemented by Gemini (`BoundedBucketStrategy`, [D-59]); reviewed under STRAT-004-R and STRAT-004-R2; amended under STRAT-004-A ([D-62]) and STRAT-004-A2 (87 strategy tests passing). Accepted at APC review 2026-10-11. See reports `docs/reports/STRAT-004-gemini-bounded-bucket.md`, `docs/reports/STRAT-004-R-gemini.md`, `docs/reports/STRAT-004-A-gemini.md`, `docs/reports/STRAT-004-R2-gemini.md`, `docs/reports/STRAT-004-A2-gemini.md`. |
 
 ## Phase 3 — Integration & Full Sweep
 
@@ -89,6 +89,6 @@ Status: **not started** (blocked on Phase 3)
 | FIX-013 | Repair and test DATA-006 (shard orchestration for the name-pool generator): fix 8 defects (verify crashes on merge_run_ids/dict sha256; shards overwrite tracked pool; lock paths in ShardLockManager; bounded pipe drain after SIGKILL; merged meta fidelity; adapter error 15 mapping to exit 7; illustrative model mismatch fixture; corpus_overlap_embed assertion); add 14 unit/integration tests; Contract v1.1 ([D-54]). | **needs-review** | Completed by Gemini. All 41 generator tests passing; full test suite 394 passing, 3 skipped. See report [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
 | FIX-014 | Finish FIX-013: rewrite D-54 in place to remove unsupported claims, close 6 test gaps (merged verify success and tampered cache, recursive results/datagen fixture, profile-lock exclusion, prompt-version-only mismatch, merged meta fidelity, exit-7 cache sha256 preservation), and correct status rows ([D-54]). | **needs-review** | Completed by Gemini. See report [`docs/reports/FIX-014-gemini-finish-fix-013.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-014-gemini-finish-fix-013.md). |
 | FIX-015 | Explicit `--adapter-thinking {auto,on,off}` control for `generate_name_pool.py` (payload, dry-run, shard commands, cache `thinking_requested`, pool `requested_thinking`, mixed-thinking merge refusal), repair `guard_results_datagen_unmodified` fixture by removing destructive cleanup loop and isolating CLI tests to `tmp_path`, replace `sleep` with ready-file handshake in `test_profile_lock_mutual_exclusion` ([D-57]). | **needs-review** | Completed by Gemini. 47 generator tests passing; full test suite 400 passing, 4 skipped. See report [`docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md). |
-| FIX-016 | Make `estimate_and_print_plan()` in `src/graph_insertion/harness.py` use `candidate_upper_bound(strategy, n_existing)` instead of `strategy.config().get("top_k", None)` so dry-run plans for Strategies 3 (`k`), 4 (`s_max`), and `NullStrategy` (`k`) match the live guard `compute_planned_calls_upper_bound`; add unit and parity tests in `tests/test_dry_run_plan.py` ([D-61]). | **needs-review** | Completed by Gemini. 11 dry-run planner tests passing; full test suite 581 passing, 3 skipped. See report [`docs/reports/FIX-016-gemini-dry-run-planner.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-016-gemini-dry-run-planner.md). |
+| FIX-016 | Make `estimate_and_print_plan()` in `src/graph_insertion/harness.py` use `candidate_upper_bound(strategy, n_existing)` instead of `strategy.config().get("top_k", None)` so dry-run plans for Strategies 3 (`k`), 4 (`s_max`), and `NullStrategy` (`k`) match the live guard `compute_planned_calls_upper_bound`; add unit and parity tests in `tests/test_dry_run_plan.py` ([D-61]). | **done** | Completed by Gemini. 11 dry-run planner tests passing; full test suite 581 passing, 3 skipped. Accepted at APC review 2026-10-11. See report [`docs/reports/FIX-016-gemini-dry-run-planner.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-016-gemini-dry-run-planner.md). |
 | TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, add thesis size check (>300 KB), add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
 | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
```

---

## 8. Post-Edit Test Counts, File Hashes, and Hygiene

- **Strategy 4 test suite:** `87 passed in 1.22s` (`.venv-ann/bin/python -m pytest tests/test_bounded_bucket_strategy.py -q`)
- **Full test suite:** `586 passed, 3 skipped in 113.48s (0:01:53)` (`.venv-ann/bin/python -m pytest -q`)
- **File hashes and line counts:**
  - `005f657dcdbbc7129c576717e87b725c3a61b13ad9411c9c38eab1fd3979cd7e` (1944 lines) `tests/test_bounded_bucket_strategy.py`
  - `c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af` (847 lines) `src/graph_insertion/strategies/bounded_bucket.py` (UNCHANGED)
- **Scratch directory hygiene:**
  - `rm -rf /tmp/strat004a2*` executed.
  - `ls /tmp/strat004a2*`: confirmed `No such file or directory`.
