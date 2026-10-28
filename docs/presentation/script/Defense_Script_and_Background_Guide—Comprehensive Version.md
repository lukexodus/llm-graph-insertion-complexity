# Defense Script and Background Guide

*An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction*

Adrian Luke A. Labasan · Alejandrei Jazz F. Lopez · Geila May C. Rigayen · Melvie Jeanna O. Abad

## How to use this guide

Every slide has two parts: a **Script** you can say almost word for word, and a **Background** that teaches the ideas behind the slide so you can answer follow-up questions. Scripts are written for a calm pace of about 130 words a minute. All numbers come from the deck and from Chapter 4 of the thesis, so quote them exactly as they appear.

**How the Backgrounds are built.** Each Background starts from the simplest idea and adds one step at a time until it reaches what the slide says. Ideas build across slides too: an idea is explained in full where it first matters, and later slides reuse it. If a term is unfamiliar, go back to the slide where it first appears (see the map below). Wherever a number or example is labelled "our arithmetic" or "illustration", it is a teaching aid and not a thesis claim.

**Naming.** Slides 15–17 and 22 use Strategies A–D, while Chapters III and IV use S1–S4. They are the same strategies: A = S1 brute force, B = S2 embedding threshold, C = S3 ANN retrieval, D = S4 bounded bucket.

**Four messages every presenter repeats**

1. We measure one insertion at a time. We do not test amortized cost over a sequence of insertions.
2. Only the narrowing step differs between strategies. The LLM decision step is identical, so differences come from narrowing.
3. Results are descriptive: one run per configuration, 10 trials per size, no hypothesis tests.
4. The classification and ranking of the strategies was defined after the results were available (post hoc).

## Concept ladder: where each idea is first taught

Read down the list to see how the study builds from a graph to a ranking. Each row uses the rows above it.

| Idea                                                               | First taught on  | Needed for                   |
| ------------------------------------------------------------------ | ---------------- | ---------------------------- |
| Graph, node, edge, direction, knowledge graph, LLM                 | Slide 4          | Everything                   |
| Batch versus incremental, the symbol n, a call as the unit of cost | Slide 5          | Cost on slides 31–32         |
| Linear cost and brute force                                        | Slide 6          | The control condition        |
| Embeddings, cosine similarity, threshold, top-k, bucket            | Slide 7          | Strategies on slide 23       |
| Research gap, aggregate versus scaling cost                        | Slide 8          | Research questions           |
| Premise versus theorem                                             | Slide 9          | RQ4 on slide 38              |
| Log-spaced sizes                                                   | Slide 10         | The slope on slide 26        |
| Gold standard, leave-one-out, precision, recall, F1                | Slide 12         | Accuracy on slides 33–34     |
| HNSW, approximate search                                           | Slide 15         | Strategy S3                  |
| Dominance, weighted sum, gates, amortized analysis                 | Slide 16         | Ranking on slide 27          |
| Controlled variables, shared decision step                         | Slides 19 and 21 | Fair comparison              |
| Hyperplane hashing, Gray order, segments                           | Slide 23         | Strategy S4                  |
| Pilot, conditional verdict                                         | Slide 24         | The accuracy bar on slide 36 |
| Trial, run, configuration                                          | Slide 25         | Data collected on slide 29   |
| Log-log slope, bootstrap interval, shortlist recall                | Slide 26         | RQ1, RQ2                     |
| Worked weighted score                                              | Slide 27         | Table 4.9 on slide 37        |


## Who presents what

| Member   | Slides | Part                                           | Approx. time |
| -------- | ------ | ---------------------------------------------- | ------------ |
| Member 1 | 1–17   | Opening, Chapter I, Chapter II                 | about 16 min |
| Member 2 | 18–27  | Chapter III, Methodology                       | about 16 min |
| Member 3 | 28–34  | Chapter IV: data collected, setup, RQ1, RQ2    | about 13 min |
| Member 4 | 35–42  | Chapter IV: RQ3, RQ4, limits, summary, closing | about 13 min |

Member numbers are not tied to any person, so assign them however the group likes. The total is roughly an hour at a calm pace. If time is short, drop the optional asides in the scripts, not the key numbers.

---

# Member 1 (Slides 1–17)

### Slide 1: Cover (about 0.5 min)

**Script**

“Good day to the members of the panel, our adviser, and everyone present. We are from the College of Computing and Information Sciences of Mariano Marcos State University. Our study asks a simple question about knowledge graphs that keep growing: when one new concept arrives, how much work does it take to connect it to the graph, and does that work grow as the graph grows? I am \[say your full name\], and my groupmates and I will take you through the study in four parts.”

**Background**

**The whole study in three layers.** Learn all three so you can zoom in or out when a panelist asks.

- **Ten words.** We measure what it costs to add one concept to a growing graph.
- **One sentence.** When an LLM connects one new concept to an existing knowledge graph, we measure how time, LLM calls and accuracy change as the graph grows, and we compare four ways of shortlisting which existing concepts the LLM must look at.
- **One minute.**
  1. Knowledge graphs keep growing, so new concepts must keep being added.
  2. Done naively, adding one concept means asking an LLM about every existing concept, so the cost grows with the graph.
  3. Published systems shorten the list first, but none of the studies we reviewed measured the cost of one insertion against graph size, or compared the shortening methods under the same conditions.
  4. We built four shortlisting strategies behind one identical LLM decision step, and ran them on graphs from 50 to 2,000 nodes and on two expert-made graphs.
  5. Brute force grows in a straight line. ANN retrieval and bounded buckets stay flat. Only ANN passes all three of our gates. No strategy reaches the accuracy bar we set in the pilot.

**Where the talk is going.** Slide 1 is only an opening, but every presenter should know the ending so nobody contradicts a teammate later.

| Part | Presenter | Question it answers |
| --- | --- | --- |
| Chapter I and II (slides 3–17) | Member 1 | What is the problem and what is already known? |
| Chapter III (slides 18–27) | Member 2 | How did we measure it fairly? |
| Chapter IV, first half (slides 28–34) | Member 3 | What did cost and accuracy look like? |
| Chapter IV, second half (slides 35–42) | Member 4 | Which strategy is better, is the bucket premise true, and what are the limits? |

**Opening etiquette.**
- Greet the panel, the adviser and the audience in that order. Check the names against the thesis acknowledgements.
- Say your own name where the script has the placeholder. Do not read the full author list here, because slide 2 does that.
- Do not quote any numbers on slide 1. Its only job is to say what the study is about, in plain words.
- Keep it to about 30 seconds. A calm start sets the pace for the hour.

### Slide 2: Title and members (about 0.5 min)

**Script**

“The title of our study is *An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction*. In plain words: we measured, rather than proved, how the cost of adding one new concept to a graph built with a Large Language Model changes as the graph gets bigger, and we compared four ways of shortlisting which existing concepts the model has to look at. The researchers are Adrian Luke Labasan, Alejandrei Jazz Lopez, Geila May Rigayen, and Melvie Jeanna Abad.”

**Background**

Decode the title one word at a time. Each step uses the idea before it, so you can rebuild the title from nothing if someone asks.

**Step 1: Graph construction.** A graph is dots (nodes) joined by lines (edges). Here each node is a concept and each edge says how two concepts relate. Constructing the graph means deciding which nodes exist and which are joined.

**Step 2: LLM-driven.** A Large Language Model (an AI trained on huge amounts of text) is asked to decide the relationship between two concepts. Hand-built graphs need human experts. LLM-built graphs need prompts, and every prompt is a call that takes time and money.

**Step 3: Incremental.** Incremental means one new item arrives after the graph already exists. The opposite is batch: build the whole graph in one go. Our whole study is about the incremental case, one concept at a time.

**Step 4: Candidate narrowing.** A candidate is an existing node the new concept might connect to. Narrowing means cutting the list of existing nodes down to a short list of likely candidates before the expensive LLM step. A strategy is one specific way of doing the cutting. We compare four.

**Step 5: Complexity analysis.** Complexity means how the cost of doing something grows as the input grows. Here the input size is n, the number of nodes already in the graph, and cost is time in seconds and number of LLM calls.
- Linear: double n and the cost doubles. Searching an unsorted list of n names for one name may need n checks.
- Constant (flat): the cost stays about the same however large n gets. Looking up item number 7 in a list takes one step whether the list has 50 or 2,000 items.
- Our study asks which of these two shapes each strategy follows.

**Step 6: Empirical.** We do not prove a formula. We run the strategies, record the numbers, and describe how they grow. Proof would say "always"; measurement says "in these runs".

**Putting it back together.** The title says: we measured, rather than proved, how the cost of adding one new concept to an LLM-built graph grows with graph size, and compared four ways of shortlisting candidates.

