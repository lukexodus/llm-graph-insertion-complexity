"""tests/test_harness_embedding.py — FIX-008
==========================================
End-to-end tests exercising an embedding-aware strategy through the full
experiment harness (run_sweep_experiment and run_accuracy_experiment).

Verifies:
  - embedding_calls == 1 per insertion
  - embedding_calls_in_update == 0 (cached embedding reuse in on_inserted)
  - embed_s > 0 (embedding wall-clock timing tracked)
  - No MeteredEmbedder identity ValueError
  - embed_s and embedding_calls appear in raw.jsonl and summary.csv
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from graph_insertion.embedding import FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    run_accuracy_experiment,
    run_sweep_experiment,
)
from graph_insertion.loader import (
    CorpusStats,
    GoldJudgmentSet,
    LoadedCorpus,
    SourceKind,
)
from graph_insertion.strategy import DecisionOutcome, DecisionStep
from tests.test_strategy_interface import FakeDecisionStep, TinyFakeStrategy


def _make_mini_corpus() -> LoadedCorpus:
    g = ConceptGraph(domain_context="computer science")
    for name in ("concept_alpha", "concept_beta", "concept_gamma"):
        g.add_node(name)
    g.add_prereq_edge("concept_alpha", "concept_beta")
    return LoadedCorpus(
        name="mini_corpus",
        source_kind=SourceKind.GOLD,
        graph=g,
        domain_context="computer science",
        judgments=GoldJudgmentSet(),
        stats=CorpusStats(
            line_count=3,
            distinct_nodes=3,
            distinct_pairs=1,
            duplicate_rows=0,
            self_loop_rows=0,
            positive_row_count=1,
            positive_edge_count=1,
        ),
    )


class TestEmbeddingThroughHarness:
    """Exercise TinyFakeStrategy through both sweep and accuracy harness runners."""

    def test_embedding_strategy_through_sweep_harness(self, tmp_path: Path) -> None:
        """Sweep mode: size 5, 1 trial. Verify embedding metrics in raw.jsonl and summary.csv."""
        out_dir = tmp_path / "sweep_embedding"
        name_source = SyntheticNameSource(
            names=[f"synth_{i:04d}" for i in range(50)],
            domain_context="computer science",
        )
        config = HarnessConfig(
            mode="sweep",
            run_id="test_sweep_embed",
            output_dir=out_dir,
            seed=42,
            sweep_sizes=(5,),
            sweep_trials_per_size=1,
            confirm=True,
        )

        res = run_sweep_experiment(
            config=config,
            strategy_factory=lambda: TinyFakeStrategy(top_k=2, seed=42),
            decision_step=FakeDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=16, seed=42),
            name_source=name_source,
        )
        assert res["status"] == "completed"

        # Verify raw.jsonl metrics
        raw_path = out_dir / "raw.jsonl"
        assert raw_path.exists()
        records = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
        assert len(records) == 1

        rec = records[0]
        assert rec["status"] == "success"
        m = rec["metrics"]
        assert m["embedding_calls"] == 1, f"Expected 1 embedding call per insertion, got {m['embedding_calls']}"
        assert m["embedding_calls_in_update"] == 0, (
            f"Expected 0 embedding calls in update (cache reuse), got {m['embedding_calls_in_update']}"
        )
        assert m["embed_s"] > 0, f"Expected embed_s > 0, got {m['embed_s']}"

        # Verify summary.csv contains embed_s and embedding_calls
        csv_path = out_dir / "summary.csv"
        assert csv_path.exists()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 1
        row = reader[0]

        # embed_s appears in summary.csv
        assert "embed_s_mean" in row, f"embed_s_mean missing from summary.csv headers: {list(row.keys())}"
        assert float(row["embed_s_mean"]) > 0.0

        # embedding_calls appears in summary.csv
        assert "embedding_calls_mean" in row, f"embedding_calls_mean missing from summary.csv headers: {list(row.keys())}"
        assert float(row["embedding_calls_mean"]) == 1.0
        assert int(row["embedding_calls_sum"]) == 1

    def test_embedding_strategy_through_accuracy_harness(self, tmp_path: Path) -> None:
        """Accuracy mode: mini corpus (3 held-out trials). Verify embedding metrics."""
        out_dir = tmp_path / "accuracy_embedding"
        mini_corpus = _make_mini_corpus()
        config = HarnessConfig(
            mode="accuracy",
            run_id="test_accuracy_embed",
            output_dir=out_dir,
            seed=42,
            confirm=True,
        )

        res = run_accuracy_experiment(
            config=config,
            strategy_factory=lambda: TinyFakeStrategy(top_k=2, seed=42),
            decision_step=FakeDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=16, seed=42),
            corpora={"mini_corpus": mini_corpus},
        )
        assert res["status"] == "completed"

        # Verify raw.jsonl metrics across all 3 held-out trials
        raw_path = out_dir / "raw.jsonl"
        assert raw_path.exists()
        records = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
        assert len(records) == 3

        for rec in records:
            assert rec["status"] == "success"
            m = rec["metrics"]
            assert m["embedding_calls"] == 1, f"Expected 1 embedding call, got {m['embedding_calls']}"
            assert m["embedding_calls_in_update"] == 0, f"Expected 0 calls in update, got {m['embedding_calls_in_update']}"
            assert m["embed_s"] > 0, f"Expected embed_s > 0, got {m['embed_s']}"

        # Verify summary.csv contains embed_s and embedding_calls
        csv_path = out_dir / "summary.csv"
        assert csv_path.exists()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 1
        row = reader[0]

        assert "embed_s_mean" in row
        assert float(row["embed_s_mean"]) > 0.0
        assert "embedding_calls_mean" in row
        assert float(row["embedding_calls_mean"]) == 1.0
        assert int(row["embedding_calls_sum"]) == 3
