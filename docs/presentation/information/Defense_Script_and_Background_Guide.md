# Defense Script and Background Guide

*An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction*

Adrian Luke A. Labasan · Alejandrei Jazz F. Lopez · Geila May C. Rigayen · Melvie Jeanna O. Abad

## How to use this guide

Every slide has two parts: a **Script** you can say almost word for word, and **Background**, the concepts you need to understand so you can answer follow-up questions. Scripts are written for a calm pace of about 130 words a minute. All numbers come from the deck and from Chapter 4 of the thesis, so quote them exactly as they appear.

**Naming.** Slides 15–17 and 22 use Strategies A–D, while Chapters III and IV use S1–S4. They are the same strategies: A = S1 brute force, B = S2 embedding threshold, C = S3 ANN retrieval, D = S4 bounded bucket.

**Four messages every presenter repeats**

1. We measure one insertion at a time. We do not test amortized cost over a sequence of insertions.
2. Only the narrowing step differs between strategies. The LLM decision step is identical, so differences come from narrowing.
3. Results are descriptive: one run per configuration, 10 trials per size, no hypothesis tests.
4. The classification and ranking of the strategies was defined after the results were available (post hoc).

## Two things to fix or phrase carefully before presenting

- **Model name (slides 22 and 24).** The figure on slide 22 says “DeepSeek V4 Flash”, but slides 24 and 30 and the thesis (Section 3.3.6) say DeepSeek V3, called through the alias deepseek-flash (which resolves to deepseek-chat). Fix the figure, or say “DeepSeek, through its official API under the alias deepseek-flash” and do not read out a version number.
- **Funk et al.’s 22–50 prompts (slides 6 and 15).** In thesis Section 2.3.1 this figure comes from Funk et al.’s own KRIS-style insertion algorithm, which already prunes the search. It is a published cost benchmark, not a measured brute-force cost. Brute force itself needs n calls. Say it that way if asked, because Chapter 1 of the thesis words it more loosely.

## Who presents what

| Member | Slides | Part | Approx. time |
| --- | --- | --- | --- |
| Member 1 | 1–17 | Opening, Chapter I, Chapter II | about 16 min |
| Member 2 | 18–27 | Chapter III, Methodology | about 16 min |
| Member 3 | 28–34 | Chapter IV: data collected, setup, RQ1, RQ2 | about 13 min |
| Member 4 | 35–42 | Chapter IV: RQ3, RQ4, limits, summary, closing | about 13 min |

Member numbers are not tied to any person, so assign them however the group likes. The total is roughly an hour at a calm pace. If time is short, drop the optional asides in the scripts, not the key numbers.

---

# Member 1 (Slides 1–17)

### Slide 1: Cover (about 0.5 min)

**Script**

“Good day to the members of the panel, our adviser, and everyone present. We are from the College of Computing and Information Sciences of Mariano Marcos State University. Our study asks a simple question about knowledge graphs that keep growing: when one new concept arrives, how much work does it take to connect it to the graph, and does that work grow as the graph grows? I am \[say your full name\], and my groupmates and I will take you through the study in four parts.”

**Background**

- Nothing technical here. Know the names of the panel members and the adviser so you can greet them correctly, and adjust the greeting if the panel differs from the one in the thesis acknowledgements.
- Be able to give the whole study in one sentence: we measure how the cost and accuracy of adding one concept to an LLM-built graph change with graph size, under four ways of shortlisting candidates.

### Slide 2: Title and members (about 0.5 min)

**Script**

“The title of our study is *An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction*. In plain words: we measured, rather than proved, how the cost of adding one new concept to a graph built with a Large Language Model changes as the graph gets bigger, and we compared four ways of shortlisting which existing concepts the model has to look at. The researchers are Adrian Luke Labasan, Alejandrei Jazz Lopez, Geila May Rigayen, and Melvie Jeanna Abad.”

**Background**

- **Empirical:** based on measurements from experiments, not on a mathematical proof.
- **Complexity analysis:** studying how cost grows with input size. Linear means cost grows in proportion to size (double the graph, double the cost). Constant or flat means cost stays about the same however large the graph gets.
- **Candidate narrowing:** shrinking the list of existing nodes to a short list worth checking.
- **Incremental:** adding one node at a time to a graph that already exists, as opposed to building the whole graph in one batch.
- **LLM-driven:** a Large Language Model decides the relationship between concepts.

### Slide 3: Chapter I, Introduction (about 0.5 min)

**Script**

“Chapter I introduces the problem. We will cover what a knowledge graph is, why adding to one is costly, what existing work has done, and the two gaps this study fills.”

**Background**

- Roadmap of the whole talk: Chapter I is the problem, Chapter II is the literature, Chapter III is the methodology, and Chapter IV is the initial results.

### Slide 4: Background of the Study (about 1 min)

**Script**

“A graph is made of nodes connected by edges. A knowledge graph uses that idea for ideas themselves: each node is a concept, and each edge is a relationship. For example, Calculus requires Limits. Knowledge graphs are used in web search, recommendation systems, and increasingly in education. In the past, domain experts built them by hand. That is accurate, but it does not scale. Today, Large Language Models can read text and extract concepts and relationships automatically, and that is why this area is growing so quickly.”

**Background**

- **Node and edge.** A road network is a graph where cities are nodes and roads are edges. In a knowledge graph the nodes are concepts and the edges are relationships.
- **Prerequisite graph.** Ours is an educational graph. An edge says that one concept must be understood before another (Limits before Calculus).
- **LLM.** An AI model trained on large amounts of text that can be prompted to judge whether two concepts are related.
- **Three stages of automated construction** (thesis Section 1.1): ontology engineering (what kinds of concepts and relations matter), knowledge extraction (pull candidates from text), and knowledge fusion (merge them into one non-redundant graph). Inserting a new concept is closest to the third stage.

### Slide 5: The problem: knowledge keeps growing (about 1 min)

**Script**

“Most systems build the graph once, in a single batch. But knowledge keeps growing: a course adds a new topic, or a field publishes a new technique. Rebuilding the whole graph for one new concept is wasteful. So the real question is what we call the incremental insertion problem: how do we connect one new concept to an existing graph without re-checking every node?”

**Background**

- **Batch versus incremental.** Batch means the LLM sees the whole corpus and produces a complete graph in one pass. Incremental means one new item arrives after the graph already exists.
- **Notation.** n is the number of nodes already in the graph. After insertion the graph has n + 1 nodes. We use n throughout the talk.
- **What insertion means here:** deciding which existing nodes the new concept links to, and in which direction.
- **Why re-checking is expensive:** every check is an LLM call, which costs time and money.

