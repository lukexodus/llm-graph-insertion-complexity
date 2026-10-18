# Briefing Document for Adviser: Methodological Decisions D1–D6 for Phase 4 Analysis

**Project**: *An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction*  
**Author**: Adrian Luke Labasan  
**Date**: October 19, 2026  
**Status**: Pre-registered and adopted for Initial Defense; open for adviser feedback and adjustments post-defense.  

---

## 1. Executive Summary and Purpose

This document provides a comprehensive briefing on **Decisions D1 through D6** governing the Phase 4 empirical analysis plan. 

To ensure complete pre-registration and methodological rigor before analyzing the final experimental sweep data, these decisions have been formalized in the repository's decision log ([D-79]) and analysis plan (`docs/context/analysis-plan.md`). For the upcoming **initial defense**, we are proceeding with these decisions as active working policy to complete the defense manuscript on schedule. 

Following the initial defense, any of these conventions can be refined, recalibrated, or expanded based on your guidance and committee recommendations.

---

## 2. Study Context and Research Questions

The study analyzes four candidate-narrowing strategies for incremental knowledge graph construction using Large Language Models (LLMs):
1. **Strategy 1 (Brute Force / S1)**: Unbounded pairwise comparison against all existing concepts ($O(n)$ calls).
2. **Strategy 2 (Embedding Threshold / S2)**: Cosine similarity pruning with threshold $\theta \in \{0.4, 0.5, 0.6\}$ ($O(n)$ embeddings, variable calls).
3. **Strategy 3 (ANN Retrieval / S3)**: HNSW approximate nearest-neighbor search with $k \in \{5, 10, 20\}$ and $\text{efSearch} \in \{64, 128, 256\}$ ($O(\log n)$ search, capped calls).
4. **Strategy 4 (Bounded Bucket / S4)**: Locality-sensitive hashing (LSH) and Gray-code segment bucketing with bounds $(s_{\min}, s_{\max}) \in \{(2, 5), (5, 10), (10, 20)\}$ ($O(1)$ amortized premise, capped calls).

The four core research questions addressed in Chapter 4 are:
- **RQ1 (Cost Scaling)**: How do LLM call counts and wall-clock insertion latencies scale as graph size $n$ increases on synthetic concept pools ($n \in \{50, 100, 200, 500, 1000, 2000\}$)?
- **RQ2 (Placement Accuracy)**: What is the precision, recall, $F_1$, and candidate shortlist recall when inserting concepts into expert gold-standard curriculum graphs (DSA and Metacademy)?
- **RQ3 (Comparative Trade-offs)**: What are the Pareto trade-offs between cost reduction and accuracy retention across strategies?
- **RQ4 (Structural Premise of Constant Time)**: Does a bucket-capped strategy maintain flat single-insertion costs as the graph expands, validating the structural assumption behind theoretical bounds?

---

## 3. Detailed Breakdown of Decisions D1 to D6

