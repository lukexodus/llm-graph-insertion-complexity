"""
scoring.py — INFRA-004
======================
Pure functions for evaluating candidate insertion accuracy against GoldJudgmentSet.

Decisions recorded here:
  - Gold standard ground truth is exclusively DSA and Metacademy ([D-04], [D-05])
  - Canonical edge direction is (prereq -> dependent) ([D-23])
  - DSA unjudged pair exclusion and sensitivity reporting ([D-30])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from graph_insertion.graph_representation import ConceptGraph, GoldJudgmentSet


@dataclass(frozen=True)
class NodeScore:
    """Evaluation score for a single held-out node insertion trial.

    Attributes
    ----------
    node:
        The held-out concept name that was inserted.
    gold_positives:
        Number of ground-truth directed edges incident to this node in the full graph.
    gold_neighbours:
        Number of distinct adjacent nodes in ground truth.
    shortlist_size:
        Number of candidates shortlisted by the strategy.
    shortlist_hits:
        Number of gold-positive neighbours captured in the shortlist.
    shortlist_recall:
        Fraction of gold-positive neighbours present in the shortlist.
    predicted_edges:
        Number of directed edges decided and applied for this node.
    tp:
        True positives: predicted directed edges confirmed in ground truth.
    fp:
        False positives: predicted directed edges refuted in ground truth.
    fn:
        False negatives: gold directed edges not predicted.
    excluded_predictions:
        Number of predicted edges involving an unjudged pair ([D-30]).
    precision:
        Standard directed precision (excluding unjudged pairs): TP / (TP + FP).
    recall:
        Standard directed recall: TP / (TP + FN).
    f1:
        Standard directed F1 score.
    fp_sensitivity:
        False positives under sensitivity analysis (counting unjudged pairs as NONE).
    precision_sensitivity:
        Sensitivity precision: TP / (TP + FP_sensitivity).
    recall_sensitivity:
        Sensitivity recall: TP / (TP + FN).
    f1_sensitivity:
        Sensitivity F1 score.
    """
    node: str
    gold_positives: int
    gold_neighbours: int
    shortlist_size: int
    shortlist_hits: int
    shortlist_recall: float
    predicted_edges: int
    tp: int
    fp: int
    fn: int
    excluded_predictions: int
    precision: float
    recall: float
    f1: float
    fp_sensitivity: int
    precision_sensitivity: float
    recall_sensitivity: float
    f1_sensitivity: float


@dataclass(frozen=True)
class AggregateScore:
    """Aggregate accuracy evaluation across multiple held-out nodes in a corpus.

    Contains micro-aggregates (pooled counts) and macro-aggregates (unweighted mean of per-node metrics).
    """
    num_nodes: int
    gold_positives_total: int
    gold_neighbours_total: int
    shortlist_hits_total: int
    predicted_edges_total: int
    tp_total: int
    fp_total: int
    fn_total: int
    excluded_total: int
    # Micro aggregates (Standard)
    shortlist_recall_micro: float
    precision_micro: float
    recall_micro: float
    f1_micro: float
    # Macro aggregates (Standard)
    shortlist_recall_macro: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    # Sensitivity aggregates (Unjudged pair counted as NONE)
    fp_total_sensitivity: int
    precision_micro_sensitivity: float
    recall_micro_sensitivity: float
    f1_micro_sensitivity: float
    precision_macro_sensitivity: float
    recall_macro_sensitivity: float
    f1_macro_sensitivity: float


def compute_gold_incident_edges(graph: ConceptGraph, node: str) -> set[tuple[str, str]]:
    """Return all directed edges incident to *node* in *graph*."""
    incident: set[tuple[str, str]] = set()
    for prereq in graph.prerequisites_of(node):
        incident.add((prereq, node))
    for dep in graph.dependents_of(node):
        incident.add((node, dep))
    return incident


def compute_gold_neighbours(graph: ConceptGraph, node: str) -> set[str]:
    """Return all distinct nodes adjacent to *node* in *graph*."""
    prereqs = set(graph.prerequisites_of(node))
    deps = set(graph.dependents_of(node))
    return prereqs | deps


def score_node_insertion(
    *,
    node: str,
    gold_graph: ConceptGraph,
    judgments: GoldJudgmentSet,
    shortlist_candidates: Sequence[str],
    decided_edges: Sequence[tuple[str, str]],
) -> NodeScore:
    """Score a single held-out node insertion against ground truth graph and judgments.

    Parameters
    ----------
    node:
        The held-out concept name.
    gold_graph:
        The complete reference ConceptGraph containing *node*.
    judgments:
        The complete GoldJudgmentSet for the corpus.
    shortlist_candidates:
        Candidates shortlisted by the narrowing strategy.
    decided_edges:
        Canonical edges (prereq, dependent) decided and committed.

    Returns
    -------
    NodeScore
        Full metrics including TP/FP/FN, precision/recall/F1, and sensitivity variants.
    """
    gold_incident = compute_gold_incident_edges(gold_graph, node)
    gold_neighbours = compute_gold_neighbours(gold_graph, node)
    shortlist_set = set(shortlist_candidates)
    decided_set = set(decided_edges)

    shortlist_hits = len(gold_neighbours & shortlist_set)
    shortlist_recall = (
        shortlist_hits / len(gold_neighbours) if gold_neighbours else 1.0
    )

    tp = 0
    fp = 0
    excluded = 0

    for edge in decided_set:
        prereq, dep = edge
        other = dep if prereq == node else prereq

        # Check if pair {node, other} has an unjudged ordered direction
        j_forward = judgments.judgment_for_edge(prereq, dep)
        j_reverse = judgments.judgment_for_edge(dep, prereq)

        if j_forward is None or j_reverse is None:
            # Pair has an unjudged direction ([D-30])
            excluded += 1
        elif j_forward is True:
            tp += 1
        else:
            fp += 1

    fn = len(gold_incident - decided_set)

    # Standard metrics (excluding unjudged pairs)
    if tp + fp > 0:
        precision = tp / (tp + fp)
    elif tp + fp + fn == 0:
        precision = 1.0
    else:
        precision = 0.0

    if tp + fn > 0:
        recall = tp / (tp + fn)
    else:
        recall = 1.0

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    # Sensitivity metrics (unjudged pair counted as NONE / not a prereq -> predicted edge is FP)
    fp_sens = fp + excluded
    if tp + fp_sens > 0:
        precision_sens = tp / (tp + fp_sens)
    elif tp + fp_sens + fn == 0:
        precision_sens = 1.0
    else:
        precision_sens = 0.0

    recall_sens = recall
    if precision_sens + recall_sens > 0:
        f1_sens = 2 * precision_sens * recall_sens / (precision_sens + recall_sens)
    else:
        f1_sens = 0.0

    return NodeScore(
        node=node,
        gold_positives=len(gold_incident),
        gold_neighbours=len(gold_neighbours),
        shortlist_size=len(shortlist_candidates),
        shortlist_hits=shortlist_hits,
        shortlist_recall=shortlist_recall,
        predicted_edges=len(decided_edges),
        tp=tp,
        fp=fp,
        fn=fn,
        excluded_predictions=excluded,
        precision=precision,
        recall=recall,
        f1=f1,
        fp_sensitivity=fp_sens,
        precision_sensitivity=precision_sens,
        recall_sensitivity=recall_sens,
        f1_sensitivity=f1_sens,
    )


def aggregate_scores(node_scores: Sequence[NodeScore]) -> AggregateScore:
    """Aggregate a sequence of NodeScore objects into micro and macro evaluation metrics."""
    if not node_scores:
        return AggregateScore(
            num_nodes=0,
            gold_positives_total=0,
            gold_neighbours_total=0,
            shortlist_hits_total=0,
            predicted_edges_total=0,
            tp_total=0,
            fp_total=0,
            fn_total=0,
            excluded_total=0,
            shortlist_recall_micro=0.0,
            precision_micro=0.0,
            recall_micro=0.0,
            f1_micro=0.0,
            shortlist_recall_macro=0.0,
            precision_macro=0.0,
            recall_macro=0.0,
            f1_macro=0.0,
            fp_total_sensitivity=0,
            precision_micro_sensitivity=0.0,
            recall_micro_sensitivity=0.0,
            f1_micro_sensitivity=0.0,
            precision_macro_sensitivity=0.0,
            recall_macro_sensitivity=0.0,
            f1_macro_sensitivity=0.0,
        )

    n = len(node_scores)
    gold_pos_tot = sum(s.gold_positives for s in node_scores)
    gold_neigh_tot = sum(s.gold_neighbours for s in node_scores)
    shortlist_hits_tot = sum(s.shortlist_hits for s in node_scores)
    pred_edges_tot = sum(s.predicted_edges for s in node_scores)
    tp_tot = sum(s.tp for s in node_scores)
    fp_tot = sum(s.fp for s in node_scores)
    fn_tot = sum(s.fn for s in node_scores)
    excl_tot = sum(s.excluded_predictions for s in node_scores)
    fp_sens_tot = sum(s.fp_sensitivity for s in node_scores)

    # Micro standard
    sl_recall_micro = shortlist_hits_tot / gold_neigh_tot if gold_neigh_tot > 0 else 1.0
    prec_micro = tp_tot / (tp_tot + fp_tot) if (tp_tot + fp_tot) > 0 else 0.0
    rec_micro = tp_tot / (tp_tot + fn_tot) if (tp_tot + fn_tot) > 0 else 1.0
    f1_micro = (
        2 * prec_micro * rec_micro / (prec_micro + rec_micro)
        if (prec_micro + rec_micro) > 0
        else 0.0
    )

    # Macro standard
    sl_recall_macro = sum(s.shortlist_recall for s in node_scores) / n
    prec_macro = sum(s.precision for s in node_scores) / n
    rec_macro = sum(s.recall for s in node_scores) / n
    f1_macro = sum(s.f1 for s in node_scores) / n

    # Micro sensitivity
    prec_micro_sens = tp_tot / (tp_tot + fp_sens_tot) if (tp_tot + fp_sens_tot) > 0 else 0.0
    rec_micro_sens = rec_micro
    f1_micro_sens = (
        2 * prec_micro_sens * rec_micro_sens / (prec_micro_sens + rec_micro_sens)
        if (prec_micro_sens + rec_micro_sens) > 0
        else 0.0
    )

    # Macro sensitivity
    prec_macro_sens = sum(s.precision_sensitivity for s in node_scores) / n
    rec_macro_sens = sum(s.recall_sensitivity for s in node_scores) / n
    f1_macro_sens = sum(s.f1_sensitivity for s in node_scores) / n

    return AggregateScore(
        num_nodes=n,
        gold_positives_total=gold_pos_tot,
        gold_neighbours_total=gold_neigh_tot,
        shortlist_hits_total=shortlist_hits_tot,
        predicted_edges_total=pred_edges_tot,
        tp_total=tp_tot,
        fp_total=fp_tot,
        fn_total=fn_tot,
        excluded_total=excl_tot,
        shortlist_recall_micro=sl_recall_micro,
        precision_micro=prec_micro,
        recall_micro=rec_micro,
        f1_micro=f1_micro,
        shortlist_recall_macro=sl_recall_macro,
        precision_macro=prec_macro,
        recall_macro=rec_macro,
        f1_macro=f1_macro,
        fp_total_sensitivity=fp_sens_tot,
        precision_micro_sensitivity=prec_micro_sens,
        recall_micro_sensitivity=rec_micro_sens,
        f1_micro_sensitivity=f1_micro_sens,
        precision_macro_sensitivity=prec_macro_sens,
        recall_macro_sensitivity=rec_macro_sens,
        f1_macro_sensitivity=f1_macro_sens,
    )
