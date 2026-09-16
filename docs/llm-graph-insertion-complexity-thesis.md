# Thesis Proposal: An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction

*(working title — open to revision)*

## 1\. Background

Large language models are increasingly used to construct knowledge graphs incrementally — extracting entities and relations from a document stream and inserting them into a growing graph one unit at a time, rather than constructing the whole graph in one pass. This incremental setting introduces a recurring subproblem: when a new candidate node arrives, the system must decide whether and where it connects to the existing graph. The naive approach — comparing the new node against every existing node — does not scale, and multiple published systems explicitly acknowledge this as a limitation.

Several strategies have been proposed across the literature to avoid this brute-force comparison, but each has been developed and evaluated in isolation, within a single paper's own pipeline. No existing work directly compares these strategies against one another as the underlying graph grows in size. This proposal identifies that gap and proposes to close it empirically.

## 2\. Related work

Two previously separate bodies of literature converge on this problem:

**General-purpose incremental LLM-driven knowledge graph construction:**

- Funk et al. \[1\] explicitly name the scalability problem of brute-force comparison and propose a tree-search-based insertion algorithm (KRIS). They also document a concrete failure of LLM subsumption judgments to behave transitively (e.g., the model affirms Healthcare Facilities ⊒ Hospitals and Commercial Building ⊒ Healthcare Facilities, but denies Commercial Building ⊒ Hospitals), and work around this by assuming transitivity rather than verifying it.  
- iText2KG \[2\] uses a fixed cosine-similarity threshold (0.6 ± 0.12, fit once against a GPT-4-generated dataset) to narrow candidates before LLM-based entity matching. The paper explicitly names, as future work, "eliminating the necessity to define a threshold as a hyperparameter" — this is a stated open problem, not an inference on our part.  
- SAC-KG \[3\] uses a fine-tuned Pruner classifier to decide expand-or-stop per node at million-node scale (89.32% precision), the closest published mechanism to an automated, learned growth decision.  
- DIAL-KG \[4\] is the most architecturally advanced system found. Its own ablation study shows coreference alignment is the single point of failure for change tracking: removing it collapses Deprecation-Handling Precision (D-HP) from 0.985 to 0.322 — attributed to entity fragmentation without it — while removing other components (Evolution-Intent Assessment or event representation) instead eliminates deprecation-handling capability entirely (D-HP undefined) rather than merely degrading it. This indicates that correctly resolving which existing entity a new mention refers to, specifically, is the load-bearing mechanism for reliable incremental graph maintenance.  
- **EraRAG** \[5\] is the closest existing work to this proposal and serves as its anchor. It proves **Theorem 4**: an amortized insertion cost of O(Δ(nd \+ S\_LLM)) per update, via a bounded-bucket-size argument in the style of B-tree/LSM-tree amortized analyses, where |C| is the existing chunk count, Δ the batch size being inserted, d the embedding dimension, n the number of hyperplanes, and S\_LLM the cost of one LLM summarization call. This theorem has been verified directly against the paper. Critically, EraRAG's own experimental section varies the *batch* being inserted while holding the *existing* corpus size roughly constant across runs — it never empirically plots insertion cost as a function of total existing graph size, despite proving a bound that predicts exactly that relationship. This is the precise gap this thesis operationalizes.

**Education-side concept/prerequisite-graph construction** (adjacent, not the focus of this thesis, but relevant to the evaluation-design discussion below): ACE \[6\] constructs prerequisite graphs using embedding-based ranking with human adjudication. Its own reported numbers show LLMs and embeddings trade off precision against recall (LLM-based: 87% precision / 61% recall; embedding-based: 46% precision / 100% recall) — nobody in that literature combines the two adaptively. ACE is notable for this proposal chiefly because it (a) released real gold-standard graphs (Metacademy, 141 nodes; a Data Structures & Algorithms graph, 29 nodes) and (b) explicitly acknowledges its own lack of independently-verified ground truth as an evaluation weakness — a consideration directly relevant to how this thesis selects its evaluation set (see Section 5).

**Confirmed absence of prior comparison:** A cross-strategy empirical comparison of candidate-narrowing methods for LLM-driven graph insertion was searched for from four independent angles — the LLM-KG construction literature, classical incremental-algorithms literature, ANN/vector-search literature, and graph-LLM-benchmarking literature — and found nowhere. Every ablation located tests components within one paper's own pipeline against removed-component variants of itself; none benchmark independently-implemented alternative strategies against each other under a shared harness and shared metrics.

Separately, classical algorithms research already provides mature amortized-cost proof techniques for structurally similar problems — incremental Voronoi diagrams \[7\] (O(√n) amortized), incremental minimum spanning trees \[8\] (O(log n) amortized), updatable learned indexes, and streaming approximate-nearest-neighbor graph construction (HNSW \[9\], Slipstream \[10\]). These confirm the analytical tools this thesis would need already exist; they have simply not been applied to LLM-driven graph insertion specifically.

## 3\. Research question

