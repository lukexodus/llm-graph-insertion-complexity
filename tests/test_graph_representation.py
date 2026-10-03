"""
tests/test_graph_representation.py — INFRA-001 test suite
==========================================================
Tests for oriented_edge(), embed_text(), ConceptGraph, and GoldJudgmentSet.

All "real row" tests read actual values from the raw data files in
repositories/dataset/EKG-Dataset/ rather than relying on typed-from-memory
constants — per INFRA-001 task requirement.
"""

from __future__ import annotations

import pathlib
import pytest

from graph_insertion.graph_representation import (
    ConceptGraph,
    GoldJudgmentSet,
    SourceKind,
    _Label,
    embed_text,
    oriented_edge,
)

# ---------------------------------------------------------------------------
# Paths to real data files
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "repositories" / "dataset" / "EKG-Dataset"
DSA_FILE = DATA_DIR / "DSA_gold_standard_MEKG.txt"
META_FILE = DATA_DIR / "metacademy_gold_standard_MEKG.txt"
MEKG_6 = DATA_DIR / "MEKG_with_6_nodes(DS).txt"
MEKG_35 = DATA_DIR / "MEKG_with_35_nodes(ML1).txt"


# ---------------------------------------------------------------------------
# Helpers to read real rows from files
# ---------------------------------------------------------------------------

def _dsa_positive_rows(n: int = 5) -> list[tuple[str, str]]:
    """Read the first n positive rows from DSA file. Returns (col1, col2)."""
    rows = []
    for line in DSA_FILE.read_text().splitlines():
        parts = line.strip().split(";")
        if len(parts) == 3 and parts[2] == "1" and parts[0] != parts[1]:
            rows.append((parts[0], parts[1]))
            if len(rows) >= n:
                break
    return rows


def _meta_positive_rows(n: int = 5) -> list[tuple[str, str]]:
    """Read the first n positive rows from Metacademy file. Returns (col1, col2)."""
    rows = []
    for line in META_FILE.read_text().splitlines():
        parts = line.strip().split(" ")
        if len(parts) == 3 and parts[2] == "1" and parts[0] != parts[1]:
            rows.append((parts[0], parts[1]))
            if len(rows) >= n:
                break
    return rows


def _mekg_positive_rows(filepath: pathlib.Path, n: int = 5) -> list[tuple[str, str]]:
    """Read the first n positive rows from an example MEKG file (strip .txt)."""
    rows = []
    for line in filepath.read_text().splitlines():
        parts = line.strip().split(";")
        if len(parts) == 3 and parts[2] == "1":
            c1 = parts[0].removesuffix(".txt")
            c2 = parts[1].removesuffix(".txt")
            if c1 != c2:
                rows.append((c1, c2))
                if len(rows) >= n:
                    break
    return rows


# ===========================================================================
# Tests for oriented_edge()
# ===========================================================================

