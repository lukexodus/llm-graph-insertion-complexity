# Background-Concepts Deck — Consolidated Content Pack

This is the **source material** for the HTML background deck. It consolidates
the facts, definitions, analogies, caveats, and teaching order that already
exist across the thesis and the two defense scripts. The APC owns the creative
plan — scene composition, copy, visual metaphors, and animation. This file
does not prescribe those.

**Use this pack as the factual base.** If a sentence here conflicts with the
thesis, the thesis wins; report the conflict rather than silently choosing.
Do not add facts from outside the listed sources.

---

## 1. The one-sentence framing

> A knowledge graph stores ideas as nodes and relationships as edges. Adding a
> new idea naively means asking an LLM about every existing idea. Four
> candidate-narrowing strategies reduce that shortlist in different ways, and
> the thesis measures their cost and accuracy as the graph grows.

The deck stops before the measurements. It teaches the foundation, states the
two gaps, asks the four research questions, and shows the conceptual framework.

---

## 2. Concept ladder (dependency order, not a scene order)

Each row uses the rows above it. This is a dependency map for teaching, not a
prescribed scene sequence; the APC decides how to group and arrange the ideas.

| Order | Idea | Must be understood before |
| --- | --- | --- |
| 1 | Graph, node, edge | Everything |
| 2 | Directed edge, knowledge graph, prerequisite | Incremental insertion, strategies |
| 3 | Why graphs matter; manual construction limit | Why LLMs are used |
| 4 | LLM, prompt, API call, call cost | Brute force, decision step |
| 5 | Batch vs incremental, graph size `n`, insertion | Cost analysis |
| 6 | Brute force, linear cost | Candidate narrowing |
| 7 | Candidate, shortlist, candidate narrowing | Embeddings and all four strategies |
| 8 | Embedding, vector, similarity | Cosine similarity |
| 9 | Cosine similarity, threshold, top-k | S2 and S3 |
| 10 | ANN, HNSW, approximate search | S3 |
| 11 | Random hyperplanes, binary code, bucket | S4 |
| 12 | Shared LLM decision step, three labels | Fair comparison |
| 13 | Gold standard, leave-one-out, precision, recall, F1 | Accuracy measurement |
| 14 | Research gap, aggregate vs scaling cost | RQs |
| 15 | Premise vs theorem, amortized cost (intuition only) | RQ4 |
| 16 | Input-process-output framework | Close |

---

## 3. Canonical definitions

Use plain language first; the formal term can follow in a small label.

### Graph

A graph is a set of **nodes** (things) and **edges** (connections between
them). A road map is a graph: cities are nodes, roads are edges. A social
network is a graph: people are nodes, friendships are edges.

### Directed edge

An edge with a direction, drawn as an arrow. In a prerequisite graph,
direction carries meaning: `Limits → Calculus` means `Limits` is needed before
`Calculus`. Reversing the arrow changes the claim.

### Knowledge graph

A graph whose nodes are **concepts** and whose edges are **meaningful
relationships** between them, such as "requires", "is a kind of", or "is
related to". A knowledge graph lets a person or a program navigate from one
concept to its prerequisites, dependents, or neighbours.

### Prerequisite

`P` is a prerequisite of `Q` if a learner needs to understand `P`, directly or
indirectly, before understanding `Q`. Example: `Limits` is a prerequisite of
`Calculus`.

### LLM (Large Language Model)

A program trained on very large amounts of text. Given a prompt, it can judge a
relationship between two concepts. It is not a database; it can be wrong.

### API call

One prompt sent to the LLM through an API, returning one answer. In the
thesis's measurements, one call takes roughly 0.8–0.9 seconds and also costs
money. The number of calls is the main driver of both time and money.

### Batch construction

Give the LLM the whole corpus and ask for a finished graph in one pass.

### Incremental insertion

The graph already exists; exactly one new concept arrives. The task is to
decide which existing concepts it connects to and in which direction. The
thesis studies only this phase.

### Graph size `n`

