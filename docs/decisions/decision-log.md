# Decision Log

Append-only. Never edit or delete a past entry — if a decision changes, add a
new entry that supersedes it and say so explicitly ("supersedes entry dated
X"). This file exists so that across API-credit-limited handoffs between APC AI
instances, a settled question never gets re-litigated from scratch because
nobody could find the earlier reasoning. When in doubt about whether something
belongs here: if re-deriving it would cost more than one paragraph of
reasoning, it belongs here.

Each entry: date (session-relative, since exact dates aren't tracked across
this project), decision, one-line reasoning, and what it affects.

---

**[D-01]** Thesis topic locked: _An Empirical Complexity Analysis of
Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction._
Pure CS mechanism study, no education-application framing, despite the
original research thread passing through an education-framed version first.
Reasoning: the education-framed version (prerequisite graphs, ACE-style) was
found to already have a close published match (ACE itself); the pure-mechanism
reframe targets a genuinely unaddressed empirical gap (insertion cost vs.
existing graph size, never measured in any reviewed paper). See
`docs/thesis/` for full Chapters 1–3 and `docs/rrl/catalogue.md` for the full
literature trail.

**[D-02]** Four candidate-narrowing strategies locked: (1) brute-force LLM
comparison, (2) embedding-similarity thresholding, (3) approximate
nearest-neighbor (ANN) retrieval, (4) bounded-bucket partitioning. Reasoning:
each is drawn from a specific, citable prior work (Funk et al. 2023 for (1)'s
failure mode; iText2KG for (2); general ANN/FAISS literature for (3); EraRAG
for (4)) rather than invented — this makes each strategy independently
defensible at defense time, and testing four rather than one strategy means a
"boring" result (no difference between strategies) is still a real finding
rather than a weak one.

**[D-03]** EraRAG's Theorem 4 (O(Δ(nd + S_LLM)) amortized insertion cost via
bounded-bucket-size argument) is the thesis's theoretical anchor. Reasoning:
it is the only reviewed work offering a formal proof of an amortized
insertion-cost bound for LLM-graph construction, AND its own paper never
empirically validates that bound against total existing graph size (every
experiment varies batch size instead) — this theory-vs-measurement gap is
precisely what the thesis's experiment operationalizes. Note: an independent,
informal (non-peer-reviewed) critique site flagged this theorem's proof as
"complexity bookkeeping" rather than a fully rigorous amortized argument; this
critique is NOT cited in the thesis text (the source isn't citable-quality)
but the underlying observation (the proof's cascade-prevention step is
asserted rather than formally proven via potential-function/accounting
argument) is stated in Chapter 2 as the thesis author's own close reading,
which needs no external citation to be a legitimate methodological
observation.

**[D-04]** Gold-standard accuracy data: reuse ACE's released Metacademy
(141-node) and DSA (29-node) graphs rather than building a hand-labeled set or
using Wikipedia/WordNet/DBpedia. Reasoning: ACE's graphs are already the
correct relation type (expert-verified prerequisite relations, not generic
is-a/part-of hierarchy), already small and pre-cleaned, and reusing them
sidesteps the "no ground truth" criticism ACE's own paper raises about itself.
Wikipedia/DBpedia were rejected specifically because they encode a different,
coarser relation type that would change what "correct placement" even means,
and because extracting a clean subset from them costs real implementation
time for no accuracy benefit.

**[D-05]** Synthetic/cost-scaling data plan locked: reuse the repo's ten
example MEKG files (6–35 nodes, see `docs/context/data-formats.md`) for the
small-to-mid range of the size sweep, and generate LLM-produced concept name
lists (domain: computer science, for topical continuity with DSA) for the
large-n range (toward 2000 nodes) where no real data exists. Reasoning:
large-n synthetic data only needs to be plausible concept-shaped strings for
cost measurement purposes (not pedagogically correct), since this half of the
experiment measures cost, not accuracy — accuracy is measured exclusively
against the real gold-standard data per D-04. **UPDATE (supersedes an earlier,
now-retracted guess):** the four CSV files (`0-100.csv` etc.) were briefly
considered as a possible additional real-data source extending the sweep to
400 nodes. Direct inspection showed this guess was WRONG — these files are
unrelated crowdsourced A-B-test data, not graphs. This does not change the
locked plan; it only confirms no additional real-data source was missed.

**[D-06]** Log-spaced graph-size sweep locked: n = 50, 100, 200, 500, 1000,
2000, supplemented at the small end by the real 29-node (DSA) and 141-node
(Metacademy) checkpoints. Reasoning: log-spacing makes polynomial cost growth
visible on a plot without requiring dense linear coverage (which would cost
more LLM API spend for less visual signal).

**[D-07]** Three dependent variables locked: wall-clock time per insertion,
LLM API call count per insertion, and placement accuracy (precision/recall
against gold-standard, where available). Reasoning: time alone conflates "the
LLM is slow" with "the algorithm makes too many calls" — call count
disentangles these; accuracy alone ignores the actual cost question driving
the thesis; all three together let cost and quality tradeoffs be seen
side-by-side per strategy per size.

**[D-08]** Five-chapter Philippine undergraduate thesis format adopted
(Introduction / RRL / Methodology / Results-Discussion / Summary-Conclusions),
per Luke's university's stated convention, including sections not present in
pure IMRAD (Statement of the Problem, Significance of the Study broken out by
stakeholder, Scope and Limitations, Definition of Terms, Theoretical/
Conceptual Framework). "To the Institution"/"To the Community" stakeholder
subsections were deliberately omitted from Significance of the Study since
this is a pure-mechanism study with no institutional/community application —
flagged as an open question for Luke's adviser, not unilaterally decided.

**[D-09]** Citation style: IEEE numbered, chosen as a working default (not
confirmed against the actual program requirement) because it suits this
technical/systems-heavy source set. Flagged explicitly as needing adviser
confirmation; if the program requires APA or ACM instead, this is a mechanical
reformatting pass, not a rewrite, since every underlying bibliographic fact is
already gathered and verified.

**[D-10]** Local-literature search for Chapter 2 found zero Philippine-
affiliated work on LLM-driven knowledge graph construction or incremental
insertion specifically (confirmed absence, not an unexamined gap — searched
via general web search and targeted Philippine-venue search). One genuinely
relevant Philippine source was found one level removed: Naguio & Roxas (2026),
"Multi-scale Graph Neural Networks for Knowledge Graph Completion in
Philippine Lexical Resources" (graph NEURAL NETWORK-based edge completion
over a fixed node set — methodologically distinct from this thesis's
LLM-driven node insertion, but conceptually adjacent as both modify an
existing graph rather than building from scratch). Fully verified (author
names, institution, DOI, page range) via direct fetch of the Springer chapter
page.

