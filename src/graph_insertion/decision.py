"""
decision.py — INFRA-006
=======================
Shared pairwise LLM decision step for candidate insertion.

Decisions recorded here:
  - Granularity: one LLM call per (new, candidate) pair; no batching ([D-29])
  - Concurrency: 1 (strictly sequential) ([D-29])
  - Canonical edge direction: (prereq -> dependent) ([D-23])
  - Node names displayed with embed_text() and no graph structural context ([D-21])
"""

from __future__ import annotations

from typing import Optional, Sequence

from graph_insertion.graph_representation import embed_text
from graph_insertion.llm import LLMClient
from graph_insertion.strategy import DecisionOutcome, DecisionStep


# ---------------------------------------------------------------------------
# Prompt Version and Templates
# ---------------------------------------------------------------------------

PROMPT_VERSION: str = "v2"

SYSTEM_PROMPT: str = (
    "You judge prerequisite relationships between concepts in a curriculum. "
    "A concept P is a prerequisite of a concept Q if a learner needs to understand P, "
    "directly or indirectly through other concepts, before learning Q. "
    "Answer with exactly one of: X_PREREQ_Y (X is a prerequisite of Y), "
    "Y_PREREQ_X (Y is a prerequisite of X), NONE (neither). Output only that token.\n\n"
    "Examples:\n"
    "Concept X: fractions / Concept Y: ratios -> X_PREREQ_Y\n"
    "Concept X: calculus / Concept Y: limits -> Y_PREREQ_X\n"
    "Concept X: poetry / Concept Y: plumbing -> NONE"
)

VALID_TOKENS: frozenset[str] = frozenset({"X_PREREQ_Y", "Y_PREREQ_X", "NONE"})


def parse_token(text: str) -> Optional[str]:
    """Parse raw LLM response text into a valid prerequisite decision token.

    Parameters
    ----------
    text:
        Raw completion text returned by the model.

    Returns
    -------
    Optional[str]
        'X_PREREQ_Y', 'Y_PREREQ_X', 'NONE', or None if unparseable.
    """
    token = text.strip().upper()
    if token in VALID_TOKENS:
        return token
    return None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DecisionParseError(ValueError):
    """Raised when an LLM response cannot be parsed into a valid prerequisite token in strict mode."""


# ---------------------------------------------------------------------------
# Pairwise Decision Step Implementation
# ---------------------------------------------------------------------------

class PairwiseDecisionStep:
    """Pairwise prerequisite decision step implementing the DecisionStep protocol.

    Sequentially queries an LLM for each (new_name, candidate) pair,
    interpreting tokens strictly into canonical prerequisite edges.
    """

    def __init__(self, llm_client: LLMClient, *, strict: bool = False) -> None:
        self.llm_client = llm_client
        self.strict = strict

    def build_user_prompt(
        self,
        new_name: str,
        cand: str,
        domain_context: Optional[str] = None,
    ) -> str:
        """Construct the user prompt for a pair, applying embed_text() formatting."""
        x_text = embed_text(new_name)
        y_text = embed_text(cand)
        if domain_context is not None:
            return f"Subject area: {domain_context}\nConcept X: {x_text}\nConcept Y: {y_text}"
        return f"Concept X: {x_text}\nConcept Y: {y_text}"

    def decide(
        self,
        new_name: str,
        candidates: tuple[str, ...],
        domain_context: Optional[str] = None,
    ) -> DecisionOutcome:
        """Evaluate relationship between new_name and each candidate sequentially.

        Parameters
        ----------
        new_name:
            The newly inserted concept name.
        candidates:
            Tuple of existing candidate concept names to evaluate against.
        domain_context:
            Optional graph-level subject area string (e.g. 'data structures and algorithms').

        Returns
        -------
        DecisionOutcome
            Canonical edges, total llm_calls equal to candidate count, and cumulative llm_seconds.
        """
        if not candidates:
            return DecisionOutcome(edges=(), llm_calls=0, llm_seconds=0.0)

        edges: list[tuple[str, str]] = []
        total_llm_seconds = 0.0

        for cand in candidates:
            user_prompt = self.build_user_prompt(new_name, cand, domain_context)
            resp = self.llm_client.complete(system=SYSTEM_PROMPT, user=user_prompt)
            total_llm_seconds += resp.latency_s

            token = parse_token(resp.text)

            if token == "X_PREREQ_Y":
                # X (new_name) is prerequisite of Y (cand) -> canonical (prereq, dependent)
                edges.append((new_name, cand))
            elif token == "Y_PREREQ_X":
                # Y (cand) is prerequisite of X (new_name) -> canonical (prereq, dependent)
                edges.append((cand, new_name))
            elif token == "NONE":
                # Neither is a prerequisite of the other
                pass
            else:
                if self.strict:
                    raise DecisionParseError(
                        f"Unparseable response for pair ({new_name!r}, {cand!r}): {resp.text!r}"
                    )
                # Default policy 'record': treat as no edge and record parse failure on meter if available
                if hasattr(self.llm_client, "record_parse_failure"):
                    self.llm_client.record_parse_failure(resp.text)

        return DecisionOutcome(
            edges=tuple(edges),
            llm_calls=len(candidates),
            llm_seconds=total_llm_seconds,
        )