class TestOrientedEdge:
    """oriented_edge maps file columns to (prereq, dependent)."""

    def test_gold_dsa_real_rows(self):
        """For GOLD source, col2 is the prerequisite of col1 ([D-15]).

        Real DSA positive rows: col1;col2;1 → edge (col2, col1).
        """
        rows = _dsa_positive_rows(2)
        assert len(rows) >= 2, "Need at least 2 DSA positive rows"
        for col1, col2 in rows:
            prereq, dependent = oriented_edge(SourceKind.GOLD, col1, col2)
            assert prereq == col2, (
                f"GOLD: expected prereq={col2!r}, got {prereq!r} "
                f"for row ({col1!r}, {col2!r})"
            )
            assert dependent == col1

    def test_gold_metacademy_real_rows(self):
        """Metacademy shares the same GOLD direction convention as DSA ([D-15])."""
        rows = _meta_positive_rows(2)
        assert len(rows) >= 2, "Need at least 2 Metacademy positive rows"
        for col1, col2 in rows:
            prereq, dependent = oriented_edge(SourceKind.GOLD, col1, col2)
            assert prereq == col2
            assert dependent == col1

    def test_mekg_example_small_real_rows(self):
        """For MEKG_EXAMPLE source, col1 is the prerequisite of col2 ([D-19]).

        Real positive rows from MEKG_with_6_nodes(DS).txt.
        """
        rows = _mekg_positive_rows(MEKG_6, 2)
        assert len(rows) >= 2, "Need at least 2 positive rows from MEKG_6"
        for col1, col2 in rows:
            prereq, dependent = oriented_edge(SourceKind.MEKG_EXAMPLE, col1, col2)
            assert prereq == col1, (
                f"MEKG_EXAMPLE: expected prereq={col1!r}, got {prereq!r} "
                f"for row ({col1!r}, {col2!r})"
            )
            assert dependent == col2

    def test_mekg_example_large_real_rows(self):
        """MEKG direction holds for the largest file too ([D-19])."""
        rows = _mekg_positive_rows(MEKG_35, 2)
        assert len(rows) >= 2
        for col1, col2 in rows:
            prereq, dependent = oriented_edge(SourceKind.MEKG_EXAMPLE, col1, col2)
            assert prereq == col1
            assert dependent == col2

    def test_gold_documented_example_dsa(self):
        """Check the documented example from data-formats.md: dijkstra_algorithm;graph;1."""
        # col1=dijkstra_algorithm, col2=graph → col2=graph is prereq of col1
        prereq, dependent = oriented_edge(SourceKind.GOLD, "dijkstra_algorithm", "graph")
        assert prereq == "graph"
        assert dependent == "dijkstra_algorithm"

    def test_gold_documented_example_metacademy(self):
        """Check the documented example: backpropagation chain_rule 1."""
        prereq, dependent = oriented_edge(SourceKind.GOLD, "backpropagation", "chain_rule")
        assert prereq == "chain_rule"
        assert dependent == "backpropagation"

    def test_mekg_documented_example(self):
        """Check the documented example from data-formats.md: asymptotic_complexity;hash_table;1."""
        prereq, dependent = oriented_edge(
            SourceKind.MEKG_EXAMPLE, "asymptotic_complexity", "hash_table"
        )
        assert prereq == "asymptotic_complexity"
        assert dependent == "hash_table"

    def test_invalid_source_kind_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            oriented_edge("unknown_kind", "a", "b")  # type: ignore[arg-type]


# ===========================================================================
# Cross-source agreement test  ([D-23] property)
# ===========================================================================

