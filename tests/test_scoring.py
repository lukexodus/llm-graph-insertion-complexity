"""
test_scoring.py — INFRA-004 Unit Tests
======================================
Tests for pure scoring functions, shortlist recall vs end-to-end recall,
unjudged pair exclusions, and micro/macro aggregations.
"""

from __future__ import annotations

import pytest

from graph_insertion.graph_representation import ConceptGraph, GoldJudgmentSet, SourceKind
from graph_insertion.scoring import (
    aggregate_scores,
    compute_gold_incident_edges,
    compute_gold_neighbours,
    score_node_insertion,
)


@pytest.fixture
def fixture_graph_and_gold():
    graph = ConceptGraph(domain_context="testing")
    # Gold positive edges:
    # a -> h
    # h -> b
    # h -> c
    graph.add_prereq_edge("a", "h")
    graph.add_prereq_edge("h", "b")
    graph.add_prereq_edge("h", "c")

    # Judgment set (SourceKind.GOLD: col1, col2, 1 means col2 -> col1)
    judgments = GoldJudgmentSet(source_kind=SourceKind.GOLD)
    # a -> h: col2=a, col1=h, label=1
    judgments.record("h", "a", 1)
    judgments.record("a", "h", 0)

    # h -> b: col2=h, col1=b, label=1
    judgments.record("b", "h", 1)
    judgments.record("h", "b", 0)

    # h -> c: col2=h, col1=c, label=1
    judgments.record("c", "h", 1)
    judgments.record("h", "c", 0)

    # Non-edge d & h: both label 0
    judgments.record("d", "h", 0)
    judgments.record("h", "d", 0)

    # Unjudged pair e & h: (e, h) recorded as 0, (h, e) missing
    judgments.record("e", "h", 0)

    return graph, judgments


class TestScoringPureFunctions:
    """Verify ground truth extraction and single-node scoring."""

    def test_compute_gold_incident_edges_and_neighbours(self, fixture_graph_and_gold):
        graph, _ = fixture_graph_and_gold
        incident = compute_gold_incident_edges(graph, "h")
        assert incident == {("a", "h"), ("h", "b"), ("h", "c")}

        neighbours = compute_gold_neighbours(graph, "h")
        assert neighbours == {"a", "b", "c"}

    def test_score_node_insertion_all_correct(self, fixture_graph_and_gold):
        graph, judgments = fixture_graph_and_gold
        candidates = ("a", "b", "c", "d")
        decided_edges = (("a", "h"), ("h", "b"), ("h", "c"))

        score = score_node_insertion(
            node="h",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=candidates,
            decided_edges=decided_edges,
        )

        assert score.node == "h"
        assert score.gold_positives == 3
        assert score.gold_neighbours == 3
        assert score.shortlist_hits == 3
        assert score.shortlist_recall == 1.0
        assert score.tp == 3
        assert score.fp == 0
        assert score.fn == 0
        assert score.excluded_predictions == 0
        assert score.precision == 1.0
        assert score.recall == 1.0
        assert score.f1 == 1.0

    def test_shortlist_recall_separate_from_e2e_recall(self, fixture_graph_and_gold):
        graph, judgments = fixture_graph_and_gold
        # Narrowing only retrieved 'a', missing 'b' and 'c'
        candidates = ("a", "d")
        # Decision step correctly decided 'a' -> 'h'
        decided_edges = (("a", "h"),)

        score = score_node_insertion(
            node="h",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=candidates,
            decided_edges=decided_edges,
        )

        # Shortlist recall: 1 hit out of 3 gold neighbours = 1/3
        assert pytest.approx(score.shortlist_recall) == 1.0 / 3.0
        # End-to-end recall: 1 TP out of 3 gold positives = 1/3
        assert score.tp == 1
        assert score.fn == 2
        assert score.precision == 1.0
        assert pytest.approx(score.recall) == 1.0 / 3.0
        assert pytest.approx(score.f1) == 0.5

    def test_unjudged_pair_exclusion_and_sensitivity(self, fixture_graph_and_gold):
        graph, judgments = fixture_graph_and_gold
        # Model predicted:
        # 1. ("a", "h") -> True (TP)
        # 2. ("d", "h") -> False in gold (FP)
        # 3. ("h", "e") -> Unjudged in gold (Excluded in standard, FP in sensitivity)
        # Gold had ("h", "b") and ("h", "c") which were not predicted -> FN=2
        candidates = ("a", "d", "e")
        decided_edges = (("a", "h"), ("d", "h"), ("h", "e"))

        score = score_node_insertion(
            node="h",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=candidates,
            decided_edges=decided_edges,
        )

        assert score.tp == 1
        assert score.fp == 1
        assert score.fn == 2
        assert score.excluded_predictions == 1

        # Standard precision excludes the unjudged prediction:
        # TP / (TP + FP) = 1 / (1 + 1) = 0.5
        assert score.precision == 0.5
        assert pytest.approx(score.recall) == 1.0 / 3.0

        # Sensitivity precision treats unjudged prediction as FP:
        # TP / (TP + FP_sens) = 1 / (1 + 2) = 1/3
        assert score.fp_sensitivity == 2
        assert pytest.approx(score.precision_sensitivity) == 1.0 / 3.0
        assert pytest.approx(score.recall_sensitivity) == 1.0 / 3.0


