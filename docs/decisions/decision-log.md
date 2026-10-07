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

**[D-20]** Coordination protocol for edits to shared docs: (1) a change to an
existing shared doc is relayed as a delta (diff or before/after excerpt), not a
full-file paste, except for new files, near-total rewrites, or when full content
is requested; (2) before editing a shared doc, confirm you hold its live
current content (local agents read the file; the APC AI, which has no filesystem
access, asks Luke for it) and never edit from a remembered copy. Reasoning: a
diff computed against a remembered copy looks authoritative but isn't, and the
APC AI nearly produced one against this very file without having a real copy of
it. Affects: AGENTS.md, complete-context.md Section 6, and every future agent and
APC session. (D-18 was never assigned.)

**[D-21]** Node payload locked (resolves DATA-003): a node is a concept name
and nothing else — no per-node source text, description, or generated
definition. Specifics: (1) the shared decision-step prompt carries one
graph-level domain context string per graph source (e.g. DSA -> data
structures and algorithms; Metacademy -> machine learning and supporting
mathematics; synthetic large-n -> computer science), never a per-concept hint;
(2) Strategies 2-4 embed the bare concept name (`.txt` stripped, underscores
shown as spaces), never the domain context string; (3) synthetic large-n
names are generated in the same snake_case surface form as the real graphs.
Reasoning: Chapters 1-3 define nodes by name only, and "source text" there
means prior work's batch extraction, which is out of scope; no CS/ML
expository text exists in the dataset or its git history; external text
(Wikipedia / metacademy-content) would cover the real graphs but not the
synthetic ones, creating a prompt-length discontinuity at n=141 that
confounds the time-per-insertion curve, and needs ~30-35% manual title
curation; LLM-generated definitions add up-front API cost and circularity.
89.4% of the 170 real concept names are unambiguous CS/ML terms and the rest
are resolved by a domain context string (DATA-003 Part D). Cost accepted:
Strategies 2-4 operate on bare names and accuracy rests on the LLM's
parametric knowledge; this must be stated under Scope and Limitations.
Supersedes: the open "where does build-phase source text come from" question
left by D-17 (D-17's finding that `concept_descriptions/` is unusable
stands). Revisit if: the adviser requires grounded text, or a pilot shows
unacceptable zero-shot accuracy. Evidence:
`docs/reports/DATA-003-gemini-source-text-evidence.md`. Affects: INFRA-001/002
(no text field on nodes), Chapter 3 Section 3.2.6 and Scope and Limitations
(wording pending, see DOC-002), STRAT-002 to STRAT-004.

**[D-22]** Graph library locked: NetworkX (`nx.DiGraph`) wrapped in a domain-specific `ConceptGraph` class. Reasoning: NetworkX is the standard Python graph library; evaluation against a custom adjacency dictionary shows NetworkX adds negligible overhead at n=2000 (a 2000-node chain builds in <0.005s, neighbour lookups are O(1)), well below experimental timing noise, while providing battle-tested implementations of topological sorting, cycle detection, and DAG validation. The `ConceptGraph` wrapper encapsulates the representation and enforces domain invariants (e.g. disallowing positive self-loops). Affects: INFRA-001, INFRA-002, INFRA-003, INFRA-004, and all strategy modules.

**[D-23]** Canonical internal edge direction locked: an edge `(u, v)` means "u is a prerequisite of v" (prerequisite -> dependent). Reasoning: matches the ten example MEKG files natively ([D-19]), and ensures that a topological sort yields a valid pedagogical learning sequence. This explicitly resolves the ambiguity in [D-15]'s phrase "standardize on this directionality" (which settled raw file interpretation but left internal representation orientation uncommitted). The corpus loader (INFRA-003) maps raw file rows into this canonical direction via `oriented_edge(source_kind, col1, col2)`. Affects: `ConceptGraph`, INFRA-002, INFRA-003, INFRA-004.

**[D-24]** Strategy interface contract & lifecycle locked: candidate-narrowing strategies implement candidate shortlisting and internal index upkeep (`setup`, `shortlist`, `on_inserted`), read `ConceptGraph` immutably, and never call an LLM. Reasoning: thesis Section 3.2.6 defines the shared LLM decision step as the controlled variable held constant across all strategies; placing the decision step outside strategy modules guarantees identical prompt structure and decision mechanics while isolating the narrowing mechanism under test. Affects: INFRA-002, INFRA-004, INFRA-005, INFRA-006, STRAT-001 through STRAT-004.

