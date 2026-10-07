"""
test_pilot.py — Unit Tests for Pilot Pure Functions
===================================================
Tests for score_pilot, token parsing, and hand-built directional validation.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from graph_insertion.decision import parse_token
from graph_insertion.graph_representation import (
    ConceptGraph,
    GoldJudgmentSet,
    SourceKind,
)
from scripts.pilot_dsa_zero_shot import evaluate_acceptance, score_pilot


class TestPilotScoring:
    """Verify pure scoring function score_pilot with hand-built fixtures."""

    def test_score_pilot_y_prereq_x_counts_as_tp_and_fp(self):
        """Verify that when node n is evaluated as X, a candidate Y with Y_PREREQ_X

        correctly predicts (Y -> X):
          - if Y -> X is gold, it counts as TP
          - if Y -> X is not gold, it counts as FP
        """
        graph = ConceptGraph(domain_context="toy_domain")
        for node in ("node_x", "node_y1", "node_y2"):
            graph.add_node(node)

        # Ground truth: node_y1 is a prerequisite of node_x (node_y1 -> node_x)
        graph.add_prereq_edge("node_y1", "node_x")

        gold = GoldJudgmentSet(source_kind=SourceKind.GOLD)
        # node_y1 -> node_x: col2=node_y1, col1=node_x, label=1
        gold.record("node_x", "node_y1", 1)
        gold.record("node_y1", "node_x", 0)

        # node_y2 & node_x: no prerequisite relationship
        gold.record("node_x", "node_y2", 0)
        gold.record("node_y2", "node_x", 0)

        # node_y1 & node_y2: no prerequisite relationship
        gold.record("node_y1", "node_y2", 0)
        gold.record("node_y2", "node_y1", 0)

        # Hand-built calls where node_x is the new concept (X):
        # 1. Against node_y1 (Y): model predicts Y_PREREQ_X -> edge (node_y1, node_x) [GOLD TRUE -> TP]
        # 2. Against node_y2 (Y): model predicts Y_PREREQ_X -> edge (node_y2, node_x) [GOLD FALSE -> FP]
        calls = [
            # Calls where new_name is node_x
            {
                "new_name": "node_x",
                "candidate": "node_y1",
                "response_text": "Y_PREREQ_X",
                "raw_token": "Y_PREREQ_X",
            },
            {
                "new_name": "node_x",
                "candidate": "node_y2",
                "response_text": "Y_PREREQ_X",
                "raw_token": "Y_PREREQ_X",
            },
            # Reverse calls for node_y1 as new_name
            {
                "new_name": "node_y1",
                "candidate": "node_x",
                "response_text": "X_PREREQ_Y",  # X=node_y1 is prereq of Y=node_x -> (node_y1, node_x) [TP]
                "raw_token": "X_PREREQ_Y",
            },
            {
                "new_name": "node_y1",
                "candidate": "node_y2",
                "response_text": "NONE",
                "raw_token": "NONE",
            },
            # Reverse calls for node_y2 as new_name
            {
                "new_name": "node_y2",
                "candidate": "node_x",
                "response_text": "X_PREREQ_Y",  # X=node_y2 is prereq of Y=node_x -> (node_y2, node_x) [FP]
                "raw_token": "X_PREREQ_Y",
            },
            {
                "new_name": "node_y2",
                "candidate": "node_y1",
                "response_text": "NONE",
                "raw_token": "NONE",
            },
        ]

        scored = score_pilot(calls, gold=gold, gold_graph=graph)

        ev = scored["evaluation"]
        totals = ev["node_insertion_scoring"]["totals"]

        # For node_x:
        # Predicted: (node_y1, node_x) [TP], (node_y2, node_x) [FP]
        # For node_y1:
        # Predicted: (node_y1, node_x) [TP]
        # For node_y2:
        # Predicted: (node_y2, node_x) [FP]
        # Total TPs = 2, Total FPs = 2
        assert totals["tp"] == 2
        assert totals["fp"] == 2
        assert totals["fn"] == 0

        # Check individual node scores
        node_scores = {s["node"]: s for s in scored["node_scores"]}
        assert node_scores["node_x"]["tp"] == 1
        assert node_scores["node_x"]["fp"] == 1
        assert node_scores["node_x"]["fn"] == 0

        assert node_scores["node_y1"]["tp"] == 1
        assert node_scores["node_y1"]["fp"] == 0
        assert node_scores["node_y1"]["fn"] == 0

        assert node_scores["node_y2"]["tp"] == 0
        assert node_scores["node_y2"]["fp"] == 1
        assert node_scores["node_y2"]["fn"] == 0

    def test_parse_token_variants(self):
        assert parse_token("  x_prereq_y \n") == "X_PREREQ_Y"
        assert parse_token("Y_PREREQ_X") == "Y_PREREQ_X"
        assert parse_token("none") == "NONE"
        assert parse_token("I think X is prereq") is None
        assert parse_token("") is None
        assert parse_token("UNKNOWN") is None


class TestEvaluateAcceptance:
    """Verify evaluate_acceptance against D-34 G1 validity and G2 usefulness criteria."""

    def test_evaluate_acceptance_pass(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 2,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-flash"],
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 4,
            "evaluation": {
                "node_insertion_scoring": {
                    "micro": {"recall": 0.75, "f1": 0.55},
                },
                "direction_flips": 1,
                "calls_with_gold_and_pred_edge": 20,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["verdict"] == "PASS"
        assert res["g1_validity"]["model_identity"]["passed"] is True
        assert res["g1_validity"]["model_identity"]["configured_equals_observed"] is True
        assert res["g2_usefulness"]["verdict"] == "PASS"
        assert res["overall_verdict"] == "PASS"

    def test_evaluate_acceptance_fail(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-flash"],
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {
                    "micro": {"recall": 0.45, "f1": 0.30},
                },
                "direction_flips": 5,
                "calls_with_gold_and_pred_edge": 10,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["verdict"] == "PASS"
        assert res["g2_usefulness"]["verdict"] == "FAIL"
        assert res["overall_verdict"] == "FAIL"

    def test_evaluate_acceptance_conditional(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-flash"],
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {
                    "micro": {"recall": 0.65, "f1": 0.45},
                },
                "direction_flips": 1,
                "calls_with_gold_and_pred_edge": 10,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["verdict"] == "PASS"
        assert res["g2_usefulness"]["verdict"] == "CONDITIONAL"
        assert res["overall_verdict"] == "CONDITIONAL"

    def test_evaluate_acceptance_invalid_g1(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 1,  # triggers G1 invalidity
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-flash"],
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {
                    "micro": {"recall": 0.85, "f1": 0.70},
                },
                "direction_flips": 0,
                "calls_with_gold_and_pred_edge": 10,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["verdict"] == "FAIL"
        assert res["overall_verdict"] == "INVALID"

    def test_evaluate_acceptance_empty_observed_model_fails_g1(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": [],  # empty list
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {"micro": {"recall": 0.80, "f1": 0.60}},
                "direction_flips": 0,
                "calls_with_gold_and_pred_edge": 10,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["model_identity"]["passed"] is False
        assert res["g1_validity"]["model_identity"]["configured_equals_observed"] is False
        assert res["g1_validity"]["verdict"] == "FAIL"
        assert res["overall_verdict"] == "INVALID"

    def test_evaluate_acceptance_multiple_distinct_observed_models_fails_g1(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-flash", "deepseek-chat"],  # 2 distinct IDs
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {"micro": {"recall": 0.80, "f1": 0.60}},
                "direction_flips": 0,
                "calls_with_gold_and_pred_edge": 10,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["model_identity"]["passed"] is False
        assert res["g1_validity"]["model_identity"]["configured_equals_observed"] is False
        assert res["g1_validity"]["verdict"] == "FAIL"
        assert res["overall_verdict"] == "INVALID"

    def test_evaluate_acceptance_unmatched_single_model_passes_g1_with_unmatched_flag(self):
        summary = {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-chat"],  # single distinct ID, different from configured
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {"micro": {"recall": 0.80, "f1": 0.60}},
                "direction_flips": 0,
                "calls_with_gold_and_pred_edge": 10,
            },
        }
        res = evaluate_acceptance(summary)
        assert res["g1_validity"]["model_identity"]["passed"] is True
        assert res["g1_validity"]["model_identity"]["configured_equals_observed"] is False
        assert res["g1_validity"]["verdict"] == "PASS"
        assert res["overall_verdict"] == "PASS"


class TestG2AcceptanceBoundaries:
    """Test exact threshold boundary values for G2 usefulness criteria ([D-34])."""

    def _make_summary(self, recall: float, f1: float, flips: int, calls_with_edge: int) -> dict[str, Any]:
        return {
            "total_calls": 812,
            "transport_failure_count": 0,
            "parse_failure_count": 0,
            "configured_model": "deepseek-flash",
            "observed_model_ids": ["deepseek-flash"],
            "prompt_version": "v2",
            "token_usage": {"reasoning_tokens": 0},
            "retried_call_count": 0,
            "evaluation": {
                "node_insertion_scoring": {
                    "micro": {"recall": recall, "f1": f1},
                },
                "direction_flips": flips,
                "calls_with_gold_and_pred_edge": calls_with_edge,
            },
        }

    def test_boundary_exact_pass(self):
        # recall 0.70 + F1 0.50 + flip rate 0.15 => PASS
        s = self._make_summary(recall=0.70, f1=0.50, flips=15, calls_with_edge=100)
        res = evaluate_acceptance(s)
        assert res["g2_usefulness"]["verdict"] == "PASS"

    def test_boundary_f1_35_recall_50_is_conditional(self):
        # F1 0.35 + recall 0.50 => CONDITIONAL
        s = self._make_summary(recall=0.50, f1=0.35, flips=0, calls_with_edge=100)
        res = evaluate_acceptance(s)
        assert res["g2_usefulness"]["verdict"] == "CONDITIONAL"

    def test_boundary_f1_just_below_35_is_fail(self):
        # F1 0.3499 => FAIL
        s = self._make_summary(recall=0.50, f1=0.3499, flips=0, calls_with_edge=100)
        res = evaluate_acceptance(s)
        assert res["g2_usefulness"]["verdict"] == "FAIL"

    def test_boundary_recall_just_below_50_is_fail(self):
        # recall 0.4999 => FAIL
        s = self._make_summary(recall=0.4999, f1=0.50, flips=0, calls_with_edge=100)
        res = evaluate_acceptance(s)
        assert res["g2_usefulness"]["verdict"] == "FAIL"

    def test_boundary_flip_rate_just_above_15_is_conditional(self):
        # flip rate 0.1501 with passing recall/F1 => CONDITIONAL
        s = self._make_summary(recall=0.70, f1=0.50, flips=1501, calls_with_edge=10000)
        res = evaluate_acceptance(s)
        assert res["g2_usefulness"]["verdict"] == "CONDITIONAL"