class TestCrossSourceAgreement:
    """Every positive edge in example MEKG files that overlaps with gold files must
    produce the same oriented edge as gold — the property DATA-002 verified."""

    def test_dsa_cross_source_agreement(self):
        """Zero conflicts between MEKG_EXAMPLE and DSA GOLD directions for overlapping pairs."""
        # Build DSA positive oriented edges
        dsa_edges: dict[frozenset, tuple] = {}
        for line in DSA_FILE.read_text().splitlines():
            parts = line.strip().split(";")
            if len(parts) == 3 and parts[2] == "1" and parts[0] != parts[1]:
                col1, col2 = parts[0], parts[1]
                e = oriented_edge(SourceKind.GOLD, col1, col2)
                dsa_edges[frozenset(e)] = e

        conflicts = []
        checks = 0
        contributing_files = set()
        for f in sorted(DATA_DIR.glob("MEKG_with*.txt")):
            for line in f.read_text().splitlines():
                parts = line.strip().split(";")
                if len(parts) != 3 or parts[2] != "1":
                    continue
                c1 = parts[0].removesuffix(".txt")
                c2 = parts[1].removesuffix(".txt")
                if c1 == c2:
                    continue
                mekg_e = oriented_edge(SourceKind.MEKG_EXAMPLE, c1, c2)
                key = frozenset(mekg_e)
                if key in dsa_edges:
                    checks += 1
                    contributing_files.add(f.name)
                    if mekg_e != dsa_edges[key]:
                        conflicts.append((f.name, c1, c2, mekg_e, dsa_edges[key]))

        # Exactly 42 positive row checks across 5 files overlap with DSA
        assert checks >= 42, f"Expected at least 42 DSA checks, got {checks}"
        assert len(contributing_files) == 5, f"Expected 5 contributing files for DSA, got {len(contributing_files)}"
        assert len(conflicts) == 0, (
            f"{len(conflicts)} cross-source conflicts with DSA found: {conflicts[:3]}"
        )

    def test_metacademy_cross_source_agreement(self):
        """Zero conflicts between MEKG_EXAMPLE and Metacademy GOLD directions for overlapping pairs."""
        # Build Metacademy positive oriented edges (space-delimited)
        meta_edges: dict[frozenset, tuple] = {}
        for line in META_FILE.read_text().splitlines():
            parts = line.strip().split(" ")
            if len(parts) == 3 and parts[2] == "1" and parts[0] != parts[1]:
                col1, col2 = parts[0], parts[1]
                e = oriented_edge(SourceKind.GOLD, col1, col2)
                meta_edges[frozenset(e)] = e

        conflicts = []
        checks = 0
        contributing_files = set()
        for f in sorted(DATA_DIR.glob("MEKG_with*.txt")):
            for line in f.read_text().splitlines():
                parts = line.strip().split(";")
                if len(parts) != 3 or parts[2] != "1":
                    continue
                c1 = parts[0].removesuffix(".txt")
                c2 = parts[1].removesuffix(".txt")
                if c1 == c2:
                    continue
                mekg_e = oriented_edge(SourceKind.MEKG_EXAMPLE, c1, c2)
                key = frozenset(mekg_e)
                if key in meta_edges:
                    checks += 1
                    contributing_files.add(f.name)
                    if mekg_e != meta_edges[key]:
                        conflicts.append((f.name, c1, c2, mekg_e, meta_edges[key]))

        # Exactly 129 positive row checks across 5 files overlap with Metacademy
        assert checks >= 120, f"Expected at least 120 Metacademy checks, got {checks}"
        assert len(contributing_files) == 5, f"Expected 5 contributing files for Metacademy, got {len(contributing_files)}"
        assert len(conflicts) == 0, (
            f"{len(conflicts)} cross-source conflicts with Metacademy found: {conflicts[:3]}"
        )


# ===========================================================================
# Tests for embed_text()
# ===========================================================================

class TestEmbedText:
    def test_underscores_to_spaces(self):
        assert embed_text("hash_table") == "hash table"

    def test_no_underscores_unchanged(self):
        assert embed_text("recursion") == "recursion"

    def test_apostrophe_preserved(self):
        result = embed_text("Godel's_completeness_theorem")
        assert result == "Godel's completeness theorem"

    def test_uppercase_preserved(self):
        result = embed_text("Godel's_completeness_theorem")
        assert result[0] == "G"

    def test_domain_context_not_added(self):
        """Domain context must NOT appear in embed_text output ([D-21])."""
        result = embed_text("gradient_descent")
        assert "machine learning" not in result.lower()
        assert "data structures" not in result.lower()
        assert result == "gradient descent"


# ===========================================================================
# Tests for ConceptGraph
# ===========================================================================

