"""tests/test_demo_trial.py — DEMO-001
======================================
Tests for the offline PILOT-001 replay defense demo.

Groups follow docs/prompts/DEMO-001-PROMPT.md section 8.  Replay and formatter
tests use synthetic caches/reports and never import MiniLM or faiss.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.demo_trial as demo
from graph_insertion.decision import SYSTEM_PROMPT, PairwiseDecisionStep, parse_token
from graph_insertion.embedding import FakeEmbedder
from graph_insertion.graph_representation import (
    ConceptGraph,
    GoldJudgmentSet,
    SourceKind,
)
from graph_insertion.llm import LLMResponse
from graph_insertion.scoring import NodeScore


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


TOY_NODES = ["n0", "n1", "n2", "n3", "n4", "n5"]


def make_toy_corpus() -> SimpleNamespace:
    graph = ConceptGraph(domain_context="toy domain")
    for name in TOY_NODES:
        graph.add_node(name)
    graph.add_prereq_edge("n0", "n1")
    graph.add_prereq_edge("n1", "n2")
    graph.add_prereq_edge("n0", "n2")

    judgments = GoldJudgmentSet(source_kind=SourceKind.GOLD)
    for a in TOY_NODES:
        for b in TOY_NODES:
            if a == b:
                continue
            label = 1 if graph.has_prereq_edge(b, a) else 0
            judgments.record(a, b, label)
    return SimpleNamespace(
        name="toy",
        graph=graph,
        judgments=judgments,
        domain_context="toy domain",
    )


def response_for(new_name: str, candidate: str) -> str:
    if new_name == "n2" and candidate in {"n0", "n1"}:
        return "Y_PREREQ_X"
    if new_name == "n2" and candidate == "n3":
        return "X_PREREQ_Y"
    return "NONE"


def make_records(corpus: SimpleNamespace) -> list[dict]:
    records = []
    index = 0
    step = PairwiseDecisionStep(None)  # type: ignore[arg-type]
    for new_name in sorted(corpus.graph.nodes()):
        for candidate in sorted(corpus.graph.nodes()):
            if new_name == candidate:
                continue
            index += 1
            token = response_for(new_name, candidate)
            records.append(
                {
                    "call_index": index,
                    "new_name": new_name,
                    "candidate": candidate,
                    "domain_context": corpus.domain_context,
                    "user_prompt": step.build_user_prompt(
                        new_name, candidate, corpus.domain_context
                    ),
                    "response_text": token,
                    "raw_token": token,
                    "latency_s": 1.0 + index / 1000.0,
                    "model": "deepseek-flash",
                    "input_tokens": 153,
                    "output_tokens": 5,
                    "reasoning_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 153,
                    "attempts": 1,
                    "retry_wait_s": 0.0,
                }
            )
    return records


def write_cache(
    tmp_path: Path,
    corpus: SimpleNamespace,
    records: list[dict] | None = None,
    *,
    summary_overrides: dict | None = None,
    raw_text: str | None = None,
) -> tuple[Path, str, list[dict]]:
    records = records if records is not None else make_records(corpus)
    directory = tmp_path / "pilot"
    directory.mkdir(parents=True, exist_ok=True)
    raw = raw_text if raw_text is not None else "".join(
        json.dumps(record) + "\n" for record in records
    )
    raw_path = directory / "raw_calls.jsonl"
    raw_path.write_text(raw, encoding="utf-8")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    input_tokens = sum(int(r["input_tokens"]) for r in records)
    output_tokens = sum(int(r["output_tokens"]) for r in records)
    cache_hits = sum(int(r["cache_hit_tokens"]) for r in records)
    cache_misses = sum(int(r["cache_miss_tokens"]) for r in records)
    latency = sum(float(r["latency_s"]) for r in records)
    cost = (cache_misses * 0.15 + cache_hits * 0.003 + output_tokens * 0.60) / 1e6
    summary = {
        "timestamp_utc": "2026-10-07T05:49:00+00:00",
        "prompt_version": "v2",
        "model_id": "deepseek-flash",
        "configured_model": "deepseek-flash",
        "temperature": 0.0,
        "thinking_mode": "disabled",
        "total_calls": len(records),
        "parse_failure_count": 0,
        "transport_failure_count": 0,
        "retries_and_errors": {"retries": 0},
        "token_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_hit_tokens": cache_hits,
            "cache_miss_tokens": cache_misses,
            "estimated_cost_usd": round(cost, 6),
        },
        "timing_s": {"cumulative_latency": latency},
    }
    if summary_overrides:
        for key, value in summary_overrides.items():
            if isinstance(value, dict) and isinstance(summary.get(key), dict):
                summary[key] = {**summary[key], **value}
            else:
                summary[key] = value
    (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return directory, digest, records


def load_synth(monkeypatch, directory: Path, digest: str, corpus: SimpleNamespace):
    monkeypatch.setattr(demo, "EXPECTED_CALLS", len(make_records(corpus)))
    return demo.load_pilot(directory, corpus=corpus, expected_sha256=digest)


def make_provenance(directory: Path, digest: str, n_calls: int) -> demo.PilotProvenance:
    return demo.PilotProvenance(
        path=str(directory / "raw_calls.jsonl"),
        sha256=digest,
        recorded_utc="2026-10-07T05:49:00+00:00",
        prompt_version="v2",
        model="deepseek-flash",
        n_calls=n_calls,
        temperature=0.0,
        thinking_mode="disabled",
        retries=0,
        parse_failures=0,
        transport_failures=0,
        input_tokens=153 * n_calls,
        output_tokens=5 * n_calls,
        cache_hit_tokens=0,
        cache_miss_tokens=153 * n_calls,
        estimated_cost_usd=0.0,
        cumulative_latency_s=float(n_calls),
        system_prompt_recorded=False,
    )


# ---------------------------------------------------------------------------
# Group 1 — Replay loader/client
# ---------------------------------------------------------------------------


class TestReplayLoader:
    def test_happy_path_and_values(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        directory, digest, records = write_cache(tmp_path, corpus)
        prov, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
        assert prov.n_calls == len(records) == 30
        assert prov.prompt_version == "v2"
        assert len(by_prompt) == 30
        client = demo.ReplayLLMClient(by_prompt)
        record = records[0]
        response = client.complete(SYSTEM_PROMPT, record["user_prompt"])
        assert response.text == record["response_text"]
        assert response.input_tokens == 153
        assert response.latency_s == record["latency_s"]
        assert client.served == [next(iter(by_prompt.values()))]

    def test_cache_miss_never_fabricates(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        directory, digest, _ = write_cache(tmp_path, corpus)
        _, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
        client = demo.ReplayLLMClient(by_prompt)
        with pytest.raises(demo.DemoError) as exc:
            client.complete(SYSTEM_PROMPT, "Concept X: nowhere\nConcept Y: nothing")
        assert exc.value.exit_code == 3
        assert "never fabricates" in exc.value.message

    def test_wrong_system_prompt(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        directory, digest, _ = write_cache(tmp_path, corpus)
        _, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
        client = demo.ReplayLLMClient(by_prompt)
        with pytest.raises(demo.DemoError) as exc:
            client.complete("different prompt", next(iter(by_prompt)))
        assert exc.value.exit_code == 3

    @pytest.mark.parametrize(
        "override",
        [
            {"prompt_version": "v1"},
            {"model_id": "another-model"},
            {"total_calls": 999},
            {"token_usage": {"input_tokens": 1}},
            {"timing_s": {"cumulative_latency": 0.0}},
        ],
    )
    def test_summary_mismatches(self, tmp_path, monkeypatch, override):
        corpus = make_toy_corpus()
        directory, digest, _ = write_cache(tmp_path, corpus, summary_overrides=override)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert exc.value.exit_code == 3

    def test_tampered_sha(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        directory, _, _ = write_cache(tmp_path, corpus)
        monkeypatch.setattr(demo, "EXPECTED_CALLS", 30)
        with pytest.raises(demo.DemoError) as exc:
            demo.load_pilot(directory, corpus=corpus, expected_sha256="deadbeef")
        assert exc.value.exit_code == 3

    def test_malformed_json_line(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        directory, digest, records = write_cache(tmp_path, corpus)
        raw = (directory / "raw_calls.jsonl").read_text().splitlines()
        raw[0] = "{not json"
        directory, digest, _ = write_cache(
            tmp_path / "bad", corpus, summary_overrides=None,
            raw_text="\n".join(raw) + "\n",
        )
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert exc.value.exit_code == 3

    def test_missing_field(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        del records[0]["candidate"]
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "missing field" in exc.value.message

    def test_wrong_type(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[0]["input_tokens"] = "153"
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "must be int" in exc.value.message

    def test_negative_latency(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[0]["latency_s"] = -1.0
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "negative latency" in exc.value.message

    def test_cache_tokens_mismatch(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[0]["cache_hit_tokens"] = 1
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "cache_hit + cache_miss" in exc.value.message

    def test_nonzero_reasoning_tokens(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[0]["reasoning_tokens"] = 3
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "reasoning" in exc.value.message

    def test_duplicate_prompt(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[1]["user_prompt"] = records[0]["user_prompt"]
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "duplicate user_prompt" in exc.value.message

    def test_duplicate_pair(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[1]["new_name"] = records[0]["new_name"]
        records[1]["candidate"] = records[0]["candidate"]
        records[1]["user_prompt"] = records[0]["user_prompt"]
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "duplicate" in exc.value.message

    def test_incomplete_pair_set(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[0]["new_name"] = "not_in_corpus"
        records[0]["candidate"] = "n0"
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "ordered pairs" in exc.value.message

    def test_line_count_mismatch(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)[:-1]
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "calls, expected" in exc.value.message

    def test_invalid_response_token(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        records = make_records(corpus)
        records[0]["response_text"] = "MAYBE"
        directory, digest, _ = write_cache(tmp_path, corpus, records)
        with pytest.raises(demo.DemoError) as exc:
            load_synth(monkeypatch, directory, digest, corpus)
        assert "unparseable" in exc.value.message

    def test_no_live_client_construction_or_socket(self, tmp_path, monkeypatch):
        corpus = make_toy_corpus()
        directory, digest, _ = write_cache(tmp_path, corpus)
        _, by_prompt = load_synth(monkeypatch, directory, digest, corpus)

        import graph_insertion.llm as llm_module

        def explode(*args, **kwargs):
            raise AssertionError("live client constructed")

        monkeypatch.setattr(llm_module, "FakeLLMClient", explode)
        monkeypatch.setattr(llm_module, "DeepSeekClient", explode)

        def no_socket(*args, **kwargs):
            raise AssertionError("network used")

        monkeypatch.setattr(socket, "socket", no_socket)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        client = demo.ReplayLLMClient(by_prompt)
        record = next(iter(by_prompt.values()))
        client.complete(SYSTEM_PROMPT, record.user_prompt)


# ---------------------------------------------------------------------------
# Group 2 — Cost
# ---------------------------------------------------------------------------


class TestCost:
    def test_no_cache_hits_matches_pilot_s1(self):
        assert demo.estimated_cost_usd(4291, 0, 71) == pytest.approx(0.00068625, abs=1e-12)
        assert round(demo.estimated_cost_usd(4291, 0, 71), 6) == 0.000686

    def test_cache_hits_are_cheaper(self):
        assert demo.estimated_cost_usd(1_000_000, 0, 0) == pytest.approx(0.15)
        assert demo.estimated_cost_usd(0, 1_000_000, 0) == pytest.approx(0.003)
        assert demo.estimated_cost_usd(0, 0, 1_000_000) == pytest.approx(0.60)
        assert demo.estimated_cost_usd(500_000, 500_000, 0) == pytest.approx(0.0765)


# ---------------------------------------------------------------------------
# Group 3 — Orchestration with FakeEmbedder
# ---------------------------------------------------------------------------


def run_toy_demo(monkeypatch, tmp_path, *, selected=None):
    corpus = make_toy_corpus()
    directory, digest, records = write_cache(tmp_path, corpus)
    prov, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
    replay = demo.ReplayLLMClient(by_prompt)
    report = demo.run_demo(
        node="n2",
        selected=selected,
        corpus=corpus,
        replay=replay,
        provenance=prov,
        raw_embedder=FakeEmbedder(dim=32, seed=42),
        argv=[],
    )
    return corpus, report


class TestOrchestration:
    def test_production_paths_and_invariants(self, monkeypatch, tmp_path):
        pytest.importorskip("faiss")
        corpus, report = run_toy_demo(monkeypatch, tmp_path)
        assert corpus.graph.num_nodes() == 6  # gold graph not mutated
        assert report.subset_of_s1 is True
        for strategy in report.strategies:
            score = strategy.score
            assert sum(1 for e in strategy.labelled_edges if e.label == "TP") == score.tp
            assert sum(1 for e in strategy.labelled_edges if e.label == "FP") == score.fp
            assert sum(1 for e in strategy.labelled_edges if e.label == "UNJUDGED") == (
                score.excluded_predictions
            )
            assert len(strategy.missed) == score.fn
            assert strategy.lost_narrowing + strategy.lost_decision == score.fn

    def test_canonical_edges_rebuilt_from_tokens(self, monkeypatch, tmp_path):
        corpus, report = run_toy_demo(monkeypatch, tmp_path, selected=["brute_force"])
        strategy = report.strategies[0]
        rebuilt = {
            call.edge for call in strategy.calls if call.edge is not None
        }
        assert rebuilt == {
            ("n1", "n2"), ("n0", "n2"), ("n2", "n3")
        }

    def test_broken_edge_triggers_consistency_error(self, monkeypatch, tmp_path):
        corpus = make_toy_corpus()
        directory, digest, _ = write_cache(tmp_path, corpus)
        prov, by_prompt = load_synth(monkeypatch, directory, digest, corpus)
        real_insert = demo.insert_node

        def broken_insert(*args, **kwargs):
            result = real_insert(*args, **kwargs)
            return dataclasses.replace(
                result,
                edges=tuple(edge for edge in result.edges if edge != ("n1", "n2")),
            )

        monkeypatch.setattr(demo, "insert_node", broken_insert)
        with pytest.raises(demo.DemoError) as exc:
            demo.run_demo(
                node="n2",
                selected=["brute_force"],
                corpus=corpus,
                replay=demo.ReplayLLMClient(by_prompt),
                provenance=prov,
                raw_embedder=FakeEmbedder(dim=32, seed=42),
                argv=[],
            )
        assert exc.value.exit_code == 6


# ---------------------------------------------------------------------------
# Group 4 — Formatter
# ---------------------------------------------------------------------------


def zero_score(node: str = "n2", *, f1: float = 0.0) -> NodeScore:
    return NodeScore(
        node=node,
        gold_positives=1,
        gold_neighbours=1,
        shortlist_size=1,
        shortlist_hits=0,
        shortlist_recall=0.0,
        predicted_edges=0,
        tp=0,
        fp=0,
        fn=1,
        excluded_predictions=0,
        precision=0.0,
        recall=0.0,
        f1=f1,
        fp_sensitivity=0,
        precision_sensitivity=0.0,
        recall_sensitivity=0.0,
        f1_sensitivity=0.0,
    )


def make_strategy(
    name: str = "brute_force",
    *,
    n_calls: int = 1,
    tokens: list[str] | None = None,
    score: NodeScore | None = None,
    shortlist_scores=None,
    f1: float = 0.0,
) -> demo.StrategyReport:
    tokens = tokens or ["NONE"] * n_calls
    calls = [
        demo.DemoCall(
            x="n2",
            y=f"c{i}",
            token=tokens[i],
            edge=(("n2", f"c{i}") if tokens[i] == "X_PREREQ_Y" else None),
            latency_s=1.0,
            input_tokens=153,
            output_tokens=5,
            user_prompt=f"prompt {i}",
        )
        for i in range(n_calls)
    ]
    score = score or zero_score(f1=f1)
    return demo.StrategyReport(
        name=name,
        display=demo.DISPLAY_NAMES[name],
        config=demo.DEMO_PARAMS[name],
        setup_s_live=0.001,
        setup_embedding_calls=0,
        shortlist_candidates=tuple(c.y for c in calls),
        shortlist_scores=shortlist_scores,
        shortlist_s_live=0.001,
        embed_s_live=0.0,
        update_s_live=0.0,
        replay_wall_s_live=0.001,
        calls=calls,
        recorded_latency_s=float(n_calls),
        recorded_input_tokens=153 * n_calls,
        recorded_output_tokens=5 * n_calls,
        recorded_cache_hit_tokens=0,
        recorded_cache_miss_tokens=153 * n_calls,
        cost_usd=0.001,
        calls_vs_s1_pct=50.0,
        kept_pct=50.0,
        applied_nodes_added=1,
        applied_edges_added=0,
        score=score,
        labelled_edges=[],
        missed=[],
        lost_narrowing=0,
        lost_decision=1,
        recall_given_shortlist=0.0,
        diagnostics={},
    )


def make_report(strategies: list[demo.StrategyReport], *, n_before: int = 28) -> demo.DemoReport:
    prov = demo.PilotProvenance(
        path=str(Path("results/pilot/20261007_053743Z/raw_calls.jsonl")),
        sha256="879f22b102f32e1e345086b96bc720d7558cabb89562323caf053719009e2008",
        recorded_utc="2026-10-07T05:49:00+00:00",
        prompt_version="v2",
        model="deepseek-flash",
        n_calls=812,
        temperature=0.0,
        thinking_mode="disabled",
        retries=0,
        parse_failures=0,
        transport_failures=0,
        input_tokens=123872,
        output_tokens=2035,
        cache_hit_tokens=0,
        cache_miss_tokens=123872,
        estimated_cost_usd=0.019802,
        cumulative_latency_s=676.8048,
        system_prompt_recorded=False,
    )
    return demo.DemoReport(
        started_utc="2026-10-29T00:00:00+00:00",
        wall_s_live=1.0,
        argv=[],
        provenance=prov,
        pilot_dir="results/pilot/20261007_053743Z",
        corpus_name="DSA",
        domain_context="data structures and algorithms",
        node="n2",
        full_nodes=n_before + 1,
        full_edges=54,
        n_before=n_before,
        e_before=47,
        gold_prerequisites=["n1"],
        gold_dependents=["n3"],
        gold_incident=2,
        prompt_version="v2",
        system_prompt_sha256=demo.SYSTEM_PROMPT_SHA256,
        prices=demo.PRICES if hasattr(demo, "PRICES") else {
            "cache_miss_in_per_m": 0.15,
            "cache_hit_in_per_m": 0.003,
            "output_per_m": 0.60,
        },
        strategies=strategies,
        selected=[s.name for s in strategies],
        subset_of_s1=True if any(s.name == "brute_force" for s in strategies) else None,
        embedder_identity=None,
        cpu_threads=None,
    )


def render(report: demo.DemoReport, *, ascii: bool = False, show_all: bool = False) -> list[str]:
    return demo.format_report(
        report,
        demo.FormatOptions(color=False, ascii=ascii, show_all_calls=show_all),
    )


class TestFormatter:
    def test_width_unicode_and_ascii(self):
        report = make_report([make_strategy(n_calls=11)])
        for ascii_mode in (False, True):
            lines = render(report, ascii=ascii_mode)
            assert max(len(line) for line in lines) <= demo.WIDTH

    def test_no_ansi_when_colour_off(self):
        report = make_report([make_strategy()])
        lines = render(report)
        assert not any("\x1b" in line for line in lines)

    @pytest.mark.parametrize(
        "n_calls,expected_visible,hidden_line",
        [
            (28, None, "... 21 NONE decisions not printed (use --show-all-calls)"),
            (10, 10, None),
            (11, 3, "... 8 NONE decisions not printed (use --show-all-calls)"),
            (1, 1, None),
        ],
    )
    def test_call_printing_rule(self, n_calls, expected_visible, hidden_line):
        tokens = ["NONE"] * n_calls
        if n_calls == 28:
            for index in (1, 5, 16, 21, 27):
                tokens[index] = "X_PREREQ_Y"
        report = make_report([make_strategy(n_calls=n_calls, tokens=tokens)])
        lines = render(report)
        call_lines = [line for line in lines if line.strip().startswith("call ")]
        visible = len(call_lines)
        if expected_visible is not None:
            assert visible == expected_visible
        else:
            assert visible == 7
        if hidden_line:
            assert any(hidden_line in line for line in lines)
        else:
            assert not any("decisions not printed" in line for line in lines)

    def test_show_all_calls(self):
        tokens = ["NONE"] * 28
        report = make_report([make_strategy(n_calls=28, tokens=tokens)])
        lines = render(report, show_all=True)
        call_lines = [line for line in lines if line.strip().startswith("call ")]
        assert len(call_lines) == 28
        assert not any("decisions not printed" in line for line in lines)

    def test_empty_shortlist_wording(self):
        strategy = make_strategy(n_calls=0)
        strategy.shortlist_candidates = ()
        report = make_report([strategy])
        lines = render(report)
        text = "\n".join(lines)
        assert "0 of 28 kept" in text
        assert "no LLM calls, no edges" in text

    def test_s1_has_no_similarity_table(self):
        report = make_report([make_strategy("brute_force", n_calls=3)])
        text = "\n".join(render(report))
        assert "all 3 existing concepts, alphabetical, no ranking" in text
        assert "top candidates by cosine" not in text

    def test_undefined_metrics_are_na(self):
        score = dataclasses.replace(
            zero_score(), precision=None, recall=None, f1=None, shortlist_recall=None
        )
        report = make_report([make_strategy(score=score)])
        text = "\n".join(render(report))
        assert "n/a" in text

    def test_one_tag_per_metric_line(self):
        report = make_report([make_strategy(n_calls=3)])
        lines = render(report)
        prefixes = (
            "  LLM ", "             cost ", "             calls vs S1",
            "  applied ", "             update ", "             replay wall",
            "    lost at", "    metrics", "    recall decomposition",
        )
        for line in lines:
            if line.startswith(prefixes):
                tags = line.count("[LIVE]") + line.count("[PILOT]") + line.count("[CALC]") + line.count("[GOLD]")
                assert tags == 1, line

    def test_takeaway_guards(self):
        s1 = make_strategy("brute_force", f1=0.6)
        s3 = make_strategy("ann_retrieval", f1=0.8)
        text = "\n".join(render(make_report([s1, s3])))
        assert "higher F1 than S1" in text
        s3_low = make_strategy("ann_retrieval", f1=0.2)
        text_low = "\n".join(render(make_report([s1, s3_low])))
        assert "no narrowing strategy beat brute-force F1" in text_low
        text_s1 = "\n".join(render(make_report([s1])))
        assert "no narrowing strategy beat" not in text_s1

    def test_banner_provenance_and_replay_notice(self):
        lines = render(make_report([make_strategy()]))
        text = "\n".join(lines)
        assert "results/pilot/20261007_053743Z/raw_calls.jsonl" in text
        assert "812 calls" in text
        assert "prompt v2" in text
        assert "deepseek-flash" in text
        assert demo.REPLAY_NOTICE in text.replace("\n  ", " ").replace("\n", " ") or all(
            word in text for word in ("REPLAY NOTICE", "real", "never", "recorded")
        )

    def test_no_gold_leak_before_after(self):
        report = make_report([make_strategy(n_calls=3)])
        lines = render(report)
        after_index = next(i for i, line in enumerate(lines) if "PHASE 3" in line)
        before = lines[:after_index]
        for line in before:
            if line.strip().startswith("TAGS") or line.strip().startswith("[CALC]"):
                continue
            assert "[GOLD]" not in line, line
            assert not any(marker in line for marker in (" TP ", " FP ", " FN ")), line
        assert any("[GOLD]" in line for line in lines[after_index:])


# ---------------------------------------------------------------------------
# Group 5 — CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_strategy_parsing_and_ordering(self):
        assert demo.parse_strategies("s3,s1") == ["brute_force", "ann_retrieval"]
        assert demo.parse_strategies("s4") == ["bounded_bucket"]
        assert demo.parse_strategies(None) == demo.CANONICAL_STRATEGIES

    def test_strategy_duplicates_and_unknown(self):
        with pytest.raises(demo.DemoError) as exc:
            demo.parse_strategies("s1,brute_force")
        assert exc.value.exit_code == 2
        with pytest.raises(demo.DemoError) as exc:
            demo.parse_strategies("s9")
        assert exc.value.exit_code == 2

    def test_unknown_node_exit_4(self, capsys):
        assert demo.main(["--node", "not_a_node", "--strategies", "s1", "--no-color"]) == 4
        assert "Close matches" in capsys.readouterr().err

    def test_json_existing_path_exit_7(self, tmp_path, capsys):
        target = tmp_path / "out.json"
        target.write_text("{}", encoding="utf-8")
        assert demo.main(["--json", str(target), "--strategies", "s1", "--no-color"]) == 7
        assert target.read_text(encoding="utf-8") == "{}"

    def test_json_under_results_exit_7(self):
        assert demo.main([
            "--json", str(demo.REPO_ROOT / "results" / "demo.json"),
            "--strategies", "s1", "--no-color",
        ]) == 7

    def test_json_missing_parent_exit_7(self, tmp_path):
        target = tmp_path / "missing" / "out.json"
        assert demo.main(["--json", str(target), "--strategies", "s1", "--no-color"]) == 7

    def test_check_runs_no_trial(self, monkeypatch, capsys):
        def fail(*args, **kwargs):
            raise AssertionError("trial ran during --check")

        monkeypatch.setattr(demo, "run_demo", fail)
        assert demo.main(["--check", "--strategies", "s1"]) == 0
        out = capsys.readouterr().out
        assert "OK   corpus" in out
        assert "OK   pilot cache" in out

    def test_broken_pipe_no_traceback(self):
        result = subprocess.run(
            f"{sys.executable} scripts/demo_trial.py --strategies s1 --no-color | head -1",
            shell=True,
            cwd=demo.REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert "Traceback" not in result.stderr


# ---------------------------------------------------------------------------
# Live mode (fake client; no network)
# ---------------------------------------------------------------------------


class FakeLiveClient:
    model = "deepseek-flash"
    base_url = "https://api.deepseek.com"
    temperature = 0.0
    thinking_mode = "disabled"

    def __init__(self, token_override=None):
        self.token_override = token_override

    def complete(self, system: str, user: str) -> LLMResponse:
        x = y = None
        for line in user.splitlines():
            if line.startswith("Concept X: "):
                x = line[11:].replace(" ", "_")
            elif line.startswith("Concept Y: "):
                y = line[11:].replace(" ", "_")
        token = self.token_override or response_for(x, y)
        return LLMResponse(
            text=token,
            input_tokens=150,
            output_tokens=5,
            latency_s=0.5,
            model_id="deepseek-flash",
        )

    def record_parse_failure(self, text: str) -> None:
        pass


class TestLiveMode:
    def test_live_orchestration_marks_live_and_uses_replay_free_path(self, tmp_path):
        corpus = make_toy_corpus()
        report = demo.run_demo(
            node="n2",
            selected=["brute_force"],
            corpus=corpus,
            live_client=FakeLiveClient(),
            raw_embedder=FakeEmbedder(dim=32, seed=42),
            argv=["--live"],
        )
        assert report.mode == "live"
        assert report.provenance.path == "(live DeepSeek API)"
        assert report.provenance.model == "deepseek-flash"
        assert report.provenance.n_calls == 5
        assert report.provenance.cumulative_latency_s == pytest.approx(2.5)
        lines = demo.format_report(report, demo.FormatOptions(color=False))
        text = "\n".join(lines)
        assert "LIVE RUN" in text
        assert demo.LIVE_NOTICE in text.replace("\n  ", " ").replace("\n", " ")
        assert "[PILOT]" not in text
        assert "5 calls · 2.50 s API latency [LIVE]" in text

    def test_live_unparseable_response_fails_closed(self):
        corpus = make_toy_corpus()
        with pytest.raises(demo.DemoError) as exc:
            demo.run_demo(
                node="n2",
                selected=["brute_force"],
                corpus=corpus,
                live_client=FakeLiveClient(token_override="MAYBE"),
                raw_embedder=FakeEmbedder(dim=32, seed=42),
                argv=["--live"],
            )
        assert exc.value.exit_code == 6

    def test_live_output_dir_refuses_nonempty(self, tmp_path):
        target = tmp_path / "out"
        target.mkdir()
        (target / "keep.txt").write_text("keep", encoding="utf-8")
        with pytest.raises(demo.DemoError) as exc:
            demo._validate_live_output_dir(str(target))
        assert exc.value.exit_code == 7
        assert (target / "keep.txt").read_text(encoding="utf-8") == "keep"

    def test_live_outputs_written(self, tmp_path):
        corpus = make_toy_corpus()
        report = demo.run_demo(
            node="n2",
            selected=["brute_force"],
            corpus=corpus,
            live_client=FakeLiveClient(),
            raw_embedder=FakeEmbedder(dim=32, seed=42),
            argv=["--live"],
        )
        output_dir = demo._validate_live_output_dir(str(tmp_path / "live"))
        report.output_dir = str(output_dir)
        demo._write_live_outputs(
            report, output_dir, ascii_mode=False, show_all_calls=False, argv=["--live"]
        )
        assert (output_dir / "transcript.txt").is_file()
        assert (output_dir / "demo.json").is_file()
        assert (output_dir / "run_meta.json").is_file()
        meta = json.loads((output_dir / "run_meta.json").read_text(encoding="utf-8"))
        assert meta["mode"] == "live"
        assert meta["model"] == "deepseek-flash"

    def test_live_cli_requires_confirm(self, capsys):
        assert demo.main(["--live", "--strategies", "s1"]) == 2
        assert "--confirm" in capsys.readouterr().err

    def test_live_cli_missing_key_exit_5(self, monkeypatch, capsys):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setattr(
            "graph_insertion.schedule.window_intersects_peak", lambda *args: False
        )
        assert demo.main(["--live", "--confirm", "--strategies", "s1"]) == 5
        assert "DEEPSEEK_API_KEY" in capsys.readouterr().err

    def test_check_live_missing_key_exit_5(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert demo.main(["--check", "--live", "--strategies", "s1"]) == 5

    def test_live_cli_end_to_end_with_fake_client(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(demo, "_build_live_client", lambda: FakeLiveClient())
        monkeypatch.setattr(
            "graph_insertion.schedule.window_intersects_peak", lambda *args: False
        )
        output_dir = tmp_path / "live-run"
        code = demo.main([
            "--live", "--confirm", "--strategies", "s1",
            "--output-dir", str(output_dir), "--no-color",
        ])
        assert code == 0
        assert (output_dir / "transcript.txt").is_file()
        assert (output_dir / "demo.json").is_file()
        assert (output_dir / "run_meta.json").is_file()
        transcript = (output_dir / "transcript.txt").read_text(encoding="utf-8")
        assert "LIVE RUN" in transcript
        assert "LIVE OUTPUT:" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Group 6 — MiniLM integration
# ---------------------------------------------------------------------------


def _strip_volatile(value):
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in value.items()
            if key != "run" and not key.endswith("_live")
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


class TestMiniLMIntegration:
    def test_default_run_matches_p8(self):
        pytest.importorskip("sentence_transformers")
        pytest.importorskip("faiss")
        pilot = demo.REPO_ROOT / demo.PILOT_DIR_DEFAULT / "raw_calls.jsonl"
        if not pilot.is_file():
            pytest.skip("PILOT-001 cache absent")
        try:
            report = demo.run_demo(argv=[])
        except demo.DemoError as exc:
            if exc.exit_code == 5:
                pytest.skip(f"offline MiniLM unavailable: {exc.message}")
            raise
        expected = {
            "brute_force": (28, 28, (4, 1, 3)),
            "embedding_threshold": (1, 1, (1, 0, 6)),
            "ann_retrieval": (10, 10, (4, 0, 3)),
            "bounded_bucket": (9, 9, (1, 0, 6)),
        }
        for strategy in report.strategies:
            size, calls, counts = expected[strategy.name]
            assert len(strategy.shortlist_candidates) == size
            assert len(strategy.calls) == calls
            assert (strategy.score.tp, strategy.score.fp, strategy.score.fn) == counts

    def test_two_runs_identical_nonvolatile_json(self):
        pytest.importorskip("sentence_transformers")
        pytest.importorskip("faiss")
        pilot = demo.REPO_ROOT / demo.PILOT_DIR_DEFAULT / "raw_calls.jsonl"
        if not pilot.is_file():
            pytest.skip("PILOT-001 cache absent")
        try:
            first = demo.report_to_json(demo.run_demo(argv=[]))
            second = demo.report_to_json(demo.run_demo(argv=[]))
        except demo.DemoError as exc:
            if exc.exit_code == 5:
                pytest.skip(f"offline MiniLM unavailable: {exc.message}")
            raise
        assert _strip_volatile(first) == _strip_volatile(second)


# ---------------------------------------------------------------------------
# Group 7 — Real cache provenance
# ---------------------------------------------------------------------------


class TestRealCache:
    def test_real_pilot_cache_loads(self):
        pilot_dir = demo.REPO_ROOT / demo.PILOT_DIR_DEFAULT
        if not (pilot_dir / "raw_calls.jsonl").is_file():
            pytest.skip("PILOT-001 cache absent")
        from graph_insertion.loader import load_corpus

        corpus = load_corpus("DSA_gold_standard_MEKG")
        prov, by_prompt = demo.load_pilot(pilot_dir, corpus=corpus)
        assert prov.n_calls == 812
        assert len(by_prompt) == 812
        assert prov.sha256 == demo.PILOT_RAW_CALLS_SHA256
