"""
test_decision.py — INFRA-006 Unit Tests
=======================================
Tests for PairwiseDecisionStep, prompt construction, parsing, token edge mapping,
pilot gold label mapping, and end-to-end integration with insert_node.
"""

from __future__ import annotations

import pytest

from graph_insertion.decision import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    DecisionParseError,
    PairwiseDecisionStep,
)
from graph_insertion.embedding import FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph, GoldJudgmentSet, SourceKind
from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
from graph_insertion.strategy import insert_node
from scripts.pilot_dsa_zero_shot import (
    compute_gold_unordered_label,
    map_token_to_unordered_relation,
)
from tests.test_strategy_interface import TinyFakeStrategy


class TestPromptConstruction:
    """Verify prompt formatting, embed_text compliance, and isolation."""

    def test_prompt_with_domain_context(self):
        fake = FakeLLMClient()
        step = PairwiseDecisionStep(fake)
        user_prompt = step.build_user_prompt(
            "binary_search_tree", "binary_search", domain_context="data structures"
        )
        expected = (
            "Subject area: data structures\n"
            "Concept X: binary search tree\n"
            "Concept Y: binary search"
        )
        assert user_prompt == expected
        assert ".txt" not in user_prompt
        assert "_" not in user_prompt

    def test_prompt_without_domain_context_omits_subject_area(self):
        fake = FakeLLMClient()
        step = PairwiseDecisionStep(fake)
        user_prompt = step.build_user_prompt(
            "graph_traversal", "breadth_first_search", domain_context=None
        )
        expected = (
            "Concept X: graph traversal\n"
            "Concept Y: breadth first search"
        )
        assert user_prompt == expected
        assert "Subject area:" not in user_prompt

    def test_prompt_contains_only_two_concepts(self):
        fake = FakeLLMClient()
        step = PairwiseDecisionStep(fake)
        user_prompt = step.build_user_prompt("concept_a", "concept_b", "domain")
        lines = user_prompt.splitlines()
        assert len(lines) == 3
        assert lines[0] == "Subject area: domain"
        assert lines[1] == "Concept X: concept a"
        assert lines[2] == "Concept Y: concept b"


class TestTokenParsingAndEdgeOrientation:
    """Verify X_PREREQ_Y, Y_PREREQ_X, NONE, and junk handling."""

    def test_x_prereq_y_produces_new_to_cand_edge(self):
        fake = FakeLLMClient(responses="X_PREREQ_Y", latency_s=0.01)
        step = PairwiseDecisionStep(fake)
        outcome = step.decide("heap", ("tree",))
        assert outcome.edges == (("heap", "tree"),)
        assert outcome.llm_calls == 1
        assert pytest.approx(outcome.llm_seconds) == 0.01

    def test_y_prereq_x_produces_cand_to_new_edge(self):
        fake = FakeLLMClient(responses="Y_PREREQ_X", latency_s=0.02)
        step = PairwiseDecisionStep(fake)
        outcome = step.decide("heap", ("tree",))
        assert outcome.edges == (("tree", "heap"),)
        assert outcome.llm_calls == 1
        assert pytest.approx(outcome.llm_seconds) == 0.02

    def test_none_produces_no_edge(self):
        fake = FakeLLMClient(responses="NONE", latency_s=0.01)
        step = PairwiseDecisionStep(fake)
        outcome = step.decide("heap", ("tree",))
        assert outcome.edges == ()
        assert outcome.llm_calls == 1

    def test_whitespace_and_lowercase_normalized(self):
        fake = FakeLLMClient(responses="  x_prereq_y \n")
        step = PairwiseDecisionStep(fake)
        outcome = step.decide("heap", ("tree",))
        assert outcome.edges == (("heap", "tree"),)

    def test_unparseable_record_policy_treats_as_none_and_records(self):
        fake = FakeLLMClient(responses="I think tree is related to heap.")
        meter = MeteredLLMClient(fake)
        step = PairwiseDecisionStep(meter, strict=False)

        outcome = step.decide("heap", ("tree",))
        assert outcome.edges == ()
        assert outcome.llm_calls == 1
        assert meter.parse_failures == 1
        assert meter.failed_parses == ["I think tree is related to heap."]

    def test_unparseable_strict_policy_raises(self):
        fake = FakeLLMClient(responses="Junk answer")
        step = PairwiseDecisionStep(fake, strict=True)
        with pytest.raises(DecisionParseError, match="Unparseable response"):
            step.decide("heap", ("tree",))

    def test_mixed_candidates_sequential_calling(self):
        # candidate1 -> X_PREREQ_Y, candidate2 -> NONE, candidate3 -> Y_PREREQ_X
        responses = {
            "Concept X: new\nConcept Y: c1": "X_PREREQ_Y",
            "Concept X: new\nConcept Y: c2": "NONE",
            "Concept X: new\nConcept Y: c3": "Y_PREREQ_X",
        }
        fake = FakeLLMClient(responses=responses, latency_s=0.01)
        step = PairwiseDecisionStep(fake)

        candidates = ("c1", "c2", "c3")
        outcome = step.decide("new", candidates)
        assert outcome.llm_calls == 3
        assert pytest.approx(outcome.llm_seconds) == 0.03
        assert outcome.edges == (("new", "c1"), ("c3", "new"))
        assert len(fake.call_history) == 3
        # In exact candidate order
        assert "c1" in fake.call_history[0]["user"]
        assert "c2" in fake.call_history[1]["user"]
        assert "c3" in fake.call_history[2]["user"]