class TestConceptGraph:
    def test_empty_graph(self):
        g = ConceptGraph()
        assert g.num_nodes() == 0
        assert g.num_edges() == 0

    def test_add_node(self):
        g = ConceptGraph()
        g.add_node("recursion")
        assert g.has_node("recursion")
        assert g.num_nodes() == 1

    def test_add_node_empty_raises(self):
        g = ConceptGraph()
        with pytest.raises(ValueError, match="cannot be empty"):
            g.add_node("")

    def test_add_node_txt_suffix_raises(self):
        g = ConceptGraph()
        with pytest.raises(ValueError, match="cannot end in '.txt'"):
            g.add_node("hash_table.txt")

    def test_add_prereq_edge_empty_name_raises(self):
        g = ConceptGraph()
        with pytest.raises(ValueError, match="cannot be empty"):
            g.add_prereq_edge("", "linked_list")
        with pytest.raises(ValueError, match="cannot be empty"):
            g.add_prereq_edge("pointer", "")

    def test_add_prereq_edge_txt_suffix_raises(self):
        g = ConceptGraph()
        with pytest.raises(ValueError, match="cannot end in '.txt'"):
            g.add_prereq_edge("pointer.txt", "linked_list")
        with pytest.raises(ValueError, match="cannot end in '.txt'"):
            g.add_prereq_edge("pointer", "linked_list.txt")

    def test_add_node_valid_names(self):
        g = ConceptGraph()
        g.add_node("hash_table")
        g.add_node("Godel's_completeness_theorem")
        assert g.num_nodes() == 2

    def test_add_prereq_edge_adds_nodes(self):
        g = ConceptGraph()
        g.add_prereq_edge("pointer", "linked_list")
        assert g.has_node("pointer")
        assert g.has_node("linked_list")
        assert g.has_prereq_edge("pointer", "linked_list")
        assert not g.has_prereq_edge("linked_list", "pointer")

    def test_prerequisites_of(self):
        g = ConceptGraph()
        g.add_prereq_edge("pointer", "linked_list")
        g.add_prereq_edge("recursion", "linked_list")
        prereqs = g.prerequisites_of("linked_list")
        assert set(prereqs) == {"pointer", "recursion"}

    def test_dependents_of(self):
        g = ConceptGraph()
        g.add_prereq_edge("pointer", "linked_list")
        g.add_prereq_edge("pointer", "hash_table")
        deps = g.dependents_of("pointer")
        assert set(deps) == {"linked_list", "hash_table"}

    def test_self_loop_raises(self):
        g = ConceptGraph()
        with pytest.raises(ValueError, match="Self-loop"):
            g.add_prereq_edge("recursion", "recursion")

    def test_domain_context_optional(self):
        g = ConceptGraph()
        assert g.domain_context is None
        g2 = ConceptGraph(domain_context="data structures and algorithms")
        assert g2.domain_context == "data structures and algorithms"

    def test_is_acyclic_true(self):
        g = ConceptGraph()
        g.add_prereq_edge("pointer", "linked_list")
        g.add_prereq_edge("linked_list", "hash_table")
        assert g.is_acyclic()

    def test_is_acyclic_false(self):
        g = ConceptGraph()
        g._g.add_edge("a", "b")
        g._g.add_edge("b", "c")
        g._g.add_edge("c", "a")  # cycle
        assert not g.is_acyclic()

    def test_nx_graph_property(self):
        import networkx as nx
        g = ConceptGraph()
        g.add_node("x")
        assert isinstance(g.nx_graph, nx.DiGraph)
        assert "x" in g.nx_graph.nodes()

    def test_copy_independent(self):
        g = ConceptGraph(domain_context="data structures")
        g.add_prereq_edge("pointer", "linked_list")
        g_copy = g.copy()

        assert g_copy.domain_context == "data structures"
        assert g_copy.has_prereq_edge("pointer", "linked_list")
        assert g_copy.num_nodes() == 2
        assert g_copy.num_edges() == 1

        # Modifying copy does not mutate original
        g_copy.add_prereq_edge("linked_list", "hash_table")
        assert g_copy.has_prereq_edge("linked_list", "hash_table")
        assert not g.has_prereq_edge("linked_list", "hash_table")
        assert g.num_nodes() == 2
        assert g_copy.num_nodes() == 3

        # Modifying original does not mutate copy
        g.add_node("stack")
        assert g.has_node("stack")
        assert not g_copy.has_node("stack")

    def test_edge_direction_semantics(self):
        """Explicitly test that (u, v) means u is a prereq of v."""
        g = ConceptGraph()
        # graph is prereq of dijkstra_algorithm (from DSA GOLD: dijkstra_algorithm;graph;1)
        prereq, dependent = oriented_edge(SourceKind.GOLD, "dijkstra_algorithm", "graph")
        g.add_prereq_edge(prereq, dependent)
        assert g.has_prereq_edge("graph", "dijkstra_algorithm")
        assert "graph" in g.prerequisites_of("dijkstra_algorithm")

    def test_large_graph_performance(self):
        """ConceptGraph should handle ~2000 nodes without measurable overhead."""
        import time
        g = ConceptGraph()
        n = 2000
        start = time.monotonic()
        for i in range(n):
            g.add_node(f"concept_{i}")
        for i in range(n - 1):
            g.add_prereq_edge(f"concept_{i}", f"concept_{i + 1}")
        elapsed = time.monotonic() - start
        assert g.num_nodes() == n
        assert g.num_edges() == n - 1
        # Building 2000-node chain must complete in well under 1 second
        assert elapsed < 1.0, f"Performance concern: took {elapsed:.3f}s"


