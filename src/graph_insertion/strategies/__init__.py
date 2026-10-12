"""graph_insertion.strategies — candidate-narrowing strategy implementations.

Exports only NullStrategy eagerly.  All other strategies and the registry
are imported lazily so this package loads without faiss and without
sentence-transformers.
"""

from graph_insertion.strategies.null import NullStrategy

__all__ = [
    "NullStrategy",
    "BruteForceStrategy",
    "EmbeddingThresholdStrategy",
    "AnnRetrievalStrategy",
    "BoundedBucketStrategy",
    "STRATEGY_FACTORIES",
]


def __getattr__(name: str):  # noqa: ANN201 — lazy module-level exports
    if name == "BruteForceStrategy":
        from graph_insertion.strategies.brute_force import BruteForceStrategy
        return BruteForceStrategy
    if name == "EmbeddingThresholdStrategy":
        from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy
        return EmbeddingThresholdStrategy
    if name == "AnnRetrievalStrategy":
        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
        return AnnRetrievalStrategy
    if name == "BoundedBucketStrategy":
        from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy
        return BoundedBucketStrategy
    if name == "STRATEGY_FACTORIES":
        from graph_insertion.strategies.registry import STRATEGY_FACTORIES
        return STRATEGY_FACTORIES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
