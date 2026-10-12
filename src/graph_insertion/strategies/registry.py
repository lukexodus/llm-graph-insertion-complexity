"""strategies/registry.py — INFRA-007
====================================
Single source of truth for strategy names, factory functions, parameter
applicability rules, and deterministic run-directory slug derivation.

Every narrowing strategy available to the experiment CLI is registered here.
Factory signature: ``factory(seed=42, k=None, **params) -> NarrowingStrategy``
with ``params`` keys ``theta``, ``ef_search``, ``s_min``, ``s_max``, ``n_bits``
all defaulting to ``None``. Legacy two-argument calls ``factory(seed, k)``
continue to work unchanged.

Lazy imports are used for ``ann_retrieval`` so this module loads without faiss.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from graph_insertion.strategy import NarrowingStrategy

from graph_insertion.strategies.stub import StubNarrowingStrategy


def _factory_null(
    seed: int = 42,
    k: Optional[int] = None,
    *,
    theta: Optional[float] = None,
    ef_search: Optional[int] = None,
    s_min: Optional[int] = None,
    s_max: Optional[int] = None,
    n_bits: Optional[int] = None,
    **params: Any,
) -> NarrowingStrategy:
    from graph_insertion.strategies.null import NullStrategy

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
    actual_k = 1 if k is None else k
    if isinstance(actual_k, bool) or not isinstance(actual_k, int) or actual_k < 1:
        raise ValueError(f"k must be >= 1, got {actual_k}")
    return NullStrategy(seed=seed, k=actual_k)


def _factory_stub(
    seed: int = 42,
    k: Optional[int] = None,
    *,
    theta: Optional[float] = None,
    ef_search: Optional[int] = None,
    s_min: Optional[int] = None,
    s_max: Optional[int] = None,
    n_bits: Optional[int] = None,
    **params: Any,
) -> NarrowingStrategy:
    actual_k = 5 if k is None else k
    if isinstance(actual_k, bool) or not isinstance(actual_k, int) or actual_k < 1:
        raise ValueError(f"k must be >= 1, got {actual_k}")
    return StubNarrowingStrategy(top_k=actual_k)


def _factory_brute_force(
    seed: int = 42,
    k: Optional[int] = None,
    *,
    theta: Optional[float] = None,
    ef_search: Optional[int] = None,
    s_min: Optional[int] = None,
    s_max: Optional[int] = None,
    n_bits: Optional[int] = None,
    **params: Any,
) -> NarrowingStrategy:
    from graph_insertion.strategies.brute_force import BruteForceStrategy

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
    return BruteForceStrategy(seed=seed)


def _factory_embedding_threshold(
    seed: int = 42,
    k: Optional[int] = None,
    *,
    theta: Optional[float] = None,
    ef_search: Optional[int] = None,
    s_min: Optional[int] = None,
    s_max: Optional[int] = None,
    n_bits: Optional[int] = None,
    **params: Any,
) -> NarrowingStrategy:
    from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
    kwargs: dict[str, Any] = {"seed": seed}
    if theta is not None:
        kwargs["theta"] = theta
    return EmbeddingThresholdStrategy(**kwargs)


def _factory_ann_retrieval(
    seed: int = 42,
    k: Optional[int] = None,
    *,
    theta: Optional[float] = None,
    ef_search: Optional[int] = None,
    s_min: Optional[int] = None,
    s_max: Optional[int] = None,
    n_bits: Optional[int] = None,
    **params: Any,
) -> NarrowingStrategy:
    # Lazy import so registry and strategies package load without faiss installed
    from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy

    kwargs: dict[str, Any] = {"seed": seed}
    if k is not None:
        kwargs["k"] = k
    if ef_search is not None:
        kwargs["ef_search"] = ef_search
    return AnnRetrievalStrategy(**kwargs)


def _factory_bounded_bucket(
    seed: int = 42,
    k: Optional[int] = None,
    *,
    theta: Optional[float] = None,
    ef_search: Optional[int] = None,
    s_min: Optional[int] = None,
    s_max: Optional[int] = None,
    n_bits: Optional[int] = None,
    **params: Any,
) -> NarrowingStrategy:
    from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy

    kwargs: dict[str, Any] = {"seed": seed}
    if s_min is not None:
        kwargs["s_min"] = s_min
    if s_max is not None:
        kwargs["s_max"] = s_max
    if n_bits is not None:
        kwargs["n_bits"] = n_bits
    return BoundedBucketStrategy(**kwargs)


# ---------------------------------------------------------------------------
# Single source of truth for strategy names and factories.
# ---------------------------------------------------------------------------

STRATEGY_FACTORIES: dict[str, Callable[..., NarrowingStrategy]] = {
    "null": _factory_null,
    "stub": _factory_stub,
    "brute_force": _factory_brute_force,
    "embedding_threshold": _factory_embedding_threshold,
    "ann_retrieval": _factory_ann_retrieval,
    "bounded_bucket": _factory_bounded_bucket,
}


# ---------------------------------------------------------------------------
# Parameter applicability rules.
# Maps each CLI parameter name to the set of strategies that accept it.
# ---------------------------------------------------------------------------

PARAM_APPLICABILITY: dict[str, frozenset[str]] = {
    "k": frozenset({"null", "stub", "ann_retrieval"}),
    "theta": frozenset({"embedding_threshold"}),
    "ef_search": frozenset({"ann_retrieval"}),
    "s_min": frozenset({"bounded_bucket"}),
    "s_max": frozenset({"bounded_bucket"}),
    "n_bits": frozenset({"bounded_bucket"}),
}

PARAM_CLI_FLAGS: dict[str, str] = {
    "k": "-k/--k",
    "theta": "--theta",
    "ef_search": "--ef-search",
    "s_min": "--s-min",
    "s_max": "--s-max",
    "n_bits": "--n-bits",
}


def check_applicability(strategy_name: str, param_name: str) -> bool:
    """Return True if param_name is applicable to strategy_name."""
    allowed = PARAM_APPLICABILITY.get(param_name)
    if allowed is None:
        return True
    return strategy_name in allowed


def build_strategy_slug(strategy_name: str, config_dict: dict[str, Any]) -> str:
    """Build deterministic configuration slug for default run directory naming.

    Encodes ONLY the keyed config() fields in fixed order and spelling:
      - embedding_threshold: theta<theta> (e.g. theta0.6)
      - ann_retrieval: k<k>_ef<ef_search> (e.g. k10_ef128)
      - bounded_bucket: smin<s_min>_smax<s_max>_nb<n_bits> (e.g. smin5_smax10_nb12)
      - null / stub: k<k> (e.g. k1, k5)
      - brute_force: "" (empty unless seed != 42)
    Appends _seed<seed> (or seed<seed> if base slug is empty) for every strategy
    that has a seed in config() when seed != 42.
    """
    parts: list[str] = []
    if strategy_name == "embedding_threshold":
        parts.append(f"theta{config_dict['theta']}")
    elif strategy_name == "ann_retrieval":
        parts.append(f"k{config_dict['k']}")
        parts.append(f"ef{config_dict['ef_search']}")
    elif strategy_name == "bounded_bucket":
        parts.append(f"smin{config_dict['s_min']}")
        parts.append(f"smax{config_dict['s_max']}")
        parts.append(f"nb{config_dict['n_bits']}")
    elif strategy_name == "null":
        parts.append(f"k{config_dict['k']}")
    elif strategy_name == "stub":
        k_val = config_dict.get("top_k", config_dict.get("k"))
        parts.append(f"k{k_val}")
    elif strategy_name == "brute_force":
        pass
    else:
        raise ValueError(f"Unknown strategy for slug derivation: {strategy_name!r}")

    if "seed" in config_dict and config_dict["seed"] != 42:
        parts.append(f"seed{config_dict['seed']}")

    return "_".join(parts)


def derive_default_run_id(mode: str, strategy_name: str, config_dict: dict[str, Any]) -> str:
    """Derive deterministic run ID `<mode>_<strategy>` or `<mode>_<strategy>_<slug>`."""
    slug = build_strategy_slug(strategy_name, config_dict)
    if slug:
        return f"{mode}_{strategy_name}_{slug}"
    return f"{mode}_{strategy_name}"