class TestPilotGoldLabelMapping:
    """Verify gold label classification including the DSA unjudged row."""

    def test_gold_mapping_and_sensitivity(self):
        gold = GoldJudgmentSet(source_kind=SourceKind.GOLD)
        # In SourceKind.GOLD: (col1, col2, 1) means col2 is prereq of col1 (oriented_edge: col2 -> col1)
        # Record A is prereq of B: col2=A, col1=B, label=1
        gold.record("b", "a", 1)
        gold.record("a", "b", 0)

        # Record D is prereq of C (i.e. B is prereq of A for pair (c, d)): col2=D, col1=C, label=1
        gold.record("c", "d", 1)
        gold.record("d", "c", 0)

        # Record E and F: neither is prereq
        gold.record("e", "f", 0)
        gold.record("f", "e", 0)

        # Record G and H: unjudged (missing row in one direction)
        gold.record("g", "h", 0)
        # (h, g) not recorded -> is_prerequisite returns None

        # Check A, B (A is prereq of B)
        rel_ab, is_unjudged = compute_gold_unordered_label(gold, "a", "b")
        assert rel_ab == "A_PREREQ_B"
        assert not is_unjudged

        # Check C, D (D is prereq of C -> B_PREREQ_A)
        rel_cd, is_unjudged = compute_gold_unordered_label(gold, "c", "d")
        assert rel_cd == "B_PREREQ_A"
        assert not is_unjudged

        # Check E, F
        rel_ef, is_unjudged = compute_gold_unordered_label(gold, "e", "f")
        assert rel_ef == "NONE"
        assert not is_unjudged

        # Check G, H
        rel_gh, is_unjudged = compute_gold_unordered_label(gold, "g", "h")
        assert rel_gh == "EXCLUDED"
        assert is_unjudged

    def test_map_token_to_unordered_relation(self):
        # A < B
        assert map_token_to_unordered_relation("X_PREREQ_Y", "a", "b", "a", "b") == "A_PREREQ_B"
        assert map_token_to_unordered_relation("Y_PREREQ_X", "a", "b", "a", "b") == "B_PREREQ_A"
        assert map_token_to_unordered_relation("NONE", "a", "b", "a", "b") == "NONE"

        # Roles swapped: new is B, cand is A
        assert map_token_to_unordered_relation("X_PREREQ_Y", "b", "a", "a", "b") == "B_PREREQ_A"
        assert map_token_to_unordered_relation("Y_PREREQ_X", "b", "a", "a", "b") == "A_PREREQ_B"
        assert map_token_to_unordered_relation("NONE", "b", "a", "a", "b") == "NONE"

        # Junk
        assert map_token_to_unordered_relation("JUNK", "a", "b", "a", "b") == "PARSE_FAILURE"


class TestInsertNodeIntegration:
    """Verify end-to-end insert_node with PairwiseDecisionStep and FakeLLMClient."""

    def test_end_to_end_insertion_with_metered_llm(self):
        graph = ConceptGraph(domain_context="data structures")
        graph.add_node("alpha")
        graph.add_node("beta")

        embedder = FakeEmbedder(dim=16, seed=42)
        meter_embed = MeteredEmbedder(embedder)

        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(graph, meter_embed)
        meter_embed.reset()

        # Decision step returning X_PREREQ_Y for alpha, and NONE for beta
        def scripted_llm(sys_prompt: str, user_prompt: str) -> str:
            if "Concept Y: alpha" in user_prompt:
                return "X_PREREQ_Y"
            return "NONE"

        fake_llm = FakeLLMClient(responses=scripted_llm, latency_s=0.01, input_tokens=15, output_tokens=2)
        meter_llm = MeteredLLMClient(fake_llm)
        step = PairwiseDecisionStep(meter_llm)

        snap_before = meter_llm.snapshot()

        result = insert_node(
            strat,
            graph,
            step,
            "gamma",
            metered_embedder=meter_embed,
        )

        snap_after = meter_llm.snapshot()
        delta = snap_after - snap_before

        assert result.new_name == "gamma"
        assert graph.has_node("gamma")
        # delta is prerequisite of alpha
        assert graph.has_prereq_edge("gamma", "alpha")
        assert not graph.has_prereq_edge("alpha", "gamma")

        # Metrics check
        assert result.metrics.llm_calls == 2
        assert result.metrics.n_before == 2
        assert result.metrics.shortlist_size == 2
        assert delta.calls == 2
        assert delta.input_tokens == 30
        assert delta.output_tokens == 4
        assert strat.on_inserted_called is True