### Slide 6: Why brute force doesn’t work (about 1 min)

**Script**

“The obvious method is brute force: ask the LLM to compare the new concept with every existing node. Funk and colleagues describe this as needing, in their words, ‘a huge number of queries’. Even their own pruned insertion algorithm needed 22 to 50 LLM prompts per concept, at a cost of 11 cents up to 12 dollars and 45 cents depending on the domain. Brute force on a graph of n nodes needs n calls, so the larger the graph, the worse it gets.”

**Background**

- **Funk et al. \[1\]**, “Towards ontology construction with language models” (2023). They insert concepts into a hierarchy using an algorithm adapted from KRIS, a classical description-logic method for testing subsumption (“is X a kind of Y?”). It searches the hierarchy top-down and bottom-up and prunes branches. Results were averaged over nine domains.
- **Careful:** the 22–50 prompts figure is from their pruned algorithm. It is a cost benchmark, not a brute-force measurement.
- **Linear cost:** n calls for n nodes. Doubling the graph doubles the calls.
- Funk et al. also found that LLM subsumption judgments were not transitive (A in B and B in C, but not A in C) and simply assumed transitivity. That is a known open issue outside our scope.

### Slide 7: The solution: candidate narrowing (about 1 min)

**Script**

“The fix is candidate narrowing. Step one: use a cheap method, such as embeddings, to shortlist the likely candidates. Step two: use the expensive LLM only on that shortlist. Three existing systems shaped our study. iText2KG keeps only nodes whose cosine similarity passes a threshold of about 0.6. SAC-KG uses learned pruning and was tested at over one million nodes. EraRAG groups nodes into size-bounded buckets, and its authors prove that insertion cost should not grow with graph size.”

**Background**

- **Embedding:** a list of numbers that represents the meaning of a text, built so that similar meanings give similar vectors. **Cosine similarity** measures the angle between two vectors: higher means more similar.
- **iText2KG \[2\]:** an incremental construction system. Its threshold of about 0.6 (standard deviation 0.12) was calibrated on 1,500 GPT-4-generated similar-entity pairs. The authors list removing the threshold as a hyperparameter as future work, which motivates our ANN strategy.
- **SAC-KG \[3\]:** a Generator proposes relations, a Verifier checks them, and a Pruner decides whether a branch keeps growing. It reached over one million nodes at 89.32% precision.
- **EraRAG \[4\]:** uses random hyperplanes to hash vectors into buckets of capped size. Its Theorem 4 gives an amortized cost of O(Δ(bd + S\_LLM)): Δ new items, b hyperplanes, d embedding dimension, S\_LLM the cost of one LLM call. Informally, an insertion should not get costlier just because the graph is bigger.
- **Analogy:** screening résumés first, then interviewing only the shortlist.

### Slide 8: The research gaps (about 1 min)

**Script**

“Reading this literature, we found two gaps. First, none of the studies we reviewed measures insertion cost as a function of graph size. Costs are reported in aggregate, such as total dollars or total time for an entire experiment. Second, none compares narrowing strategies against each other under the same task and the same measurements. Each system is tested only against generic baselines. Those two gaps are what this study addresses.”

**Background**

- **Aggregate versus scaling cost.** “Total tokens for the whole experiment” does not tell you what one insertion costs at 50 nodes versus at 2,000 nodes.
- **EraRAG’s experiments** hold the starting corpus at a fixed 50% and vary only the size of the incoming batch. They never vary the size of the graph being inserted into, so even a proven bound has not been shown to hold as the graph itself grows.
- **Honest scope:** these gaps come from a structured but non-exhaustive literature search. Say “none of the studies we reviewed”, not “nobody has ever”.

### Slide 9: Statement of the Problem (about 1 min)

**Script**

“Our central question is: how can a new concept be added to an LLM-built knowledge graph without checking every existing node? It breaks into four research questions. RQ1: how do time and LLM calls per insertion change as the graph grows? RQ2: does placement accuracy hold up as the graph grows? RQ3: how do the four strategies compare under identical conditions? RQ4: does the cost of a single insertion stay flat under a bucket-capped strategy?”

**Background**

- The four questions map, in order, to four unresolved issues: cost, accuracy, comparison, and the gap between a theoretical claim and its empirical premise.
- **Cost** means two measurements: wall-clock time per insertion and the number of LLM calls per insertion.
- **Placement accuracy** means how well the inserted node’s links match an expert-verified gold-standard graph, using precision, recall and F1.
- **Bucket-capped** means the strategy only ever compares the new concept with the members of one bounded bucket, so the shortlist has a fixed maximum size.
- RQ4 tests only the premise behind EraRAG’s amortized bound, not the amortized bound itself.

### Slide 10: Objectives of the Study (about 1 min)

**Script**

“The general objective is to characterize and compare the cost and accuracy of narrowing strategies as the graph grows. Specifically, we implement four strategies: brute-force LLM comparison, embedding-similarity thresholding, approximate nearest-neighbor retrieval, and bounded-bucket partitioning. We run insertions on graphs from 50 to 2,000 nodes, measure time, LLM calls and accuracy, test whether bucket-capped cost stays flat, and release a reproducible codebase and dataset.”

**Background**

- **Log-spaced sizes:** 50, 100, 200, 500, 1,000, 2,000. Spacing roughly by multiples lets us see whether cost follows a straight line, a curve, or a flat line across a 40-fold range.
- **Objective 4** says the study tests whether cost stays flat, consistent with the premise of the amortized bound. It does not test amortization itself.
- **Reproducible artifact:** the code and datasets let future researchers rerun and extend the experiment.

### Slide 11: Significance of the Study (about 0.75 min)

**Script**

“This study matters to three groups. To the field of Computer Science, it provides an empirical benchmark comparing several insertion strategies under identical conditions across graph sizes. To future researchers, it checks whether theoretical cost claims hold up in practice and gives a base for testing new strategies, domains, and limits. To practitioners building knowledge-graph systems, it helps choose a narrowing strategy that fits their expected graph size and update frequency.”

**Background**

- The benchmark is new in the sense that, among the studies we reviewed, none compares multiple narrowing strategies side by side as a function of graph size.
- “Validates theoretical cost claims” is limited: we check the premise (bounded work per single insertion), not the full amortized proof.
- A practical reading: if your graph will stay small, brute force may be tolerable. If it will grow, the flat strategies matter.

