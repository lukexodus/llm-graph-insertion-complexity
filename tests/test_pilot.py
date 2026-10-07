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
from scripts.pilot_dsa_zero_shot import score_pilot


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
