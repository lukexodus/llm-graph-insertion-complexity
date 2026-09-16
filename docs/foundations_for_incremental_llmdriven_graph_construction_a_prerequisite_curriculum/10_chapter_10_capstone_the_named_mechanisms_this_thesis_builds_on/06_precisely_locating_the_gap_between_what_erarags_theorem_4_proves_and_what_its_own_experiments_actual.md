## Precisely locating the gap between what EraRAG's Theorem 4 proves and what its own experiments actually measure

### The query-planner-estimate analogy

A database query planner's EXPLAIN output gives a formal cost estimate for a query plan, built from a cost model with its own assumptions: uniform data distribution, independent columns, a particular disk-seek cost constant. A benchmark suite that runs the query ten times on a real dataset and reports average wall-clock milliseconds is a completely different kind of evidence. The benchmark can show the query is fast in practice; it cannot, by itself, confirm that the cost model's assumptions held, or that the estimate's asymptotic shape (how cost would grow if the table were ten times larger) is correct — because the benchmark was run at one table size, with one specific data distribution, and never varied the exact quantity the cost model made a claim about.

EraRAG's Theorem 4 and its accompanying experiments sit in exactly this relationship. The theorem is a cost-model-style asymptotic claim; the experiments are a benchmark suite. Precisely locating the gap between them means identifying, term by term, which parts of the theorem's claim the experiments actually exercise, and which parts they never touch.

### Recap: the theoretical-bound-versus-measured-curve distinction

Recall that a theoretical bound and an empirically measured curve are different kinds of evidence: a bound is a claim about how a cost scales under stated assumptions, proven by reasoning about the algorithm's structure independent of any particular hardware or dataset, while a measured curve is an empirical record of what actually happened under one specific set of conditions. A measured curve can be consistent with a theoretical bound without confirming it, because the curve was only ever produced at the specific parameter values the experiment happened to use — it says nothing about what would happen outside that narrow window unless the experiment was specifically designed to vary the quantity the bound makes a claim about.

### Restating what Theorem 4 actually claims

Theorem 4 states that handling $\Delta$ newly arriving chunks against a graph already holding $|C|$ chunks costs $T_{update}(\Delta) = O(\Delta(nd + S_{LLM}))$, where $d$ is the embedding dimension, $n$ the number of stored hyperplanes, and $S_{LLM}$ the cost of one LLM summarization call — conditional on the assumption that the bucket-size bounds satisfy $1 < S_{min} \le S_{max} = O(1)$. The single most important, checkable feature of this bound is what is *absent* from the right-hand side: $|C|$ does not appear. The entire justification for EraRAG's incremental-update design — that it avoids the full-graph-reconstruction cost that competing systems pay — rests on this specific claim: update cost depends only on the size of the incoming batch, not on how large the existing graph has already grown.

### What the experiments actually report

The paper's dynamic-update evaluation splits each dataset into an initial 50% and ten sequential 5% increments, then reports, per dataset, the cumulative token consumption and cumulative graph (re)construction wall-clock time accumulated across all ten rounds, compared against baselines that perform a full rebuild at every round. A second experiment performs one single insertion — one entry, split into two chunks — into a graph already built from 50% of a corpus, and reports the wall-clock time and token cost of that one update in isolation, again compared against baselines. A third experiment varies the segment-size tolerance $\delta$ across five settings and reports the resulting accuracy, total token cost, and total rebuild time for the same 50%-plus-ten-increments pipeline. A fourth, more granular measurement breaks down the time spent on re-summarization, embedding updates, and signature updates at each of four layers during one update, finding that re-summarization consumes roughly 98–99% of the time at every layer.

### Locating the gap precisely

**Gap 1 — the theorem's own variables are never reported.** $n$, $S_{min}$, $S_{max}$, $L$, and the token budget $T$ are free parameters in the theorem's statement, and the assumption $S_{max} = O(1)$ is the load-bearing premise of the entire bound. None of these values are given as concrete numbers used in the experiments. A reader cannot check whether $S_{max}$ was actually held constant in the deployed system, what constant it was held at, or how $L$ was chosen — the theorem's central assumption is simply unverifiable against the reported results.