### Decision D1: Uncertainty Estimation via 95% Percentile Bootstrap
- **Context**: In latency measurements (`total_s`), network round-trips to API endpoints and garbage collection introduce right-skewed, heavy-tailed distributions. Standard parametric intervals (e.g., Student's $t$ or Gaussian confidence intervals) assume normality and can produce distorted or negative lower bounds.
- **Adopted Policy**: All reported intervals across cost and accuracy figures use a **95% percentile bootstrap** over empirical trials with **10,000 resamples** and a fixed pseudo-random seed.
- **Reporting**: Alongside bootstrap intervals, tables and text report complete descriptive statistics: sample mean, standard deviation (SD), minimum, maximum, and median.
- **Benefit**: Non-parametric robustness with zero distributional assumptions; fully reproducible.

---

### Decision D2: Flatness Classification Bins for Scaling Slope (RQ4)
- **Context**: RQ4 examines whether insertion cost remains flat as graph size $n$ grows. For each strategy, we fit an ordinary least squares (OLS) log-log regression:
  $$\log(\text{Cost}) = \alpha + \beta \log(n)$$
  where $\beta$ represents the empirical scaling exponent ($\text{Cost} \propto n^\beta$). A truly constant-time strategy exhibits $\beta = 0$, while a linear strategy exhibits $\beta = 1$.
- **Adopted Policy**: To prevent post-hoc interpretation bias, descriptive slope bins are fixed prior to examining sweep results:
  - $\beta < 0.1$: **"Approximately flat"** (consistent with the structural premise of constant-time insertion)
  - $0.1 \le \beta \le 0.9$: **"Sub-linear"**
  - $\beta > 0.9$: **"Approximately linear"**
- **Methodological Nuances**:
  1. For Strategies 3 and 4, LLM call counts are mechanically bounded by $k$ or $s_{\max}$, so call counts are flat by design. Therefore, the critical empirical test of the structural premise lies in the **wall-clock curve** (`total_s`, specifically `shortlist_s` and `decide_s`) and whether realized call counts remain below the cap.
  2. The single-insertion protocol measures an **un-amortized single step** (as acknowledged in the thesis scope limitations, [D-68](1)). It evaluates the structural premise of the bound rather than multi-insertion amortization over time.
- **Adviser Discussion Item**: These bins represent a convention established for this study. We welcome your advice on whether you prefer alternative cutoff thresholds (e.g., $\beta < 0.05$) or alternative statistical tests for the final dissertation manuscript.

---

### Decision D3: Benchmark Matrix Configuration and Observational Variance Citation
- **Context**: The full benchmark matrix encompasses 24 distinct experimental runs (12 accuracy configurations + 12 sweep configurations) totaling **184,758 planned LLM calls**. Due to API rate limits, costs, and token quotas, running multiple complete replicates for all 24 configurations was not feasible.
- **Adopted Policy**: The primary benchmark matrix consists of a single controlled execution per configuration under identical runtime environments (`commit 3323bfb`, uniform PyTorch single-thread pin, verified dependencies).
- **Accounting for Non-determinism**: LLM reasoning exhibits minor run-to-run stochasticity. In an earlier procedural test run on DSA (Run 1, which was excluded due to an accidental single-corpus flag), the measured micro-$F_1$ was 0.4859, compared to 0.5111 on the subsequent full re-run (an observed difference of $\sim 0.025$). 
- **Reporting Convention**: We report this observed difference transparently as **one observed empirical variation** between two runs of the same configuration, explicitly noting that it does *not* constitute an estimated noise floor or confidence interval.
- **Adviser Discussion Item**: Post-defense, if you recommend running multi-run replicates for a specific high-interest subset (such as the primary configurations of Strategy 3 and 4), we can schedule them.

---

### Decision D4: Accuracy Reporting Per Corpus (Not as a Continuous Curve)
- **Context**: In thesis Chapter 3 Section 3.5, the text originally suggested investigating "accuracy against graph size". However, verified expert gold-standard prerequisite graphs exist only for two specific corpora:
  - **DSA (Data Structures and Algorithms)**: 29 concepts, 54 positive prerequisite edges.
  - **Metacademy**: 141 concepts, 318 positive prerequisite edges.
  Synthetic name pools allow arbitrary sizes $n$ for cost measurement, but synthetic names do not have expert pedagogical ground-truth edges.
- **Adopted Policy**: Accuracy claims are derived strictly from the gold corpora and reported **per corpus** (DSA $n=29$ and Metacademy $n=141$) in side-by-side tables and bar charts, rather than attempting to plot an artificial continuous curve across arbitrary $n$. The thesis text explicitly clarifies that accuracy scaling is answered at the discrete benchmark sizes provided by literature corpora.

---

### Decision D5: Mechanical Dominance and Indistinguishability Threshold (Figure F6)
- **Context**: Figure F6 visualizes the primary cost-accuracy trade-off by plotting insertion cost (LLM calls) against accuracy (micro-$F_1$) across all configurations. When comparing two strategies, declaring that Strategy A "dominates" Strategy B requires that Strategy A has lower cost and strictly superior accuracy.
- **Adopted Policy**: Pareto dominance is computed mechanically. However, to respect the empirical non-determinism identified in D3, an $F_1$ difference smaller than **0.025** is categorized as **"not distinguishable"** rather than claiming strict dominance.
- **Benefit**: Prevents overclaiming superiority when differences fall within the observed stochastic margin of LLM judgments.

---

### Decision D6: Headline Central Tendency Statistic (Mean with Median)
- **Context**: Thesis Section 3.4 specifies evaluating the "average" latency per insertion. However, as noted in D1, latency distributions are skewed by outliers.
- **Adopted Policy**: We report the **sample mean** as the headline statistic in text and summary tables to strictly adhere to the thesis proposal's commitment to "average" latency, while systematically reporting the **median** alongside it in all tables and figures.
- **Benefit**: Full fidelity to the original thesis wording while providing complete distributional transparency.

---

## 4. Summary Table for Adviser Review

| Decision | Topic | Working Policy (Initial Defense) | Rationale | Post-Defense Flexibility |
| :--- | :--- | :--- | :--- | :--- |
| **D1** | **Bootstrap Intervals** | 95% percentile bootstrap, 10,000 resamples, fixed seed. | Skewed latency distributions; avoids invalid normality assumptions. | Number of resamples or interval type (e.g., BCa) can be updated. |
| **D2** | **Scaling Flatness Bins** | Slope $\beta < 0.1$ = flat; $0.1 \le \beta \le 0.9$ = sub-linear; $\beta > 0.9$ = linear. | Pre-registered classification for OLS log-log slope to evaluate RQ4. | Bin thresholds can be adjusted based on committee preference. |
| **D3** | **Replicates & Variance** | Single benchmark matrix runs; cite observed $\sim 0.025$ $F_1$ difference. | Compute and API budget bounds; avoids unsubstantiated noise-floor claims. | Replicates can be added for selected primary configurations if funded/requested. |
| **D4** | **Accuracy vs. Size** | Discrete per-corpus reporting (DSA $n=29$, Metacademy $n=141$). | Ground-truth gold prerequisite graphs exist only at these two sizes. | Thesis text aligned to reflect discrete benchmark constraints. |
| **D5** | **Pareto Dominance** | Mechanical dominance; $| \Delta F_1 | < 0.025$ labeled "indistinguishable". | Prevents declaring dominance on differences within stochastic noise. | Indistinguishability band can be tightened or relaxed. |
| **D6** | **Central Tendency** | Mean as headline statistic; median reported alongside. | Aligns with Section 3.4 "average" wording while presenting robust median. | Can switch headline emphasis between mean and median if desired. |

---

## 5. Next Steps and Consultation

We are proceeding with this rigorous, pre-registered analysis framework for the initial defense submission. Once you have had an opportunity to review this briefing, we look forward to discussing any adjustments or additional analyses you would like to see incorporated for the final dissertation.