### Slide 12: Scope of the Study (about 1 min)

**Script**

“We focus only on the incremental insertion phase: adding one new node to an existing graph. We do not propose a new batch-construction method. We cover four strategies: brute force, embedding threshold, ANN, and bounded bucket. For data, we use two gold-standard graphs, Metacademy with 141 concepts and DSA with 29 concepts, for accuracy, and synthetic concept names up to about 2,000 nodes for cost scaling. We measure wall-clock time per insertion, LLM calls per insertion, and placement accuracy as precision, recall, and F1.”

**Background**

- **Gold standard:** a graph verified by domain experts, released by Aytekin and Saygın \[6\], \[7\]. Metacademy covers machine learning, statistics and linear algebra. DSA covers data structures and algorithms.
- **Why two data sources:** accuracy needs a known right answer, which only the gold graphs give (at 29 and 141 nodes). Cost can be measured on any graph, so synthetic names let us scale to 2,000 nodes.
- **Precision** is the share of predicted links that are correct. **Recall** is the share of true links that were found. **F1** combines the two.

### Slide 13: Limitations of the Study (about 1 min)

**Script**

“We want to be upfront about the limits. Concepts are represented by bare names only, with one model and one fixed prompt. The synthetic concepts are unverified, so they are used for cost only. Parameters are fixed, and no thresholds stricter than 0.6 were tested. We test single insertions, not amortized cost. There is one run per configuration and 10 trials per size, with no hypothesis tests. Accuracy is measured at only two graph sizes. And the ranking framework was defined after the results.”

**Background**

- **Bare names:** no definitions or text per node, so accuracy depends on what the model already knows. A pilot on DSA set a baseline of micro F1 0.541 for this setup.
- **No hypothesis tests:** with single runs and 10 trials per size, we describe results with bootstrap intervals and do not claim statistical significance.
- **Single, un-amortized insertion:** we cannot confirm or reject EraRAG’s amortized bound, only its premise.
- **Post hoc ranking:** gates and weights were fixed after seeing results, so the classes label these measurements and are not statistical findings.

### Slide 14: Chapter II, Review of Related Literature (about 0.5 min)

**Script**

“Chapter II reviews the related literature. For each strategy and method we use, we show what the source says and why it matters to this study.”

**Background**

- Chapter II follows the same order as the strategies: brute force, embedding thresholding, ANN retrieval, bounded buckets. It then covers how to measure cost and accuracy, amortized analysis, and the Philippine research context.

### Slide 15: Related literature, part 1 (about 1.5 min)

**Script**

“This table links each source to its role in our study. Funk and colleagues show that comparing a new concept with every node needs too many LLM calls, so brute force is our control condition, and their 22 to 50 prompts is our cost benchmark. iText2KG uses a cosine threshold, which is the basis for Strategy B at 0.6, and its threshold problem motivates a count-based alternative. HNSW and FAISS give us top-k retrieval, the basis for Strategy C, which needs no similarity cutoff. EraRAG gives us size-bounded buckets, the basis for Strategy D, and its theorem is the claim whose premise we test. Finally, SAC-KG shows automated construction working at over a million nodes, which makes a 2,000-node sweep realistic.”

**Background**

- **HNSW \[10\]** (Malkov and Yashunin): a layered proximity graph searched greedily from the coarse top layer down to the fine bottom layer. It is approximate, so it can occasionally miss a true nearest neighbor. **FAISS \[11\]** (Johnson, Douze, Jégou) is the widely used library that implements it.
- **Top-k versus threshold.** A threshold keeps everything above a similarity value, so the shortlist size varies. Top-k keeps a fixed number, so the shortlist size is fixed.
- **Control condition:** the baseline everything else is compared against.
- The 22–50 prompts figure comes from Funk et al.’s pruned algorithm (see the note at the top).

### Slide 16: Related literature, part 2 (about 1.5 min)

**Script**

“The second table covers evaluation and context. ACE and the Metacademy and DSA gold graphs give us ground truth for accuracy. Pareto dominance, the weighted-sum model, TOPSIS and minimum-level gates support how we judge cost and accuracy together. Amortized analysis explains why single-insertion tests cannot confirm an amortized bound. EraRAG’s experiments varied the incoming batch size, not the graph size, which is the gap we fill. Last, public datasets make our work reproducible, and we found no local study on incremental insertion, which supports novelty.”

**Background**

- **ACE \[6\]** (Aytekin and Saygın): builds educational prerequisite graphs with embeddings plus human experts. They found embeddings reach 100% recall but only 46.13% precision, while LLMs reach up to 87.23% precision but as low as 35.80% recall (zero-shot). That precision-recall trade-off helps us interpret our results.
- **Pareto dominance:** strategy A dominates B if A is at least as good on every criterion and better on at least one. **Weighted sum** combines normalized criteria with weights. **TOPSIS** ranks options by closeness to an ideal point. **Minimum-level gates** (from Simon’s satisficing idea) set pass or fail bars before any weighting, because a weighted sum is compensatory and can hide a terrible score behind a great one.
- **Amortized complexity:** cost averaged over a sequence of operations. For example, doubling a dynamic array is occasionally expensive but cheap on average.
- **Local context:** Balilo \[8\] found about 60% of capstone projects at Bicol University (2011–2019) were information systems. Naguio and Roxas \[9\] applied graph neural networks to Philippine lexical resources (113,557 words, 304,171 relations). Neither addresses incremental insertion. Our claim is limited by the scope of our search.

### Slide 17: Conceptual Framework (about 1.25 min)

**Script**

“Our framework follows input, process, output. The input is an existing graph of size n, from 50 to 2,000 nodes, one new concept, and a narrowing strategy: A brute force, B embedding threshold, C ANN retrieval, or D bounded bucket. In the process, the strategy reduces the graph to a candidate shortlist, a shared LLM decision step judges the relationship for each shortlisted candidate, and the graph is updated and measured. The output is an updated graph of size n plus one, with cost measured as time and LLM calls, and accuracy measured as precision, recall and F1 against the gold standard.”

**Background**

- The study rests on three foundations: **graph theory** (nodes and edges, structure and growth), **amortized algorithm analysis** (how to reason about cost over many operations), and **vector semantics** (similar meanings sit close together as vectors, so closeness can shortlist candidates).
- **Shared decision step:** the identical LLM judgment used by all four strategies, which is what lets us attribute differences to narrowing alone.
- Remember the letter-to-number mapping: A = S1, B = S2, C = S3, D = S4.