**Gap 2 — the experiments never isolate the variable the theorem makes a claim about.** The theorem's claim is that cost is independent of $|C|$. The flagship dynamic-update experiment does implicitly vary $|C|$ across its ten rounds — but it reports a single cumulative total per dataset rather than a per-round breakdown showing marginal update cost at round 1 versus round 10. The one experiment that isolates a single update (the one-entry insertion into MultihopRAG) does so at exactly one fixed value of $|C|$ (50% coverage), so it cannot show whether that single update's cost would look the same at 10% or at 90% coverage. Nowhere in the paper is $\Delta$ held fixed while $|C|$ is swept across a range specifically to plot the curve Theorem 4 predicts should be flat.

```mermaid
flowchart TD
    A[Theorem 4 claim: T_update depends on Delta, not on |C|] --> B{Did any experiment hold Delta fixed and vary |C|?}
    B -- No --> C[Dynamic-update experiment: cumulative totals across 10 rounds, not a per-round marginal curve]
    B -- No --> D[Single-insertion experiment: one Delta, one fixed |C|, no sweep]
    C --> E[Gap: independence from |C| never directly plotted]
    D --> E
```

**Gap 3 — the comparison actually run answers a different question than the theorem asks.** The reported 57.6% token reduction and 77.5% time reduction against RAPTOR are *relative* claims: selective update costs less than a competitor's full rebuild. That is a real, useful, and separately defensible result — but it is not the same claim as Theorem 4's *absolute* scaling claim that EraRAG's own update cost stays flat in $|C|$. A system whose update cost grows with $|C|$, just more slowly than a full rebuild's cost grows, would produce exactly the same relative-improvement numbers reported here. The experiment as designed cannot distinguish "EraRAG's cost is $O(\Delta)$, independent of $|C|$" from "EraRAG's cost grows with $|C|$, but sub-linearly compared to a full rebuild" — both hypotheses predict the same qualitative pattern in the reported figures.

**Gap 4 — wall-clock seconds are a noisy proxy for the theorem's $S_{LLM}$ term, not a measurement of it.** The theorem treats $S_{LLM}$ as a fixed per-call constant. The experiments report real wall-clock seconds produced by one specific backbone LLM (Llama-3.1-8B-Instruct-Turbo) and one specific embedding model (BGE-M3), quantities that in practice vary with prompt length, batching, and serving load rather than behaving as a fixed constant. No error bars, variance, or repeated-seed results are reported anywhere in the paper's efficiency experiments, so there is no way to tell how much of the measured time reflects the algorithm's structure versus incidental noise in LLM serving latency on the day the experiment ran.

**Gap 5 — the retrieval-quality experiments are a genuinely separate claim, not evidence either way for Theorem 4.** The paper's incremental accuracy-and-recall curves (showing quality converging toward a fully rebuilt graph's performance as insertions proceed) test something Theorem 4 says nothing about at all — the theorem is purely a cost bound, silent on retrieval correctness. This is worth stating precisely so it is not mistaken for support: strong incremental-quality results cannot be read as indirect confirmation of the efficiency theorem, because they measure a different, orthogonal property of the system.

**Gap 6 — the one place the assumption is tested, it is tested only locally, not at its boundary.** The segment-size-tolerance experiment (varying $\delta$ across roughly a 0.5× to 2× range around a baseline) does show that looser bounds increase cost and can hurt accuracy, which is at least directionally consistent with wanting $S_{max}$ to stay small. But this experiment perturbs the bound by a small multiplicative factor around one working value — it never tests the actual alternative the theorem's assumption is designed to exclude, namely bounds that are allowed to grow with $|C|$ rather than staying $O(1)$. The boundary condition the proof depends on is never approached, let alone crossed, in the reported experiments.