class TestScoreAggregation:
    """Verify micro and macro aggregation across multiple node scores."""

    def test_aggregate_scores_micro_and_macro(self, fixture_graph_and_gold):
        graph, judgments = fixture_graph_and_gold

        # Node 1: Perfect (P=1.0, R=1.0, F1=1.0, shortlist_recall=1.0, TP=3, FP=0, FN=0)
        s1 = score_node_insertion(
            node="h",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=("a", "b", "c"),
            decided_edges=(("a", "h"), ("h", "b"), ("h", "c")),
        )

        # Node 2: Subgraph centered on 'a' (in gold, incident edges to 'a' is only ('a', 'h'))
        # Suppose model missed ('a', 'h') and predicted ('d', 'a') (which is False)
        # TP=0, FP=1, FN=1 -> P=0.0, R=0.0, F1=0.0
        judgments.record("d", "a", 0)
        judgments.record("a", "d", 0)
        s2 = score_node_insertion(
            node="a",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=("d",),
            decided_edges=(("d", "a"),),
        )

        agg = aggregate_scores([s1, s2])
        assert agg.num_nodes == 2
        assert agg.tp_total == 3
        assert agg.fp_total == 1
        assert agg.fn_total == 1

        # Micro: TP_tot / (TP_tot + FP_tot) = 3 / (3 + 1) = 0.75
        assert agg.precision_micro == 0.75
        # Micro recall: 3 / (3 + 1) = 0.75
        assert agg.recall_micro == 0.75
        assert agg.f1_micro == 0.75

        # Macro: average of per-node metrics
        # P_macro = (1.0 + 0.0) / 2 = 0.5
        assert agg.precision_macro == 0.5
        # R_macro = (1.0 + 0.0) / 2 = 0.5
        assert agg.recall_macro == 0.5
        assert agg.f1_macro == 0.5

    def test_aggregate_scores_undefined_exclusion(self, fixture_graph_and_gold):
        graph, judgments = fixture_graph_and_gold

        # Node 1: Perfect (P=1.0, R=1.0, F1=1.0, shortlist_recall=1.0)
        s1 = score_node_insertion(
            node="h",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=("a", "b", "c"),
            decided_edges=(("a", "h"), ("h", "b"), ("h", "c")),
        )

        # Node 2: Gold incident edge exists, but no predictions made (decided_edges=())
        # TP=0, FP=0, FN=1 -> precision=None, recall=0.0, F1=0.0 (included in macro F1!)
        judgments.record("d", "a", 0)
        judgments.record("a", "d", 0)
        s2 = score_node_insertion(
            node="a",
            gold_graph=graph,
            judgments=judgments,
            shortlist_candidates=("d",),
            decided_edges=(),
        )
        assert s2.precision is None
        assert s2.recall == 0.0
        assert s2.f1 == 0.0

        agg = aggregate_scores([s1, s2])
        # s1 has defined precision; both have defined recall and f1
        assert agg.n_precision_defined == 1
        assert agg.n_recall_defined == 2
        assert agg.n_f1_defined == 2
        # Macro precision: mean of defined only = 1.0 / 1 = 1.0
        assert agg.precision_macro == 1.0
        # Macro recall: mean of defined = (1.0 + 0.0) / 2 = 0.5
        assert agg.recall_macro == 0.5
        # Macro f1: mean of defined = (1.0 + 0.0) / 2 = 0.5
        assert agg.f1_macro == 0.5

    def test_macro_f1_zero_and_undefined_cases(self):
        # Case (i): node with gold edges and zero predictions gives F1 = 0.0, included in macro F1
        g1 = ConceptGraph()
        g1.add_node("x")
        g1.add_node("y")
        g1.add_prereq_edge("x", "y")  # incident to both
        j1 = GoldJudgmentSet()
        j1.record("x", "y", 1)
        j1.record("y", "x", 0)
        s_i = score_node_insertion(
            node="x",
            gold_graph=g1,
            judgments=j1,
            shortlist_candidates=("y",),
            decided_edges=(),
        )
        assert s_i.tp == 0 and s_i.fn == 1 and s_i.fp == 0
        assert s_i.f1 == 0.0
        assert s_i.precision is None

        # Case (ii): node with no gold edges and one false positive gives F1 = 0.0
        g2 = ConceptGraph()
        g2.add_node("isolated")
        g2.add_node("other")
        j2 = GoldJudgmentSet()
        j2.record("isolated", "other", 0)
        j2.record("other", "isolated", 0)
        s_ii = score_node_insertion(
            node="isolated",
            gold_graph=g2,
            judgments=j2,
            shortlist_candidates=("other",),
            decided_edges=(("isolated", "other"),),
        )
        assert s_ii.tp == 0 and s_ii.fn == 0 and s_ii.fp == 1
        assert s_ii.f1 == 0.0
        assert s_ii.precision == 0.0
        assert s_ii.recall is None

        # Case (iii): node with no gold edges and no predictions is excluded (F1 = None)
        s_iii = score_node_insertion(
            node="isolated",
            gold_graph=g2,
            judgments=j2,
            shortlist_candidates=("other",),
            decided_edges=(),
        )
        assert s_iii.tp == 0 and s_iii.fn == 0 and s_iii.fp == 0
        assert s_iii.f1 is None
        assert s_iii.precision is None
        assert s_iii.recall is None

        # Case (iv): when n_defined == 0, macro value must be None
        agg_empty = aggregate_scores([s_iii])
        assert agg_empty.n_f1_defined == 0
        assert agg_empty.f1_macro is None
        assert agg_empty.precision_macro is None
        assert agg_empty.recall_macro is None

        # Aggregation with case (i), case (ii), and case (iii):
        # case (iii) excluded, case (i) and (ii) yield 0.0
        agg_both = aggregate_scores([s_i, s_ii, s_iii])
        assert agg_both.n_f1_defined == 2
        assert agg_both.f1_macro == 0.0