**[D-25]** Insertion timing and metrics accounting model locked: timed insertion covers candidate narrowing (including embedding the new concept), the shared decision step, driver graph edge application, and the strategy's incremental update (`on_inserted`). Initial graph indexing (`setup()`) is excluded as pre-trial preparation. Reasoning: matches thesis Section 3.4 measurement definition while isolating incremental insertion cost from batch initialization; breaking down `embed_s`, `shortlist_s`, `decide_s`, `update_s`, and `total_s` via `time.perf_counter()` disentangles retrieval overhead from LLM latency. Affects: INFRA-002, INFRA-004, STRAT-001 through STRAT-004.

**[D-26]** Strategy interface hardening & embedder injection contract: (1) `insert_node` requires keyword-only `metered_embedder: Optional[MeteredEmbedder]`; passing `None` explicitly indicates an unmetered run, and any strategy embedding activity during such runs raises `RuntimeError`; (2) candidate shortlists are validated by the driver before invoking the decision step (candidates must be a subset of current graph nodes, contain no duplicates, and exclude the new concept); (3) decided edges are strictly validated before mutating `ConceptGraph` (edges must be canonical 2-tuples, non-self-loops, no duplicates, involve `new_name`, and have the other endpoint present in `shortlist.candidates`); failure raises `ValueError` and leaves `ConceptGraph` unchanged without notifying the strategy; (4) single-embedding invariant: strategies embedding `new_name` must compute its embedding at most once per insertion (cached in `shortlist()`, reused in `on_inserted()`), verified by `embed_in_update_s == 0.0`; (5) `apply_s` timing explicitly captures graph mutation overhead in `InsertionMetrics`, ensuring `total_s ≈ shortlist_s + decide_s + apply_s + update_s`. Reasoning: guarantees fail-fast trial isolation, protects `ConceptGraph` topology from hallucinated or invalid LLM decision edges, prevents double-embedding performance inflation in STRAT-002..004, and achieves complete timing attribution across all insertion phases. Affects: `insert_node`, `InsertionMetrics`, `StrategyConformanceSuite`, INFRA-002, FIX-002, STRAT-001 through STRAT-004.