**Handoff:** “That is the problem and the literature behind it. My groupmate will now explain how we designed the experiment.”

---

# Member 2 (Slides 18–27)

### Slide 18: Chapter III, Research Methodology (about 0.5 min)

**Script**

“Chapter III explains how we designed the experiment: the data we used, the four strategies, the shared decision step, the procedure, and how we measure and judge the results.”

**Background**

- Roadmap of the chapter: research design, data sources, the pipeline and strategies, the decision step, the procedure, the analysis, and the post hoc ranking framework.

### Slide 19: Research Design (about 1 min)

**Script**

“Our design is developmental and experimental. It works like an algorithm benchmark: there are no human respondents and no surveys. We control two independent variables, the narrowing strategy and the graph size, and we measure two kinds of dependent variables: insertion cost, as time and LLM calls, and placement accuracy.”

**Background**

- **Independent variable:** what we deliberately change (strategy, graph size). **Dependent variable:** what we measure in response (time, calls, precision, recall, F1).
- **Algorithm benchmark:** run each algorithm under identical, repeatable conditions and record numbers. That is why the methodology has no sampling, respondents or instrument validity.
- **Developmental:** we built the working implementation, meaning the four strategies and the test harness, and released it as a reproducible artifact.

### Slide 20: Data Sources (about 2 min)

**Script**

“We use two kinds of data. For accuracy, we use gold-standard graphs: Metacademy with 141 concepts and DSA with 29 concepts, both with expert-verified prerequisite relationships. For each trial we withhold one concept, re-insert it with a strategy, and compare the result with the true answers. For cost, we use a synthetic pool of 2,254 unique computer science concept names generated with an LLM, used to build graphs from 50 up to 2,000 nodes. Because those names are not verified, we never use them for accuracy claims.”

**Background**

- **File format.** The gold files list nearly every ordered pair with a label. Metacademy has 19,740 pairs (141 × 140), of which 318 are positive. DSA has 54 distinct positive pairs. A label of 1 means the target concept is a prerequisite of the source concept.
- **Not transitively reduced.** 25.9% of DSA edges (14 of 54) and 33.0% of Metacademy edges (105 of 318) are implied by other edges. That is why the decision prompt accepts indirect prerequisites.
- **Leave-one-out.** Withhold one concept, keep the rest as the existing graph, insert the concept back, and compare its links with the true row. Repeat for different concepts.
- **Synthetic pool.** 80 computer science subfields were prompted (73 were reached), returning 2,922 names. After removing invalid names, 95 overlaps with the evaluation corpora, 542 duplicates and 29 singular/plural pairs, 2,254 remain. The generator was a different model family from the decision-step model, which reduces shared-vocabulary bias.
- **Why cost only.** Time and call counts do not need a correct graph. Accuracy does.

### Slide 21: Experimental Design (about 1 min)

**Script**

“Every insertion has the same shape. The input is one new concept and an existing graph. The narrowing step, which is different for each strategy, produces a shortlist of candidates. The decision step, which is identical for all four, has an LLM judge the new concept against each shortlisted candidate. Because only the narrowing step changes, any difference in the results comes from the narrowing method.”

**Background**

- **Controlled variable:** same model, same prompt, same temperature, same sequential call order for every strategy. That is the reason the comparison is fair.
- **Calls run one at a time** so the client’s own load does not distort latency.
- **What is timed:** from the start of the narrowing step to the end of the decision step for one insertion.
- Be ready for: “why not let each strategy use its own decision method?” Because then we could not tell whether differences come from narrowing or from the decision method.

### Slide 22: Research Design diagram (about 2 min)

**Script**

“This diagram shows one insertion from top to bottom. At the top are the inputs: the existing graph with n concepts, the new concept, and a subject-area label such as ‘data structures and algorithms’. Strategies B, C and D also use a small embedding model that runs on CPU. In the middle is the only part that differs: candidate narrowing. A uses every node, B uses nodes above 0.6 similarity, C uses the top 10 nearest neighbors, and D uses only the members of one bucket. Each strategy produces a candidate shortlist: n for A, between 0 and n for B, 10 for C, and at most 10 for D. Every shortlist goes into the same decision step: one LLM call per candidate, one at a time, at temperature 0, returning one of three labels. The output is the updated graph with n plus one concepts, plus the measurements for that insertion. The gold-standard graphs are used only for the accuracy trials.”

**Background**

- **Reading the labels.** X\_PREREQ\_Y means the new concept is a prerequisite of the candidate. Y\_PREREQ\_X means the candidate is a prerequisite of the new concept. NONE means neither.
- **Embedder.** all-MiniLM-L6-v2 is a small sentence-embedding model run locally on CPU with one thread, so the embedding times of B, C and D are comparable.
- **Fix before presenting.** The figure says “DeepSeek V4 Flash”, but the thesis (Section 3.3.6) and slide 24 say DeepSeek V3 under the alias deepseek-flash. See the note at the top of this guide.
- **Prompt v2** includes three worked examples and is held fixed for all runs.

### Slide 23: The Four Strategies (about 2 min)

**Script**

“Here are the four strategies and their worst-case cost. S1, brute force, is the control: it judges every existing node, so up to n calls. S2 keeps nodes whose cosine similarity is above 0.6, so its calls can go up to n, but often it finds none. S3 keeps the top 10 most similar nodes using a FAISS HNSW index, so at most 10 calls. S4 keeps only the members of the new concept’s bucket, between 5 and 10 nodes, so also at most 10 calls.”

**Background**

- **S1:** one call per existing node. Cost is exactly n.
- **S2:** cosine similarity must be strictly above 0.6. The shortlist may be empty, in which case no LLM call is made. It has no cap, so in the worst case it equals brute force. 0.6 was fixed beforehand following iText2KG, and 0.4 and 0.5 are sensitivity runs.
- **S3:** FAISS HNSW with M = 16, efConstruction = 200 and efSearch = 128, all fixed in advance. It is approximate, so it can occasionally miss a true nearest neighbor. The study records how often its results match the exact top 10. Sensitivity: k = 5 and 20, efSearch = 64 and 256.
- **S4:** hyperplane locality-sensitive hashing. Random hyperplanes turn each vector into a 12-bit code, and similar vectors tend to share codes. Codes are ordered along a Gray curve and grouped into segments (buckets) of 5 to 10 members. Oversize segments are split at the midpoint, and undersize ones are merged into the closest neighbor segment. 12 bits gives 4,096 possible codes, more than the 2,000-node maximum.
- **Honest caveat:** S3 and S4 both cap the shortlist at 10, so the comparison does not separate partitioning geometry from shortlist capacity.
- All parameters were fixed before any run and not tuned on the data.