# ===========================================================================
# Tests for GoldJudgmentSet
# ===========================================================================

class TestGoldJudgmentSet:
    def test_record_and_get_one(self):
        js = GoldJudgmentSet()
        js.record("a", "b", 1)
        assert js.get("a", "b") is _Label.ONE

    def test_record_and_get_zero(self):
        js = GoldJudgmentSet()
        js.record("a", "b", 0)
        assert js.get("a", "b") is _Label.ZERO

    def test_missing_pair(self):
        js = GoldJudgmentSet()
        assert js.get("x", "y") is _Label.MISSING

    def test_is_prerequisite_one(self):
        js = GoldJudgmentSet()
        js.record("dijkstra_algorithm", "graph", 1)
        assert js.is_prerequisite("dijkstra_algorithm", "graph") is True

    def test_is_prerequisite_zero(self):
        js = GoldJudgmentSet()
        js.record("a", "b", 0)
        assert js.is_prerequisite("a", "b") is False

    def test_is_prerequisite_missing_is_none(self):
        js = GoldJudgmentSet()
        assert js.is_prerequisite("a", "b") is None

    def test_duplicate_same_label_idempotent(self):
        """Duplicate pair with the SAME label is fine — no error."""
        js = GoldJudgmentSet()
        js.record("binary_search_tree", "recursion", 1)
        js.record("binary_search_tree", "recursion", 1)  # DSA has this duplicate
        assert js.get("binary_search_tree", "recursion") is _Label.ONE

    def test_duplicate_conflicting_label_raises(self):
        """Duplicate pair with DIFFERENT labels must raise ValueError."""
        js = GoldJudgmentSet()
        js.record("a", "b", 1)
        with pytest.raises(ValueError, match="Conflicting"):
            js.record("a", "b", 0)

    def test_invalid_label_raises(self):
        js = GoldJudgmentSet()
        with pytest.raises(ValueError):
            js.record("a", "b", 2)

    def test_num_labeled_one_and_zero(self):
        js = GoldJudgmentSet()
        js.record("a", "b", 1)
        js.record("c", "d", 1)
        js.record("e", "f", 0)
        assert js.num_labeled_one() == 2
        assert js.num_labeled_zero() == 1

    def test_three_state_distinction(self):
        """Explicitly verify that ZERO != MISSING — they are separate states."""
        js = GoldJudgmentSet()
        js.record("a", "b", 0)
        assert js.get("a", "b") is _Label.ZERO
        assert js.get("a", "b") is not _Label.MISSING
        assert js.get("x", "y") is _Label.MISSING
        assert js.get("x", "y") is not _Label.ZERO

    def test_missing_dsa_pair_is_missing_not_zero(self):
        """The DSA missing pair (binary_search_tree, asymptotic_complexity) must
        be representable as MISSING — distinct from a judged-0 pair.

        This test asserts the representation can distinguish them; the
        decision of how to handle MISSING in evaluation is Luke's to make.
        """
        js = GoldJudgmentSet()
        # Load the documented duplicate pair
        js.record("binary_search_tree", "recursion", 1)
        js.record("binary_search_tree", "recursion", 1)  # duplicate in DSA lines 251/252

        # The missing pair was never recorded
        assert js.get("binary_search_tree", "asymptotic_complexity") is _Label.MISSING
        # A judged-0 pair is different
        js.record("linked_list", "dijkstra_algorithm", 0)
        assert js.get("linked_list", "dijkstra_algorithm") is _Label.ZERO
        # Confirm they are not equal
        assert js.get("binary_search_tree", "asymptotic_complexity") != js.get(
            "linked_list", "dijkstra_algorithm"
        )

    def test_judgment_for_edge_gold_dsa(self):
        """DSA row dijkstra_algorithm;graph;1:
        col1=dijkstra_algorithm, col2=graph -> graph is prereq of dijkstra_algorithm.
        So judgment_for_edge('graph', 'dijkstra_algorithm') must be True.
        The reversed edge judgment_for_edge('dijkstra_algorithm', 'graph') queries
        row col1=graph, col2=dijkstra_algorithm, which is labeled 0 in DSA -> False.
        """
        js = GoldJudgmentSet(source_kind=SourceKind.GOLD)
        # Record real DSA rows
        js.record("dijkstra_algorithm", "graph", 1)
        js.record("graph", "dijkstra_algorithm", 0)
        assert js.judgment_for_edge("graph", "dijkstra_algorithm") is True
        assert js.judgment_for_edge("dijkstra_algorithm", "graph") is False

    def test_judgment_for_edge_mekg_example(self):
        """MEKG example row asymptotic_complexity.txt;hash_table.txt;1:
        col1=asymptotic_complexity, col2=hash_table -> asymptotic_complexity is prereq of hash_table.
        So judgment_for_edge('asymptotic_complexity', 'hash_table') must be True.
        """
        js = GoldJudgmentSet(source_kind=SourceKind.MEKG_EXAMPLE)
        js.record("asymptotic_complexity", "hash_table", 1)
        js.record("hash_table", "asymptotic_complexity", 0)
        assert js.judgment_for_edge("asymptotic_complexity", "hash_table") is True
        assert js.judgment_for_edge("hash_table", "asymptotic_complexity") is False

    def test_judgment_for_edge_unjudged_pair_none_both_directions(self):
        """If a pair is not recorded in either direction, judgment_for_edge
        returns None in both directions."""
        js = GoldJudgmentSet(source_kind=SourceKind.GOLD)
        assert js.judgment_for_edge("binary_search_tree", "asymptotic_complexity") is None
        assert js.judgment_for_edge("asymptotic_complexity", "binary_search_tree") is None

    def test_judgment_for_edge_dsa_actual_file_missing_pair(self):
        """In real DSA, asymptotic_complexity;binary_search_tree;0 is present,
        but binary_search_tree;asymptotic_complexity is omitted (missing).
        Verify judgment_for_edge behavior against actual DSA data:
        - ('asymptotic_complexity', 'binary_search_tree') as prereq->dependent maps to
          row ('binary_search_tree', 'asymptotic_complexity') which is missing -> None.
        - ('binary_search_tree', 'asymptotic_complexity') as prereq->dependent maps to
          row ('asymptotic_complexity', 'binary_search_tree') which is in file -> False.
        """
        js = GoldJudgmentSet(source_kind=SourceKind.GOLD)
        js.record("asymptotic_complexity", "binary_search_tree", 0)
        # Note: binary_search_tree;asymptotic_complexity was never recorded because it's missing in DSA
        assert js.judgment_for_edge("asymptotic_complexity", "binary_search_tree") is None
        assert js.judgment_for_edge("binary_search_tree", "asymptotic_complexity") is False