`n` is the number of concepts already in the graph. After one insertion the
graph has `n + 1` concepts. The thesis uses `n` consistently for existing graph
size.

### Brute force

Compare the new concept with every existing concept, one LLM call each. No
shortlist, no shortcut. Cost is exactly `n` calls, so it grows linearly with
the graph.

### Candidate

An existing concept that might connect to the new concept.

### Candidate narrowing

Cutting the list of existing concepts down to a shortlist of likely candidates
before the expensive LLM step. Two stages: a cheap shortlist step, then an
expensive LLM decision step on the shortlist only.

### Embedding

A list of numbers (a vector) that represents the meaning of a text, built so
that similar meanings get similar vectors. The thesis uses the local
`all-MiniLM-L6-v2` model, which gives each concept name a vector of 384
numbers. Computing an embedding is far cheaper than an LLM call.

### Cosine similarity

A measure of the angle between two vectors. Same direction gives 1; unrelated
vectors give about 0. It is used to decide which existing concepts are close in
meaning to the new concept.

### Threshold

Keep every concept whose similarity is above a fixed cutoff. Example: with
scores 0.90, 0.70, 0.62, 0.55, 0.30 and a cutoff of 0.6, keep the first three.
The shortlist size varies with the data and can be zero or very large.

### Top-k

Always keep the `k` most similar concepts. The shortlist size is fixed. Example:
with the same scores, top-2 keeps 0.90 and 0.70.

### ANN (approximate nearest-neighbor) retrieval

A fast similarity search that may occasionally miss a true nearest neighbor.
The thesis uses an HNSW index through the FAISS library. `k = 10`, so the
shortlist is 10 concepts.

### HNSW

Hierarchical Navigable Small World: a layered proximity graph. The top layer is
sparse with long jumps; the bottom layer holds everything with short links. A
search starts at the top, moves greedily to a closer neighbour, drops a layer,
and repeats. Because the walk is greedy, it is approximate.

### Bounded bucket

A partitioning strategy. Random hyperplanes turn each concept vector into a
short binary code; similar vectors tend to share a code. Codes are ordered
along a Gray-code line and cut into contiguous segments (buckets) of bounded
size. A new concept joins its home segment and is compared only with that
segment's members.

### Shared decision step

The identical final step used by all four strategies. For each shortlisted
candidate, one LLM call asks whether the new concept is a prerequisite of the
candidate, the candidate is a prerequisite of the new concept, or neither. The
model, prompt, temperature, and call order are held fixed.

### Gold standard

An expert-verified graph used as ground truth. The thesis uses the DSA graph
(29 concepts) and the Metacademy graph (141 concepts), both with
expert-verified prerequisite relationships.

### Leave-one-out

Withhold one concept from a gold graph; treat the rest as the existing graph;
re-insert the held-out concept with a strategy; compare the produced links with
the true links for that concept.

### Precision, recall, F1

- **Precision** = correct proposed links ÷ all proposed links. "Of what you
  said, how much was right?"
- **Recall** = correct proposed links ÷ all true links. "Of what was true, how
  much did you find?"
- **F1** = harmonic mean of precision and recall; high only when both are high.

Worked illustration: suppose 4 links are true, the strategy proposes 5 links,
and 3 are correct. Precision = 3/5 = 0.60; recall = 3/4 = 0.75;
F1 = 2·0.60·0.75/(0.60+0.75) ≈ 0.667. A link in the wrong direction counts as
both a wrong proposal and a missed true link.

### Research gap

A question the existing studies do not answer. The thesis claims gaps only
within the studies it reviewed: say "none of the studies we reviewed", never
"nobody has ever".

### Amortized cost (intuition only)

Cost averaged over a sequence of operations. Example: a dynamic array usually
appends in one step but occasionally copies everything to a larger array; the
copy is expensive but rare, so the average per append is small. The thesis
measures one insertion at a time, so it cannot confirm an amortized bound.

---

## 4. The four strategies

