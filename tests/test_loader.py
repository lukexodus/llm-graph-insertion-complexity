"""
test_loader.py — INFRA-003 test suite
======================================
Tests for corpus loader: API, parsing, pinned stats, domain context,
error handling, and determinism.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from graph_insertion import (
    ConceptGraph,
    CorpusSpec,
    CorpusStats,
    GoldJudgmentSet,
    LoadedCorpus,
    SourceKind,
    discover_corpora,
    load_corpus,
)


# ===========================================================================
# 1. Corpus Discovery Tests
# ===========================================================================

class TestCorpusDiscovery:
    def test_discover_corpora_returns_exactly_12_specs(self, dataset_root):
        specs = discover_corpora(dataset_root)
        assert len(specs) == 12

        # Order: DSA, Metacademy, then 10 MEKG files sorted
        assert specs[0].name == "DSA_gold_standard_MEKG"
        assert specs[0].source_kind is SourceKind.GOLD
        assert specs[0].delimiter == ";"
        assert specs[0].has_txt_suffix is False
        assert specs[0].domain_context == "data structures and algorithms"

        assert specs[1].name == "metacademy_gold_standard_MEKG"
        assert specs[1].source_kind is SourceKind.GOLD
        assert specs[1].delimiter == " "
        assert specs[1].has_txt_suffix is False
        assert specs[1].domain_context == "machine learning and supporting mathematics"

        example_specs = specs[2:]
        assert len(example_specs) == 10
        # All 10 must be MEKG_EXAMPLE and have .txt suffix
        for s in example_specs:
            assert s.source_kind is SourceKind.MEKG_EXAMPLE
            assert s.delimiter == ";"
            assert s.has_txt_suffix is True
            assert s.name.startswith("MEKG_with")

        # Sorted by filename
        example_names = [s.name for s in example_specs]
        assert example_names == sorted(example_names)

    def test_discover_nonexistent_root_raises(self, tmp_path):
        bad_dir = tmp_path / "nonexistent_dir"
        with pytest.raises(FileNotFoundError, match="does not exist"):
            discover_corpora(bad_dir)

    def test_discover_missing_dsa_raises(self, tmp_path):
        d = tmp_path / "missing_dsa"
        d.mkdir()
        (d / "metacademy_gold_standard_MEKG.txt").write_text("a b 0\n")
        with pytest.raises(FileNotFoundError, match="DSA file missing"):
            discover_corpora(d)

    def test_discover_wrong_mekg_count_raises(self, tmp_path):
        d = tmp_path / "wrong_count"
        d.mkdir()
        (d / "DSA_gold_standard_MEKG.txt").write_text("a;b;0\n")
        (d / "metacademy_gold_standard_MEKG.txt").write_text("a b 0\n")
        # create only 2 example files instead of 10
        (d / "MEKG_with_6_nodes(DS).txt").write_text("a.txt;b.txt;0\n")
        (d / "MEKG_with_8_nodes(DS3).txt").write_text("a.txt;b.txt;0\n")

        with pytest.raises(FileNotFoundError, match="Expected exactly 10 MEKG example files"):
            discover_corpora(d)


# ===========================================================================
# 2. Pinned Expectations Tests (Gold Corpora)
# ===========================================================================

class TestPinnedGoldExpectations:
    def test_dsa_pinned_stats_and_semantics(self, dataset_root):
        """DSA: 29 nodes, 841 lines, 840 distinct pairs, 1 duplicate row, 54 positive edges."""
        loaded = load_corpus("DSA_gold_standard_MEKG", root=dataset_root)

        assert isinstance(loaded, LoadedCorpus)
        assert loaded.name == "DSA_gold_standard_MEKG"
        assert loaded.source_kind is SourceKind.GOLD
        assert loaded.domain_context == "data structures and algorithms"

        s = loaded.stats
        assert s.line_count == 841
        assert s.distinct_nodes == 29
        assert s.distinct_pairs == 840
        assert s.duplicate_rows == 1
        assert s.self_loop_rows == 29
        assert s.positive_row_count == 55
        assert s.positive_edge_count == 54

        # Graph verification
        assert loaded.graph.num_nodes() == 29
        assert loaded.graph.num_edges() == 54
        assert loaded.graph.is_acyclic() is True

        # Gold judgment set counts
        assert loaded.judgments.num_labeled_one() == 54
        assert loaded.judgments.num_labeled_zero() == 840 - 54

        # The missing ordered row is binary_search_tree;asymptotic_complexity
        # col2=asymptotic_complexity is asserted prereq of col1=binary_search_tree
        assert (
            loaded.judgments.judgment_for_edge("asymptotic_complexity", "binary_search_tree")
            is None
        )
        # Reverse row exists in file (labeled 0)
        assert (
            loaded.judgments.judgment_for_edge("binary_search_tree", "asymptotic_complexity")
            is False
        )

    def test_metacademy_pinned_stats_and_semantics(self, dataset_root):
        """Metacademy: 141 nodes, 19,740 lines, 318 positive edges, 0 self loops."""
        loaded = load_corpus("metacademy_gold_standard_MEKG", root=dataset_root)

        assert loaded.name == "metacademy_gold_standard_MEKG"
        assert loaded.source_kind is SourceKind.GOLD
        assert loaded.domain_context == "machine learning and supporting mathematics"

        s = loaded.stats
        assert s.line_count == 19740
        assert s.distinct_nodes == 141
        assert s.distinct_pairs == 19740
        assert s.duplicate_rows == 0
        assert s.self_loop_rows == 0
        assert s.positive_row_count == 318
        assert s.positive_edge_count == 318

        # Graph verification
        assert loaded.graph.num_nodes() == 141
        assert loaded.graph.num_edges() == 318
        assert loaded.graph.is_acyclic() is True

        # Gold judgment set counts
        assert loaded.judgments.num_labeled_one() == 318
        assert loaded.judgments.num_labeled_zero() == 19740 - 318


# ===========================================================================
# 3. Pinned Expectations Tests (Example MEKG Corpora)
# ===========================================================================

class TestPinnedExampleExpectations:
    # (stem, expected_nodes, expected_pos_edges, expected_domain)
    EXPECTED_EXAMPLES = [
        ("MEKG_with7nodes", 7, 16, None),
        ("MEKG_with_6_nodes(DS)", 6, 7, "data structures and algorithms"),
        ("MEKG_with_8_nodes(DS3)", 8, 18, "data structures and algorithms"),
        ("MEKG_with_8_nodes(DS4)", 8, 23, "data structures and algorithms"),
        ("MEKG_with_8_nodes(logic)", 8, 15, "mathematical logic"),
        ("MEKG_with_10_nodes(DS1)", 10, 29, "data structures and algorithms"),
        ("MEKG_with_10_nodes(DS2)", 10, 19, "data structures and algorithms"),
        ("MEKG_with_18_nodes(ML)", 18, 76, "machine learning"),
        ("MEKG_with_21_nodes(ML)", 21, 138, "machine learning"),
        ("MEKG_with_35_nodes(ML1)", 35, 244, "machine learning"),
    ]

    @pytest.mark.parametrize(
        "stem, n_nodes, n_pos_edges, domain",
        EXPECTED_EXAMPLES,
    )
    def test_mekg_example_corpus(self, dataset_root, stem, n_nodes, n_pos_edges, domain):
        loaded = load_corpus(stem, root=dataset_root)

        assert loaded.name == stem
        assert loaded.source_kind is SourceKind.MEKG_EXAMPLE
        assert loaded.domain_context == domain

        s = loaded.stats
        assert s.line_count == n_nodes * n_nodes
        assert s.distinct_nodes == n_nodes
        assert s.distinct_pairs == n_nodes * n_nodes
        assert s.duplicate_rows == 0
        assert s.self_loop_rows == n_nodes
        assert s.positive_row_count == n_pos_edges
        assert s.positive_edge_count == n_pos_edges

        # Graph verification
        assert loaded.graph.num_nodes() == n_nodes
        assert loaded.graph.num_edges() == n_pos_edges
        assert loaded.graph.is_acyclic() is True

        # Node names must not have .txt suffix
        for node in loaded.graph.nodes():
            assert not node.endswith(".txt")


# ===========================================================================
# 4. Determinism & API Flexibility Tests
# ===========================================================================

class TestLoaderDeterminismAndAPI:
    def test_loading_is_deterministic(self, dataset_root):
        corpus1 = load_corpus("DSA_gold_standard_MEKG", root=dataset_root)
        corpus2 = load_corpus("DSA_gold_standard_MEKG", root=dataset_root)

        assert list(corpus1.graph.nodes()) == list(corpus2.graph.nodes())
        assert set(corpus1.graph.edges()) == set(corpus2.graph.edges())
        assert corpus1.stats == corpus2.stats

    def test_load_by_convenience_alias(self, dataset_root):
        dsa = load_corpus("dsa", root=dataset_root)
        assert dsa.name == "DSA_gold_standard_MEKG"

        meta = load_corpus("metacademy", root=dataset_root)
        assert meta.name == "metacademy_gold_standard_MEKG"

    def test_load_by_path(self, dataset_root):
        dsa_path = dataset_root / "DSA_gold_standard_MEKG.txt"
        loaded = load_corpus(dsa_path)
        assert loaded.stats.distinct_nodes == 29

    def test_load_by_spec(self, dataset_root):
        specs = discover_corpora(dataset_root)
        loaded = load_corpus(specs[0])
        assert loaded.name == specs[0].name


# ===========================================================================
# 5. Strict Parsing & Error Handling Tests
# ===========================================================================

class TestLoaderErrorHandling:
    def test_malformed_line_too_few_fields_raises(self, tmp_path):
        f = tmp_path / "bad_fields.txt"
        f.write_text("node1;node2\n")
        spec = CorpusSpec(
            name="bad", path=f, source_kind=SourceKind.GOLD, delimiter=";"
        )
        with pytest.raises(ValueError, match="line 1.*expected 3 fields"):
            load_corpus(spec)

    def test_malformed_line_too_many_fields_raises(self, tmp_path):
        f = tmp_path / "extra_fields.txt"
        f.write_text("a;b;1\nc;d;1;extra\n")
        spec = CorpusSpec(
            name="bad", path=f, source_kind=SourceKind.GOLD, delimiter=";"
        )
        with pytest.raises(ValueError, match="line 2.*expected 3 fields"):
            load_corpus(spec)

    def test_invalid_label_raises(self, tmp_path):
        f = tmp_path / "bad_label.txt"
        f.write_text("a;b;2\n")
        spec = CorpusSpec(
            name="bad", path=f, source_kind=SourceKind.GOLD, delimiter=";"
        )
        with pytest.raises(ValueError, match="line 1.*label must be '0' or '1'"):
            load_corpus(spec)

    def test_example_missing_txt_suffix_raises(self, tmp_path):
        f = tmp_path / "MEKG_with_6_nodes(DS).txt"
        f.write_text("a.txt;b;0\n")
        spec = CorpusSpec(
            name="bad_example",
            path=f,
            source_kind=SourceKind.MEKG_EXAMPLE,
            has_txt_suffix=True,
            delimiter=";",
        )
        with pytest.raises(ValueError, match="line 1.*missing '.txt' suffix"):
            load_corpus(spec)

    def test_positive_self_loop_raises(self, tmp_path):
        f = tmp_path / "self_loop.txt"
        f.write_text("a;b;0\nc;c;1\n")
        spec = CorpusSpec(
            name="self_loop", path=f, source_kind=SourceKind.GOLD, delimiter=";"
        )
        with pytest.raises(ValueError, match="line 2.*positive self-loop"):
            load_corpus(spec)

    def test_conflicting_duplicate_raises(self, tmp_path):
        f = tmp_path / "conflicting.txt"
        f.write_text("a;b;0\na;b;1\n")
        spec = CorpusSpec(
            name="conflict", path=f, source_kind=SourceKind.GOLD, delimiter=";"
        )
        with pytest.raises(ValueError, match="line 2.*conflicting label"):
            load_corpus(spec)
