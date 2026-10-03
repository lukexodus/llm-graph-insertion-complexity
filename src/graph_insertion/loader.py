"""
loader.py — INFRA-003
======================
Corpus loader for the LLM graph-insertion complexity experiments.

Normalizes DSA, Metacademy, and the ten example MEKG files into
ConceptGraph plus GoldJudgmentSet, applying D-15, D-16, D-19, D-21, D-23,
and D-27.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional, Union

from graph_insertion.graph_representation import (
    ConceptGraph,
    GoldJudgmentSet,
    SourceKind,
    oriented_edge,
)

# Default location for the EKG-Dataset within the repository
DEFAULT_DATASET_ROOT = (
    Path(__file__).resolve().parents[2] / "repositories" / "dataset" / "EKG-Dataset"
)

# Domain context mapping table per [D-21] and [D-27]
CORPUS_DOMAIN_CONTEXT_MAP: dict[str, Optional[str]] = {
    "DSA_gold_standard_MEKG": "data structures and algorithms",
    "metacademy_gold_standard_MEKG": "machine learning and supporting mathematics",
    "MEKG_with_6_nodes(DS)": "data structures and algorithms",
    "MEKG_with_8_nodes(DS3)": "data structures and algorithms",
    "MEKG_with_8_nodes(DS4)": "data structures and algorithms",
    "MEKG_with_10_nodes(DS1)": "data structures and algorithms",
    "MEKG_with_10_nodes(DS2)": "data structures and algorithms",
    "MEKG_with_18_nodes(ML)": "machine learning",
    "MEKG_with_21_nodes(ML)": "machine learning",
    "MEKG_with_35_nodes(ML1)": "machine learning",
    "MEKG_with_8_nodes(logic)": "mathematical logic",
    "MEKG_with7nodes": None,
}

TAG_DOMAIN_CONTEXT_MAP: dict[str, str] = {
    "DS": "data structures and algorithms",
    "ML": "machine learning",
    "logic": "mathematical logic",
}


def derive_domain_context(filename_or_stem: str) -> Optional[str]:
    """Derive the domain context from filename tag or lookup table.

    Tags:
      - DS, DS1..DS4 -> "data structures and algorithms"
      - ML, ML1 -> "machine learning"
      - logic -> "mathematical logic"
    Files without a tag (e.g. MEKG_with7nodes) return None per [D-27].
    """
    stem = Path(filename_or_stem).stem
    if stem in CORPUS_DOMAIN_CONTEXT_MAP:
        return CORPUS_DOMAIN_CONTEXT_MAP[stem]

    m = re.search(r"\(([^)]+)\)", stem)
    if m:
        tag = m.group(1)
        if tag.startswith("DS"):
            return TAG_DOMAIN_CONTEXT_MAP["DS"]
        if tag.startswith("ML"):
            return TAG_DOMAIN_CONTEXT_MAP["ML"]
        if tag == "logic":
            return TAG_DOMAIN_CONTEXT_MAP["logic"]
    return None


@dataclass(frozen=True)
class CorpusSpec:
    """Specification of a corpus to load.

    Attributes
    ----------
    name:
        Unique name of the corpus (filename stem, e.g. "DSA_gold_standard_MEKG").
    path:
        Path to the text file on disk.
    source_kind:
        SourceKind.GOLD or SourceKind.MEKG_EXAMPLE (controls orientation).
    domain_context:
        Graph-level domain context string ([D-21]), or None.
    delimiter:
        Delimiter string (";" for DSA and MEKG examples, " " for Metacademy).
    has_txt_suffix:
        Whether concept names carry a ".txt" suffix that must be stripped.
    """

    name: str
    path: Path
    source_kind: SourceKind
    domain_context: Optional[str] = None
    delimiter: str = ";"
    has_txt_suffix: bool = False


@dataclass(frozen=True)
class CorpusStats:
    """Statistics collected during corpus loading."""

    line_count: int
    distinct_nodes: int
    distinct_pairs: int
    duplicate_rows: int
    self_loop_rows: int
    positive_row_count: int
    positive_edge_count: int


@dataclass
class LoadedCorpus:
    """Result of loading a corpus.

    Attributes
    ----------
    name:
        Corpus identifier.
    source_kind:
        SourceKind.GOLD or SourceKind.MEKG_EXAMPLE.
    graph:
        ConceptGraph containing all nodes and positive edges.
    judgments:
        GoldJudgmentSet containing all parsed pairs (0, 1, and self-loops).
    domain_context:
        Graph-level domain context string ([D-21]), or None.
    stats:
        Detailed counts and structural statistics.
    """

    name: str
    source_kind: SourceKind
    graph: ConceptGraph
    judgments: GoldJudgmentSet
    domain_context: Optional[str]
    stats: CorpusStats


def discover_corpora(root: Optional[Union[Path, str]] = None) -> list[CorpusSpec]:
    """Discover all 12 corpora in the dataset directory.

    Returns exactly 12 CorpusSpec entries in order:
    1. DSA (SourceKind.GOLD)
    2. Metacademy (SourceKind.GOLD)
    3-12. The ten MEKG_with*.txt files sorted by filename (SourceKind.MEKG_EXAMPLE).

    Raises
    ------
    FileNotFoundError:
        If dataset directory does not exist, or required files are missing,
        or glob('MEKG_with*.txt') does not find exactly 10 files.
    """
    dataset_dir = Path(root) if root is not None else DEFAULT_DATASET_ROOT
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"Dataset root directory does not exist: {dataset_dir}")

    dsa_path = dataset_dir / "DSA_gold_standard_MEKG.txt"
    if not dsa_path.is_file():
        raise FileNotFoundError(f"Required DSA file missing: {dsa_path}")

    meta_path = dataset_dir / "metacademy_gold_standard_MEKG.txt"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Required Metacademy file missing: {meta_path}")

    example_files = sorted(dataset_dir.glob("MEKG_with*.txt"))
    if len(example_files) != 10:
        raise FileNotFoundError(
            f"Expected exactly 10 MEKG example files matching 'MEKG_with*.txt' in {dataset_dir}, "
            f"found {len(example_files)}"
        )

    specs: list[CorpusSpec] = []

    # 1. DSA
    specs.append(
        CorpusSpec(
            name=dsa_path.stem,
            path=dsa_path,
            source_kind=SourceKind.GOLD,
            domain_context=CORPUS_DOMAIN_CONTEXT_MAP.get(
                dsa_path.stem, "data structures and algorithms"
            ),
            delimiter=";",
            has_txt_suffix=False,
        )
    )

    # 2. Metacademy
    specs.append(
        CorpusSpec(
            name=meta_path.stem,
            path=meta_path,
            source_kind=SourceKind.GOLD,
            domain_context=CORPUS_DOMAIN_CONTEXT_MAP.get(
                meta_path.stem, "machine learning and supporting mathematics"
            ),
            delimiter=" ",
            has_txt_suffix=False,
        )
    )

    # 3-12. Example MEKG files
    for p in example_files:
        domain = derive_domain_context(p.stem)
        specs.append(
            CorpusSpec(
                name=p.stem,
                path=p,
                source_kind=SourceKind.MEKG_EXAMPLE,
                domain_context=domain,
                delimiter=";",
                has_txt_suffix=True,
            )
        )

    return specs


def _spec_from_path(path: Path) -> CorpusSpec:
    stem = path.stem
    if "gold_standard" in stem:
        source_kind = SourceKind.GOLD
        delimiter = " " if "metacademy" in stem.lower() else ";"
        has_txt = False
    elif stem.startswith("MEKG_with"):
        source_kind = SourceKind.MEKG_EXAMPLE
        delimiter = ";"
        has_txt = True
    else:
        source_kind = SourceKind.GOLD
        delimiter = ";"
        has_txt = False

    domain = derive_domain_context(stem)
    return CorpusSpec(
        name=stem,
        path=path,
        source_kind=source_kind,
        domain_context=domain,
        delimiter=delimiter,
        has_txt_suffix=has_txt,
    )


def load_corpus(
    target: Union[CorpusSpec, Path, str],
    root: Optional[Union[Path, str]] = None,
) -> LoadedCorpus:
    """Load a corpus into ConceptGraph and GoldJudgmentSet.

    Parameters
    ----------
    target:
        A CorpusSpec, or a Path to a file, or a corpus name string
        (e.g., "DSA", "metacademy", "MEKG_with_6_nodes(DS)").
    root:
        Optional dataset root directory override if target is a string name.

    Returns
    -------
    LoadedCorpus
        The parsed and validated corpus.
    """
    if isinstance(target, str):
        target_path = Path(target)
        if target_path.is_file():
            spec = _spec_from_path(target_path)
        else:
            specs = discover_corpora(root)
            matching = [
                s
                for s in specs
                if s.name == target or s.name.lower() == target.lower()
            ]
            if not matching:
                matching = [s for s in specs if target.lower() in s.name.lower()]
            if not matching:
                raise ValueError(
                    f"Corpus {target!r} not found among discovered corpora"
                )
            if len(matching) > 1:
                exact = [s for s in matching if s.name.lower() == target.lower()]
                if len(exact) == 1:
                    spec = exact[0]
                else:
                    raise ValueError(
                        f"Ambiguous corpus name {target!r}, matches: {[s.name for s in matching]}"
                    )
            else:
                spec = matching[0]
    elif isinstance(target, Path):
        spec = _spec_from_path(target)
    elif isinstance(target, CorpusSpec):
        spec = target
    else:
        raise TypeError(
            f"Expected CorpusSpec, Path, or str, got {type(target).__name__}"
        )

    return _parse_corpus_file(spec)


def _parse_corpus_file(spec: CorpusSpec) -> LoadedCorpus:
    """Internal parsing function for a CorpusSpec."""
    if not spec.path.is_file():
        raise FileNotFoundError(f"Corpus file not found: {spec.path}")

    graph = ConceptGraph(domain_context=spec.domain_context)
    judgments = GoldJudgmentSet(source_kind=spec.source_kind)

    line_count = 0
    distinct_pairs: set[tuple[str, str]] = set()
    duplicate_rows = 0
    self_loop_rows = 0
    positive_row_count = 0
    seen_nodes: set[str] = set()

    with spec.path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue

            line_count += 1
            parts = stripped.split(spec.delimiter)
            if len(parts) != 3:
                raise ValueError(
                    f"Parse error in {spec.path.name} at line {line_no}: "
                    f"expected 3 fields delimited by {spec.delimiter!r}, "
                    f"got {len(parts)} fields: {line.strip()!r}"
                )

            col1_raw, col2_raw, label_str = parts
            if label_str not in ("0", "1"):
                raise ValueError(
                    f"Parse error in {spec.path.name} at line {line_no}: "
                    f"label must be '0' or '1', got {label_str!r}"
                )
            label = int(label_str)

            if spec.has_txt_suffix:
                if not col1_raw.endswith(".txt") or not col2_raw.endswith(".txt"):
                    raise ValueError(
                        f"Parse error in {spec.path.name} at line {line_no}: "
                        f"concept name missing '.txt' suffix: {col1_raw!r}, {col2_raw!r}"
                    )
                c1 = col1_raw.removesuffix(".txt")
                c2 = col2_raw.removesuffix(".txt")
            else:
                c1 = col1_raw
                c2 = col2_raw

            # Add nodes in order of first appearance
            for c in (c1, c2):
                if c not in seen_nodes:
                    seen_nodes.add(c)
                    graph.add_node(c)

            # Self-loop check
            if c1 == c2:
                self_loop_rows += 1
                if label == 1:
                    raise ValueError(
                        f"Data error in {spec.path.name} at line {line_no}: "
                        f"positive self-loop ({c1} -> {c2} with label 1) is not allowed"
                    )

            # Record in judgment set & track duplicate rows
            pair = (c1, c2)
            if pair in distinct_pairs:
                duplicate_rows += 1
            else:
                distinct_pairs.add(pair)

            try:
                judgments.record(c1, c2, label)
            except ValueError as e:
                raise ValueError(
                    f"Data error in {spec.path.name} at line {line_no}: "
                    f"conflicting label for pair ({c1}, {c2}): {e}"
                ) from e

            # Positive edge application
            if label == 1:
                positive_row_count += 1
                prereq, dependent = oriented_edge(spec.source_kind, c1, c2)
                graph.add_prereq_edge(prereq, dependent)

    stats = CorpusStats(
        line_count=line_count,
        distinct_nodes=len(seen_nodes),
        distinct_pairs=len(distinct_pairs),
        duplicate_rows=duplicate_rows,
        self_loop_rows=self_loop_rows,
        positive_row_count=positive_row_count,
        positive_edge_count=graph.num_edges(),
    )

    return LoadedCorpus(
        name=spec.name,
        source_kind=spec.source_kind,
        graph=graph,
        judgments=judgments,
        domain_context=spec.domain_context,
        stats=stats,
    )