| Strategy | Shortlist rule | Maximum LLM calls per insertion | Role |
| --- | --- | --- | --- |
| **S1 — Brute force** | Every existing concept | `n` | Control condition |
| **S2 — Embedding threshold** | Concepts with cosine similarity above `θ = 0.6` | `n` (worst case; often much less, and can be zero) | Threshold-based narrowing |
| **S3 — ANN retrieval** | Top `k = 10` most similar concepts, using a FAISS HNSW index | 10 | Count-based narrowing |
| **S4 — Bounded bucket** | Members of the new concept's bucket, a segment of 5–10 concepts | At most 10 | Partition-based narrowing |

### Facts that must survive any rewriting

- **S1** is the control: every existing concept goes to the decision step.
- **S2** keeps concepts **strictly above** `θ = 0.6`. Its shortlist can be
  empty, in which case no LLM call is made. It has no cap, so its worst case
  equals brute force.
- **S3** uses the same embeddings and similarity idea as S2; the difference is
  that it selects by **count** (`k = 10`) rather than by a cutoff. It is
  approximate and can occasionally miss a true nearest neighbour.
- **S4** is inspired by EraRAG's size-bounded buckets but is adapted to
  concept-node insertion, not EraRAG's own text-chunk-summarization task.
- **S3 and S4 both cap the shortlist at 10.** Therefore the comparison cannot
  fully separate bucket geometry from shortlist capacity. This caveat must be
  stated when the four strategies are compared.
- All parameters were fixed before any run and were not tuned on the
  evaluation data. This is a methodology fact, not a result.

### S4 mechanics (if the deck explains the bucket)

1. Pick a random plane through the embedding space. A vector is on one side or
   the other: one yes/no question, one bit.
2. With 12 hyperplanes, each concept gets a 12-bit code. Similar vectors tend
   to fall on the same side of most planes, so they get similar codes.
3. 12 bits allow 4,096 possible codes, more than the 2,000-node maximum.
4. Map codes to a Gray-code ordering, where neighbouring codes differ in one
   bit, so similar codes sit next to each other on a line.
5. Cut the line into contiguous segments of 5–10 concepts. Oversize segments
   split at the midpoint; undersize segments merge into the closest neighbour.
6. A new concept joins its home segment and is compared only with the members
   there, so at most 10 calls.

Seed 42 fixes the hyperplanes. The thesis fills unspecified split/merge details
with its own rules; do not claim it reproduces EraRAG's full architecture.

---

## 5. The shared decision step

For every shortlisted candidate:

- **Input:** the new concept name, the candidate name, and a graph-level
  subject-area label such as "data structures and algorithms".
- **Output:** one of three labels:
  - `X_PREREQ_Y` — the new concept is a prerequisite of the candidate.
  - `Y_PREREQ_X` — the candidate is a prerequisite of the new concept.
  - `NONE` — neither.
- **Held fixed:** same model, same prompt, temperature 0, one call per
  candidate, calls run one at a time.

**Why it is shared:** if each strategy used its own decision method, a
difference in results could come from either the shortlist or the decision.
Sharing the decision step isolates the narrowing mechanism. This is the
fairness argument of the whole study.

The model is accessed through an API. This background deck should say "an LLM,
called through an API" and avoid naming a model version; the `.pptx` and thesis
have a version-name inconsistency that is irrelevant to the background lesson.

---

## 6. Accuracy measurement

- Accuracy needs a known right answer, so it uses the two gold-standard graphs:
  DSA (29 concepts) and Metacademy (141 concepts).
- Cost can be measured on any graph, so the cost sweep uses a synthetic pool of
  2,254 unique computer-science concept names up to 2,000 nodes. The synthetic
  names are unverified and are **never** used for accuracy claims.
- Leave-one-out: withhold one concept, re-insert it, compare with the true
  links, repeat.
- Precision, recall, and F1 are defined in Section 3, with a worked example.
- The gold graphs are not transitively reduced: some true links are implied by
  chains of other links. The decision prompt therefore accepts direct or
  indirect prerequisites. This matters for interpreting a "wrong" answer that
  is actually implied by the gold graph.

For this background deck, the key idea is: **accuracy is measured against an
expert graph, not against the LLM's own opinion.** Do not present accuracy
numbers.

