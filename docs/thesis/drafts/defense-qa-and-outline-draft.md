# Defense material draft (APC-B), 2026-10-21

Source: Bundle B (`bundle_b_final_outputs.tar.gz`, sha `f700b66b…7dfb`), run from commit `554bde3`, gate PASS, 24 runs. Numbers below come from `T1`, `T2_slope_fits`, `T2_sweep_cost_summary`, `T4`, `F6_dominance` in that bundle unless marked **[derived]** (my arithmetic on those tables) or **[open]**. Nothing here is from agent prose.

## 0. Corrections to my earlier message

- I guessed S2's `total_s` growth came from a shortlist scan. Wrong. S2 shortlist time is 0.01 to 0.03 s at every n; the growth is the decide step (LLM calls).
- I said S4 on DSA was "about at random" using 6.97/28. The random baseline in T1 for S4 primary is 0.3571 (= 10/28, i.e. s_max/m). Shortlist recall for S4 primary on DSA is **0.2593, below that baseline**. See Q9.

## 1. Headline findings (all from the tables)

1. **Scaling of LLM calls.** S1 slope 1.0000 (linear). S3 constant at 10. S4 primary slope −0.0004 (CI −0.0433 to 0.0424). S2 call counts rise with n but stay far below S1 (θ=0.6, n=2000: 0.8 calls; θ=0.4: 13.5).
2. **Scaling of wall-clock.** S1 `total_s` slope 0.9605 (CI 0.8472 to 1.0624) on all trials; 1.0558 (CI 1.0439 to 1.0677, min 8 trials/size) on the clean post-hoc set. S3 −0.0201, S4 0.0084. S1 at n=2000: 1,713 s per insertion on average; S3 8.3 s; S4 5.6 s; S2 θ=0.6 0.94 s.
3. **Time follows calls [derived].** Per-call latency is about 0.8 to 0.9 s: S1 1713.1/2000 = 0.857, S3 8.277/10 = 0.83, S4 5.638/7.0 = 0.81. Shortlist time is 0.01 to 0.03 s for S2 to S4 and about 0.001 s for S1. So the cost of every strategy is dominated by LLM calls, and the strategies differ in how many calls they make.
4. **Accuracy trade-off (micro-F1, T1).** DSA: S1 0.586, S3 0.511, S4 0.271, S2 0.148. Metacademy: S3 0.294, S2 0.270, S1 0.143, S4 0.114. S1's Metacademy precision is 0.081 against recall 0.624: with 140 candidates the LLM over-links.
5. **Dominance (R2, mechanical).** DSA: all 6 pairs trade-off. Metacademy: S3 dominates S1; S2 dominates S1 and S4; S3 vs S2 not distinguishable (ΔF1 = 0.0246); S4 vs S1 trade-off. I recomputed these from T1; all 12 match.
6. **S2's low cost is a recall cost.** Shortlist recall at θ=0.6: 0.111 (DSA), 0.202 (Metacademy), against 1.000 for S1.

## 2. Slide outline (about 14 slides; trim to the time slot, which I do not know **[open]**)

1. Title, problem, research question.
2. Setting: the four strategies in one line each; corpora (DSA 29 nodes, Metacademy 141 nodes); accuracy stage 59 trials, sweep 60 trials per run.
3. Pre-registered design: frozen sizes {50…2000}, D2 flatness categories, R1 to R3, the 24-run matrix.
4. Run provenance and validation: validator gate (24 runs PASS, hashes), independent review chain, the pipeline checker (3,399 checks, 0 failures on the final output; fixed version, see section 6).
5. F1 / F1b: calls vs n. F1 is pre-registered; F1b is exploratory and shown with it.
6. F2 Panel A / F2b Panel A: wall-clock vs n. Use Panel A only (Section 5).
7. T2 slope fits: the table, with S3 and S4 flat, S1 linear.
8. S2: show counts, not a slope. θ=0.6 has zero mean calls at n=50 and 500, so the pre-registered fit is undefined; the exploratory fit (0.8095, CI 0.2689 to 0.9538, 4,123 of 10,000 resamples usable) is labelled exploratory.
9. S1 timing with and without retried trials and `t9`, labelled post-hoc.
10. F4 accuracy by strategy (T1), with shortlist recall next to F1.
11. F6 dominance (use F6 for the labels and result text, see Section 5), with the recall-cost message for S2.
12. Sensitivity (T4 / F5): unjudged predictions are 0 except 2 cells.
13. Limits: synthetic-data recall caveat, one LLM, two corpora, operator-asserted `--src-diff-clean`, retry backoff, peak launches.
14. Conclusion and answer to the RQ.

## 3. Likely examiner questions

**Q1. Why do your fitted slopes for S3 and S4 differ from zero, if they are "flat"?**
Flat is by the pre-registered D2 threshold (|slope| < 0.1), not by a CI that contains zero. S3 total_s −0.0201 has CI −0.0324 to −0.0079; S3 ef=256 (0.0154) and k=20 (0.0123) also exclude zero. The effect is under 0.03 of a log-unit; timing noise from the API, not a trend. Don't say "CI includes zero" for S3.

**Q2. S3 calls slope prints 5.99e-32.** The series is constant at 10; the slope is zero and R² is arbitrary. Say "0, constant".

**Q3. Why is the S2 fit undefined?** A log-log fit needs positive means. θ=0.5 has zero mean at n=50; θ=0.6 at n=50 and n=500. R1 forbids clamping, so the pre-registered fit is undefined and an exploratory fit on positive-mean sizes is given with its limits (bootstrap conditions on positive draws, so intervals are exploratory and optimistic in one direction).