```
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 340">
  <text x="320" y="26" font-size="15" font-weight="bold" text-anchor="middle" fill="#222">The Curve the Theorem Predicts vs. What Was Measured (svg_diagram)</text>

  <line x1="70" y1="280" x2="580" y2="280" stroke="#333" stroke-width="2" />
  <line x1="70" y1="280" x2="70" y2="60" stroke="#333" stroke-width="2" />
  <text x="320" y="308" font-size="12" text-anchor="middle" fill="#333">Existing corpus size |C|, at fixed batch size Delta</text>
  <text x="35" y="170" font-size="12" text-anchor="middle" fill="#333" transform="rotate(-90 35 170)">Update cost</text>

  <line x1="90" y1="220" x2="560" y2="220" stroke="#2f855a" stroke-width="3" />
  <text x="480" y="205" font-size="11" fill="#2f855a">Theorem 4 predicts: flat</text>

  <rect x="120" y="230" width="40" height="30" fill="#e6f0ff" stroke="#2b6cb0" />
  <text x="140" y="275" font-size="9" text-anchor="middle" fill="#1a365d">round 1</text>
  <rect x="220" y="150" width="40" height="110" fill="#e6f0ff" stroke="#2b6cb0" />
  <text x="240" y="275" font-size="9" text-anchor="middle" fill="#1a365d">round 5</text>
  <rect x="320" y="90" width="40" height="170" fill="#e6f0ff" stroke="#2b6cb0" />
  <text x="340" y="275" font-size="9" text-anchor="middle" fill="#1a365d">round 10 (?)</text>
  <text x="360" y="80" font-size="10" fill="#c53030">Never actually reported</text>
  <text x="360" y="93" font-size="10" fill="#c53030">this way per round</text>

  <text x="320" y="330" font-size="11" text-anchor="middle" fill="#555">Only cumulative totals across all rounds were published — the per-round shape needed to confirm or refute flatness was never shown.</text>
</svg>
```

### Convergence with independent critical readings

This gap has also been identified by outside technical review of the paper, which noted specifically that the proof assumes a single insertion perturbs only a constant number of segments per layer and that layer depth stays effectively constant, and separately observed the absence of reported values for $n$, $S_{min}/S_{max}$, $L$, and $T$, along with the lack of error bars or repeated seeds across the efficiency experiments. That review recommended adding a same-method control — EraRAG's own selective update measured against EraRAG's own full rebuild, rather than only against competing systems' full rebuilds — as the specific experiment that would isolate the mechanism's actual contribution from the general advantage of not rebuilding at all. This converges with the analysis above: the missing experiment in both cases is the one that would directly plot cost as a function of $|C|$ at fixed $\Delta$, using EraRAG against itself, with its own governing parameters reported.

**Key Points**
- Theorem 4's most consequential claim is what it omits: update cost has no dependence on $|C|$, the existing graph size — this is the specific, checkable content the whole incremental-update design is justified by.
- The experiments report cumulative totals across ten insertion rounds and single-point measurements at one fixed corpus size, neither of which plots update cost as a function of $|C|$ at fixed batch size, so the theorem's central claim is never directly exercised.
- The headline efficiency comparisons (EraRAG versus full-rebuild baselines) answer a relative question — selective update beats full rebuild — that is compatible with, but does not confirm, the absolute scaling claim the theorem makes.
- The theorem's own free variables ($n$, $S_{min}$, $S_{max}$, $L$, $S_{LLM}$) are never reported as concrete values, and wall-clock seconds from a specific LLM backbone are a noisy, unvalidated proxy for the theorem's idealized $S_{LLM}$ constant.
- The retrieval-quality experiments and the segment-size-tolerance experiment are genuine, useful measurements, but neither one tests the specific boundary condition ($S_{max}$ growing with $|C|$) that the theorem's proof explicitly assumes away.

**Related Topics**
- Designing a controlled experiment that sweeps $|C|$ at fixed $\Delta$, with explicit reporting of $n$, $S_{min}$, $S_{max}$, and $L$, to directly test Theorem 4's independence claim
- Distinguishing relative efficiency claims (beats a baseline) from absolute scaling claims (this specific asymptotic bound holds) in systems papers generally
- Applying the same theory-versus-measured-curve gap analysis to the other four named mechanisms this thesis builds on
- Using repeated trials and reported variance to distinguish algorithmic cost from LLM-serving-latency noise in future incremental-KG benchmarks
- Formal potential-function techniques that could tighten Theorem 4's proof at the specific step flagged as informal, connecting back to this chapter's earlier treatment of the theorem's internal argument