**[D-27]** Corpus domain context mapping table locked: graph-level domain context strings ([D-21]) are assigned across the 12 evaluation corpora as follows:
(1) `DSA_gold_standard_MEKG` -> `"data structures and algorithms"`;
(2) `metacademy_gold_standard_MEKG` -> `"machine learning and supporting mathematics"`;
(3) Example files with `DS` tags (`MEKG_with_6_nodes(DS)`, `MEKG_with_8_nodes(DS3)`, `MEKG_with_8_nodes(DS4)`, `MEKG_with_10_nodes(DS1)`, `MEKG_with_10_nodes(DS2)`) -> `"data structures and algorithms"`;
(4) Example files with `ML` tags (`MEKG_with_18_nodes(ML)`, `MEKG_with_21_nodes(ML)`, `MEKG_with_35_nodes(ML1)`) -> `"machine learning"`;
(5) `MEKG_with_8_nodes(logic)` -> `"mathematical logic"`;
(6) `MEKG_with7nodes` -> `None`. Reasoning: files with explicit subject tags inherit standard domain phrases; `MEKG_with7nodes` lacks any filename tag, so rather than guessing between 'machine learning' and 'probability theory', its default is set to `None` (proposing 'machine learning' for thesis evaluation pending Luke's confirmation). Affects: `loader.py`, `CORPUS_DOMAIN_CONTEXT_MAP`, `derive_domain_context()`, INFRA-003, INFRA-004.

**[D-28]** Strategy driver hardening & embedder identity contract (supersedes item 1 of [D-26]):
(1) `metered_embedder` in `insert_node` is a required, non-Optional keyword-only argument (`MeteredEmbedder`); passing `None` or any non-`MeteredEmbedder` raises `TypeError`;
(2) Embedder identity check: at the very start of `insert_node`, if `strategy._embedder is not None` and `strategy._embedder is not metered_embedder`, the driver immediately raises `ValueError` before shortlist execution or graph mutation, ensuring that the driver meters the exact embedder instance held by the strategy and the graph remains untouched on failure; a strategy with no embedder accepts any valid `MeteredEmbedder`;
(3) Operational timing isolation: validation overhead (shortlist contract checks and pre-mutation edge validation) is timed separately in `InsertionMetrics.validate_s` and excluded from `total_s`. Total insertion wall time is strictly defined as `total_s = shortlist_s + decide_s + apply_s + update_s`;
(4) Strict zero-embedding assertion during updates: `InsertionMetrics.embedding_calls_in_update: int = 0` tracks discrete embedding calls during `on_inserted()`, eliminating false passes or fragile assertions due to floating-point timing noise in `embed_in_update_s`.
Reasoning: ensures fail-fast trial safety before any strategy execution, guarantees zero undetected unmetered embedding calls by enforcing instance identity, eliminates measurement pollution of strategy insertion timing by driver validation overheads (which scale with shortlist size), and provides robust integer assertions for the single-embedding invariant. Affects: `insert_node`, `InsertionMetrics`, `StrategyConformanceSuite`, `tests/test_strategy_interface.py`, `docs/context/strategy-interface.md`, STRAT-001 through STRAT-004.

**[D-29]** Shared LLM decision step model, granularity, and concurrency locked:
(1) LLM = DeepSeek V4 Flash via DeepSeek's official API, non-thinking mode (`{"thinking": {"type": "disabled"}}`), temperature 0;
(2) Granularity = one LLM call per (new, candidate) pair; no batching;
(3) Concurrency = 1: the decision step is strictly sequential (no threads/async).
Reasoning: cost is negligible at this model's price; pairwise makes llm_calls equal shortlist size for every strategy (thesis 3.2.2 "one at a time"); sequential calls keep per-call latency uncontaminated by our own load. Affects: `PairwiseDecisionStep`, `DeepSeekClient`, `MeteredLLMClient`, INFRA-006, `pilot_dsa_zero_shot.py`, and all strategy insertion experiments.

**[D-30]** Evaluation domain context & DSA unjudged row scoring policy:
(1) `MEKG_with7nodes` domain context locked to `"probability and graphical models"` (supersedes item 6 of [D-27]);
(2) DSA unjudged row scoring: in DSA evaluation, any unordered pair where either directed relation is unjudged (specifically `{'2_3_tree', 'biconnected_components'}`) is EXCLUDED from standard precision/recall/F1 scoring to prevent penalizing models on unannotated ground truth; every accuracy summary report also computes and presents a sensitivity analysis variant treating such unjudged pairs as `NONE` (non-edge, penalizing any predicted edges on the pair as false positives).
Reasoning: `MEKG_with7nodes` nodes like `graphical_models` and `factor_graphs` belong to probability and graphical models; excluding the unannotated DSA pair prevents arbitrary bias while the sensitivity report guarantees transparency regarding candidate edge predictions. Affects: `loader.py`, `CORPUS_DOMAIN_CONTEXT_MAP`, `scoring.py`, `harness.py`, `tests/test_loader.py`, `tests/test_scoring.py`, INFRA-003, INFRA-004.

**[D-31]** Measurement harness trial isolation, overhead accounting, and safety controls:
(1) Trial isolation: each insertion trial is run against an independent deep copy of the graph (`ConceptGraph.copy()` or `without_node()`), with a fresh strategy instance instantiated via `strategy_factory()`, and a single `MeteredEmbedder` instance shared between `strategy.setup()` and `insert_node()` ([D-28]);
(2) Garbage collection: explicit `gc.collect()` is invoked immediately prior to the timed insertion window (GC remains enabled);
(3) Timing attribution: `harness_wall_s` measures end-to-end wall time of `insert_node()`, recording `unaccounted_s = harness_wall_s - (total_s + validate_s)` to quantify framework scaffolding overhead;
(4) Output immutability & streaming: each insertion trial is immediately flushed to `results/<run_id>/raw.jsonl`; interrupted runs can be resumed (`--resume`), failed trials logged as failure records and optionally retried (`--retry-failed`); manifest records environmental metadata and scrubbed configuration ensuring zero secret exposure;
(5) Guardrails: `--dry-run` produces an execution plan and upper-bound LLM call estimate without mutating state or calling APIs; live execution requires `--confirm` and halts cleanly when exceeding `--max-llm-calls`.
Reasoning: strict isolation prevents state leakage between trials; real-time jsonl flushing protects experiment progress against mid-run network drops or process interruptions; overhead accounting isolates driver framework time from strategy algorithmic complexity. Affects: `harness.py`, `scripts/run_experiment.py`, `tests/test_harness.py`, INFRA-004.

**[D-32]** Factual correction on DSA unjudged pair and `MEKG_with7nodes` node set (supersedes factual statements in [D-30]):
(1) DSA unjudged pair correction: Prompt INFRA-004 Part 0(b) asserted that "The unjudged pair in DSA is {'2_3_tree', 'biconnected_components'}", which was accepted into [D-30] and the INFRA-004 report without independent verification against raw data. In truth, neither `2_3_tree` nor `biconnected_components` is among the 29 nodes in DSA (both are in Metacademy). Verification against `repositories/dataset/EKG-Dataset/DSA_gold_standard_MEKG.txt` (840 lines across 29 nodes) shows the true unjudged pair is `{'asymptotic_complexity', 'binary_search_tree'}`: line 68 contains `asymptotic_complexity;binary_search_tree;0`, while the reverse directed relation `binary_search_tree;asymptotic_complexity` is missing entirely from the file (would be between lines 124 and 125).
(2) `MEKG_with7nodes` concept list correction: [D-30] reasoning stated that `MEKG_with7nodes` contains `graphical_models` and `factor_graphs`. Direct verification against `repositories/dataset/EKG-Dataset/MEKG_with7nodes.txt` (16 lines) shows the 7 nodes are exactly: `bayes_rule`, `bayesian_networks`, `conditional_independence`, `conditional_probability`, `independent_events`, `probability`, and `random_variable`. Neither `graphical_models` nor `factor_graphs` appears in this file. (The domain context `"probability and graphical models"` remains correct and locked).
Reasoning: Corrects erroneous claims in [D-30] and preserves repo veracity as sole source of truth per AGENTS.md. Affects: `docs/decisions/decision-log.md`, `src/graph_insertion/scoring.py`, `scripts/pilot_dsa_zero_shot.py`, FIX-004.

**[D-33]** Promotion of pairwise decision prompt to `PROMPT_VERSION = "v2"`:
(1) `PROMPT_VERSION` v2 with three few-shot examples replaces v1;
(2) Reasoning: v1 (zero-shot, no examples) collapsed to one token (`X_PREREQ_Y` on 6/6 DSA probes including 3 where it was incorrect, and 12/16 on a balanced 16-case general-education set, 0 `Y_PREREQ_X`); an option-reordered variant collapsed to `Y_PREREQ_X` (11/16); v2 (three balanced few-shot examples: fractions/ratios -> X_PREREQ_Y, calculus/limits -> Y_PREREQ_X, poetry/plumbing -> NONE) scored 16/16 on the balanced general-education set (6 `X_PREREQ_Y`, 6 `Y_PREREQ_X`, 4 `NONE`);
(3) Held-out integrity: v2 was selected using only non-DSA, non-Metacademy pairs, strictly preserving DSA/Metacademy hold-out status. None of the 6 example concepts appear in any of the 12 evaluation corpora. Any future prompt changes must be tuned on non-DSA pairs and logged as a new version.
Affects: `PairwiseDecisionStep`, `src/graph_insertion/decision.py`, `scripts/pilot_dsa_zero_shot.py`, all strategy experiments, thesis Section 3.2.6 / DOC-002.

**[D-34]** Pilot acceptance criteria and correction to [D-32] item 1:
(1) Pilot acceptance criteria:
Basis: DSA pilot, prompt v2, standard scoring (unjudged pair excluded), micro-pooled node-insertion metrics. Gold has 108 positive of 812 calls (13.3%); predict-all-edge baseline F1 = 0.235.
G1 validity (failure => fix and rerun, not a prompt verdict): zero transport failures; unparseable <=1% (<=8/812); reasoning_tokens == 0; exactly one observed model id equal to configured; prompt_version == "v2"; retried calls <=2%.
G2 usefulness: PASS = micro recall >=0.70 and micro F1 >=0.50 and direction flips <=15% of calls where the model predicts an edge on a pair with a gold edge in either direction. FAIL = micro F1 <0.35 or recall <0.50 (D-21 revisit trigger; options: tune on non-DSA pairs, two-step yes/no, thinking mode via D-29 amendment). Otherwise CONDITIONAL (proceed, document limitation, no tuning on DSA).
Reported, not gated: swap consistency, confusion matrices, sensitivity variant, latency.
Reasoning: set before seeing any pilot results; thresholds are judgment-based, not derived from a benchmark; change only via a new decision entry made before a run;
(2) Correction to [D-32] item 1 line count: [D-32] stated `repositories/dataset/EKG-Dataset/DSA_gold_standard_MEKG.txt` has "840 lines across 29 nodes". Direct measurement (`wc -l`) confirms the file has 841 lines (840 distinct ordered pairs + 1 duplicate row `binary_search_tree;recursion;1`), exactly matching `docs/context/data-formats.md`.
Affects: `docs/decisions/decision-log.md`, `scripts/pilot_dsa_zero_shot.py`, `tests/test_pilot.py`, FIX-005.

**[D-35]** Experimental sweep sizes, accuracy evaluation scope, local embedding model, and Strategy 2 threshold:
(1) Sweep sizes & repeats: sweep sizes 50, 100, 200, 500, 1000, 2000 x 10 trials;
(2) Accuracy mode: all 29 DSA nodes + seeded sample of 30 Metacademy nodes, 1 run each;
(3) DATA-004 parameters: CS domain, graph-level domain string "computer science", snake_case per D-21, no edges, fixed seed, cached, deduplicated, no overlap with any corpus node, >=2100 names;
(4) Embedding model: local sentence-transformers `all-MiniLM-L6-v2` on CPU, version pinned (local execution keeps `embed_s` free of network latency; hosted embedding APIs rejected);
(5) Strategy 2 threshold: fixed a priori at 0.6, sensitivity analyses at 0.4 and 0.5, no tuning on evaluation corpora;
(6) Artifact tracking: `results/` untracked in `.gitignore` except the accepted pilot run, which will be force-added.
Reasoning: fixes experimental matrix before execution, isolates embedding computation timing from network jitter, prevents post-hoc threshold tuning on evaluation graphs, and keeps repository clean from intermediate sweep artifacts. Affects: `docs/tasks/status.md` (DATA-004), `.gitignore`, `harness.py`, `scripts/run_experiment.py`, STRAT-002, DATA-004.

**[D-36]** Model identity integrity, G1 validity amendment, default model alias, and off-peak pilot scheduling:
(1) Model identifier & alias: `DeepSeekClient` default model is updated to `"deepseek-flash"` (standard official API model alias replacing `"deepseek-v4-flash"`). API response `model_id` provenance is strictly enforced from the response `"model"` field (`""` if absent or None, never falling back to configured model name). In offline simulation, `FakeLLMClient` defaults to `"fake-deepseek-flash"` and exposes constant `max_tokens = 16`; unexposed client parameters in manifest extraction default to `None` without fabrication.
(2) G1 validity model check amended (supersedes model identity criterion in [D-34]): G1 validity requires `len(set(observed_model_ids)) == 1` (exactly one observed model ID across all calls; an empty observed list fails). Model concordance with configured name (`configured_equals_observed: bool`) is recorded as an informational, un-gated metric.
(3) Off-peak pricing and pilot scheduling: DeepSeek API off-peak pricing applies during 16:30–00:30 UTC (00:30–08:30 Beijing time), offering a 50% discount: input cache miss $0.15/M (vs $0.30/M peak), cache hit $0.003/M (vs $0.006/M peak), and output $0.60/M (vs $1.20/M peak). Pilot execution (812 calls) and future live sweeps should be scheduled within off-peak windows when practical.
Reasoning: prevents silent masking of API response model anomalies or empty model telemetry, decouples G1 protocol validity from potential vendor routing alias mismatches while tracking concordance, locks official current DeepSeek model alias strings, and minimizes API budget expenditure via off-peak execution. Affects: `src/graph_insertion/llm.py`, `src/graph_insertion/harness.py`, `scripts/pilot_dsa_zero_shot.py`, `tests/test_llm.py`, `tests/test_harness.py`, `tests/test_pilot.py`, FIX-006.

**[D-37]** Off-peak window correction, DSA pilot acceptance outcome, decision step locked:
(1) Correction to [D-36] item 3: the off-peak window stated in [D-36] (16:30–00:30 UTC) was incorrect. Per DeepSeek's official pricing documentation (verified 2026-10-07): peak hours are 01:00–04:00 and 06:00–10:00 UTC, Monday through Friday, excluding Chinese public holidays; all other times (including weekends, weekdays 00:00–01:00, 04:00–06:00, 10:00–24:00 UTC, and Chinese public holidays) are off-peak. Flash pricing per 1M tokens: input cache-miss $0.15 off-peak / $0.30 peak, cache-hit $0.003 / $0.006, output $0.60 / $1.20. Additional facts omitted from [D-36]: legacy model identifiers `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` remain accepted by the API endpoint but are retired and served by DeepSeek-V4.1-Flash; the earlier v2 probe runs used the legacy name and were served by this identical model; DeepSeek's pricing page lists model version "DeepSeek-V4.1-Flash" but publishes no dated snapshot ID (updating the finding in FIX-004). All timed experiment sweeps and harness runs must be scheduled off-peak under THIS corrected window.
(2) Pilot outcome: DSA pilot, run ID `20261007_053743Z` (executed 05:37–05:49 UTC, Wednesday, off-peak), prompt v2, configured model `deepseek-flash`, API-reported model ID `deepseek-flash` (API echoes the requested alias; no underlying version string is observable in response payloads).
- G1 Validity: PASS across all criteria (0 transport failures, 0 parse failures / 0.0%, 0 reasoning tokens, exactly 1 observed model ID matching configured, prompt version v2, 0 retried calls / 0.0%).
- G2 Usefulness: CONDITIONAL verdict. Micro F1 = 0.5410 (passes >=0.50 threshold), micro recall = 0.6111 (below 0.70 pass threshold, but above 0.50 fail threshold, so not FAIL), direction-flip rate = 12/78 = 0.1538 (exceeds 0.15 threshold by one call). Micro precision = 0.4853, macro F1 = 0.5346, macro precision = 0.5523, macro recall = 0.6064. 3-way call accuracy = 0.8765 (sensitivity variant = 0.8756), swap consistency = 0.8571 (348/406 unordered pairs; 13 pairs return the same directed token in both orders, 45 return edge-vs-NONE). Edge totals: TP = 66, FP = 70, FN = 42, with 1 prediction on the unjudged pair. Shortlist recall = 1.0 by construction (brute-force candidate set at n=29); these metrics define the empirical brute-force accuracy ceiling for DSA. Run resource metrics: total cost $0.0198 (123,872 input tokens, 2,035 output tokens, 0 cache hits), mean latency 0.834 s, median 0.808 s, p95 1.183 s, max latency 4.68 s, 0 retries.
(3) Decision on decision step: per [D-34], CONDITIONAL acceptance requires proceeding with prompt v2 unchanged as the fixed shared decision step across all four strategies, documenting this performance baseline and its limitations in Chapter 3, and disallowing further prompt tuning on DSA. Rejected alternatives: further prompt tuning (risks overfitting to DSA); judging each candidate pair in both directions and ensembling (doubles LLM calls per candidate pair, violates [D-29] single-call contract, and alters the measured candidate-narrowing comparison).
(4) Telemetry note: raw pilot call records in `raw_calls.jsonl` carry no per-call timestamps; the execution window is bounded by output directory name (`20261007_053743Z`) and summary `timestamp_utc` (`05:49:00Z`). In contrast, measurement harness records (`harness.py`) do record per-trial ISO UTC timestamps (`timestamp`).
Reasoning: acceptance criteria were locked a priori ([D-34]); `evaluate_acceptance` pure function computed CONDITIONAL; preserves evaluation integrity and fixes accurate vendor window parameters. Affects: thesis Chapter 3 Section 3.2.6 (prompt lock, limitations, model naming), DOC-002, scheduling of all Phase 2 and Phase 3 experimental sweeps.