**Q4. S2's call count is tiny, so is it the best strategy?** No. Shortlist recall is 0.111 (DSA) and 0.202 (Metacademy); S2 makes few calls because it rarely proposes candidates. On DSA it is dominated in accuracy (F1 0.148). On Metacademy it is competitive (0.270) and S3 is not distinguishable from it (ΔF1 0.0246).

**Q5. "Not distinguishable" is only 0.0004 under the cutoff.** True. R2's 0.025 margin was fixed in advance, mechanically. The ΔF1 is 0.0246, so a threshold of 0.02 would flip the label. Say it before they do. [Whether a bootstrap CI on ΔF1 exists: **open**; do not claim one.]

**Q6. Why did S1 and S2 run at sizes 50 to 500 first?** To save time, then extended to all six sizes once throughput allowed. The frozen design is unchanged; recorded in D-84. Dates: n ≤ 500 on 2026-10-19 02:55 to 08:35; n = 1000, 2000 from 2026-10-19 18:00 to 2026-10-20 15:32.

**Q7. The 01:00 shutdown and the peak launch.** Use Luke's own words only, as recorded in D-84: the shutdown "was my mistake because i thought it would finish before 1AM"; peak: "I had to allow peak at 3PM because of time constraints". One trial (`sweep:brute_force:2000:t9`) ran at peak (15:02:43 to 15:32:09). Effect: t9 took about 1,766 s against clean mean 1,710 s **[agent-relayed]**; descriptive, N=10, not proof of a peak effect. Launches with `ALLOW_PEAK=1` set: four (D-84 (5)(b)); only the 2026-10-20 15:02 one was in a peak window; the other three ran and finished before 09:00 PHT (D-88 (2), once merged). Luke's recollection is one peak-hour launch, around 3PM Tuesday. File note: two earlier attempts at about 15:02 started and stopped on a malformed API key string before completing a call, and a third capture shows a missing key; whether they carried the flag is not established. Say that if asked; do not say "exactly one attempt".

**Q8. Retries.** `total_s` includes backoff for retried trials. S1 n=50: mean 58.6 s all trials, 35.7 s clean (1 retried trial). S2 θ=0.4 n=500: 9.39 s all, 3.53 s clean. That is why the S1 all-trials slope (0.9605) is below the clean one (1.0558); both read "approximately linear".

**Q9. Is S4 doing anything useful?** Its shortlist recall on DSA (0.259 primary; 0.093 for (2,5); 0.593 for (10,20)) is below the random baseline for the same shortlist size (0.357; 0.179; 0.714) in all three configurations. On Metacademy it is above (0.147 vs 0.071; 0.101 vs 0.036; 0.220 vs 0.143), about 2 to 3 times. Say that S4 buys flat cost at a large accuracy price on DSA, and that its low `exact_topk_overlap` at large n is a finding (D-35). Check the baseline definition in the plan before quoting it **[open]**.

**Q10. Why does ANN (S3) beat brute force on Metacademy?** Brute force sees all 140 candidates and links too many (precision 0.081, recall 0.624, F1 0.1435); S3 shows 10 and gets F1 0.2941. On DSA (28 candidates) brute force wins (0.586 vs 0.511). So "fewer candidates helps" is corpus-dependent.

**Q11. Different commits for the two stages.** Accuracy ran at `3323bfb`, sweep at `ad81414`. Accepted under plan Amendment 2 with `--src-diff-clean`; `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml` returned 0 at the final HEAD per the agent's report. The assertion is the operator's; the diff should be re-run by Luke himself before Friday.

**Q12. Were the analysis rules fixed before looking at the data?** An early draft of the pipeline was run on the real results before R1 to R3 were fixed; whether anyone looked at its numbers is "not confirmed by Luke" in D-84. Amendment 3 says this plainly. Luke's own answer (D-88 (1)): he looked at the output and saw label overlaps; asked whether he noticed any numbers or results or asked for any change because of it, he answered "None". Answer plainly: not blind, no numbers noted, no change requested.

**Q13. Recall numbers in the thesis (0.841 / 0.968 / 0.999 for efSearch 64/128/256).** Synthetic Gaussian data; MiniLM recall on the real corpora was not measured separately. In the real runs, S3 shortlist recall is 0.528 (DSA) and 0.505 (Metacademy), but this is against gold edges, not exact top-k.

**Q14. Why only θ ≤ 0.6?** No stricter θ was run; the design fixed {0.4, 0.5, 0.6}. Stated as a limitation.

## 4. Figures and tables: which to show

| Item | Use | Note |
| --- | --- | --- |
| F1 / F1b | both, side by side | F1b is log-log and exploratory; never replaces F1 |
| F2 Panel A / F2b Panel A | yes | |
| F2b Panel B | **do not show** | S2 `decide_s` points at n=50 and n=500 are silently dropped (zero means) and the line is drawn across the gap; no footnote on this panel |
| F6 | use for dominance text and labels | label collision between S2 and S3 on Metacademy |
| F6b | only after a visual fix | on the DSA panel the S4 label sits behind the legend; on the Metacademy panel the S1 label (140, 0.143) is cut off at the right edge and the legend overlaps it. A slide-only redraw from `F6b_cost_vs_accuracy_logx.csv` with the legend outside the axes is a small job; label it "redrawn from F6b CSV" |
| PDFs | avoid | six pre-registered PDFs differ between the two output directories while their CSVs are byte-identical; use PNGs |

## 5. Open items before Friday

1. (done) Luke's answers are recorded in D-88; no statement from him on the 08:36 launch exists.
2. Re-run of `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml` and the final checker by Luke, raw output pasted.
3. Time slot for the presentation and the deck tool.
4. D-88 correcting entry (status-row commit for DOC-011, ANALYSIS-002 row, F2b Panel B, peak count).
5. The 3.7x DSA embedding-latency swing between the two S3 accuracy runs is unexplained; if asked, say so.