### Slide 24: The Shared Decision Step (about 2 min)

**Script**

“The decision step is the same for every strategy. For each shortlisted candidate, we make one LLM call, one at a time. We call DeepSeek through its official API at temperature 0, with one fixed prompt. The input is only the two concept names plus a subject-area label, and the output is one of three answers: X is a prerequisite of Y, Y is a prerequisite of X, or none. Before comparing strategies, we ran a pilot with brute force on the DSA graph. It gave a micro F1 of 0.541 and recall of 0.611, which counted as a conditional pass. We kept the prompt unchanged and did not tune it further.”

**Background**

- **Model.** The thesis states it is DeepSeek V3, called through the alias deepseek-flash, with thinking disabled so no reasoning tokens are produced. The provider reports only the alias, so it could change the model behind it. This is a stated limitation. Timed runs were scheduled outside DeepSeek’s peak hours.
- **Bare names.** No definitions or text per node, so the model relies on what it already knows.
- **Prompt v2.** It adds three worked examples (fractions/ratios, calculus/limits, poetry/plumbing). A zero-shot version answered “X is a prerequisite of Y” on all six DSA probe pairs, which suggested position bias.
- **Pilot details.** Leave-one-out on 29 DSA concepts, 812 decisions: micro F1 0.541, recall 0.611, precision 0.485, direction-flip rate 15.38%, swap consistency 85.71%. Bars set beforehand: F1 at least 0.50, recall at least 0.70, flip rate at most 15%. F1 met the bar, recall fell below the pass bar but above the fail bar of 0.50, and the flip rate was just over 15%. The verdict was therefore conditional.
- **Why not keep tuning?** Tuning on the evaluation graph would make the later results look better than they are.
- 34 of the 58 false positives in the pilot are implied by the transitive closure of the gold graph, so precision is understated.

### Slide 25: Experimental Procedure (about 1.5 min)

**Script**

“We test graph sizes of 50, 100, 200, 500, 1,000 and 2,000, with one single insertion per trial and 10 trials per size. Accuracy runs use 59 trials: 29 on DSA and 30 on Metacademy. All parameters were fixed before running and were not tuned on the data. We also ran 8 one-at-a-time sensitivity settings: thresholds 0.4 and 0.5 for S2, k of 5 and 20 and efSearch of 64 and 256 for S3, and bucket bounds of (2, 5) and (10, 20) for S4. That gives 12 configurations in total, one run each.”

**Background**

- **Counts.** 6 sizes × 10 trials = 60 trials per sweep run. 29 + 30 = 59 trials per accuracy run. The 12 configurations are 4 primary plus 8 sensitivity, each run in both modes, which gives the 24 runs reported in Chapter IV.
- **One-at-a-time sensitivity.** Change one parameter while keeping the others at their primary values, to see how much the conclusions depend on the choice. It is a description, not a search for a better setting.
- **One run per configuration** because of time and API cost. This is why we report no hypothesis tests.
- **Procedure per trial:** prepare the graph, insert one concept, measure, repeat with different concepts.

### Slide 26: Measures and Analysis (about 2 min)

**Script**

“For cost we measure wall-clock time per insertion and LLM calls per insertion. For accuracy we use precision, recall and F1, micro-averaged. We also track shortlist recall: the share of true neighbors that narrowing keeps. To judge scaling, we fit the slope of log cost against log graph size. A slope below 0.1 is approximately flat, 0.1 to 0.9 is sub-linear, and above 0.9 is approximately linear. We describe results with 95% bootstrap intervals, and we run no hypothesis tests.”

**Background**

- **Time per insertion** is shortlist time plus decision time plus graph update time. It includes backoff time for retried calls.
- **Precision** = correct predicted links ÷ all predicted links. **Recall** = correct predicted links ÷ all true links. **F1** is the harmonic mean of the two. A link predicted in the wrong direction counts as both a false positive and a missed true link. **Micro** pools all trials. **Macro** averages per concept.
- **Shortlist recall** is a ceiling: a true neighbor that narrowing discards cannot be recovered by the LLM. Random baseline: picking min(k, m) concepts at random from the m present gives expected recall min(k, m) ÷ m.
- **Log-log slope.** Plot log of cost against log of n and fit a line. Slope 1 means cost doubles when the graph doubles. Slope 0 means flat. The three bins are a convention chosen for this study and may be reconciled with the adviser.
- **95% bootstrap interval.** Resample the trials with replacement 10,000 times, recompute the statistic, and take the middle 95%. It shows spread and is not a hypothesis test.

### Slide 27: Decision and Ranking Framework, post hoc (about 2 min)

**Script**

“This framework was defined after the Chapter IV measurements were available, and we label it that way. First, three gates. G1: the shortlist recall must beat a random shortlist. G2: at most 50 LLM calls per insertion at n of 2,000. G3: the strategy must not be beaten on both calls and F1 by another strategy. A strategy is classed as Effective, Conditionally effective, or Not effective. Then we rank strategies with a weighted score of F1 and the log of calls under three weight scenarios, plus a 20,000-draw weight sweep and a TOPSIS cross-check.”

**Background**

- **G1** is not assessable for S2 (no shortlist cap) and not applicable to S1 (the shortlist is the whole graph). **G2** takes the 50-call limit from the 22–50 prompts of Funk et al., a reference point from a different task and not a standard. **G3** uses Pareto dominance with a 0.025 F1 margin, the one observed run-to-run difference in DSA runs (0.4859 versus 0.5111).
- **Classes.** Effective: passes every gate and G1 is assessable. Conditionally effective: passes every assessable gate but G1 is not assessable. Not effective: fails any assessable gate.
- **Weighted score.** F1 and log10(1 + calls) are each min-max scaled to 0–1 across the four strategies. The log is used because calls span three orders of magnitude. Scenarios: accuracy-first (0.7 accuracy, 0.3 cost), balanced (0.5, 0.5), cost-first (0.3, 0.7). The sweep draws 20,000 random accuracy weights (seed 42) and counts how often each strategy takes each rank. **TOPSIS** ranks by distance to an ideal point, and Kendall’s tau compares its ranking with the weighted-sum one.
- **Why gates come first.** A weighted sum is compensatory, so a great score on one criterion can hide a very poor one. The gates act as minimum levels.
- **Be honest:** the gates, weights and log transform are the authors’ conventions, and the classes label these measurements, not statistical findings.