**[D-11]** Reference [8] in the thesis reference list remains an open/TBC
slot — a general citation for "LLMs can extract structured knowledge from
text" was never pinned to a specific paper. This is a known gap, not an
oversight to silently paper over; resolve before final submission.

**[D-12]** Architecture change: work moved from single-thread conversational
drafting to a multi-agent, multi-session structure. One "APC AI" (Analyzer/
Planner/Controller — no repo filesystem access, coordinates via standalone
prompts) works alongside local coding agents (Claude Code, Gemini, opencode)
that DO have repo access. APC instances will be handed off across sessions
due to credit limits; all durable state must live in repo files, never in any
single AI's conversational memory. This decision log, the task-status
tracker, and the handoff-template convention all exist specifically to make
this handoff pattern work. Agent role recommendation (not a hard rule):
Claude Code for first-draft implementation (interface, loader, harness,
strategy modules); Gemini for independent review/verification specifically
BECAUSE it's a different model lineage than the APC AI itself, which matters
for catching APC-originated spec errors rather than just re-confirming them;
opencode's role unassigned pending more information about its configuration.

**[D-13]** Reports convention locked: one file per completed task at
`docs/reports/<task-id>-<agent>-<short-slug>.md`, never appended to across
agents. Reasoning: a single shared running log risks write collisions between
agents working concurrently and forces a new APC instance to scroll an
ever-growing file; one-file-per-task is collision-free and instantly
discoverable by filename alone, matching the project's existing
ToC-driven-efficiency pattern for the thesis documents.

**[D-14]** First local-agent task (DATA-001) is independent re-verification
of every claim in `docs/context/data-formats.md` against the full raw files,
BEFORE any loader code is written. Reasoning: the APC AI's own CSV guess (see
D-05 update) was wrong on first pass from filename alone, which is direct
evidence that APC-only analysis of these files carries real error risk; a
cheap verification pass now is far less costly than four parallel strategy
implementations later being built against a wrong assumption baked into
shared infrastructure.

**[D-15]** Gold standard edge directionality confirmed: `concept1;concept2;1`
means `concept2` is a prerequisite of `concept1` (`concept1 requires concept2`).
Reasoning: empirically confirmed on DSA (`dijkstra_algorithm;graph;1`) and
Metacademy (`backpropagation chain_rule 1`); loader in INFRA-003 and graph model
in INFRA-001 must standardize on this directionality to avoid inverted evaluation graphs.

**[D-16]** Format standardization for example MEKG files: all 10 files use
semicolon delimiters (matching DSA), but node identifiers include `.txt` suffixes.
Reasoning: verified in DATA-001; loaders must strip `.txt` from node names when
ingesting these files.

**[D-17]** `concept_descriptions/` folder is unusable as build-phase source text
for DSA/Metacademy. Reasoning: contains exclusively elementary school mathematics
articles (matching Section 6.2 crowdsourced CSVs), with 0% overlap with DSA or
Metacademy; build-phase text must be sourced externally or via parametric LLM prompts.

**[D-19]** Example MEKG files directionality resolved: in all ten example MEKG files
(`MEKG_with*.txt`), `concept1.txt;concept2.txt;1` means `concept1` is a prerequisite of
`concept2` (`col1 is prerequisite of col2`, i.e., prerequisite -> dependent).
Reasoning: systematically verified across all ten files in DATA-002; 100% of positive
edges overlapping with DSA/Metacademy match the reversed column order relative to D-15.
Corpus loader (INFRA-003) must apply this reversed mapping for example MEKG files.