**If asked "why not prove it?"** Proof needs a mathematical model of the LLM and the embeddings. We had a published claim (EraRAG's Theorem 4) whose empirical premise had never been varied against graph size, so measuring was the missing piece.

**Author names (for reading aloud).** Adrian Luke A. Labasan, Alejandrei Jazz F. Lopez, Geila May C. Rigayen, Melvie Jeanna O. Abad.

### Slide 3: Chapter I, Introduction (about 0.5 min)

**Script**

“Chapter I introduces the problem. We will cover what a knowledge graph is, why adding to one is costly, what existing work has done, and the two gaps this study fills.”

**Background**

This slide is a signpost. Use it to give the panel a map, and use these notes to be sure of the map yourself.

**The logic chain of the whole defense.** Each part answers the question the previous part leaves open.

1. **Chapter I, the problem.** Why adding a concept is costly, and what no one has measured yet. This is slides 3–13.
2. **Chapter II, the literature.** What exists, what each source contributes, and where it stops. This is slides 14–17.
3. **Chapter III, the method.** How we built a fair experiment out of the gaps. This is slides 18–27.
4. **Chapter IV, the results.** What the experiment showed. This is slides 28–40.

**What is inside Chapter I of the thesis.** 1.1 Background, 1.2 Statement of the Problem, 1.3 Objectives, 1.4 Significance, 1.5 Scope and Limitations, 1.6 Definition of Terms, 1.7 Conceptual Framework. The slides follow the same order, with the definitions folded into the explanations.

**Why the deck is labelled "initial result".** This is the initial-results stage. The manuscript ends at Chapter IV (Section 4.7, the summary of findings), so there is no concluding chapter with recommendations yet. If someone asks where the conclusions and recommendations are, say so plainly: the results chapter is complete for this stage, and the summary of findings in Section 4.7 is the current endpoint.

**Four messages (repeat them).** Single insertions only. Only the narrowing step differs. Results are descriptive. The ranking is post hoc. You will hear each one again.

### Slide 4: Background of the Study (about 1 min)

**Script**

“A graph is made of nodes connected by edges. A knowledge graph uses that idea for ideas themselves: each node is a concept, and each edge is a relationship. For example, Calculus requires Limits. Knowledge graphs are used in web search, recommendation systems, and increasingly in education. In the past, domain experts built them by hand. That is accurate, but it does not scale. Today, Large Language Models can read text and extract concepts and relationships automatically, and that is why this area is growing so quickly.”

**Background**

Build this slide from the smallest idea up. Do not skip a step when explaining it to the panel.

**Step 1: What is a graph?** A graph is a collection of nodes (dots) and edges (lines joining two dots). A road map is a graph: cities are nodes, roads are edges. A social network is a graph: people are nodes, friendships are edges. Graphs matter because many problems become questions about structure, such as the shortest path or how tightly a group is connected.

**Step 2: Edges can have direction.** In a road map you can drive both ways. In a prerequisite map you cannot: Limits comes before Calculus, not the other way round. A directed edge is drawn as an arrow. Our edges are directed, and the direction is exactly what the LLM has to decide.

**Step 3: A knowledge graph.** Make the nodes concepts or topics and the edges meaningful relationships such as "requires", "is a kind of" or "is related to". Because you can follow the edges, a person or a program can navigate from one concept to prerequisites, dependents or neighbours.

**Step 4: An educational (prerequisite) graph.** This is the kind we use. An edge says that one concept must be understood before another. Calculus requires Limits. Educational graphs power study paths and curriculum planning.

**Step 5: How graphs used to be built.** Domain experts read the sources and drew every edge by hand. That is accurate, but it does not scale: a large or fast-changing domain needs endless expert time.

**Step 6: What an LLM is.** A Large Language Model is an AI trained on very large amounts of text. If you give it a prompt such as "Is Limits a prerequisite of Calculus?", it can answer. That ability to judge a relationship between two concepts is what makes automated construction possible.

**Step 7: The three stages of automated construction** (thesis 1.1 and 2.2).
- Ontology engineering: decide what kinds of concepts and relationships matter.
- Knowledge extraction: pull candidate concepts and relations out of text.
- Knowledge fusion: merge them into one coherent graph without duplicates.
What LLMs changed was the cost and speed of extraction, not the three-stage structure. Inserting a new concept is closest to the third stage.

**Where this leads.** Step 5 shows why humans do not scale. Step 6 shows why LLMs help. Slide 5 will show why LLMs bring a new cost problem.

### Slide 5: The problem: knowledge keeps growing (about 1 min)

**Script**

“Most systems build the graph once, in a single batch. But knowledge keeps growing: a course adds a new topic, or a field publishes a new technique. Rebuilding the whole graph for one new concept is wasteful. So the real question is what we call the incremental insertion problem: how do we connect one new concept to an existing graph without re-checking every node?”

**Background**

This slide introduces the study's core vocabulary. Every later slide reuses it.

**Step 1: Batch versus incremental.**
- Batch: give the LLM the whole corpus and ask for a finished graph in one pass.
- Incremental: the graph already exists and exactly one new concept arrives.
- Everyday picture: building a library catalogue from scratch versus filing one newly donated book.

**Step 2: Why batch is not enough.** Knowledge grows after the graph is built: a course adds a topic, a field publishes a technique. Rebuilding everything for one new concept would re-examine nodes that have not changed.

**Step 3: The symbol n.** n is the number of nodes already in the graph. After one insertion the graph has n + 1 nodes. The study uses n for graph size in every chapter, and the thesis even renames EraRAG's own symbol (b for the number of hyperplanes) so that n never means anything else.

**Step 4: What "inserting" means.** For the new concept and each existing concept, decide: is there a prerequisite edge, and which way does it point? So insertion is a set of yes/no/direction decisions.

**Step 5: What a call is, and why calls are the unit of cost.** Each decision is one prompt sent to the LLM through an API, which returns one answer. In our measurements one call takes roughly 0.8 to 0.9 seconds and also costs money. So the number of calls is the main driver of both time and money. Chapter 4 later confirms that time follows calls.

**Step 6: The naive count.** Checking the new concept against every existing node takes n calls. That is the incremental insertion problem in one line: how do we connect one concept without making n calls?

**A bigger picture (our own arithmetic, not a thesis claim).** If you built a graph by brute-force inserting nodes one after another, call counts would add up like 1 + 2 + … + n, about n squared over two. For n = 2,000 that is nearly two million calls. Use this only as an illustration of why linear cost per insertion hurts, and say it is our own arithmetic.

**If asked "why not just rebuild in batch?"** Batch sees the whole corpus and is fine when you build once. It wastes effort when only one item is new, and the thesis argues that repeating it per new concept does not reflect how knowledge grows.

### Slide 6: Why brute force doesn’t work (about 1 min)

**Script**

“The obvious method is brute force: ask the LLM to compare the new concept with every existing node. Funk and colleagues describe this as needing, in their words, ‘a huge number of queries’. Even their own pruned insertion algorithm needed 22 to 50 LLM prompts per concept, at a cost of 11 cents up to 12 dollars and 45 cents depending on the domain. Brute force on a graph of n nodes needs n calls, so the larger the graph, the worse it gets.”

**Background**

This slide shows why the obvious method breaks. First learn what "linear" means in practice, then the benchmark we borrow.

**Step 1: Brute force.** Compare the new concept with every existing node, one LLM call each. No shortlist, no shortcut. It is simple and thorough, which is why it is our control condition: the reference everything else is compared against.

**Step 2: Linear cost, with numbers from our own measurements.**

| Graph size n | LLM calls | Mean time per insertion |
| --- | --- | --- |
| 50 | 50 | 58.63 s (35.75 s without one retried trial) |
| 500 | 500 | 357.57 s |
| 2,000 | 2,000 | 1,713.10 s (about 28.5 minutes) |

Calls equal n exactly. Time is about 0.86 seconds per call. Multiply n by 40 and both calls and time grow about 40 times. You do not need these numbers on slide 6, but they show why the claim is not exaggerated. Slide 31 presents them.

**Step 3: Who said it first.** Funk, Hosemann, Jung and Lutz [1] studied building ontology hierarchies with LLMs. They note that comparing a new concept against every concept needs "a huge number of queries". That phrase is the only direct quote on this slide. Keep it short.

**Step 4: What Funk et al. did about it.** They used an insertion algorithm adapted from KRIS, a classical method from description logic for testing subsumption ("is X a kind of Y?"). It searches the hierarchy top-down and bottom-up and prunes branches once a test fails.

**Step 5: Their numbers.** Averaged over nine domains, their pruned algorithm needed 22 to 50 LLM prompts per inserted concept, at costs from $0.11 to $12.45 depending on the domain.

**Careful: what the 22 to 50 figure is and is not.**
- It is the cost of their own pruned algorithm, not a measurement of brute force. Brute force on n nodes needs n calls.
- Chapter 1 of the thesis words this loosely ("their brute-force approach"), and Section 2.3.1 is more accurate. Use the Section 2.3.1 wording if challenged.
- We use it as a published cost benchmark, and later as the source of our 50-call limit in gate G2 (slide 27). That limit is a convention from a different task, not a standard.

**Step 6: A known open issue (outside our scope).** Funk et al. found that LLM subsumption answers were not transitive: the model could say A is under B and B is under C but deny that A is under C. They assumed transitivity anyway. We note it, and we handle a related effect in our own data (the gold graphs are not transitively reduced, slide 20).

**If asked "why not use Funk's algorithm as a strategy?"** Our scope (slide 12) is a fixed set of narrowing strategies, not a new algorithm. Their method is designed for subsumption hierarchies, while our task is prerequisite relations. We use their work as a cost benchmark and a motivation. The thesis does not claim to compare against it, so do not claim that either.

### Slide 7: The solution: candidate narrowing (about 1 min)

**Script**

“The fix is candidate narrowing. Step one: use a cheap method, such as embeddings, to shortlist the likely candidates. Step two: use the expensive LLM only on that shortlist. Three existing systems shaped our study. iText2KG keeps only nodes whose cosine similarity passes a threshold of about 0.6. SAC-KG uses learned pruning and was tested at over one million nodes. EraRAG groups nodes into size-bounded buckets, and its authors prove that insertion cost should not grow with graph size.”

**Background**

This slide has the most new vocabulary in Chapter I. Take it in the order below: what we want, what tool makes it possible, three ways to use the tool, then three systems that used them.

**Step 1: The two-stage idea.** Stage one is cheap and rough: shortlist likely candidates. Stage two is expensive and careful: let the LLM judge only that shortlist. Picture screening résumés first and interviewing only the shortlist.

**Step 2: How can a cheap method judge "likely"? Embeddings.**
- An embedding turns a piece of text into a list of numbers (a vector) so that texts with similar meaning get similar vectors. Think of each concept as a point in space, with related concepts sitting close together.
- Our embedding model, all-MiniLM-L6-v2, gives each concept name a vector of 384 numbers.
- Computing an embedding is far cheaper than an LLM call. In our runs the whole shortlist step takes under 0.03 seconds, against about 0.85 seconds for one LLM call.

**Step 3: How "close" is measured. Cosine similarity.** It compares the angle between two vectors. Same direction gives 1, unrelated gives about 0. A tiny example in two dimensions: vector A = (1, 0) and vector B = (0.8, 0.6). Their cosine similarity is 0.8, because they point in similar directions. Real embeddings do the same thing in 384 dimensions.

**Step 4: Three ways to cut the list, using similarities to the new concept.** Suppose five existing concepts score 0.90, 0.70, 0.62, 0.55 and 0.30.
- Threshold: keep everything above a cutoff. With a cutoff of 0.6 you keep three. The shortlist size varies with the data and can even be zero or very large.
- Top-k: always keep the k most similar. With k = 2 you keep two. The size is fixed.
- Bucket: precompute groups of similar nodes, each with a capped size. A new concept goes to one group and is compared only with that group's members.

**Step 5: Three published systems that shaped the study.**
- **iText2KG [2]** keeps nodes whose cosine similarity passes a threshold of about 0.6 (standard deviation 0.12), calibrated on 1,500 GPT-4-generated pairs. Its authors list removing that hyperparameter as future work. That gap motivates our count-based ANN strategy.
- **SAC-KG [3]** has a Generator that proposes relations, a Verifier that checks them, and a Pruner that decides whether a branch keeps growing. It reached over one million nodes at 89.32% precision. It shows large scale is possible. It is not one of our four strategies.
- **EraRAG [4]** uses random hyperplanes to hash vectors into buckets with a capped size. Its Theorem 4 gives an amortized insertion cost of O(Δ(bd + S_LLM)): Δ new items, b hyperplanes, d embedding dimension, S_LLM the cost of one LLM call. Informally, inserting should not get costlier just because the graph is bigger.

**Step 6: Where the fourth strategy comes from.** Approximate nearest-neighbour retrieval (HNSW indexes, FAISS library) is a standard similarity-search tool, not an insertion system. We add it as the top-k option. Slides 15 and 23 explain it.

**Careful.** The thesis notes that iText2KG's maintainers later moved to pure cosine matching for scalable parallel merging. You can mention it as a sign that even the original authors reduced LLM use for scale, but do not dwell on it.

### Slide 8: The research gaps (about 1 min)

**Script**

“Reading this literature, we found two gaps. First, none of the studies we reviewed measures insertion cost as a function of graph size. Costs are reported in aggregate, such as total dollars or total time for an entire experiment. Second, none compares narrowing strategies against each other under the same task and the same measurements. Each system is tested only against generic baselines. Those two gaps are what this study addresses.”

**Background**

A gap claim is only as strong as you can explain it. Use these steps so you can defend each gap in your own words.

**Step 1: What a research gap is.** A question the existing studies do not answer. It is the reason a new study is worth doing.

**Step 2: Gap 1, cost as a function of graph size.**
- Aggregate cost is a total over a whole experiment: total dollars, tokens or time.
- Scaling cost is what one insertion costs at 50 nodes versus at 2,000 nodes.
- Analogy: a restaurant that reports total monthly food spend does not tell you what one dish costs as the menu grows.
- EraRAG shows the point. Every dynamic experiment starts with 50% of a dataset as the existing graph and inserts the rest in fixed increments, so it varies the size of the incoming batch, never the size of the graph being inserted into. Its theorem concerns the size of the existing graph, and that variable was never varied.

**Step 3: Gap 2, no like-for-like comparison.**
- Each system is tested against general system-level baselines, not against the other narrowing methods.
- Analogy: comparing whole cars when you want to compare engines. To compare engines you must keep the rest of the car the same. In our study the "rest of the car" is the shared decision step (slide 21).

**Step 4: The third, methodological gap (thesis 2.8; not on this slide).** None of the reviewed insertion studies says in advance what level of accuracy and cost counts as adequate. That is why Chapter III has explicit gates (slide 27). If someone asks why the thesis mentions a third gap, this is the answer.

**Step 5: How strong is the claim?** The thesis calls it an absence claim from a structured but non-exhaustive search (web search, citation trails, reading primary sources), not a systematic review like PRISMA. Always say "none of the studies we reviewed", never "nobody has ever".

**Likely question: "How do you know no one did this?"** Answer: we do not. We searched in a structured way and found none, and we say so plainly. If a study exists, it would strengthen the case for the comparison rather than remove the need for measuring.

### Slide 9: Statement of the Problem (about 1 min)

**Script**

“Our central question is: how can a new concept be added to an LLM-built knowledge graph without checking every existing node? It breaks into four research questions. RQ1: how do time and LLM calls per insertion change as the graph grows? RQ2: does placement accuracy hold up as the graph grows? RQ3: how do the four strategies compare under identical conditions? RQ4: does the cost of a single insertion stay flat under a bucket-capped strategy?”

**Background**

This slide turns the gaps into four testable questions. For each one, learn what we vary, what we measure, and where it is answered.

| RQ | In plain words | We vary | We measure | Answered on |
| --- | --- | --- | --- | --- |
| RQ1 | Does cost grow with graph size? | n from 50 to 2,000 | time and LLM calls per insertion | slides 31–32 |
| RQ2 | Does accuracy hold up as the graph grows? | graph (29 versus 141 nodes) | precision, recall, F1 | slides 33–34 |
| RQ3 | Which strategy is better? | strategy | cost and accuracy together | slides 35–37 |
| RQ4 | Does bucket-capped cost stay flat? | n | calls and time for the bucket strategy | slide 38 |

**How the four map to the four unresolved issues in Section 1.2.**
1. Cost: nobody reported how one insertion's cost changes with graph size.
2. Placement accuracy: narrowing saves computation but risks excluding the right connection, and that risk may change as the pool grows.
3. Comparison: no like-for-like measurement of the strategies.
4. Premise versus theorem: EraRAG's proof assumes bounded work per insertion, but its experiments never varied graph size.

**New terms in this slide.**
- **Placement accuracy:** how well the links we create for an inserted node match an expert-verified graph, scored with precision, recall and F1. Slide 12 explains those scores with an example.
- **Bounded or bucket-capped:** the strategy only ever looks at one bucket whose size has an upper limit, so the shortlist cannot grow with the graph.
- **Premise versus theorem:** a theorem is the full mathematical claim. The premise is the idea it stands on. Here the premise is "one insertion touches only a bounded region". We can test the premise with single insertions. We cannot test the amortized theorem that way.

**Careful with RQ2.** The gold graphs give only two sizes (29 and 141 nodes), and they differ in domain and density as well as size. So RQ2 can be answered only at those two points, and size alone cannot be blamed for any difference.

**Careful with RQ4.** Say "tests the premise behind the amortized bound", never "tests the amortized bound".

### Slide 10: Objectives of the Study (about 1 min)

**Script**

“The general objective is to characterize and compare the cost and accuracy of narrowing strategies as the graph grows. Specifically, we implement four strategies: brute-force LLM comparison, embedding-similarity thresholding, approximate nearest-neighbor retrieval, and bounded-bucket partitioning. We run insertions on graphs from 50 to 2,000 nodes, measure time, LLM calls and accuracy, test whether bucket-capped cost stays flat, and release a reproducible codebase and dataset.”

**Background**

**Step 1: General versus specific objectives.** The general objective is the overall aim. The specific objectives are the concrete tasks that achieve it. Each one maps to a research question and to a part of Chapter III.

| Objective | What it asks | Links to |
| --- | --- | --- |
| 1 | Implement the four strategies | Section 3.3, slide 23 |
| 2 | Run insertions on graphs of increasing, log-spaced size | Section 3.4, slide 25 |
| 3 | Measure time, calls and placement accuracy | Section 3.4, slide 26 (RQ1–RQ3) |
| 4 | Analyze whether bucket-capped cost stays flat | RQ4, slide 38 |
| 5 | Release a reproducible codebase and dataset | Section 2.7 |

**Step 2: What "log-spaced" means.** Sizes are 50, 100, 200, 500, 1,000 and 2,000. Each is roughly double (or 2.5 times) the one before, instead of equally spaced steps such as 50, 100, 150. This covers a 40-fold range in only six sizes. It also makes the sizes evenly spaced on a logarithmic axis, which is what the slope analysis on slide 26 needs.

**Step 3: Why one needs a wide range.** If you only tested 50 to 100 nodes, linear and flat growth would look alike. Over 40 times the range, a linear cost climbs 40 times and a flat cost does not move. That difference is what the experiment is built to expose.

**Step 4: Objective 4 wording.** It says the study tests whether the cost stays flat, consistent with the premise of the amortized bound. It does not test amortization itself. Keep that wording.

**Step 5: Reproducible artifact.** Code, data and run records are released so another researcher can rerun the experiment. The thesis records run directories, commit hashes, a decision log and a validation gate, which slide 29 covers. If asked what "reproducible" means: same code, same data, same fixed seeds (the hyperplane seed is 42), same parameters, and a recorded procedure.

### Slide 11: Significance of the Study (about 0.75 min)

**Script**

“This study matters to three groups. To the field of Computer Science, it provides an empirical benchmark comparing several insertion strategies under identical conditions across graph sizes. To future researchers, it checks whether theoretical cost claims hold up in practice and gives a base for testing new strategies, domains, and limits. To practitioners building knowledge-graph systems, it helps choose a narrowing strategy that fits their expected graph size and update frequency.”

**Background**

**Step 1: Significance means who benefits and how.** The thesis names three audiences. For each, keep one sentence of evidence ready.

- **The field (computer science and knowledge-graph research).** A benchmark: a controlled, side-by-side comparison of several insertion strategies as the graph grows. Among the studies reviewed, no one had published one.
- **Future researchers.** A test of whether the premise behind a theoretical cost claim (bounded work per insertion) holds in practice, and a base for new strategies, domains and limits.
- **Practitioners.** Evidence to choose a narrowing strategy for the graph size and update rate they expect.

**Step 2: What a benchmark is.** A fixed task, data and measurements that let different methods be compared fairly. Fairness here comes from the identical decision step and the fixed parameters.

**Step 3: A practical reading of the results (our wording).**
- Small graph, rare updates: brute force may be tolerable. On DSA it makes 28 calls per insertion, roughly 24 seconds at about 0.86 seconds a call.
- Large or growing graph: brute force at 2,000 nodes costs about 28 minutes per insertion, so a capped strategy is the realistic choice.
- Among capped strategies, ANN retrieval was the only one to pass every gate (slide 36), but accuracy is modest, so a practitioner must weigh cost against missed links.

**Step 4: Limits on "validates theoretical cost claims".** The slide's wording is short for "checks whether the premise holds". We cannot confirm or refute EraRAG's amortized bound, and the thesis says so (slides 13 and 38).

**Likely question: "Who would actually use this?"** Anyone maintaining a curriculum or course graph that grows over time and wants LLM-assisted updates without paying for n calls each time.

### Slide 12: Scope of the Study (about 1 min)

**Script**

“We focus only on the incremental insertion phase: adding one new node to an existing graph. We do not propose a new batch-construction method. We cover four strategies: brute force, embedding threshold, ANN, and bounded bucket. For data, we use two gold-standard graphs, Metacademy with 141 concepts and DSA with 29 concepts, for accuracy, and synthetic concept names up to about 2,000 nodes for cost scaling. We measure wall-clock time per insertion, LLM calls per insertion, and placement accuracy as precision, recall, and F1.”

**Background**

This slide introduces the data and the accuracy scores. Both are used on almost every later slide, so take the time to understand them here.

**Step 1: In scope and out of scope.**
- In scope: one insertion into an existing graph, four fixed strategies, two kinds of data, three measurements.
- Out of scope: batch construction methods, a new narrowing algorithm of our own, amortized sequences of insertions, definitions or text attached to nodes.

**Step 2: Why two data sources.** Accuracy needs a known right answer. Cost does not.
- Gold-standard graphs from Aytekin and Saygın [6], [7] have expert-verified prerequisite relations. Metacademy has 141 concepts (machine learning, statistics, linear algebra). DSA has 29 (data structures and algorithms).
- Synthetic concept names reach 2,000 nodes. They carry no verified edges, so they measure only cost.

**Step 3: How accuracy is measured: withhold and re-insert (leave-one-out).**
1. Take a gold graph and hold one concept out.
2. Treat the rest as the existing graph.
3. Re-insert the held-out concept with a strategy.
4. Compare the links it produced with the expert answers for that concept.
5. Repeat for many concepts.

**Step 4: Precision, recall and F1, with a worked example.** Suppose a concept truly has 4 prerequisite links. The strategy proposes 5 links and 3 of them are correct.
- Precision = correct proposals ÷ all proposals = 3 ÷ 5 = 0.60. "Of what you said, how much was right?"
- Recall = correct proposals ÷ all true links = 3 ÷ 4 = 0.75. "Of what was true, how much did you find?"
- F1 = a single score that is high only when both are high (their harmonic mean): 2 × 0.60 × 0.75 ÷ (0.60 + 0.75) ≈ 0.667.
- Direction matters. A link proposed in the wrong direction counts as a wrong proposal and also as a missed true link.

**Step 5: Why not just recall?** A method that links everything has perfect recall and awful precision. F1 punishes that.

**Step 6: Gold graph file facts you may need.** Metacademy lists 19,740 ordered pairs (141 × 140), of which 318 are prerequisites. DSA lists 840 distinct ordered pairs including 29 self-pairs, of which 54 are prerequisites. About 6% of DSA ordered pairs and about 1.6% of Metacademy ordered pairs are positive.

**Careful.** The synthetic names are unverified, so never use them for any accuracy claim.

### Slide 13: Limitations of the Study (about 1 min)

**Script**

“We want to be upfront about the limits. Concepts are represented by bare names only, with one model and one fixed prompt. The synthetic concepts are unverified, so they are used for cost only. Parameters are fixed, and no thresholds stricter than 0.6 were tested. We test single insertions, not amortized cost. There is one run per configuration and 10 trials per size, with no hypothesis tests. Accuracy is measured at only two graph sizes. And the ranking framework was defined after the results.”

**Background**

Limitations are where panels probe hardest, so know what each one prevents you from claiming. Learn them in groups.

**Group 1: What was measured (construct limits).**
- *Bare concept names only.* No definitions or text per node, so the model leans on what it already knows. A pilot set the ceiling: on DSA brute force gave micro F1 0.541, micro recall 0.611, micro precision 0.485.
- *One model and one fixed prompt.* We cannot say the ranking holds for other models or prompts.

**Group 2: What was held fixed (parameter limits).**
- Thresholds, k, index settings and bucket sizes were fixed before any run and not tuned. No threshold stricter than 0.6 was run, so strict thresholds are untested.
- The synthetic pool is unverified, so it is used only for cost.

**Group 3: How much was run (statistical limits).**
- One run per configuration and 10 trials per size. Run-to-run variation is not established.
- A hypothesis test (a formal procedure for deciding whether a difference is bigger than chance) needs repeated, independent runs. We did not have them, so we describe results and give bootstrap intervals but make no significance claims.
- Accuracy is measured at only two sizes (29 and 141 nodes), which also differ in domain and density.

**Group 4: What kind of insertion (scope limits).**
- Single insertions only. Amortized behavior over a sequence of insertions is not tested.

**Group 5: When decisions were made (procedure limits).**
- The ranking and its gates were fixed after the results were seen (post hoc), so the classes label these measurements and are not statistical findings.

**A safe way to answer any limitation question.** (1) Name the limit. (2) Say what claim it blocks. (3) Say what we still claim. Example: "One run per configuration blocks significance claims; we still report what these runs showed, with bootstrap intervals."

**Careful.** Do not apologize for the limits. They are stated openly, and each one is tied to a claim we did not make.

### Slide 14: Chapter II, Review of Related Literature (about 0.5 min)

**Script**

“Chapter II reviews the related literature. For each strategy and method we use, we show what the source says and why it matters to this study.”

**Background**

This slide opens the literature review. Learn the order and the reference numbers, because panelists often ask "what is reference [x]?"

**How Chapter II is organized (Sections 2.3 to 2.7 follow the objectives).**
- 2.2 Foundations of knowledge graph construction.
- 2.3 The four narrowing strategies, in the same order as the strategies: brute force, embedding threshold, ANN, bounded bucket.
- 2.4 Graph scale and experimental design (SAC-KG).
- 2.5 Measuring cost and accuracy (ACE, gold graphs, and the Pareto and gate methods in 2.5.2).
- 2.6 Amortized complexity and EraRAG's claim.
- 2.7 Reproducible artifacts and the Philippine research context.
- 2.8 Synthesis, with Table 2.1, then 2.9 Conclusion.

**How to read the next two table slides.** Each row names a source, its key idea, and its role in our study. A role is one of: control condition, basis for a strategy, ground truth, evaluation method, theoretical claim to test, or context.

**Reference cheat sheet.**

| Ref | Source | One line |
| --- | --- | --- |
| [1] | Funk et al. | LLM ontology construction; brute force needs too many queries; 22–50 prompts with pruning |
| [2] | iText2KG | Incremental KG construction with a cosine threshold near 0.6 |
| [3] | SAC-KG | Generator, Verifier, Pruner; over a million nodes at 89.32% precision |
| [4] | EraRAG | Size-bounded buckets via hyperplane hashing; Theorem 4 |
| [5] | DIAL-KG | Schema-free incremental KG construction; appears in the range [1]–[5] but is not discussed in detail |
| [6] | Aytekin and Saygın (ACE) | Educational KGs with prerequisite relations; embeddings versus LLMs |
| [7] | EKG-Dataset | The released gold graphs (Metacademy, DSA) and example files |
| [8] | Balilo | Bicol University capstone trends; about 60% are information systems |
| [9] | Naguio and Roxas | Graph neural networks for Philippine lexical resources |
| [10] | Malkov and Yashunin | HNSW |
| [11] | Johnson, Douze, Jégou | FAISS |
| [12]–[22] | Evaluation methods | Pareto, TOPSIS, weighted sum, SMAA, satisficing, non-inferiority, min-max scaling, Kendall |

**Check before presenting.** The deck on slide 16 cites the evaluation-methods range as [13]–[21], but the thesis reference list numbers them [12]–[20] (Han et al. is [21] and Kendall is [22]). The thesis text for Objective 2 also cites ANN retrieval as [11], [12], where it should be [10], [11]. Make the deck and thesis use one numbering before the defense. Until then, say "the evaluation-methods references" instead of reading out the range.

### Slide 15: Related literature, part 1 (about 1.5 min)

**Script**

“This table links each source to its role in our study. Funk and colleagues show that comparing a new concept with every node needs too many LLM calls, so brute force is our control condition, and their 22 to 50 prompts is our cost benchmark. iText2KG uses a cosine threshold, which is the basis for Strategy B at 0.6, and its threshold problem motivates a count-based alternative. HNSW and FAISS give us top-k retrieval, the basis for Strategy C, which needs no similarity cutoff. EraRAG gives us size-bounded buckets, the basis for Strategy D, and its theorem is the claim whose premise we test. Finally, SAC-KG shows automated construction working at over a million nodes, which makes a 2,000-node sweep realistic.”

**Background**

Each row of this table gives a source, what it does, and why we need it. Learn them in this order, since each builds on the last.

**Row 1: Funk et al. [1] (brute force, control).**
- A control condition is the reference case you compare everything else with. Brute force is the simplest possible method, so every other strategy must beat it on cost to be worth using.
- Their pruned algorithm needed 22–50 prompts per concept ($0.11–$12.45 across nine domains). That is a published benchmark of what insertion costs, not our brute-force measurement.

**Row 2: iText2KG [2] (embedding threshold, Strategy B).**
- A threshold of about 0.6 keeps nodes whose cosine similarity passes it. We fix θ = 0.6 in advance, following this precedent.
- Problem the authors admit: a threshold is a hyperparameter someone has to choose. The shortlist size also changes with the data: strict cutoffs give empty lists, loose ones give huge lists.
- Illustration: similarities 0.90, 0.70, 0.62, 0.55, 0.30. A 0.6 threshold keeps three. Top-2 keeps two. A 0.5 threshold would keep four.

**Row 3: HNSW [10] and FAISS [11] (ANN, Strategy C).** Teach it in three levels.
- *The need.* Exact nearest-neighbour search compares a query to all n vectors. That is cheap for 2,000 vectors, but indexes exist so the same idea scales to millions.
- *The structure.* HNSW (Hierarchical Navigable Small World) links each vector to a few near neighbours and stacks several layers. The top layer is sparse, with long jumps. The bottom layer holds everything, with short links.
- *The search.* Start at the top layer, move greedily to whichever neighbour is closer to the query, drop a layer, repeat, and finish near the true nearest neighbours.
- *Why "approximate".* Greedy walking can get stuck and miss a true neighbour. We measure this with `exact_topk_overlap`.
- *FAISS* is the widely used library that implements HNSW and other indexes.
- Top-k means always return k results, so the shortlist size is fixed and no similarity cutoff is needed. k and the index settings are still design choices.

**Row 4: EraRAG [4] (bounded buckets, Strategy D).** Random hyperplanes hash vectors into short codes, and nodes with the same code land in the same bucket. Each bucket has a size cap, so inserting one concept touches only one capped region. Slide 23 explains the hashing step by step. The theorem is the claim whose premise we test.

**Row 5: SAC-KG [3] (scale).** It builds domain graphs beyond one million nodes, so a 2,000-node sweep is a modest, realistic scale. Like the others, it does not report cost against the size of the existing graph.

**Honesty check.** SAC-KG's Pruner is a learned decision about whether a branch keeps growing. We do not implement it. It is evidence that automated pruning is possible at scale, not one of our four strategies.

### Slide 16: Related literature, part 2 (about 1.5 min)

**Script**

“The second table covers evaluation and context. ACE and the Metacademy and DSA gold graphs give us ground truth for accuracy. Pareto dominance, the weighted-sum model, TOPSIS and minimum-level gates support how we judge cost and accuracy together. Amortized analysis explains why single-insertion tests cannot confirm an amortized bound. EraRAG’s experiments varied the incoming batch size, not the graph size, which is the gap we fill. Last, public datasets make our work reproducible, and we found no local study on incremental insertion, which supports novelty.”

**Background**

This table covers how we judge strategies and the surrounding context. Each concept is introduced here and used in full on slide 27, so learn the ideas now and the numbers later.

**Row 1: ACE and the gold graphs [6], [7].** Aytekin and Saygın built educational prerequisite graphs with embeddings plus human experts. They found embeddings reach 100% recall at only 46.13% precision, while LLMs reach up to 87.23% precision but as low as 35.80% recall (zero-shot). That trade-off helps interpret our results: shortlisting by embeddings keeps many links but invites false ones, and LLM judging is careful but misses links. Their released graphs are our ground truth.

**Row 2: Evaluation methods, introduced one by one.**
- *Why not accuracy alone?* Kapoor et al. argue that ignoring cost hides how expensive a method is, so report accuracy and cost together.
- *Pareto dominance.* Strategy A dominates B if A is at least as good on every criterion and better on at least one. Example: 10 calls and F1 0.294 versus 140 calls and F1 0.143 (S3 versus S1 on Metacademy). The first dominates. If one is cheaper but the other is more accurate, neither dominates and you have a trade-off.
- *Weighted sum.* Scale each criterion to 0–1 and add them with weights. Simple, but compensatory: a great score on one criterion can hide a terrible one.
- *TOPSIS.* Rank options by how close they are to an ideal point.
- *Weight sensitivity.* Rankings can change with the weights, so look across the whole range of weights and count how often each option takes each rank (the idea of SMAA).
- *Minimum-level gates (satisficing, after Simon).* Set pass or fail bars before any weighting so a terrible score cannot be offset. Bars should be fixed in advance and justified by context, as for non-inferiority margins in clinical research.
- None of these sources supplies the actual threshold values. Ours are conventions, anchored to our own criteria and to [1], and we say so.

**Row 3: Amortized analysis, from a first example.** A dynamic array (a list that grows) usually appends in one step, but sometimes runs out of room and must copy everything to a bigger array. That copy is expensive, but it happens rarely. Averaged across many appends the cost per append is small and constant. That averaging over a sequence is amortized cost. We only measure one insertion at a time, so we cannot confirm an amortized claim.

**Row 4: EraRAG's batch-size experiments.** They varied the incoming batch and held the starting graph at about 50%, so graph size was never the variable. We vary graph size, which fills the gap.

**Row 5: Context [7], [8], [9].** Public datasets make our work reproducible. Balilo [8] found that about 60% of Bicol University CS/IT capstones (2011–2019) were information systems. Naguio and Roxas [9] used multi-scale graph neural networks for completion over Philippine lexical data (113,557 words, 304,171 relations). Neither addresses incremental insertion. Our claim of local novelty is limited by the scope of our search.

**Check before presenting.** The deck cites [13]–[21] here while the thesis reference list numbers these sources [12]–[20]. See the note on slide 14.

### Slide 17: Conceptual Framework (about 1.25 min)

**Script**

“Our framework follows input, process, output. The input is an existing graph of size n, from 50 to 2,000 nodes, one new concept, and a narrowing strategy: A brute force, B embedding threshold, C ANN retrieval, or D bounded bucket. In the process, the strategy reduces the graph to a candidate shortlist, a shared LLM decision step judges the relationship for each shortlisted candidate, and the graph is updated and measured. The output is an updated graph of size n plus one, with cost measured as time and LLM calls, and accuracy measured as precision, recall and F1 against the gold standard.”

**Background**

The conceptual framework is the study's blueprint: what goes in, what happens, what comes out. Walk through it once using a small example, then connect it to the thesis.

**Step 1: The three foundations.**
- *Graph theory:* nodes, edges, structure and growth.
- *Amortized algorithm analysis:* how to reason about cost over many operations. Our single-insertion protocol is related to it but does not itself test amortization.
- *Vector semantics:* meaning as position in space, so closeness can shortlist candidates.

**Step 2: Input, process, output.**
- Input: an existing graph of size n (50–2,000), one new concept, and one narrowing strategy.
- Process: narrow, then decide, then update and measure.
- Output: an updated graph of n + 1 nodes plus measurements of cost (time and calls) and accuracy (precision, recall, F1).

**Step 3: A worked walk-through (illustration only, not study data).** Existing graph with 5 concepts: Arrays, Loops, Recursion, Trees, Sorting. New concept: Binary Search Tree.
- Brute force sends all 5 pairs to the LLM (A).
- Embedding threshold keeps those above 0.6, perhaps Trees and Recursion, or sometimes none (B).
- ANN with k = 3 keeps the three most similar, perhaps Trees, Recursion, Arrays (C).
- Bounded bucket keeps the members of Binary Search Tree's bucket, perhaps Trees, Recursion, Sorting (D).
- Whatever the shortlist is, the same LLM decision step judges each shortlisted pair and returns one of three labels. Then we add the edges and record time, calls and accuracy.

**Step 4: Why the decision step is shared.** If each strategy used its own decision method, a difference in results could come from either the shortlist or the decision. Sharing the decision step isolates the shortlist.

**Step 5: Letter-to-number mapping.** A = S1, B = S2, C = S3, D = S4. The deck uses letters in the framework and the design diagram, and Chapter IV uses S1–S4.

**Likely question: "Why input, process, output and not independent and dependent variables?"** They are the same story told two ways. Slide 19 gives the variable view.

**Handoff:** “That is the problem and the literature behind it. My groupmate will now explain how we designed the experiment.”


---

# Member 2 (Slides 18–27)

### Slide 18: Chapter III, Research Methodology (about 0.5 min)

**Script**

“Chapter III explains how we designed the experiment: the data we used, the four strategies, the shared decision step, the procedure, and how we measure and judge the results.”

**Background**

**Step 1: What a methodology chapter must do.** Explain the study well enough that someone else could repeat it, and show why the measurements can be trusted.

**Step 2: Three promises the chapter makes.**
- *Fairness:* the strategies are compared under identical conditions (slides 21 and 24).
- *Repeatability:* parameters, seeds and procedures are fixed and recorded (slides 23 and 25).
- *Honesty about timing:* choices made before the data are separated from choices made after (slides 25 and 27).

**Step 3: Pre-registration, in plain words.** Before looking at the sweep data the team froze an analysis plan: which measurements, which statistics, which labels. It is the same idea as writing down your prediction before an experiment so you cannot adjust it to fit the result. The thesis tracks this with a decision log (decisions numbered D-xx), and amendments to the plan. Chapter IV labels each result as pre-registered, post hoc or exploratory.

**Step 4: Roadmap of the chapter.** 3.1 research design, 3.2 data sources, 3.3 the pipeline, the four strategies and the shared decision step, 3.4 procedure, 3.5 analysis, 3.6 the post hoc decision and ranking framework.

**If asked "what is post hoc?"** It means "after the fact". A choice made after seeing results. It is allowed if labelled, because it cannot be mistaken for a prediction. Section 3.6 is labelled post hoc.

### Slide 19: Research Design (about 1 min)

**Script**

“Our design is developmental and experimental. It works like an algorithm benchmark: there are no human respondents and no surveys. We control two independent variables, the narrowing strategy and the graph size, and we measure two kinds of dependent variables: insertion cost, as time and LLM calls, and placement accuracy.”

**Background**

**Step 1: What kind of study is this?** An experimental study where the "subjects" are algorithms, not people. You change one thing, hold the rest steady, and measure. This resembles an algorithm benchmark more than a survey.

**Step 2: Why there is no sampling or survey validity.** Those ideas apply to human respondents. There are no respondents. What replaces them is controlled conditions and repeatable runs.

**Step 3: Sort the variables.**

| Role                       | Variable           | Values                                                                        |
| -------------------------- | ------------------ | ----------------------------------------------------------------------------- |
| Independent (we change)    | Narrowing strategy | S1, S2, S3, S4                                                                |
| Independent (we change)    | Graph size n       | 50, 100, 200, 500, 1,000, 2,000 (cost); 29 and 141 (accuracy)                 |
| Dependent (we measure)     | Cost               | wall-clock time and LLM calls per insertion                                   |
| Dependent (we measure)     | Placement accuracy | precision, recall, F1, and shortlist recall                                   |
| Controlled (we hold fixed) | Decision step      | same model, same prompt, temperature 0, one call per candidate, one at a time |
| Controlled (we hold fixed) | Embedding model    | all-MiniLM-L6-v2, run on CPU with one thread                                  |
| Controlled (we hold fixed) | Parameters         | θ = 0.6, k = 10, HNSW settings, buckets (5, 10), seed 42                      |

**Step 4: Why "developmental".** We did not only test existing code. We built the four strategies and the test harness, and released them as a reusable artifact.

**Step 5: Why the controlled column matters most.** A comparison is only fair if everything except the thing under study is identical. That is the reason slide 21 stresses the shared decision step.

### Slide 20: Data Sources (about 2 min)

**Script**

“We use two kinds of data. For accuracy, we use gold-standard graphs: Metacademy with 141 concepts and DSA with 29 concepts, both with expert-verified prerequisite relationships. For each trial we withhold one concept, re-insert it with a strategy, and compare the result with the true answers. For cost, we use a synthetic pool of 2,254 unique computer science concept names generated with an LLM, used to build graphs from 50 up to 2,000 nodes. Because those names are not verified, we never use them for accuracy claims.”

**Background**

This slide has a lot of numbers. Understand the logic first and the numbers will fall into place.

**Step 1: Two questions need two kinds of data.**
- Accuracy needs a known right answer, so we use gold graphs.
- Cost can be measured on any graph, so we use a large synthetic pool to reach 2,000 nodes.

**Step 2: What a gold file looks like.** Each line is a triple: a source concept, a target concept and a label. Label 1 means the target is a prerequisite of the source. The files list nearly every ordered pair, so a missing edge means an explicit 0, not an unknown.
- Metacademy: 19,740 lines (141 × 140), 318 positive.
- DSA: 841 lines, 840 distinct ordered pairs including 29 self-loops, 54 distinct positive pairs, one repeated row, and one pair left unjudged (binary_search_tree;asymptotic_complexity, though its reverse is present). That pair is left out of the standard scores and counted as a false positive in a separate sensitivity variant, which changed only two cells and no conclusion.

**Step 3: A direction trap.** The gold files and the ten example (MEKG) files use opposite orientation conventions. The thesis checked that nine of the ten agree with the reversed orientation. The study's prompt always puts the new concept as X and the candidate as Y, so direction is explicit.

**Step 4: Not transitively reduced, taught from an example.** Suppose Arrays → Trees and Trees → BST are edges. Then Arrays → BST is implied by following the path. A "transitively reduced" graph removes such implied edges. Our gold graphs keep them: 14 of 54 DSA edges (25.9%) and 105 of 318 Metacademy edges (33.0%) are implied. So the prompt asks whether one concept must be understood "directly or indirectly" before the other, and a model answer that looks like a false positive may be an implied true link.

**Step 5: Leave-one-out in detail.** For one trial: withhold a concept, build the existing graph from the rest, insert it back with a strategy, compare with the true row for that concept. Do this for 29 concepts on DSA and 30 on Metacademy.

**Step 6: The synthetic pool, as arithmetic.**
- 80 computer-science subfields were planned, and 73 were reached. Each call asked for 40 concept names.
- Raw names returned: 2,922.
- Remove 2 invalid, 95 overlapping with evaluation corpora, 542 exact duplicates and 29 singular/plural pairs: 2,922 − 2 − 95 − 542 − 29 = **2,254**.
- Why we needed at least 2,001: a graph of 2,000 plus one new concept to insert.
- It was generated with Claude Sonnet 5, a different model family from the decision model, which reduces but does not remove shared-vocabulary bias. The names are not verified, so they are never used for accuracy.

**Careful.** Section 3.2.2 of the thesis also describes reusing ten small example files for the low end of the sweep. Chapter IV states that all cost claims come from the synthetic pool at sizes 50 to 2,000. When asked, say what Chapter IV says, and treat the ten example files as used for the orientation and overlap checks.

### Slide 21: Experimental Design (about 1 min)

**Script**

“Every insertion has the same shape. The input is one new concept and an existing graph. The narrowing step, which is different for each strategy, produces a shortlist of candidates. The decision step, which is identical for all four, has an LLM judge the new concept against each shortlisted candidate. Because only the narrowing step changes, any difference in the results comes from the narrowing method.”

**Background**

This slide is the logic of the whole experiment. If you understand this, you can defend the study against most methodological questions.

**Step 1: The shape of one insertion.** Input: one concept and an existing graph. Narrowing: shortlist the candidates. Decision: judge each candidate. Output: updated graph plus measurements.

**Step 2: What differs and what is identical.**
- Different per strategy: how the shortlist is built (the narrowing step).
- Identical for all: model, prompt, temperature 0, one call per candidate, strictly one at a time.

**Step 3: Why this isolates the narrowing step.** If the same decision machinery is applied to different shortlists, any difference in calls, time or accuracy must come from the shortlists. This is the controlled-variable principle (slide 19).

**Step 4: Why calls are sequential.** Concurrency 1 means no overlap between calls, so one call's latency is not distorted by the client's own load. It also makes per-call time easy to read.

**Step 5: What exactly is timed.** From the start of the narrowing step to the end of the decision step for one insertion. The thesis defines total time as shortlist time plus decision time plus apply and update time. The harness's own validity checks are timed separately and are not counted.

**Step 6: A natural objection and its answer.** "Why not let each strategy use its own best decision method?" Because then the comparison would mix two things, the shortlist and the decision, and we could not say which caused a difference. The thesis chooses attributability over tuning.

**Step 7: A caveat you should volunteer.** Strategies S3 and S4 both cap the shortlist at 10. So the comparison cannot separate the geometry of bucket partitioning from simple shortlist capacity. Say this before a panelist does.

### Slide 22: Research Design diagram (about 2 min)

**Script**

“This diagram shows one insertion from top to bottom. At the top are the inputs: the existing graph with n concepts, the new concept, and a subject-area label such as ‘data structures and algorithms’. Strategies B, C and D also use a small embedding model that runs on CPU. In the middle is the only part that differs: candidate narrowing. A uses every node, B uses nodes above 0.6 similarity, C uses the top 10 nearest neighbors, and D uses only the members of one bucket. Each strategy produces a candidate shortlist: n for A, between 0 and n for B, 10 for C, and at most 10 for D. Every shortlist goes into the same decision step: one LLM call per candidate, one at a time, at temperature 0, returning one of three labels. The output is the updated graph with n plus one concepts, plus the measurements for that insertion. The gold-standard graphs are used only for the accuracy trials.”

**Background**

Read the diagram top to bottom and name each box. The slide is Figure 3.1 of the thesis in deck form.

**Layer 1: Inputs.**
- The existing graph (n concepts), the new concept, and a subject-area label such as "data structures and algorithms".
- A small embedding model, all-MiniLM-L6-v2, runs locally on CPU with one thread for strategies B, C and D, so embedding times are comparable.

**Layer 2: Candidate narrowing (the only part that differs).**

| Strategy | Rule | Shortlist size |
| --- | --- | --- |
| A (S1) | every existing node | n |
| B (S2) | cosine similarity above 0.6 | from 0 up to n |
| C (S3) | top 10 by similarity (FAISS HNSW) | 10 |
| D (S4) | members of one bucket (5–10 nodes) | at most 10 |

**Layer 3: The shared decision step.** One LLM call per candidate, one at a time, temperature 0, one of three labels.
- X_PREREQ_Y: the new concept is a prerequisite of the candidate.
- Y_PREREQ_X: the candidate is a prerequisite of the new concept.
- NONE: neither.

**Layer 4: Output.** Updated graph with n + 1 nodes plus measurements for that insertion. Gold graphs enter only in accuracy trials, to score the result.

**Two modes use the same pipeline.** *Accuracy mode* runs on the gold graphs (29 and 141 nodes) and reports precision, recall and F1. *Sweep mode* runs on the synthetic pool at six sizes and reports time and calls.

**Fix before presenting.** The figure labels the model "DeepSeek V4 Flash". The thesis (Section 3.3.6) and slide 24 say DeepSeek V3, called through the alias deepseek-flash (which resolves to deepseek-chat). Fix the figure, or say "DeepSeek, through its official API under the alias deepseek-flash" and do not read out a version number.

**Reading tip.** Point at the middle layer and say "this is the only thing that changes between strategies". It is the clearest one-line summary of the whole design.

### Slide 23: The Four Strategies (about 2 min)

**Script**

“Here are the four strategies and their worst-case cost. S1, brute force, is the control: it judges every existing node, so up to n calls. S2 keeps nodes whose cosine similarity is above 0.6, so its calls can go up to n, but often it finds none. S3 keeps the top 10 most similar nodes using a FAISS HNSW index, so at most 10 calls. S4 keeps only the members of the new concept’s bucket, between 5 and 10 nodes, so also at most 10 calls.”

**Background**

Learn the strategies as a progression. Each adds one idea to the one before it.

**S1: Brute force.** No idea added. Every existing node goes to the decision step, so calls = n exactly. It is the control.

**S2: Embedding threshold. Adds embeddings and cosine similarity (slide 7).**
- Embed the new concept, compute its cosine similarity to every existing node, and keep those strictly above θ = 0.6.
- The shortlist can be empty, in which case no LLM call is made. It has no cap, so in the worst case it equals brute force.
- θ = 0.6 was fixed in advance after iText2KG. Sensitivity runs use 0.4 and 0.5.

**S3: ANN retrieval. Adds an index and top-k (slide 15).**
- Same embeddings and similarity as S2 (inner product on length-normalised vectors), so S2 and S3 differ only in how candidates are picked: by cutoff or by count.
- Index: FAISS HNSW with M = 16 (links per node), efConstruction = 200 (how many candidates considered while building the index), efSearch = 128 (how many candidates tracked while searching; higher is more accurate and slower). The thesis states these are fixed in advance and differ from FAISS defaults (40 and 16).
- k = 10, so at most 10 calls.
- Because HNSW is approximate, the study records `exact_topk_overlap`, the fraction of returned candidates that belong to the exact top-k, outside the timed measurement. Separately, a pre-run test on random vectors gave recall@10 of 0.841, 0.968 and 0.999 at efSearch 64, 128 and 256. Those figures come from random vectors, not from our concept data.

**S4: Bounded bucket. Adds hashing and a size cap.** Built in four small steps:
1. *Random hyperplane = one yes/no question.* Pick a random plane through the embedding space. A vector is on one side or the other, which gives 1 bit.
2. *Code.* With 12 hyperplanes each concept gets a 12-bit code. Vectors with a small angle between them tend to fall on the same side of most planes, so similar concepts get similar codes. 12 bits allow 4,096 codes, more than the 2,000-node maximum.
3. *Order the codes.* Codes are mapped to a Gray-code ordering, in which neighbouring codes differ in one bit, so similar codes sit next to each other on a line.
4. *Segments.* Cut the line into contiguous segments of 5 to 10 concepts. If one grows past 10 it is split at the midpoint. If one drops below 5 it is merged into its closest neighbour (by Hamming distance of the touching codes, then Gray-rank gap, then neighbour size, left before right). A new concept goes to its home segment and is compared only with the members there, so at most 10 calls.
- Seed 42 fixes the hyperplanes.
- This adapts the hyperplane partitioning idea and the [s_min, s_max] lifecycle from EraRAG. It does not reproduce EraRAG's multi-layer summarisation architecture, and the thesis fills unspecified details (split and merge ordering) with the rules above.

**Sensitivity settings.** θ ∈ {0.4, 0.5}; k ∈ {5, 20} and efSearch ∈ {64, 256}; bucket bounds (2, 5) and (10, 20). Each is changed one at a time around the primary setting.

**Honest caveat.** S3 and S4 share a worst-case cap of 10, so their comparison does not isolate partitioning geometry from capacity.

**Rule to remember.** Every parameter was fixed before any run and not tuned on the evaluation data.

### Slide 24: The Shared Decision Step (about 2 min)

**Script**

“The decision step is the same for every strategy. For each shortlisted candidate, we make one LLM call, one at a time. We call DeepSeek through its official API at temperature 0, with one fixed prompt. The input is only the two concept names plus a subject-area label, and the output is one of three answers: X is a prerequisite of Y, Y is a prerequisite of X, or none. Before comparing strategies, we ran a pilot with brute force on the DSA graph. It gave a micro F1 of 0.541 and recall of 0.611, which counted as a conditional pass. We kept the prompt unchanged and did not tune it further.”

**Background**

The decision step is the part everyone shares. Learn what a call looks like, what the model returns, and how the pilot justified keeping the prompt.

**Step 1: One call, concretely.** The system prompt defines "prerequisite" (P is a prerequisite of Q if a learner needs to understand P, directly or indirectly, before Q) and requires exactly one answer token. The user prompt has three lines: the subject area, Concept X (the new one) and Concept Y (the candidate). No definitions, no text, no neighbours. The reply must be one of X_PREREQ_Y, Y_PREREQ_X or NONE.

**Step 2: Settings and what they mean.**
- Temperature 0 means the model picks its most likely answer each time, so answers are as repeatable as the service allows. The thesis still says the model is not fully deterministic, which is one reason we run no hypothesis tests.
- Thinking is disabled, so no reasoning tokens are produced.
- Model: DeepSeek V3, via the official API under the alias deepseek-flash (resolving to deepseek-chat). The provider reports only the alias, so it could change the model behind it, a stated limitation.
- Timed runs were scheduled outside DeepSeek's peak hours.

**Step 3: Why bare names.** Giving each concept a definition would help accuracy but would change the study to depend on per-node text. Bare names keep the focus on the narrowing strategies. The cost is that accuracy rests on the model's own knowledge.

**Step 4: Why prompt v2 has three worked examples.** A zero-shot version answered "X is a prerequisite of Y" on all six DSA probe pairs and on 12 of 16 pairs of a balanced general-education set. Reversing the option order flipped it to "Y is a prerequisite of X" on 11 of 16. That looks like position bias. Version 2 adds three examples (fractions/ratios, calculus/limits, poetry/plumbing), none from the evaluation corpora, and answered all 16 balanced pairs correctly. Honest note: the six DSA probe pairs were seen before v2 was chosen.

**Step 5: The pilot, defined term by term.**
- Leave-one-out brute force on the 29 DSA concepts: each inserted concept paired with 28 others, 29 × 28 = 812 decisions.
- Micro F1 0.541, recall 0.611, precision 0.485.
- Direction-flip rate 15.38%: among the 78 predicted edges that fall on gold-positive pairs, 12 pointed the wrong way.
- Swap consistency 85.71%: a check of how stable answers are when the order of the pair is swapped. If asked for the exact procedure, say the thesis and decision log hold it.
- Protocol validity passed: no transport or parse failures, no retries, no reasoning tokens, one model identifier.

**Step 6: Criteria fixed beforehand, and the verdict.** Pass needed F1 ≥ 0.50, recall ≥ 0.70 and flip rate ≤ 15%. Recall below 0.50 would be a fail. Result: F1 passed, recall 0.611 fell between fail and pass, and flip rate was just over 15%. So the verdict was conditional.

**Step 7: What we did with a conditional verdict.** Kept prompt v2 unchanged and did no further tuning. Tuning on the evaluation graph would make later results look better than they are.

**Step 8: A note on precision.** Of the pilot's 58 false positives, 34 are implied by the transitive closure of the gold graph (slide 20), so precision there is understated.

**Careful.** Say "DeepSeek V3" only if you are sure the figure on slide 22 has been fixed. Otherwise avoid the version number.

### Slide 25: Experimental Procedure (about 1.5 min)

**Script**

“We test graph sizes of 50, 100, 200, 500, 1,000 and 2,000, with one single insertion per trial and 10 trials per size. Accuracy runs use 59 trials: 29 on DSA and 30 on Metacademy. All parameters were fixed before running and were not tuned on the data. We also ran 8 one-at-a-time sensitivity settings: thresholds 0.4 and 0.5 for S2, k of 5 and 20 and efSearch of 64 and 256 for S3, and bucket bounds of (2, 5) and (10, 20) for S4. That gives 12 configurations in total, one run each.”

**Background**

Learn the counting hierarchy first, then the procedure, then the sensitivity design.

**Step 1: Four levels of counting.**
- *Trial:* one insertion.
- *Run:* all trials for one configuration in one mode.
- *Configuration:* a strategy with a specific set of parameters.
- *Study:* all runs.

**Step 2: The sums.**
- Sweep run: 6 sizes × 10 trials = 60 trials.
- Accuracy run: 29 DSA + 30 Metacademy = 59 trials.
- 12 configurations = 4 primary + 8 sensitivity.
- Each configuration is run in both modes, so 12 × 2 = 24 runs.
- Trials in total: 12 × 59 + 12 × 60 = 1,428 insertions (our arithmetic).

**Step 3: The eight sensitivity settings, one at a time.**

| Strategy | Primary | Variants |
| --- | --- | --- |
| S2 | θ = 0.6 | θ = 0.4, θ = 0.5 |
| S3 | k = 10, efSearch = 128 | k = 5, k = 20, efSearch = 64, efSearch = 256 |
| S4 | (5, 10) | (2, 5), (10, 20) |

**Step 4: Why one at a time.** Changing one parameter while holding the others at primary values shows how much the conclusions depend on that choice. It is a description, not a search for a better setting.

**Step 5: Per-trial procedure.** Prepare the graph, insert one concept with the strategy under test, record time, calls and (in accuracy mode) precision, recall and shortlist recall, then repeat with a different concept.

**Step 6: Why one run and 10 trials.** Time and API cost. The consequence is that no hypothesis tests are run and run-to-run variation is not established. One observed example: two runs of the same DSA configuration differed by 0.025 micro-F1 (0.4859 versus 0.5111).

**Step 7: Rules that protect fairness.** All parameters were fixed before running. Sizes follow the same log-spaced progression for every strategy.

### Slide 26: Measures and Analysis (about 2 min)

**Script**

“For cost we measure wall-clock time per insertion and LLM calls per insertion. For accuracy we use precision, recall and F1, micro-averaged. We also track shortlist recall: the share of true neighbors that narrowing keeps. To judge scaling, we fit the slope of log cost against log graph size. A slope below 0.1 is approximately flat, 0.1 to 0.9 is sub-linear, and above 0.9 is approximately linear. We describe results with 95% bootstrap intervals, and we run no hypothesis tests.”

**Background**

Each measure is explained with a tiny example. Use the examples in answers.

**Cost measures.**
- *Time per insertion* = shortlist time + decision time + apply time + update time. It includes backoff time when a call is retried, which matters for a few trials (slide 31).
- *LLM calls per insertion* = one per shortlisted candidate.

**Accuracy measures (worked example on slide 12).**
- Precision = correct proposals ÷ all proposals. Recall = correct proposals ÷ all true links. F1 combines them.
- *Micro* pools all trials, so concepts with many links weigh more. *Macro* averages per-concept scores, so each concept counts equally. We report micro as the headline.
- A link in the wrong direction is both a false positive and a miss.

**Shortlist recall, and why it is a ceiling.**
- Fraction of the concept's true neighbours (linked in either direction) that the shortlist contains. It measures what narrowing throws away before the LLM sees anything.
- Whatever the shortlist drops cannot be recovered, so final recall can never exceed shortlist recall.
- Random baseline: pick min(k, m) concepts at random from the m present. Expected shortlist recall = min(k, m) ÷ m. On DSA with k = 10 and m = 28 that is 0.357. On Metacademy with m = 140 it is 0.071.

**Scaling: the log-log slope, from first principles.**
1. Suppose cost grows like cost ≈ c × n^s.
2. Take logs of both sides: log(cost) = log(c) + s × log(n).
3. That is a straight line whose slope is s. So the slope is the exponent.
4. What the exponent means: doubling n multiplies cost by 2^s. Slope 1: cost doubles (linear). Slope 0: no change (flat). Slope 0.5: cost grows about 1.4 times.
5. We fit a line through six points of log(mean cost) against log(n).
6. Bins (a convention of this study, to be reconciled with the adviser): below 0.1 is approximately flat, 0.1 to 0.9 is sub-linear, above 0.9 is approximately linear.
7. Limits: the fit needs positive means, so if some size averages zero calls the slope is undefined and the plan forbids clamping.

**Uncertainty: the 95% bootstrap interval.** With 10 trial times at one size, resample those 10 values with replacement, compute the mean, repeat 10,000 times, and take the middle 95% of the results. It shows how much the mean could vary given only these trials. It is not a significance test.

**Descriptive, not inferential.** We report what happened. We do not claim a strategy is "significantly" different from another.

### Slide 27: Decision and Ranking Framework, post hoc (about 2 min)

**Script**

“This framework was defined after the Chapter IV measurements were available, and we label it that way. First, three gates. G1: the shortlist recall must beat a random shortlist. G2: at most 50 LLM calls per insertion at n of 2,000. G3: the strategy must not be beaten on both calls and F1 by another strategy. A strategy is classed as Effective, Conditionally effective, or Not effective. Then we rank strategies with a weighted score of F1 and the log of calls under three weight scenarios, plus a 20,000-draw weight sweep and a TOPSIS cross-check.”

**Background**

This framework was written after the results existed, and we say so. Build it in the order a reader would: why it is needed, the gates, dominance, then weighted ranking.

**Step 1: Why we need a framework.** "Better" has two ingredients here, cost and accuracy, and no published criterion says what is adequate. Without stated rules, a claim like "S3 is better" rests on the author's reading. The framework states the rules and applies them mechanically.

**Step 2: The three gates (minimum levels).** A gate is a pass or fail bar applied before any weighting.
- **G1, beats chance.** Shortlist recall must beat the random baseline min(k, m) ÷ m on every corpus. Not assessable for S2 (no shortlist cap) and not applicable to S1 (the shortlist is the whole graph).
- **G2, practical cost.** At most 50 LLM calls per insertion at n = 2,000. The 50 comes from the upper end of Funk et al.'s 22–50 prompts. It is a reference point from another task, not a standard.
- **G3, not dominated.** No other strategy is at least as cheap and more accurate, on either corpus, using a 0.025 F1 margin.

**Step 3: Classes.** Effective: passes every gate and G1 is assessable. Conditionally effective: passes every assessable gate, but G1 cannot be assessed. Not effective: fails any assessable gate.

**Step 4: Dominance, with an example.** S3 (10 calls, F1 0.294) versus S1 (140 calls, F1 0.143) on Metacademy: fewer calls and higher F1, so S3 dominates. S3 versus S1 on DSA: S1 has higher F1 (0.586 versus 0.511) but more calls (28 versus 10), so neither dominates. That is a trade-off. Differences in F1 under 0.025 are labelled "not distinguishable". The margin is the one observed run-to-run difference.

**Step 5: Weighted score, with a full worked example (DSA, S3, balanced).**
- F1 values on DSA: S1 0.586, S2 0.148, S3 0.511, S4 0.271. Min-max scaling puts the lowest at 0 and highest at 1. For S3: (0.511 − 0.148) ÷ (0.586 − 0.148) = 0.829.
- Calls on DSA (accuracy runs): S1 28, S2 0.76, S3 10, S4 6.97. Take log10(1 + calls): 1.462, 0.246, 1.041, 0.902. Scale and reverse so cheaper is better. For S3: 1 − (1.041 − 0.246) ÷ (1.462 − 0.246) = 0.346.
- Balanced (0.5 accuracy, 0.5 cost): 0.5 × 0.829 + 0.5 × 0.346 = 0.587, matching Table 4.9.
- Why the log: calls span three orders of magnitude (0.8 to 2,000 at n = 2,000), and a linear scale would let brute force flatten the other three.
- Why only calls, not time also: time follows calls (slide 31), so weighting both would count the same cost twice.

**Step 6: Weight scenarios and the sweep.** Three declared scenarios: accuracy-first (0.7 accuracy, 0.3 cost), balanced (0.5, 0.5), cost-first (0.3, 0.7). The sweep draws the accuracy weight uniformly 20,000 times with seed 42 and counts how often each strategy takes each rank, so no conclusion rests on one weighting.

**Step 7: TOPSIS and Kendall's tau.** The thesis specifies a TOPSIS cross-check (rank by closeness to an ideal point) and Kendall's tau to compare rankings. Chapter IV does not report TOPSIS or tau results, so do not quote any. If asked, say the cross-check is specified in Section 3.6 and its results are not part of the current Chapter IV tables.

**Step 8: Why gates come first.** A weighted sum is compensatory: a very good score on one criterion can offset a very bad one. Gates stop that.

**Step 9: Conventions, stated openly.** The log transform, the gate rules, the 50-call reference and the weight scenarios are choices of the authors, not published standards. Min-max scores also depend on which four strategies are in the set.

**Before presenting.** Tables 4.9 and 4.10 are marked in the revision notes as regenerated from a scratch script. Confirm they match the analysis pipeline output before the defense.

**Handoff:** “With the design in place, my groupmate will present what we found.”


---

# Member 3 (Slides 28–34)

### Slide 28: Chapter IV, Results and Discussions, initial result (about 0.5 min)

**Script**

“Chapter IV presents our initial results. They are organized around the four research questions: cost scaling, placement accuracy, comparison of the strategies, and the bucket-cost premise.”

**Background**

Before the numbers, learn how to read them. Every result slide uses the same conventions.

**Step 1: Where each question is answered.** RQ1 cost: Section 4.2 (slides 31–32). RQ2 accuracy: Section 4.3 (slides 33–34). RQ3 comparison: Section 4.4 (slides 35–37). RQ4 bucket premise: Section 4.5 (slide 38). Limits: 4.6 (slide 39). Summary: 4.7 (slide 40).

**Step 2: Three labels for how results were decided.**
- *Pre-registered:* the analysis was frozen before the sweep data was opened.
- *Post hoc:* added after the results were seen (the gates and ranking in Section 4.4.1, and a timing sensitivity set that excludes retried and peak-hour trials).
- *Exploratory:* extra looks, such as the slope fit on positive-mean sizes where the planned fit is undefined.
- Nothing post hoc or exploratory replaces a pre-registered result.

**Step 3: How to read a result table.**
- Values are means over trials with a 95% bootstrap interval where shown (slide 26).
- Sweep tables come from synthetic graphs and report cost only. Accuracy tables come from the two gold graphs.
- Every configuration is a single run, so differences between strategies are descriptive.

**Step 4: What the phrase "initial result" covers.** The measurements are complete for the 24 planned runs. "Initial" refers to the stage of the thesis, not to partial data.

**Disclosure you should know.** The accuracy-mode summaries were seen before the analysis plan was frozen, so accuracy-side choices (per-corpus reporting and the 0.025 labelling margin) were not made blind. A first draft of the analysis pipeline was run on the real results before the final one was accepted. The recorded answer is that its output was looked at, label overlaps were noticed, no numbers or results were noticed, and no change was requested because of it.

### Slide 29: Data Collected (about 1.5 min)

**Script**

“We collected 24 runs across 12 configurations on three data sources. The 24 runs are 12 accuracy-mode runs and 12 size-sweep runs, and the 12 configurations are 4 primary settings plus 8 sensitivity settings. Accuracy runs have 59 trials, and sweep runs have 60. All 24 runs passed the validation gate. The three data sources are the DSA gold graph, 29 expert-verified concepts, used for 29 leave-one-out trials; the Metacademy gold graph, 141 concepts, used for 30 trials; and the synthetic concept pool of 2,254 names, which has no ground truth and is used only for cost at n from 50 to 2,000, with 10 trials per size.”

**Background**

Think of this slide as an inventory of what was collected. Learn the hierarchy and the sums, then the quality controls.

**Step 1: The hierarchy and the sums.**
- 12 configurations = 4 primary + 8 sensitivity (slide 25).
- Each configuration runs in 2 modes, accuracy and sweep: 12 + 12 = **24 runs**.
- Accuracy run: 29 DSA + 30 Metacademy = **59** trials. Sweep run: 6 sizes × 10 trials = **60** trials.
- Trials in total: 12 × 59 + 12 × 60 = 1,428 (our arithmetic).

**Step 2: Three data sources.**
- DSA gold graph (29 concepts): 29 leave-one-out trials.
- Metacademy gold graph (141 concepts): 30 trials.
- Synthetic pool (2,254 names): cost only, 10 trials per size at 50, 100, 200, 500, 1,000 and 2,000.

**Step 3: The validation gate.** An automated check that a run completed correctly before its data may be used. All 24 runs passed. 20 passed outright and 4 passed as resumed runs, meaning they were interrupted and then resumed: accuracy brute force, sweep brute force, sweep bounded bucket (10, 20) and sweep embedding threshold θ = 0.5. No trial remained failed in any run.

**Step 4: Why resumed runs are not a problem.** Resuming continues the same configuration from where it stopped. Brute force and the threshold strategy were also first run at sizes 50–500 and then extended to all six sizes before analysis, without changing the design (Amendment 3). Failed-then-succeeded trials are listed, and none is dropped or imputed.

**Step 5: Reproducibility details if asked.** Accuracy runs were executed at commit 3323bfb and sweep runs at ad81414. Amendment 2 accepts both because the files that affect results did not change between them. Tables and figures were generated at 554bde3 by one script from validated data, and an independent consistency check of 3,399 items reported no failures.

**Step 6: Pre-registered versus post hoc, restated.** The analysis plan was frozen before the sweep data was opened. The accuracy summaries had been seen first. The thesis discloses both.

**Careful.** "All 24 runs passed the validation gate" means the runs completed correctly. It does not mean the results are statistically established.

### Slide 30: Setup, the four strategies compared (about 1 min)

**Script**

“A quick reminder of the setup. S1 judges every existing node, up to n calls. S2 keeps nodes with cosine similarity above 0.6, up to n calls and uncapped. S3 keeps the top 10 using a FAISS HNSW index, so 10 calls. S4 uses bounded buckets of 5 to 10 nodes, so at most 10 calls. All four share the same decision step, so differences come from the narrowing mechanism. Results are means with 95% bootstrap intervals, and we run no hypothesis tests.”

**Background**

This slide is a refresher so the results make sense. Keep it quick, but check that you can explain each row.

**Step 1: Rebuild the strategies in one line each.**
- S1: judge every existing node, up to n calls.
- S2: keep nodes with cosine similarity above 0.6, up to n calls, often none.
- S3: keep the top 10 by similarity using a FAISS HNSW index, 10 calls.
- S4: compare only with the 5–10 members of the new concept's bucket, at most 10 calls.

**Step 2: What "primary" and "sensitivity" mean.** The primary setting is the one fixed in advance (θ = 0.6, k = 10, buckets (5, 10)). Sensitivity settings change one parameter to show how much conclusions depend on it. Slides 31–33 and 35–38 use the primary settings unless they say otherwise.

**Step 3: Why the decision step is repeated here.** Same model (DeepSeek), temperature 0, one call per candidate, one at a time. So differences come from the narrowing mechanism.

**Step 4: What a mean with a bootstrap interval means.** Slide 26 explains it. Short version: take the trials we have, resample them 10,000 times, and see how much the mean moves. It shows spread and is not a significance test.

**Step 5: Reminder of the four messages.** Single insertions. Only narrowing differs. Descriptive results. Post hoc ranking.

### Slide 31: RQ1, wall-clock time at n = 2,000 (about 2.5 min)

**Script**

“Our first question is how time per insertion changes as the graph grows. At n of 2,000, one brute-force insertion takes 1,713 seconds, which is about 29 minutes. S3 takes 8.28 seconds and S4 takes 5.64 seconds. S2 takes 0.94 seconds, but only because most of its trials make no call at all. The slopes agree: brute force is approximately linear at 0.96, while S3 and S4 are approximately flat, at minus 0.02 and 0.008. Time follows calls. Each LLM call takes about 0.8 to 0.9 seconds, and the shortlist step takes under 0.03 seconds. At n of 2,000, brute force is about 207 times slower than S3 and 304 times slower than S4. So the answer to RQ1: linear for brute force, flat for the capped strategies, and call-dependent for the threshold.”

**Background**

Slide 31 is the headline cost result. Read it in three steps: the picture, the shape of each curve, and the reason behind it.

**Step 1: The raw picture at n = 2,000.**

| Strategy | Mean time per insertion | Reading |
| --- | --- | --- |
| S1 brute force | 1,713.10 s (about 28.5 min) | slope 0.9605, approximately linear |
| S2 θ = 0.6 | 0.938 s | only because most trials make no call |
| S3 k = 10 | 8.277 s | slope −0.0201, approximately flat |
| S4 (5, 10) | 5.638 s | slope 0.0084, approximately flat |

At n = 2,000 brute force is about 207 times slower than S3 (1,713.1 ÷ 8.277) and about 304 times slower than S4 (1,713.1 ÷ 5.638). These ratios are computed from the means.

**Step 2: What the slope tells us.** Slide 26 explains slopes: 1 is linear and 0 is flat. From n = 50 to n = 2,000, a 40-fold increase, S1's time grows about 40 times in a straight line. S3's and S4's times do not trend at all.

**Step 3: Why time follows calls.** The shortlist step (embedding, similarity scan, HNSW search, hashing) takes under 0.03 seconds for S2, S3 and S4, and under 0.001 seconds for brute force. So time is essentially the decision step, which is number of calls times time per call.
- Time per call at n = 2,000: S1 0.857 s (1,713.1 ÷ 2,000), S3 0.828 s (8.277 ÷ 10), S4 0.805 s (5.638 ÷ 7.0), S2 at θ = 0.4 0.838 s (11.318 ÷ 13.5).
- So the strategies differ in cost almost entirely because they make different numbers of calls.

**Three traps in the table (all in Section 4.2.2).**
- *S1's slope is 0.96, not 1.* One retried trial at n = 50 inflated that point (mean 58.63 s, versus 35.75 s without it). Excluding retried trials gives 1.0558 with R² 0.998. Both are approximately linear.
- *S3's interval excludes zero.* The interval (−0.0324 to −0.0079) does not contain zero, so "approximately flat" holds because the slope is tiny (about 0.02 across a 40-fold range), not because the interval contains zero. The mean wanders between 7.9 and 9.5 seconds with no steady trend.
- *S2's weak fit.* R² is only 0.461. Most trials make no call and take about 0.01 s, while the few that do take about a second each, so each size's mean mostly reflects how many trials happened to call. "Sub-linear" is a weak description. The means are more informative than the label.

**Step 4: Peak hours and retries.** One sweep trial ran inside DeepSeek's peak window. With 10 trials per size, no claim is made about a peak-hour effect. Excluding retried trials and that trial changes no flatness category.

**Answer to RQ1 in one line.** Linear for brute force, flat for the two capped strategies, and call-dependent for the threshold.

### Slide 32: RQ1, LLM calls per insertion (about 2 min)

**Script**

“This table shows LLM calls per insertion by graph size. Brute force needs exactly n calls, the linear cost that Funk and colleagues warned about. S3 always makes 10 calls, and S4 averages between 6.6 and 7.5, because their shortlists are capped. S2 depends on how many nodes pass the threshold. At the primary threshold of 0.6 it averages at most 0.8 calls at n of 2,000, and at a looser threshold of 0.4 it reaches 13.5 calls, about 0.7% of the nodes. Its slope at 0.6 is undefined because some sizes have zero average calls.”

**Background**

Calls are the cause and time is the effect, so this table explains the previous slide. Learn it strategy by strategy.

**The table (mean LLM calls per insertion, sweep runs).**

| Strategy | 50 | 100 | 200 | 500 | 1,000 | 2,000 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 brute force | 50 | 100 | 200 | 500 | 1,000 | 2,000 |
| S2 θ = 0.6 (primary) | 0.0 | 0.1 | 0.1 | 0.0 | 0.7 | 0.8 |
| S2 θ = 0.5 | 0.0 | 0.3 | 0.6 | 1.3 | 2.5 | 3.0 |
| S2 θ = 0.4 | 0.2 | 0.6 | 1.0 | 4.3 | 7.8 | 13.5 |
| S3 k = 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| S4 (5, 10) | 6.6 | 7.5 | 7.1 | 7.1 | 6.8 | 7.0 |

**Step 1: S1.** Exactly n calls at every size, so the slope is 1.0000.

**Step 2: S3.** Always 10. It prints as "0, constant" because the fitted value is floating-point noise on a constant series.

**Step 3: S4.** Between 6.6 and 7.5, below the cap of 10, with a fitted slope of −0.0004 (interval −0.0433 to 0.0424). Buckets hold 5 to 10 members, and the average sits in the middle because segments are not always full.

**Step 4: S2 needs the most care.** Calls depend on how many existing nodes pass the threshold.
- At θ = 0.6 the average is at most 0.8 calls at n = 2,000.
- At θ = 0.4 it reaches 13.5 calls, about 0.7% of the 2,000 nodes, and between 0.4% and 0.9% of n at every size.
- *Slope versus magnitude.* The θ = 0.4 slope is 1.1535 (approximately linear), so calls grow roughly in proportion to n, but the level is tiny. Slope describes growth rate, not size.
- *Undefined slope.* A log-log fit needs positive values, and θ = 0.5 and 0.6 have sizes with zero mean calls. The plan forbids clamping, so no flatness category is given. An exploratory fit on the positive sizes gives 0.7966 (θ = 0.5) and 0.8095 (θ = 0.6). The θ = 0.6 interval is optimistic because only 4,123 of 10,000 resamples were usable. Quote the counts, not that slope.

**Step 5: The "so what".** Funk et al. warned that brute force needs a huge number of queries, and the S1 row shows exactly that: calls equal the graph size. Capping the shortlist removes that dependence.

### Slide 33: RQ2, accuracy of the primary configurations (about 2.5 min)

**Script**

“Our second question is whether placement accuracy holds up as the graph grows. We can answer it only at two sizes: 29 concepts on DSA and 141 on Metacademy. On DSA, brute force has the best F1 at 0.586, using 28 calls, and S3 follows at 0.511 with 10 calls. On Metacademy the order changes: S3 is best at 0.294, S2 is next at 0.270, and brute force falls to 0.143. Look at brute force: its recall stays about the same, 0.630 and 0.624, but its precision falls from 0.548 to 0.081. The last column, shortlist recall, shows how much of the true neighborhood each shortlist keeps. It is 1.0 for brute force, about 0.5 for S3, and much lower for S2 and S4. These are micro-averaged, one run each.”

**Background**

This is the densest table in the deck. Learn the columns first, then the three patterns, then the numbers.

**Step 1: The columns.** Calls are LLM calls per insertion. Precision, recall and F1 are micro-averaged over all trials. Shortlist recall is the share of true neighbours that narrowing kept. Each cell is one run.

**Step 2: The table (primary configurations).**

| Corpus | Strategy | Calls | Precision | Recall | F1 | Shortlist recall |
| --- | --- | --- | --- | --- | --- | --- |
| DSA (29 trials) | S1 | 28.0 | 0.548 | 0.630 | **0.586** | 1.000 |
| | S2 θ = 0.6 | 0.76 | 0.643 | 0.083 | 0.148 | 0.111 |
| | S3 k = 10 | 10.0 | 0.639 | 0.426 | 0.511 | 0.528 |
| | S4 (5, 10) | 6.97 | 0.594 | 0.176 | 0.271 | 0.259 |
| Metacademy (30 trials) | S1 | 140.0 | 0.081 | 0.624 | 0.143 | 1.000 |
| | S2 θ = 0.6 | 1.13 | 0.594 | 0.174 | 0.270 | 0.202 |
| | S3 k = 10 | 10.0 | 0.245 | 0.367 | **0.294** | 0.505 |
| | S4 (5, 10) | 7.37 | 0.149 | 0.092 | 0.114 | 0.147 |

**Step 3: Rank order changes.** DSA by F1: S1, S3, S4, S2. Metacademy: S3, S2, S1, S4.

**Step 4: Three facts that explain most of it.**
- *Brute force keeps its recall but loses precision.* Recall 0.630 then 0.624. Precision 0.548 then 0.081.
- *A recall ceiling.* Recall never exceeds shortlist recall.
- *Density.* About 6% of ordered pairs are positive in DSA (54 of 840) and about 1.6% in Metacademy (318 of 19,740). With few true links and many candidates, there are many chances to produce a false positive.

**Step 5: Random baselines for shortlist recall.** 0.357 on DSA and 0.071 on Metacademy for k = 10. S3 is above both. S4 is below on DSA (0.259 versus 0.357) but above on Metacademy (0.147 versus 0.071).

**Step 6: Absolute level is modest.** No cell meets the pilot bar (F1 ≥ 0.50 and recall ≥ 0.70). The only cell with F1 ≥ 0.50 and recall ≥ 0.50 is S1 on DSA.

**Careful.** One run per cell, so small differences are not established.

### Slide 34: RQ2, why accuracy differs across strategies (about 2.5 min)

**Script**

“There are three reasons accuracy differs. First, brute force over-links. Its recall is steady at 0.630 and 0.624, but precision falls from 0.548 to 0.081 when 140 candidates are judged one by one. Second, narrowing trades recall for precision. S2 has high precision, 0.643 and 0.594, but recall of only 0.083 and 0.174, because at a threshold of 0.6 most concepts reach no decision. Third, the decision step caps recall. Recall never exceeds shortlist recall, and the decision step labels only 62% to 86% of the shortlisted true neighbors correctly. So F1 is lower on Metacademy than on DSA for S1, S3 and S4, but domain and edge density differ too, so size alone cannot be blamed.”

**Background**

This slide answers "why", so every claim needs a mechanism. Use the mini-explanations below.

**Reason 1: Brute force over-links on the larger graph.**
- *Precision made concrete.* Precision 0.081 means only about 8 of every 100 proposed links are correct, or roughly 12 proposals for every correct one (1 ÷ 0.081).
- *Why it happens.* Judging 140 candidates one at a time gives the model 140 chances to say "prerequisite" when it should say NONE. With only about 1.6% of pairs truly positive, even a small error rate per pair produces many false links.
- *Transitive closure, from an example.* If A→B and B→C are in the gold graph, then A→C follows by chaining (the closure). If the model says A is a prerequisite of C, the gold label may be 0 yet the answer is defensible. In the DSA pilot 34 of 58 false positives were of this kind, so DSA precision is understated. That analysis was not repeated for Metacademy.

**Reason 2: Narrowing trades recall for precision.**
- S2 has the highest precision on DSA (0.643) and high on Metacademy (0.594), but recall of only 0.083 and 0.174. At θ = 0.6 most insertions find no candidate above the threshold, so no decision is made. Shortlist recall is 0.111 and 0.202.
- S3 keeps about half the true neighbours (0.528 and 0.505), with moderate precision and recall.
- This echoes Aytekin and Saygın [6]: embeddings favour recall, LLMs favour precision.

**Reason 3: The decision step caps recall too.**
- Recall ÷ shortlist recall tells you what share of shortlisted true neighbours the model labels correctly. S1 DSA 0.630, S1 Metacademy 0.624, S3 DSA 0.807, S3 Metacademy 0.727, S2 DSA 0.748, S2 Metacademy 0.861, S4 DSA 0.680, S4 Metacademy 0.626.
- So the range is about 0.62 to 0.86. A large part of the loss happens in the decision step itself, including direction errors, and not only in narrowing.

**Confounding, explained.** The two graphs differ in size, domain and density at the same time. So we cannot say size alone caused the F1 change from DSA to Metacademy. That is why the slide says "domain and density differ too".

**Sensitivity (if asked).** Looser settings raise recall at a cost in calls. On DSA S3's F1 rises with k (0.374, 0.511, 0.569 for k = 5, 10, 20). On Metacademy it falls (0.368, 0.294, 0.266), because precision drops faster than recall rises (0.402, 0.245, 0.186). The efSearch variants return identical shortlist recall, so their small F1 differences (at most about 0.028) come from the decision step and are about the size of the single run-to-run difference of 0.025.

**Handoff:** “That covers cost and accuracy. My groupmate will now compare the strategies and test the bucket premise.”


---

# Member 4 (Slides 35–42)

### Slide 35: RQ3, trade-offs on DSA, domination on Metacademy (about 2.5 min)

**Script**

“Our third question compares the four strategies under identical conditions. We use dominance: one strategy dominates another if it makes no more calls and has a higher F1. On DSA, every pair of strategies is a trade-off. Brute force has the best F1, 0.586, at 28 calls, but it gains only 0.075 F1 over S3 for 18 more calls. On Metacademy, S3 dominates brute force: F1 is 0.151 higher with 130 fewer calls. S2 dominates both brute force and S4. S3 versus S2 is not distinguishable, because the F1 difference of 0.0246 is inside our 0.025 margin. And S2’s low call count is a recall cost, not a free saving: most insertions find no candidate above the threshold, so its shortlist recall is only 0.111 and 0.202. The largest graph reverses the DSA picture, because brute force is dominated outright.”

**Background**

This slide compares strategies on cost and accuracy together. Learn dominance first, then read the table pair by pair.

**Step 1: Dominance, from first principles.** Put each strategy on two axes: calls (lower is better) and F1 (higher is better).
- A dominates B if A makes no more calls and has higher F1.
- If A is cheaper but B is more accurate, neither dominates. That is a trade-off.
- Differences in F1 under 0.025 are labelled "not distinguishable". That margin is the single observed run-to-run difference (0.4859 versus 0.5111), fixed before the sweep data was opened.

**Step 2: The numbers feeding every comparison.**

| Corpus | S1 | S2 | S3 | S4 |
| --- | --- | --- | --- | --- |
| DSA: calls / F1 | 28.0 / 0.586 | 0.76 / 0.148 | 10.0 / 0.511 | 6.97 / 0.271 |
| Metacademy: calls / F1 | 140.0 / 0.143 | 1.13 / 0.270 | 10.0 / 0.294 | 7.37 / 0.114 |

**Step 3: DSA, every pair is a trade-off.** The most accurate strategy (S1, 0.586) is also the most expensive (28 calls), and every cheaper strategy gives up F1. S1 gains 0.075 F1 over S3 for 18 more calls (28 − 10).

**Step 4: Metacademy, brute force is dominated.**
- S3 dominates S1: F1 is 0.151 higher with 130 fewer calls (140 − 10).
- S2 dominates S1 and S4: fewer calls and higher F1.
- S3 versus S2: ΔF1 = 0.0246, which is inside the 0.025 margin, so "not distinguishable". S2 uses 1.13 calls where S3 uses 10.
- S4 versus S1: S4 is cheaper but 0.030 lower in F1, so a trade-off.
- S4 is not dominant over any strategy on either corpus.

**Step 5: Be honest about the S3 versus S2 label.** 0.0246 is only 0.0004 below the margin, and a margin of 0.02 would label S3 higher. No interval was computed for the difference, and none is claimed.

**Step 6: S2's low call count is a recall cost, not a free saving.** Most insertions find no candidate above θ, so no decision is made. Its shortlist recall is only 0.111 and 0.202. Whether that is acceptable depends on how much an application can tolerate missed relationships, which the study does not assess.

**One-line takeaway.** The largest graph reverses the DSA picture: the strategy that looks best on 29 nodes (brute force) is dominated on 141.

### Slide 36: RQ3, only S3 passes every gate (about 2 min)

**Script**

“Applying the three gates to the primary configurations, only S3 passes every gate and is classed Effective. S2 passes the gates that can be assessed, but G1 cannot be assessed for it because it has no shortlist cap, so it is Conditionally effective. S1 fails the cost gate at 2,000 calls and is dominated on Metacademy. S4 fails the random baseline on DSA and is dominated on Metacademy, so both are Not effective. This is post hoc and single-run. And no strategy meets the pilot’s absolute accuracy bar of F1 at least 0.50 and recall at least 0.70, so S3 is best only in a relative sense.”

**Background**

Now apply the three gates from slide 27 to the primary configurations. Learn the table, then why the classes are robust, then what they do not mean.

**Step 1: Recall the gates.** G1: shortlist recall beats a random shortlist. G2: at most 50 calls at n = 2,000. G3: not dominated on either corpus (0.025 margin).

**Step 2: The table, strategy by strategy.**

| Strategy | G1 | G2 | G3 | Class |
| --- | --- | --- | --- | --- |
| S1 | Not applicable (full shortlist) | Fail (2,000 calls) | Fail on Metacademy (dominated by S3 and S2) | Not effective |
| S2 θ = 0.6 | Not assessable (no cap) | Pass (0.8 calls) | Pass on both | Conditionally effective |
| S3 k = 10 | Pass (0.528 vs 0.357; 0.505 vs 0.071) | Pass (10 calls) | Pass on both | **Effective** |
| S4 (5, 10) | Fail on DSA (0.259 vs 0.357); pass on Metacademy (0.147 vs 0.071) | Pass (7.0 calls) | Fail on Metacademy (dominated by S2) | Not effective |

**Step 3: Why S2 is "conditionally" effective.** G1 cannot be assessed because S2 has no shortlist cap, so the random baseline min(k, m) ÷ m is undefined. It passes every gate that can be assessed, but its recall is low, so the class carries that condition.

**Step 4: Why S4 is not effective.** It fails G1 on DSA and G3 on Metacademy. Against a random draw of the same average size (6.97 ÷ 28 = 0.249) S4's 0.259 is about level on DSA, but the class does not change because G3 also fails.

**Step 5: Robustness of the classes (Section 4.4.1).**
- G2: the four strategies make 0.8, 7.0, 10 and 2,000 calls at n = 2,000, so any limit from 10 to 1,999 gives the same result.
- G1: S3 always returns 10 candidates, so its size-matched baseline equals the pre-registered one.
- G3: S1 and S4 are dominated on Metacademy for any margin up to 0.15 F1, and no margin makes S2 or S3 dominated.

**Step 6: What "Effective" does and does not mean.** It is a label for these measurements under criteria the authors set after the results. It is not a statistical finding, and it is not a statement about absolute quality.

**Step 7: Absolute accuracy, kept separate.** No cell meets the pilot bar (F1 ≥ 0.50 and recall ≥ 0.70). S3 on DSA has F1 0.511 but recall 0.426, below the pilot's fail threshold of 0.50, and on Metacademy its F1 is 0.294. So S3 is best only in a relative sense.

**Don't say.** "S3 is accurate." Say "S3 is the best available option under these gates, and its accuracy is modest."

### Slide 37: RQ3, S3 is the most stable across weights (about 2.5 min)

**Script**

“If we ask which strategy is best under a weighted score, the answer depends on the weights. On DSA the leader changes: accuracy-first favors brute force at 0.700, balanced favors S3 at 0.587, and cost-first favors S2 at 0.700. On Metacademy, S2 leads in all scenarios, scoring 0.907 to 0.960, with S3 second at 0.726 to 0.883. S2 gains on cost what it lacks in recall. Across 20,000 random weights, S3 is last in under 0.5% of draws, and it is second most often, 60% on DSA and 69% on Metacademy. S4 is first in no draw. So S3 is the most stable choice across weights. These scores are post hoc, single-run, and scaled across only four strategies, so they describe these measurements and not repeated-run differences.”

**Background**

This slide shows how rankings change with the weights. Understand the score first, then the sweep, then the cautions.

**Step 1: Where the scores come from.** Each strategy's F1 and its log of calls are scaled to 0–1 across the four strategies, calls are reversed so cheaper is better, and the two are combined with weights. The worked example for DSA S3 (balanced) is on slide 27: accuracy score 0.829, cost score 0.346, weighted score 0.587.

**Step 2: Table 4.9 (best per row marked).**

| Corpus | Scenario (accuracy / cost) | S1 | S2 | S3 | S4 |
| --- | --- | --- | --- | --- | --- |
| DSA | Accuracy-first (0.7 / 0.3) | **0.700** | 0.300 | 0.684 | 0.335 |
| DSA | Balanced (0.5 / 0.5) | 0.500 | 0.500 | **0.587** | 0.371 |
| DSA | Cost-first (0.3 / 0.7) | 0.300 | **0.700** | 0.491 | 0.407 |
| Metacademy | Accuracy-first | 0.113 | **0.907** | 0.883 | 0.202 |
| Metacademy | Balanced | 0.081 | **0.933** | 0.804 | 0.337 |
| Metacademy | Cost-first | 0.048 | **0.960** | 0.726 | 0.472 |

On DSA the leader changes with the weights (S1, then S3, then S2). On Metacademy S2 leads in every scenario and S3 is second.

**Step 3: Why S2 leads on Metacademy.** It has the fewest calls, so its cost score is the best, and its F1 (0.270) is second. It gains on cost what it lacks in recall (0.174). That is a compensation effect, which is why S2 is read together with the gate table and not from the score alone.

**Step 4: The weight sweep.** Instead of trusting three weight choices, draw the accuracy weight uniformly between 0 and 1, 20,000 times (seed 42), rank the strategies each time, and count how often each takes each rank. The shares are Monte Carlo estimates with a standard error of at most 0.004.

**Step 5: Table 4.10 (shares of draws giving each rank).**

| Corpus | Strategy | Rank 1 | Rank 2 | Rank 3 | Rank 4 |
| --- | --- | --- | --- | --- | --- |
| DSA | S1 | 0.33 | 0.17 | 0.11 | 0.39 |
| | S2 | 0.44 | 0.06 | 0.16 | 0.34 |
| | S3 | 0.23 | 0.60 | 0.17 | 0.00 |
| | S4 | 0.00 | 0.17 | 0.56 | 0.26 |
| Metacademy | S1 | 0.00 | 0.00 | 0.19 | 0.81 |
| | S2 | 0.75 | 0.25 | 0.00 | 0.00 |
| | S3 | 0.25 | 0.69 | 0.06 | 0.00 |
| | S4 | 0.00 | 0.06 | 0.75 | 0.19 |

**Step 6: What "most stable" means.** S3 is last in under 0.5% of draws on both corpora and second most often (60% on DSA, 69% on Metacademy). S1 and S2 swing between first and last on DSA. S4 is first in no draw on either corpus. S3 is not first most often. It is the one that never does badly.

**Step 7: Cautions to state.**
- Post hoc and single-run.
- Min-max scaling depends on the set of four strategies, so adding or removing one can change the scores.
- The scores describe how these measurements order under these criteria. They do not show that the differences would persist in repeated runs.

**Check before presenting.** The revision notes say Tables 4.8–4.10 came from a scratch script and need regenerating in the pipeline. Confirm every number on this slide against the regenerated output. Do not quote any TOPSIS or Kendall figure, since Chapter IV does not report them.

### Slide 38: RQ4, bucket cost does not grow with graph size (about 2 min)

**Script**

“Our fourth question is whether the cost of one insertion stays flat under a bucket-capped strategy. For S4, mean LLM calls stay between 6.6 and 7.5 against a cap of 10, across n from 50 to 2,000. Mean time stays between 5.15 and 5.77 seconds, and the shortlist step takes about 0.01 seconds. The fitted slopes are near zero, minus 0.0004 for calls and 0.0084 for time, and the intervals contain zero. This is consistent with the premise behind the amortized bound in EraRAG: an insertion touches a bounded region of the graph. But there are two cautions. Flat calls are close to guaranteed by the cap, and S3 is equally flat, so flatness is not specific to bucket partitioning. And we tested single insertions, so the amortized bound itself is not tested.”

**Background**

RQ4 tests a specific idea. Be precise about what that idea is and what the evidence can and cannot show.

**Step 1: The claim we are checking.** EraRAG's Theorem 4 says insertion cost should not grow just because the graph grew, because each insertion touches only a bounded bucket. The theorem is about the average cost over a sequence of insertions. We check its premise: that one insertion touches a bounded region, so single-insertion cost stays flat as n grows.

**Step 2: The evidence.** For S4 (5, 10) across n = 50 to 2,000 (a 40-fold increase):
- Mean calls stay between 6.6 and 7.5, against a cap of 10. The largest single-trial count was 10.
- Mean time stays between 5.15 and 5.77 seconds. The shortlist step takes about 0.01 seconds at every size.
- Fitted slopes: −0.0004 for calls and 0.0084 for time. Every interval contains zero, and every category is approximately flat.

**Step 3: The other two bucket settings are flat as well.**

| Setting | Calls slope | Time slope | Calls vs cap |
| --- | --- | --- | --- |
| (5, 10) | −0.0004 | 0.0084 | 6.6 to 7.5 vs 10 |
| (2, 5) | 0.0033 | 0.0170 | 2.7 to 3.2 vs 5 |
| (10, 20) | −0.0149 | −0.0193 (−0.0296 on the clean set) | 12.7 to 15.1 vs 20 |

**Step 4: Two cautions the thesis states.**
- *Flat calls are nearly guaranteed by the cap.* A shortlist capped at 10 cannot exceed 10 calls. The informative evidence is the wall-clock curve and the fact that realised counts sit below the cap.
- *Flatness is not specific to buckets.* S3 is equally flat (calls constant at 10, time slope −0.0201), and S3 and S4 have the same worst-case cap of 10, so the study does not isolate partitioning geometry from capacity.

**Step 5: What this does not show.** Amortized cost over a sequence of insertions. Splits and merges cascading over many insertions. We performed one insertion per trial, and the hyperplane seed was fixed, not varied.

**Safe answer to "so is EraRAG's bound true?"** "We found no growth in single-insertion cost, which is consistent with the premise. The bound itself is about averages over many insertions, and we did not test that."

### Slide 39: Limits of these results (about 1.5 min)

**Script**

“Here is what the results do not show. There is one run per configuration and 10 trials per size, so there are no hypothesis tests. There is one decision model, one prompt, and bare concept names. Accuracy is measured at only two sizes, 29 and 141 concepts, which also differ in domain and density. The synthetic pool is unverified and used for cost only. We tested single, un-amortized insertions, so the amortized bound is untested. And the gates and weights were set post hoc, so the classes label these measurements only.”

**Background**

Know each limit, what it blocks, and what you can still claim. This is the table to rehearse for the question period.

| Limit | What it blocks | What we still claim |
| --- | --- | --- |
| One run per configuration, 10 trials per size, no hypothesis tests | Significance claims; run-to-run variation is not established | Descriptive results with bootstrap intervals |
| One decision model, one prompt, bare concept names | Generalising to other models, prompts or richer node text | The ranking under these fixed conditions |
| Accuracy at only two sizes (29 and 141), different domain and density | Saying size alone causes accuracy change | The observed change between those two graphs |
| Synthetic pool unverified | Any accuracy claim from the pool | Cost scaling from 50 to 2,000 nodes |
| Single, un-amortized insertions | Testing amortized bounds | The bounded-region premise for single insertions |
| Gates, thresholds and weights set post hoc | Calling the classes statistical findings | Labels on these measurements, with robustness checks |

**Further points you may be asked about.**
- *Timing hardware.* Timings come from one laptop (Intel i5-8250U, 4 cores, 8 threads) with no controlled load. Latencies in the two S3 primary accuracy runs differed by up to 3.7 times for unexplained reasons, so accuracy-run latencies are never used for cost claims. Cost claims come from the sweep runs.
- *Index recall.* The HNSW recall figures (0.841, 0.968, 0.999 for efSearch 64, 128, 256) come from random Gaussian vectors, not from our corpora. On the real corpora the observable is shortlist recall against gold neighbours.
- *Parameters.* No θ stricter than 0.6 was run. M = 16 and efConstruction = 200 were fixed in advance.
- *Procedure disclosure.* Accuracy summaries were seen before the analysis plan was frozen, and a first-draft pipeline was run on real results before the final one was accepted.
- *Model alias.* The provider can change the model behind an alias.

**How to answer.** Name the limit, say which claim it blocks, then say what we still claim, as on slide 13.

### Slide 40: Summary of findings (about 1.5 min)

**Script**

“To summarize by research question. RQ1: brute force grows linearly, 1,713 seconds at n of 2,000, while ANN retrieval and bounded buckets stay flat, and the threshold grows with the number of passing nodes, from a small base. RQ2: F1 is lower on the 141-node graph for S1, S3 and S4, but domain and density are confounded, and brute force over-links with a precision of 0.081. RQ3: only S3 is effective, S2 is conditionally effective, and S1 and S4 are not, and no strategy meets the pilot’s absolute accuracy bar. RQ4: calls and time did not grow with graph size, consistent with the premise, and the amortized bound remains untested.”

**Background: the answer to each question, then likely panel questions**

**Part 1: One sentence per research question, with its evidence and its caveat.**

| RQ | Answer | Key evidence | Caveat |
| --- | --- | --- | --- |
| RQ1 | Brute force grows linearly. ANN and bounded buckets stay flat. The threshold depends on how many nodes pass. | 1,713 s at n = 2,000; slopes 0.96, −0.02, 0.008 | Single insertions; the θ = 0.6 fit is undefined |
| RQ2 | F1 is lower on the 141-node graph for S1, S3 and S4, but not for S2. | S1 precision 0.548 to 0.081 | Domain and density are confounded with size |
| RQ3 | Only S3 is effective. S2 is conditionally effective. S1 and S4 are not. | Gate table, dominance, weight sweep | Post hoc and single-run; no strategy meets the pilot bar |
| RQ4 | Cost did not grow with n for the bucket strategy. | Calls 6.6–7.5 of cap 10; slopes near zero | Premise only, not the amortized bound; S3 equally flat |

**Part 2: Likely questions, grouped, with short answers.**

*Problem and novelty*
- **Why does this matter?** Knowledge graphs grow, and each new concept costs one LLM call per existing node if done naively. We measured how that cost behaves and which shortlisting method controls it.
- **How do you know no one did this?** We do not. None of the studies we reviewed did, from a structured but non-exhaustive search, and the thesis says so.

*Design and fairness*
- **Why one decision step for all strategies?** So differences can be attributed to the narrowing method alone.
- **Why DeepSeek, and why bare names?** One model and one prompt keep the comparison controlled, and bare names keep the focus on narrowing. Both are stated limitations.
- **Why did you fix the parameters?** To avoid tuning on the evaluation data. The sensitivity runs show how much conclusions depend on them.
- **Did you tune the prompt?** Only before the strategies were compared, using probes and pairs outside the evaluation graphs. After the conditional pilot verdict it was frozen.

*Results*
- **Which strategy do you recommend?** S3 (ANN) is the best available in a relative sense: only one to pass all gates and the most stable across weights. But no strategy meets the pilot's absolute accuracy bar, and on DSA the best choice depends on how much accuracy is weighted.
- **Why does brute force do best on DSA but worst on Metacademy?** On 28 candidates the full shortlist has the highest recall and few chances to over-link. On 140 candidates precision collapses to 0.081.
- **Why is S2 so cheap?** Because at θ = 0.6 most insertions find no candidate above the threshold. Its shortlist recall is 0.111 and 0.202.
- **Is S3 really better than S2 on Metacademy?** The F1 gap is 0.0246, inside our 0.025 margin, so we label them not distinguishable. S2 uses fewer calls but has a lower shortlist recall.
- **Is the bucket bound proven?** No. We found that cost did not grow for single insertions, which is consistent with the premise.

*Validity*
- **Why no statistical tests?** One run per configuration and 10 trials per size give no basis for inference. We describe and give bootstrap intervals.
- **Is the ranking biased because it was set after the results?** It could be, which is why it is labelled post hoc, and why we show robustness: any G2 limit from 10 to 1,999 calls, G3 margins to 0.15, and a weight sweep.
- **Would another model or prompt change the results?** Possibly. We used one model and one prompt, and we state it as a limitation.
- **Where are the conclusions and recommendations?** The manuscript is at the initial-results stage and ends at the summary of findings in Section 4.7.

*Future work*
- **What would you do next?** Repeat runs for variation estimates; test sequences of insertions to address the amortized bound; try other models and node text; test stricter thresholds and more corpora.

### Slide 41: Thank you (about 0.5 min)

**Script**

“Thank you. In short: cost per insertion grows linearly with brute force and stays flat with ANN retrieval and bounded buckets. ANN retrieval was the only strategy to pass every gate, though no strategy reached the absolute accuracy bar. And the bucket premise held for single insertions. We welcome your questions.”

**Background**

**The closing, in order.** Use the same structure each time so the panel hears a clear ending.
1. Cost: linear for brute force, flat for ANN and buckets.
2. Accuracy: modest, and lower on the larger graph, with domain and density confounded.
3. Comparison: ANN is the only strategy to pass every gate, and no strategy reaches the absolute accuracy bar.
4. Premise: bucket cost did not grow for single insertions, but the amortized bound is untested.

**Taking questions: a short protocol.**
- Pause, then repeat the question in your own words to confirm it.
- Answer in one or two sentences, then point to the slide or thesis section.
- If the question belongs to another member, say "my groupmate can answer that more fully" and hand it over (slide 42).
- If you do not know, say so, and say where the answer would be found: the thesis, the decision log or the run records. Do not invent a number.

**The four messages to return to if a question is hard.**
1. Single insertions only.
2. Only the narrowing step differs.
3. Results are descriptive.
4. The ranking is post hoc.

**If a panelist challenges a claim.** Check which of the four messages applies. Most challenges fall under one of them, and each is already stated openly in the thesis.

### Slide 42: Contact (leave on screen)

**Script**

No script. Leave this slide up during questions.

**Background: who answers what**

Leave this slide up during questions. Use the map below to route questions.

| Topic | Member |
| --- | --- |
| Problem, literature, gaps, scope, limitations, conceptual framework | Member 1 |
| Data sources, strategies, decision step, procedure, measures, ranking framework and gates | Member 2 |
| Data collected, RQ1 cost, RQ2 accuracy | Member 3 |
| RQ3 comparison and ranking, RQ4 bucket premise, limits, summary | Member 4 |

**Routing rules.**
- If a question lands on the wrong person, say "my groupmate can answer that more fully" and hand it over.
- Questions about the ranking framework can reach Member 2 (how it was built) or Member 4 (how it applies to the results). Agree in advance who takes the first reply.
- If two members disagree on a number, check the thesis table, not memory.

**If you do not know.** Say "I will check the thesis" and name the section, then follow up after the session.


---

# Appendix A: Numbers cheat sheet

Quote these exactly. Each is in the thesis chapter shown.

**Study size**
- 24 runs = 12 accuracy-mode + 12 size-sweep. 12 configurations = 4 primary + 8 sensitivity. (4.1)
- Accuracy run: 59 trials (29 DSA + 30 Metacademy). Sweep run: 60 trials (6 sizes × 10). (4.1)
- Graph sizes: 50, 100, 200, 500, 1,000, 2,000. Synthetic pool: 2,254 names. (3.2.2)
- Gold graphs: Metacademy 141 concepts, 318 positive pairs of 19,740. DSA 29 concepts, 54 positive pairs. (3.2.1)

**Primary parameters**
- S2 θ = 0.6. S3 k = 10, HNSW M = 16, efConstruction = 200, efSearch = 128. S4 (s_min, s_max) = (5, 10), 12 hash bits, seed 42. (3.3)
- Sensitivity: θ 0.4 and 0.5; k 5 and 20; efSearch 64 and 256; buckets (2, 5) and (10, 20). (3.4)

**Pilot (DSA, brute force, 812 decisions)**
- Micro F1 0.541, recall 0.611, precision 0.485. Direction-flip rate 15.38%. Swap consistency 85.71%. Verdict: conditional. (3.3.6)
- Bars: F1 ≥ 0.50, recall ≥ 0.70, flip rate ≤ 15%.

**RQ1 cost at n = 2,000**
- Time: S1 1,713.10 s, S2 0.938 s, S3 8.277 s, S4 5.638 s. Ratios: about 207 and 304. (4.2)
- Slopes (time): S1 0.9605, S3 −0.0201, S4 0.0084. S2 θ = 0.6: 0.8771, R² 0.461. (4.2)
- Calls: S1 2,000, S2 0.8, S3 10, S4 7.0. Per-call time about 0.8 to 0.9 s. (4.2)

**RQ2 accuracy (F1)**
- DSA: S1 0.586, S3 0.511, S4 0.271, S2 0.148. Metacademy: S3 0.294, S2 0.270, S1 0.143, S4 0.114. (4.3)
- Brute force precision 0.548 then 0.081. Recall 0.630 then 0.624.
- Shortlist recall: S3 0.528 and 0.505; random baselines 0.357 and 0.071.

**RQ3 comparison**
- S3 versus S2 on Metacademy: ΔF1 0.0246 (margin 0.025). S1 versus S3 on DSA: ΔF1 0.075 for 18 more calls.
- Classes: S3 Effective. S2 Conditionally effective. S1 and S4 Not effective. (4.4.1)
- Weighted scores and rank shares: see Tables 4.9 and 4.10 on slide 37.

**RQ4 bucket premise**
- S4 calls 6.6 to 7.5 of cap 10. Time 5.15 to 5.77 s. Slopes −0.0004 (calls) and 0.0084 (time). (4.5)

# Appendix B: Glossary

| Term | Meaning | First taught |
| --- | --- | --- |
| Amortized cost | Cost averaged over a sequence of operations | Slide 16 |
| ANN (approximate nearest neighbour) | Fast search that may miss a true nearest neighbour | Slide 15 |
| Bootstrap interval | Range from resampling trials with replacement | Slide 26 |
| Brute force | Compare the new concept with every existing node | Slide 6 |
| Candidate narrowing | Shortlisting existing nodes before the LLM step | Slide 7 |
| Cosine similarity | Closeness of two vectors by angle | Slide 7 |
| Dominance (Pareto) | A is at least as cheap and more accurate than B | Slide 16 |
| Embedding | Text turned into a vector so similar meanings are close | Slide 7 |
| F1 | Combined precision and recall | Slide 12 |
| Gate | Pass or fail bar applied before weighting | Slide 27 |
| Gold standard | Expert-verified graph used as ground truth | Slide 12 |
| HNSW | Layered proximity graph for approximate search | Slide 15 |
| Incremental insertion | Adding one new node to an existing graph | Slide 5 |
| Leave-one-out | Withhold a concept, re-insert it, compare with truth | Slide 12 |
| Log-log slope | Exponent describing how cost grows with n | Slide 26 |
| LLM | Large Language Model | Slide 4 |
| Micro and macro | Pooled versus per-concept averaging | Slide 26 |
| Post hoc | Decided after seeing the results | Slide 18 |
| Pre-registered | Fixed before looking at the data | Slide 18 |
| Precision | Share of proposed links that are correct | Slide 12 |
| Premise versus theorem | The idea a claim rests on versus the full claim | Slide 9 |
| Recall | Share of true links that were found | Slide 12 |
| Shortlist recall | Share of true neighbours kept by narrowing | Slide 26 |
| Transitive closure | All links implied by chaining edges | Slide 20 |