**Handoff:** “With the design in place, my groupmate will present what we found.”

---

# Member 3 (Slides 28–34)

### Slide 28: Chapter IV, Results and Discussions, initial result (about 0.5 min)

**Script**

“Chapter IV presents our initial results. They are organized around the four research questions: cost scaling, placement accuracy, comparison of the strategies, and the bucket-cost premise.”

**Background**

- Chapter IV order: 4.2 cost (RQ1), 4.3 accuracy (RQ2), 4.4 comparison (RQ3), 4.5 bucket premise (RQ4), 4.6 limits, 4.7 summary.
- The analysis plan was frozen before any sweep data was opened. Anything added afterward, such as the gates and ranking, is labelled post hoc.

### Slide 29: Data Collected (about 1.5 min)

**Script**

“We collected 24 runs across 12 configurations on three data sources. The 24 runs are 12 accuracy-mode runs and 12 size-sweep runs, and the 12 configurations are 4 primary settings plus 8 sensitivity settings. Accuracy runs have 59 trials, and sweep runs have 60. All 24 runs passed the validation gate. The three data sources are the DSA gold graph, 29 expert-verified concepts, used for 29 leave-one-out trials; the Metacademy gold graph, 141 concepts, used for 30 trials; and the synthetic concept pool of 2,254 names, which has no ground truth and is used only for cost at n from 50 to 2,000, with 10 trials per size.”

**Background**

- **Validation gate:** automated checks that a run completed correctly. 20 runs passed outright and 4 passed as resumed runs (interrupted and then resumed). No trial remained failed in any run.
- **Quality checks:** all tables and figures were generated by one script from data that passed the gate, and an independent consistency check of 3,399 items reported no failures.
- **Pre-registered versus post hoc:** the plan was frozen before the sweep data was opened. The accuracy-mode summaries had already been seen, which the thesis discloses. Post-freeze additions are labelled wherever they appear.
- Know the arithmetic: 12 + 12 = 24 runs, 4 + 8 = 12 configurations, 29 + 30 = 59 accuracy trials, and 6 sizes × 10 = 60 sweep trials.

### Slide 30: Setup, the four strategies compared (about 1 min)

**Script**

“A quick reminder of the setup. S1 judges every existing node, up to n calls. S2 keeps nodes with cosine similarity above 0.6, up to n calls and uncapped. S3 keeps the top 10 using a FAISS HNSW index, so 10 calls. S4 uses bounded buckets of 5 to 10 nodes, so at most 10 calls. All four share the same decision step, so differences come from the narrowing mechanism. Results are means with 95% bootstrap intervals, and we run no hypothesis tests.”

**Background**

- Same decision step for every strategy: DeepSeek, temperature 0, one call per candidate, one at a time.
- S4’s shortlist rule is its hash segment (bucket), with lower and upper bounds (s\_min, s\_max) of (5, 10).
- If asked what a bootstrap interval is: resample the trials many times and look at the spread of the result. It shows variability but is not a significance test.

### Slide 31: RQ1, wall-clock time at n = 2,000 (about 2.5 min)

**Script**

“Our first question is how time per insertion changes as the graph grows. At n of 2,000, one brute-force insertion takes 1,713 seconds, which is about 29 minutes. S3 takes 8.28 seconds and S4 takes 5.64 seconds. S2 takes 0.94 seconds, but only because most of its trials make no call at all. The slopes agree: brute force is approximately linear at 0.96, while S3 and S4 are approximately flat, at minus 0.02 and 0.008. Time follows calls. Each LLM call takes about 0.8 to 0.9 seconds, and the shortlist step takes under 0.03 seconds. At n of 2,000, brute force is about 207 times slower than S3 and 304 times slower than S4. So the answer to RQ1: linear for brute force, flat for the capped strategies, and call-dependent for the threshold.”

**Background**

- **Reading the slope.** A slope near 1 means time grows in proportion to the graph. A slope near 0 means time stays about the same. The bins (below 0.1 flat, 0.1 to 0.9 sub-linear, above 0.9 linear) are a convention of this study.
- **S3’s slope** is −0.0201 with an interval of −0.0324 to −0.0079. The interval excludes zero, so “approximately flat” holds because the slope is below 0.1 in size, not because the interval contains zero. The mean wanders between 7.9 and 9.5 seconds with no steady trend.
- **S2’s weak fit (R² 0.46).** Most trials make no call and take about 0.01 seconds, while the few that do take about a second each. The six size means mostly reflect how many trials happened to call, so the means are more informative than the “sub-linear” label.
- **Why brute force’s slope is 0.96, not 1.** One retried trial at n = 50 inflated that point (mean 58.63 s, versus 35.75 s without it). Excluding retried trials gives 1.0558. Either way it is approximately linear.
- **Per-call latency:** about 0.857 s for S1, 0.828 s for S3, 0.805 s for S4. Strategies differ in cost mostly because they make different numbers of calls.
- **One trial** ran inside DeepSeek’s peak window. We make no claim about a peak-hour effect.

### Slide 32: RQ1, LLM calls per insertion (about 2 min)

**Script**

“This table shows LLM calls per insertion by graph size. Brute force needs exactly n calls, the linear cost that Funk and colleagues warned about. S3 always makes 10 calls, and S4 averages between 6.6 and 7.5, because their shortlists are capped. S2 depends on how many nodes pass the threshold. At the primary threshold of 0.6 it averages at most 0.8 calls at n of 2,000, and at a looser threshold of 0.4 it reaches 13.5 calls, about 0.7% of the nodes. Its slope at 0.6 is undefined because some sizes have zero average calls.”

**Background**

- **Why the slope is undefined.** A log-log fit needs positive values, and some S2 sizes average zero calls. The plan forbids clamping, so no flatness category is given. An exploratory fit on the positive sizes gives 0.7966 (θ = 0.5) and 0.8095 (θ = 0.6). The θ = 0.6 interval is optimistic (only 4,123 of 10,000 resamples were usable), so quote the counts, not the slope.
- **Slope versus magnitude.** S2 at θ = 0.4 has a steep slope (1.15, approximately linear) but a tiny level, between 0.4% and 0.9% of n at every size.
- **S4** stays below its cap in every setting, with a largest single-trial count of 10.
- **S3’s constant 10** prints as slope 0, because the fitted value is floating-point noise on a constant series.