---

## 7. The two research gaps

### Gap 1 — cost is not measured against existing graph size

None of the studies reviewed measures insertion cost as an explicit function of
how large the existing graph already is. Costs are reported in aggregate:
total dollars, total time, or total tokens for an entire experiment. An
aggregate total does not say what one insertion costs at 50 nodes versus at
2,000 nodes.

Analogy: a restaurant reporting its total monthly food spend does not tell you
what one dish costs as the menu grows.

### Gap 2 — no like-for-like comparison

None of the studies reviewed compares narrowing strategies head-to-head under
the same task and the same measurements. Each system is tested against generic
baseline systems, not against the other narrowing methods.

Analogy: comparing whole cars when you want to compare engines. To compare
engines, keep the rest of the car the same. In this thesis, the "rest of the
car" is the shared decision step.

**Claim strength:** these are absence claims from a structured but
non-exhaustive literature search, not a systematic review. Always say "none of
the studies we reviewed". If asked whether someone else has done it, say the
search was structured but not exhaustive.

### Optional third gap (thesis Section 2.8)

None of the reviewed insertion studies says in advance what level of accuracy
and cost counts as adequate. The thesis addresses this with explicit gates in
its methodology. This is optional in the background deck; the two gaps above
are the headline.

---

## 8. The four research questions

| RQ | Plain-language question | What is varied | What is measured |
| --- | --- | --- | --- |
| **RQ1 — Cost** | How do time and LLM calls per insertion change as the graph grows? | `n` from 50 to 2,000 | wall-clock time; LLM calls per insertion |
| **RQ2 — Accuracy** | Does placement accuracy hold up as the graph grows? | graph (29 vs 141 nodes) | precision, recall, F1 against the gold graph |
| **RQ3 — Comparison** | How do the four strategies compare under identical conditions? | strategy | cost and accuracy together |
| **RQ4 — Bucket premise** | Does the cost of one insertion stay flat under a bucket-capped strategy? | `n` | calls and time for the bounded-bucket strategy |

### RQ4 wording rule

RQ4 tests the **premise** behind EraRAG's amortized bound: that one insertion
touches only a bounded region of the graph, so its cost does not grow just
because the graph is larger. It does **not** test the amortized theorem itself.
Use "premise" and "single insertion"; never "we prove EraRAG's bound".

### EraRAG in one paragraph

EraRAG proposes size-bounded buckets and gives an amortized cost bound for
insertion. Informally: inserting should not get costlier just because the graph
is bigger. Its own experiments vary the size of the incoming batch, not the
size of the existing graph. The thesis varies the existing graph size and tests
the single-insertion premise. That is the gap RQ4 addresses.

---

## 9. Conceptual framework

### Input

- An existing graph of size `n`.
- One new concept to insert.
- One narrowing strategy: S1, S2, S3, or S4.

### Process

1. The strategy narrows the graph to a candidate shortlist.
2. The shared LLM decision step judges the relationship for each shortlisted
   candidate.
3. The graph is updated and the insertion is measured.

### Output

- An updated graph of size `n + 1`.
- **Cost:** wall-clock time and LLM calls per insertion.
- **Accuracy:** precision, recall, and F1 against the gold-standard graph.

**One-line summary:** same pipeline for all four strategies; only the
narrowing box changes.

### Three foundations (optional background)

- **Graph theory:** nodes, edges, structure, growth.
- **Algorithm analysis:** how cost grows with input size; amortized cost is a
  related idea the thesis does not test.
- **Vector semantics:** meaning as position in space, so closeness can
  shortlist candidates.

---

## 10. Analogies bank

Use these as starting points; the APC may invent better ones, but keep the
mapping accurate.