As an LLM-constructed graph grows from small to large (e.g., n \= 50 to n ≥ 2000 nodes), how do different candidate-narrowing strategies for inserting a new node actually behave — in computational cost and in placement quality — and does their empirical behavior match the theoretical predictions where a theoretical bound exists (as it does for the bucket-capped strategy, per EraRAG's Theorem 4)?

## 4\. Proposed strategies under comparison

| \# | Strategy | Basis |
| :---- | :---- | :---- |
| 1 | Brute-force | Control condition; matches the scalability limitation Funk et al. (2023) name explicitly |
| 2 | Embedding-threshold narrowing | Current published practice (iText2KG); still O(n) per insertion, a distinction not clearly flagged in existing literature |
| 3 | ANN index (FAISS/HNSW) | Sub-linear candidate retrieval before LLM decision |
| 4 | Bucket-capped / tree structure | EraRAG-style; the only strategy with a proven amortized-cost theorem to test empirically |

## 5\. Methodology

- **Independent variable:** narrowing strategy (4 levels, above) and graph size (log-spaced checkpoints, e.g., n \= 50, 100, 200, 500, 1000, 2000+, chosen to make polynomial-vs-logarithmic growth differences visible while keeping LLM API costs bounded).  
- **Dependent variables, measured at each checkpoint per strategy:**  
  - Wall-clock time per insertion  
  - LLM API call count per insertion (isolates raw LLM latency from algorithmic call-count inefficiency)  
  - Placement accuracy against a gold-standard reference (does the new node connect to the correct existing neighbors?)  
- **Gold-standard evaluation set — open decision, presented here for guidance:**  
  - *Option A: reuse existing structured data with known ground truth* — e.g., Wikipedia category subgraphs, WordNet/DBpedia subsets, or ACE's own released gold graphs (Metacademy, DSA). Lower manual effort, stronger provenance, and directly sidesteps the ground-truth weakness ACE's own paper admits to.  
  - *Option B: construct a small hand-labeled evaluation set.* Full control over domain and difficulty, at the cost of more upfront manual annotation work and a self-constructed (rather than externally validated) ground truth.  
  - We would appreciate your input on which direction is preferable, or whether a hybrid (e.g., reuse for the main results, hand-labeled for an edge-case stress test) makes sense.

## 6\. Why the comparative design is defensible regardless of outcome

Testing a single strategy in isolation risks an unsurprising, hard-to-defend result. Testing four strategies against each other under identical conditions converts that risk into a source of contribution either way: convergent results despite differing theoretical guarantees is itself a finding; divergent results matching theoretical predictions produce an actionable, evidence-based recommendation for practitioners. The only outcome that would fail to defend is running no comparison at all — which is the current state of the literature.

## 7\. Scope note

This thesis is scoped as a pure computer-science/algorithms contribution. It does not require an educational-domain framing, despite drawing several source papers from education-side concept-graph literature; those are cited for their relevant findings (evaluation methodology, precision/recall tradeoffs) rather than as the application context.

## 8\. Proposed next steps

1. Finalize the gold-standard corpus decision (Section 5\) — pending your input.  
2. Implement Strategies 1 and 2 first, and validate the full measurement harness end-to-end at small scale (n \= 50, 100).  
3. Add Strategies 3 and 4 once the harness is validated.  
4. Run the full graph-size sweep across all four strategies and all three metrics; analyze against the EraRAG Theorem 4 prediction specifically for Strategy 4\.

## Questions for discussion

- Preference between Option A and Option B (Section 5), or a hybrid?  
- Is the proposed graph-size range (50–2000+) appropriate given available compute/API budget, or should it be adjusted?  
- Any concerns about scoping this as a pure-CS contribution versus retaining an applied framing?

&nbsp;

## References

\[1\] M. Funk, S. Hosemann, J. C. Jung, and C. Lutz, "Towards ontology construction with language models," presented at the Workshop on Knowledge Base Construction from Pre-Trained Language Models (KBC-LM) / LM-KBC, co-located with ISWC 2023, arXiv:2309.09898, 2023\.

\[2\] Y. Lairgi, L. Moncla, R. Cazabet, K. Benabdeslem, and P. Cléau, "iText2KG: Incremental knowledge graphs construction using large language models," in *Proc. 25th Int. Conf. Web Information Systems Engineering (WISE 2024\)*, arXiv:2409.03284, 2024\.

\[3\] H. Chen, X. Shen, Q. Lv, J. Wang, X. Ni, and J. Ye, "SAC-KG: Exploiting large language models as skilled automatic constructors for domain knowledge graphs," in *Proc. 62nd Annu. Meeting Assoc. Comput. Linguistics (ACL 2024), Volume 1: Long Papers*, Bangkok, Thailand, Aug. 2024, pp. \[see ACL Anthology 2024.acl-long.238\].

\[4\] W. Bao, Y. Wang, R. Gao, F. Leng, Y. Bao, and G. Yu, "DIAL-KG: Schema-free incremental knowledge graph construction via dynamic schema induction and evolution-intent assessment," accepted to *25th Int. Conf. Database Systems for Advanced Applications (DASFAA 2026\)*, arXiv:2603.20059, 2026\.

\[5\] F. Zhang, Z. Huang, Y. Zhou, Q. Guo, Z. Li, W. Luo, D. Jiang, Y. Fang, and X. Zhou, "EraRAG: Efficient and incremental retrieval augmented generation for growing corpora," arXiv:2506.20963, 2025\.

\[6\] M. C. Aytekin and Y. Saygın, "ACE: AI-assisted construction of educational knowledge graphs with prerequisite relations," *Journal of Educational Data Mining*, vol. 16, no. 2, pp. 85–114, 2024\. doi: 10.5281/zenodo.14250896.

\[7\] \[Classical result — incremental Voronoi diagram construction with amortized-cost analysis. Specific canonical source not yet pinned; recommend confirming exact citation before submission.\]

\[8\] \[Classical result — incremental minimum spanning tree maintenance with amortized-cost analysis. Specific canonical source not yet pinned; recommend confirming exact citation before submission.\]

\[9\] Y. A. Malkov and D. A. Yashunin, "Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs," *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 42, no. 4, pp. 824–836, 2020\. \[HNSW — recommend verifying this citation directly before submission; sourced from general knowledge, not independently searched this session.\]

\[10\] \[Slipstream — streaming ANN graph construction. Specific canonical source not yet pinned; recommend confirming exact citation before searching/submission.\]