### Slide 33: RQ2, accuracy of the primary configurations (about 2.5 min)

**Script**

“Our second question is whether placement accuracy holds up as the graph grows. We can answer it only at two sizes: 29 concepts on DSA and 141 on Metacademy. On DSA, brute force has the best F1 at 0.586, using 28 calls, and S3 follows at 0.511 with 10 calls. On Metacademy the order changes: S3 is best at 0.294, S2 is next at 0.270, and brute force falls to 0.143. Look at brute force: its recall stays about the same, 0.630 and 0.624, but its precision falls from 0.548 to 0.081. The last column, shortlist recall, shows how much of the true neighborhood each shortlist keeps. It is 1.0 for brute force, about 0.5 for S3, and much lower for S2 and S4. These are micro-averaged, one run each.”

**Background**

- **Columns.** Calls are LLM calls per insertion. Precision, recall and F1 are micro-averaged over all trials. Shortlist recall is the share of true neighbors the narrowing step kept.
- **Recall never exceeds shortlist recall,** because a true neighbor that narrowing discards cannot be recovered.
- **Density matters.** About 6% of ordered pairs are positive in DSA and about 1.6% in Metacademy, so a method that judges many candidates has many chances to produce false positives on the larger, sparser graph.
- **Absolute level is modest.** No cell meets the pilot’s bar of F1 at least 0.50 and recall at least 0.70.
- **Random baselines** for S3 shortlist recall are 0.357 on DSA and 0.071 on Metacademy.

### Slide 34: RQ2, why accuracy differs across strategies (about 2.5 min)

**Script**

“There are three reasons accuracy differs. First, brute force over-links. Its recall is steady at 0.630 and 0.624, but precision falls from 0.548 to 0.081 when 140 candidates are judged one by one. Second, narrowing trades recall for precision. S2 has high precision, 0.643 and 0.594, but recall of only 0.083 and 0.174, because at a threshold of 0.6 most concepts reach no decision. Third, the decision step caps recall. Recall never exceeds shortlist recall, and the decision step labels only 62% to 86% of the shortlisted true neighbors correctly. So F1 is lower on Metacademy than on DSA for S1, S3 and S4, but domain and edge density differ too, so size alone cannot be blamed.”

**Background**

- **Over-linking.** With few true prerequisites and many candidates, the model labels many non-prerequisite pairs as prerequisites. In the DSA pilot, 34 of 58 false positives were implied by the transitive closure of the gold graph, so precision there is understated. That analysis was not repeated for Metacademy.
- **Precision-recall trade-off.** This echoes Aytekin and Saygin \[6\], who found embeddings give high recall and low precision, and LLMs the reverse.
- **The 62% to 86% figure** is recall divided by shortlist recall across the eight corpus-and-strategy cells.
- **Confounding.** The two graphs differ in size, domain and density, so the study does not claim that size alone causes the change.
- **Sensitivity (if asked).** Looser settings raise recall at the price of calls. On DSA, S3’s F1 rises with k (0.374, 0.511, 0.569 for k of 5, 10, 20). On Metacademy it falls (0.368, 0.294, 0.266). The efSearch variants return the same shortlist recall, so their small F1 differences are decision-step noise, about the size of the one observed run-to-run difference of 0.025.

**Handoff:** “That covers cost and accuracy. My groupmate will now compare the strategies and test the bucket premise.”

---

# Member 4 (Slides 35–42)

### Slide 35: RQ3, trade-offs on DSA, domination on Metacademy (about 2.5 min)

**Script**

“Our third question compares the four strategies under identical conditions. We use dominance: one strategy dominates another if it makes no more calls and has a higher F1. On DSA, every pair of strategies is a trade-off. Brute force has the best F1, 0.586, at 28 calls, but it gains only 0.075 F1 over S3 for 18 more calls. On Metacademy, S3 dominates brute force: F1 is 0.151 higher with 130 fewer calls. S2 dominates both brute force and S4. S3 versus S2 is not distinguishable, because the F1 difference of 0.0246 is inside our 0.025 margin. And S2’s low call count is a recall cost, not a free saving: most insertions find no candidate above the threshold, so its shortlist recall is only 0.111 and 0.202. The largest graph reverses the DSA picture, because brute force is dominated outright.”

**Background**

- **Dominance (Pareto):** A dominates B if A makes no more calls and has higher F1. If neither dominates, the pair is a trade-off.
- **The 0.025 margin** is the one observed run-to-run difference between two runs of the same DSA configuration (0.4859 versus 0.5111). It was fixed before the sweep data was opened.
- **Be honest about S3 versus S2.** 0.0246 is only 0.0004 below the margin, and a margin of 0.02 would label S3 higher. No interval was computed for this difference and none is claimed.
- **130 fewer calls** is 140 (brute force on Metacademy) minus 10 (S3).
- **S4** is not dominant over any strategy on either corpus.

### Slide 36: RQ3, only S3 passes every gate (about 2 min)

**Script**

“Applying the three gates to the primary configurations, only S3 passes every gate and is classed Effective. S2 passes the gates that can be assessed, but G1 cannot be assessed for it because it has no shortlist cap, so it is Conditionally effective. S1 fails the cost gate at 2,000 calls and is dominated on Metacademy. S4 fails the random baseline on DSA and is dominated on Metacademy, so both are Not effective. This is post hoc and single-run. And no strategy meets the pilot’s absolute accuracy bar of F1 at least 0.50 and recall at least 0.70, so S3 is best only in a relative sense.”

**Background**

- **G1 numbers.** S3’s shortlist recall beats the random baseline on both corpora (0.528 versus 0.357, and 0.505 versus 0.071). S4 is below it on DSA (0.259 versus 0.357). Against a random draw of the same average size it is about level, and its class is the same either way because it also fails G3.
- **Robustness.** Any call limit from 10 to 1,999 gives the same G2 result, and dominance margins up to 0.15 F1 give the same G3 result for S1 and S4. The classes do not change under the alternatives examined.
- **Absolute accuracy.** Only S1 on DSA has F1 at least 0.50 and recall at least 0.50 (0.586 and 0.630). S3 on DSA has F1 0.511 but recall 0.426, below the pilot’s fail threshold of 0.50.
- **Do not overclaim:** “Effective” here is a label for these measurements under author-set criteria.