| Concept | Analogy | The mapping |
| --- | --- | --- |
| Graph | Road map | Cities = nodes; roads = edges |
| Directed edge | One-way street | Direction changes what the connection means |
| Knowledge graph | Map of ideas | Concepts = places; relationships = roads |
| Batch vs incremental | Build a library vs file one new book | Batch builds everything; incremental adds one item |
| Brute force | Asking every person in a building | One question per person; cost grows with the crowd |
| Candidate narrowing | Screen résumés, interview the shortlist | Cheap filter first; expensive judgment second |
| Embedding | Coordinates on a map of meaning | Similar meanings sit close together |
| Cosine similarity | Angle between two arrows | Same direction = similar; perpendicular ≈ unrelated |
| Threshold | A height bar at an entrance | Everyone above the bar enters; crowd size varies |
| Top-k | A fixed number of seats | Always exactly `k` enter, regardless of scores |
| HNSW | Highway shortcuts to a neighbourhood | Start on fast top roads, then take local streets |
| Bounded bucket | Filing cabinet with size-capped folders | A new item goes into one folder; only that folder is searched |
| Aggregate vs scaling cost | Total monthly food spend vs price of one dish | A total does not reveal per-item cost as the menu grows |
| Head-to-head comparison | Compare engines in the same car | Keep everything else identical |
| Amortized cost | Occasionally copying a growing list | Rare expensive operation averaged over many cheap ones |

---

## 11. Do-not-use list

These are the most likely factual errors. The background deck must not contain
them.

1. **No Chapter 4 numbers.** No 1,713 s, no 8.28 s, no F1 values (0.586, 0.294,
   etc.), no call counts from the sweep, no gate classes, no weighted scores,
   no TOPSIS or Kendall figures. This deck stops before results.
2. **No post-hoc ranking framework.** No G1/G2/G3, no "Effective" classes, no
   weight scenarios.
3. **No model version name.** The `.pptx` slide 22 says "DeepSeek V4 Flash";
   the thesis says DeepSeek V3 via the alias `deepseek-flash`. Avoid the issue
   entirely: say "an LLM, called through an API".
4. **No reference-number ranges.** The `.pptx` literature slides and the thesis
   reference list number the evaluation-methods sources differently. The
   background deck does not need reference numbers; name authors if needed.
5. **No "nobody has ever".** Say "none of the studies we reviewed".
6. **No claim that the 22–50 prompts figure is brute force.** It is Funk et
   al.'s pruned algorithm. Brute force itself needs `n` calls.
7. **No claim that S2 is always cheap.** It is uncapped; its worst case is `n`.
8. **No claim that S3 and S4 are cleanly comparable on geometry.** Both cap at
   10; state the caveat.
9. **No claim that the thesis proves EraRAG's theorem.** It tests a
   single-insertion premise.
10. **No synthetic-data accuracy claim.** The synthetic pool is for cost only.
11. **Do not treat the five-node running example as thesis data.** Label it
    "illustration".
12. **Do not add new sources or new claims.** If it is not in the thesis or the
    two defense scripts, leave it out.

---

## 12. Topic inventory

Every in-scope idea the deck must cover. This is a coverage checklist, not a
scene sequence. The APC decides how to group, order, and present these topics.

