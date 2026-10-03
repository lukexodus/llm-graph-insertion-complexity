"""
graph_representation.py — INFRA-001
====================================
In-memory graph representation for the LLM graph-insertion thesis.

Decisions recorded here:
  - Library: NetworkX DiGraph  ([D-22])
  - Node payload: concept name (str) only, no text  ([D-21])
  - Internal edge direction: (u, v) = u is a prerequisite of v  ([D-23])
  - Source-kind mapping: oriented_edge() / SourceKind  ([D-23])

See docs/reports/INFRA-001-claude-code-graph-representation.md for full
justification and measurements.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx


# ---------------------------------------------------------------------------
# Source-kind constants  ([D-23])
# ---------------------------------------------------------------------------

class SourceKind(enum.Enum):
    """Identifies which file family a parsed row came from.

    Used by :func:`oriented_edge` to apply the correct column-order mapping.

    GOLD
        DSA_gold_standard_MEKG.txt and metacademy_gold_standard_MEKG.txt.
        A label-1 row (col1, col2) means col2 is a prerequisite of col1,
        so the canonical edge is (col2 → col1).  ([D-15])

    MEKG_EXAMPLE
        The ten MEKG_with*.txt example files.
        A label-1 row (col1, col2) means col1 is a prerequisite of col2,
        so the canonical edge is (col1 → col2).  ([D-19])
    """
    GOLD = "gold"
    MEKG_EXAMPLE = "mekg_example"


def oriented_edge(source_kind: SourceKind, col1: str, col2: str) -> tuple[str, str]:
    """Return the canonical (prereq, dependent) pair for a label-1 row.

    Parameters
    ----------
    source_kind:
        :attr:`SourceKind.GOLD` or :attr:`SourceKind.MEKG_EXAMPLE`.
    col1:
        First concept name in the file row (`.txt` suffix must already be
        stripped by the caller before passing here).
    col2:
        Second concept name in the file row.

    Returns
    -------
    tuple[str, str]
        ``(prereq, dependent)`` — i.e. the prerequisite concept and the
        concept that depends on it.  This pair maps directly to a DiGraph
        edge ``(prereq, dependent)`` following the internal convention that
        an edge u→v means "u is a prerequisite of v".

    Examples
    --------
    DSA gold row ``dijkstra_algorithm;graph;1``:
    col1=dijkstra_algorithm, col2=graph → col2 is prereq → (graph, dijkstra_algorithm)

    MEKG example row ``asymptotic_complexity.txt;hash_table.txt;1`` (stripped):
    col1=asymptotic_complexity, col2=hash_table → col1 is prereq → (asymptotic_complexity, hash_table)
    """
    if source_kind is SourceKind.GOLD:
        # col2 is the prerequisite of col1  ([D-15])
        return (col2, col1)
    elif source_kind is SourceKind.MEKG_EXAMPLE:
        # col1 is the prerequisite of col2  ([D-19])
        return (col1, col2)
    else:
        raise ValueError(f"Unknown source_kind: {source_kind!r}")


# ---------------------------------------------------------------------------
# Node payload: bare concept name only  ([D-21])
# ---------------------------------------------------------------------------

def embed_text(name: str) -> str:
    """Return the single string Strategies 2–4 will embed.

    Per [D-21]: the embedding input is the bare concept name with
    underscores replaced by spaces.  The domain context string is NOT
    included here — it belongs in the shared decision-step prompt only.

    Parameters
    ----------
    name:
        Canonical concept name (no `.txt` suffix, surface form preserved
        including any apostrophes or uppercase letters, e.g.
        ``Godel's_completeness_theorem``).

    Returns
    -------
    str
        Name with underscores replaced by spaces; nothing else added.
    """
    return name.replace("_", " ")


def _validate_concept_name(name: str) -> None:
    """Enforce that concept names are non-empty and stripped of '.txt' suffixes.

    Per [D-16] and [D-21], nodes must be bare concept names.
    """
    if not isinstance(name, str) or not name:
        raise ValueError(f"Concept name cannot be empty, got {name!r}")
    if name.endswith(".txt"):
        raise ValueError(
            f"Concept name cannot end in '.txt' (D-16/D-21: nodes must be bare names), got {name!r}"
        )


# ---------------------------------------------------------------------------
# ConceptGraph — the main in-memory graph object
# ---------------------------------------------------------------------------

@dataclass
class ConceptGraph:
    """Directed prerequisite graph over concept names.

    Uses a NetworkX ``DiGraph`` as the backing store.  ([D-22])

    Edges are stored as ``(u, v)`` where u is a prerequisite of v.  ([D-23])

    Nodes are bare concept-name strings (no text payload).  ([D-21])

    Attributes
    ----------
    _g:
        The underlying NetworkX DiGraph.  Not exposed directly; use the
        public methods.
    domain_context:
        Optional free-text string describing the subject domain for the
        whole graph (e.g. ``"data structures and algorithms"``).  Used by
        the shared decision-step LLM prompt.  Not per-node.  ([D-21])
    """

    _g: nx.DiGraph = field(default_factory=nx.DiGraph, repr=False)
    domain_context: Optional[str] = None

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, name: str) -> None:
        """Add a concept node if it doesn't already exist."""
        _validate_concept_name(name)
        self._g.add_node(name)

    def has_node(self, name: str) -> bool:
        return self._g.has_node(name)

    def nodes(self):
        """Return a view of all concept names."""
        return self._g.nodes()

    def num_nodes(self) -> int:
        return self._g.number_of_nodes()

    # ------------------------------------------------------------------
    # Edge operations  (u → v means u is a prerequisite of v)
    # ------------------------------------------------------------------

    def add_prereq_edge(self, prereq: str, dependent: str) -> None:
        """Add an edge meaning *prereq* is a prerequisite of *dependent*.

        Both nodes are added automatically if not already present.
        """
        _validate_concept_name(prereq)
        _validate_concept_name(dependent)
        if prereq == dependent:
            raise ValueError(
                f"Self-loop not allowed: {prereq!r} → {dependent!r}"
            )
        self._g.add_edge(prereq, dependent)

    def has_prereq_edge(self, prereq: str, dependent: str) -> bool:
        """Return True if *prereq* → *dependent* exists."""
        return self._g.has_edge(prereq, dependent)

    def prerequisites_of(self, name: str) -> list[str]:
        """Return the direct prerequisites of *name* (its in-neighbours)."""
        return list(self._g.predecessors(name))

    def dependents_of(self, name: str) -> list[str]:
        """Return the concepts that directly depend on *name* (out-neighbours)."""
        return list(self._g.successors(name))

    def num_edges(self) -> int:
        return self._g.number_of_edges()

    def edges(self):
        """Return a view of all (prereq, dependent) edges."""
        return self._g.edges()

    # ------------------------------------------------------------------
    # Graph-level queries
    # ------------------------------------------------------------------

    def is_acyclic(self) -> bool:
        """Return True if the positive-edge graph contains no cycles."""
        return nx.is_directed_acyclic_graph(self._g)

    # ------------------------------------------------------------------
    # Access to the underlying NetworkX graph (read-only intent)
    # ------------------------------------------------------------------

    @property
    def nx_graph(self) -> nx.DiGraph:
        """Expose the raw DiGraph for algorithms not yet wrapped here.

        Callers should treat this as read-only from outside INFRA-001.
        """
        return self._g


# ---------------------------------------------------------------------------
# GoldJudgmentSet — full pairwise judgment set for accuracy evaluation
# ---------------------------------------------------------------------------

class _Label(enum.Enum):
    ZERO = 0       # judged non-prerequisite
    ONE = 1        # judged prerequisite
    MISSING = -1   # pair not present in the file at all


@dataclass
class GoldJudgmentSet:
    """Stores the complete pairwise judgment set from a gold-standard file.

    This is a superset of :class:`ConceptGraph`: it tracks label-0 pairs
    (judged non-prerequisite), label-1 pairs (judged prerequisite), and
    distinguishes both from pairs that were never judged at all.

    Rationale: DSA is missing exactly one pair
    (``binary_search_tree``, ``asymptotic_complexity``).  Whether that
    missing pair should be treated as label-0 or as "not judged" during
    evaluation is *Luke's decision*, not implemented here.
    The distinction is encoded by the enum: ``MISSING`` vs ``ZERO``.

    A duplicate pair with a *conflicting* label raises :exc:`ValueError`
    at load time.  Duplicate pairs with the *same* label are recorded
    once (idempotent).

    Attributes
    ----------
    _judgments:
        Maps (col1, col2) — in file-order, before any direction
        interpretation — to a :class:`_Label`.
    source_kind:
        Which file family this judgment set came from (affects how callers
        should interpret directed pairs for evaluation).
    """

    _judgments: dict[tuple[str, str], _Label] = field(default_factory=dict)
    source_kind: SourceKind = SourceKind.GOLD

    def record(self, col1: str, col2: str, label: int) -> None:
        """Record a (col1, col2, label) triple from the raw file.

        Parameters
        ----------
        col1, col2:
            Concept names exactly as parsed from the file (caller must
            have already stripped ``.txt`` suffixes for MEKG_EXAMPLE files).
        label:
            Must be 0 or 1.  Any other value raises :exc:`ValueError`.

        Raises
        ------
        ValueError
            If *label* is not 0 or 1.
        ValueError
            If the pair was already recorded with a *different* label
            (duplicate with conflicting label — signals a data error).
        """
        if label not in (0, 1):
            raise ValueError(f"label must be 0 or 1, got {label!r}")
        lbl = _Label(label)
        key = (col1, col2)
        existing = self._judgments.get(key)
        if existing is not None and existing is not lbl:
            raise ValueError(
                f"Conflicting labels for pair {key!r}: "
                f"already recorded as {existing.value}, now got {label}"
            )
        self._judgments[key] = lbl

    def get(self, col1: str, col2: str) -> _Label:
        """Look up the judgment for (col1, col2).

        Returns ``_Label.MISSING`` if the pair was never recorded.
        """
        return self._judgments.get((col1, col2), _Label.MISSING)

    def is_prerequisite(self, col1: str, col2: str) -> Optional[bool]:
        """Return True/False/None for judged-1 / judged-0 / not-judged.

        The caller is responsible for interpreting the column direction
        per :func:`oriented_edge` before calling this.
        """
        lbl = self.get(col1, col2)
        if lbl is _Label.MISSING:
            return None
        return lbl is _Label.ONE

    def judgment_for_edge(self, prereq: str, dependent: str) -> Optional[bool]:
        """Return True/False/None for judged-1 / judged-0 / not-judged on canonical edge.

        Takes a CANONICAL pair (prereq, dependent) where prereq is asserted to be
        a prerequisite of dependent, and looks up the judgment using the column order
        defined by this set's source_kind. Reuses :func:`oriented_edge` as the single
        source of truth for the column mapping.

        Parameters
        ----------
        prereq:
            The candidate prerequisite concept name.
        dependent:
            The candidate dependent concept name.

        Returns
        -------
        Optional[bool]
            True if judged 1 (prerequisite relationship exists),
            False if judged 0 (explicitly judged non-prerequisite),
            None if the pair was not judged in the dataset (missing).
        """
        col1, col2 = oriented_edge(self.source_kind, prereq, dependent)
        return self.is_prerequisite(col1, col2)

    def all_judged_pairs(self) -> list[tuple[str, str, int]]:
        """Return all (col1, col2, label_int) triples."""
        return [(c1, c2, lbl.value) for (c1, c2), lbl in self._judgments.items()]

    def num_labeled_one(self) -> int:
        return sum(1 for lbl in self._judgments.values() if lbl is _Label.ONE)

    def num_labeled_zero(self) -> int:
        return sum(1 for lbl in self._judgments.values() if lbl is _Label.ZERO)