### Slide 37: RQ3, S3 is the most stable across weights (about 2.5 min)

**Script**

“If we ask which strategy is best under a weighted score, the answer depends on the weights. On DSA the leader changes: accuracy-first favors brute force at 0.700, balanced favors S3 at 0.587, and cost-first favors S2 at 0.700. On Metacademy, S2 leads in all scenarios, scoring 0.907 to 0.960, with S3 second at 0.726 to 0.883. S2 gains on cost what it lacks in recall. Across 20,000 random weights, S3 is last in under 0.5% of draws, and it is second most often, 60% on DSA and 69% on Metacademy. S4 is first in no draw. So S3 is the most stable choice across weights. These scores are post hoc, single-run, and scaled across only four strategies, so they describe these measurements and not repeated-run differences.”

**Background**

- **Weighted score.** Each strategy gets an accuracy score (scaled F1) and a cost score (scaled log of calls), combined with a weight. Min-max scaling depends on which strategies are in the set, so adding or removing one can change the scores.
- **Weight sweep.** Draw the accuracy weight uniformly between 0 and 1, 20,000 times, and count how often each strategy takes each rank. The shares have a standard error of at most 0.004.
- **Why S2 leads on Metacademy:** it is a compensation effect, because its very low calls offset its recall of only 0.174. That is why S2 is read together with the gate results and not from the score alone.
- **TOPSIS** was computed as a cross-check on the ranking.

### Slide 38: RQ4, bucket cost does not grow with graph size (about 2 min)

**Script**

“Our fourth question is whether the cost of one insertion stays flat under a bucket-capped strategy. For S4, mean LLM calls stay between 6.6 and 7.5 against a cap of 10, across n from 50 to 2,000. Mean time stays between 5.15 and 5.77 seconds, and the shortlist step takes about 0.01 seconds. The fitted slopes are near zero, minus 0.0004 for calls and 0.0084 for time, and the intervals contain zero. This is consistent with the premise behind the amortized bound in EraRAG: an insertion touches a bounded region of the graph. But there are two cautions. Flat calls are close to guaranteed by the cap, and S3 is equally flat, so flatness is not specific to bucket partitioning. And we tested single insertions, so the amortized bound itself is not tested.”

**Background**

- **Premise versus theorem.** EraRAG’s Theorem 4 is an amortized bound over a sequence of insertions. We only check its premise: that one insertion touches a bounded region, so cost does not rise just because the graph is larger.
- **What is informative.** Because calls are capped by construction, the real evidence is the wall-clock curve and the fact that realized counts sit below the cap.
- **Other bucket settings** are also flat: slopes of 0.0033 (calls) and 0.0170 (time) for (2, 5), and −0.0149 and −0.0193 for (10, 20). Every interval contains zero.
- No theoretical curve is overlaid, because our curves describe one insertion, not amortized behavior.

### Slide 39: Limits of these results (about 1.5 min)

**Script**

“Here is what the results do not show. There is one run per configuration and 10 trials per size, so there are no hypothesis tests. There is one decision model, one prompt, and bare concept names. Accuracy is measured at only two sizes, 29 and 141 concepts, which also differ in domain and density. The synthetic pool is unverified and used for cost only. We tested single, un-amortized insertions, so the amortized bound is untested. And the gates and weights were set post hoc, so the classes label these measurements only.”

**Background**

- **Timing hardware:** timings come from one laptop (Intel i5-8250U) with no controlled load. Latencies in the two S3 primary accuracy runs differed by up to 3.7 times for unexplained reasons, so accuracy-run latencies are not used for any cost claim.
- **Index recall:** the HNSW recall figures (0.841, 0.968, 0.999 for efSearch 64, 128, 256) come from random vectors, not from our corpora. On the real corpora we only observe shortlist recall against gold neighbors.
- **Parameters:** no threshold stricter than 0.6 was run.
- **Disclosure:** accuracy-mode summaries were seen before the analysis plan was frozen.

### Slide 40: Summary of findings (about 1.5 min)

**Script**

“To summarize by research question. RQ1: brute force grows linearly, 1,713 seconds at n of 2,000, while ANN retrieval and bounded buckets stay flat, and the threshold grows with the number of passing nodes, from a small base. RQ2: F1 is lower on the 141-node graph for S1, S3 and S4, but domain and density are confounded, and brute force over-links with a precision of 0.081. RQ3: only S3 is effective, S2 is conditionally effective, and S1 and S4 are not, and no strategy meets the pilot’s absolute accuracy bar. RQ4: calls and time did not grow with graph size, consistent with the premise, and the amortized bound remains untested.”

**Background: likely questions and short answers**

- **Which strategy do you recommend?** S3 (ANN retrieval) is the best available in a relative sense: it is the only one to pass every gate and the most stable across weights. But no strategy reaches the pilot’s absolute accuracy bar, and the best choice on DSA depends on how heavily accuracy is weighted.
- **Why does brute force do best on DSA?** The graph is small (28 candidates), so the full shortlist has the highest recall and few chances to over-link.
- **Is the bucket bound proven?** No. We only found that cost did not grow for single insertions, consistent with the premise.
- **Would a different model or prompt change results?** Possibly. We used one model and one prompt with bare concept names, which we state as a limitation.

### Slide 41: Thank you (about 0.5 min)

**Script**

“Thank you. In short: cost per insertion grows linearly with brute force and stays flat with ANN retrieval and bounded buckets. ANN retrieval was the only strategy to pass every gate, though no strategy reached the absolute accuracy bar. And the bucket premise held for single insertions. We welcome your questions.”

**Background**

- Return to the four messages at the top of this guide if a question is hard: single insertions only, only the narrowing step differs, results are descriptive, ranking is post hoc.

### Slide 42: Contact (leave on screen)

**Script**

No script. Leave this slide up during questions.

**Background: who answers what**

- **Member 1:** problem, literature, gaps, scope and limitations.
- **Member 2:** data, strategies, decision step, procedure, measures, ranking framework.
- **Member 3:** data collected, RQ1 cost, RQ2 accuracy.
- **Member 4:** RQ3 comparison and ranking, RQ4 bucket premise, limits and summary.
- If a question lands on the wrong person, say “my groupmate can answer that more fully” and hand it over.