| Topic | Core content | Primary source |
| --- | --- | --- |
| Opening | Title, speakers, one-sentence promise | Deck slide 2; script Slide 1 |
| Roadmap | What the deck will teach; no results yet | Script Slides 1–3 |
| Graph basics | Node, edge, graph; road-map analogy | Script Slide 4; thesis 1.1 |
| Knowledge graph | Concept nodes, meaningful directed edges, prerequisite example, uses, hand-built limit | Script Slide 4; thesis 1.1 |
| LLM and calls | What an LLM is; one prompt = one API call; time/money; can be wrong | Script Slides 4–5; thesis 1.1 |
| Incremental insertion | Batch vs incremental; `n`; `n+1`; insertion means edges + direction | Script Slides 5, 9; thesis 1.2 |
| Brute force | Every node; `n` calls; linear growth; 22–50 caveat | Script Slides 6, 15; thesis 2.3.1 |
| Candidate narrowing | Candidate, shortlist, two-stage idea, résumé analogy | Script Slide 7; thesis 2.3.2 |
| Embeddings | Meaning as vector; similar meanings close; 384 dimensions; cheap | Script Slide 7; thesis 3.3 |
| Similarity and selection | Cosine similarity; threshold; top-k; worked score illustration | Script Slides 7, 10; thesis 3.3 |
| S1 brute force | Shortlist = everyone; `n`; control condition | Script Slide 23; thesis 3.3.1 |
| S2 threshold | `θ = 0.6`; variable shortlist; empty case; uncapped | Script Slide 23; thesis 3.3.2 |
| S3 ANN | ANN, HNSW layers, greedy search, approximate, `k = 10` | Script Slide 23; thesis 3.3.3 |
| S4 bucket | Hyperplanes, 12-bit code, Gray order, segments 5–10, split/merge, ≤10 calls, EraRAG adaptation caveat | Script Slide 23; thesis 3.3.4 |
| Shared decision step | One call per candidate; three labels; fixed settings; fairness | Script Slide 24; thesis 3.3.6 |
| Four side by side | Shortlist rules and call bounds; S3/S4 cap caveat | Script Slides 21–23; thesis 3.3 |
| Accuracy | Gold standard, leave-one-out, precision/recall/F1, direction errors | Script Slide 12; thesis 3.2, 3.5 |
| Gaps | No cost-vs-size; no head-to-head; claim-strength caveat | Script Slide 8; thesis 1.2, 2.8 |
| RQs | RQ1–RQ4 in plain words; RQ4 premise-not-theorem note | Script Slide 9; thesis 1.2 |
| Framework | Input → process → output; shared pipeline | Script Slide 17; thesis 1.7 |
| Close | Five-sentence recap; bridge to the main deck | Script Slides 1, 40–41 |

---

## 13. Source index

Use these files to verify or expand any item.

| Short name | Path |
| --- | --- |
| Comprehensive script | `docs/presentation/script/Defense_Script_and_Background_Guide—Comprehensive Version.md` |
| Short script | `docs/presentation/script/Defense_Script_and_Background_Guide.md` |
| Thesis | `docs/thesis/[REVISED] An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction—With Chapter 4.md` |
| Deck extract | `docs/presentation/background-deck/DECK-EXTRACT.md` |
| Existing deck | `docs/presentation/An Empirical Complexity Analysis Of Candidate-Narrowing Strategies For Incremental LLM-Driven Graph Construction—Presentation.pptx` |
| Complete context | `docs/context/complete-context.md` |
| Decision log | `docs/decisions/decision-log.md` |

For the background deck, read thesis Chapter 1 and Chapter 3 only. Chapter 4 is
out of scope and should not be mined for examples.

---

## 14. Coverage checklist for the finished HTML

The deck is content-complete only if a viewer can answer all of these from the
slides alone:

- [ ] What is a node? What is an edge? What is a graph?
- [ ] What makes a knowledge graph different from any graph?
- [ ] Why does edge direction matter?
- [ ] Why can't experts build large knowledge graphs by hand?
- [ ] What is an LLM, and what is one API call?
- [ ] What is the difference between batch and incremental construction?
- [ ] What does `n` mean? What does `n + 1` mean?
- [ ] Why does brute force cost `n` calls, and why is that called linear?
- [ ] What is a candidate? What is a shortlist? What is narrowing?
- [ ] What is an embedding, in plain words?
- [ ] What does cosine similarity measure?
- [ ] What is the difference between threshold and top-k?
- [ ] What is S1's shortlist rule?
- [ ] What is S2's shortlist rule, and why is it not always cheap?
- [ ] What is S3's shortlist rule, and why is it approximate?
- [ ] What is S4's shortlist rule, and why is it bounded?
- [ ] Why do all four strategies share one decision step?
- [ ] What are the three possible outputs of the decision step?
- [ ] How is accuracy measured against a gold graph?
- [ ] What are precision, recall, and F1, in plain words?
- [ ] What are the two research gaps?
- [ ] What are the four research questions?
- [ ] What is the input, process, and output of the conceptual framework?
- [ ] Why does RQ4 test a premise rather than an amortized theorem?
