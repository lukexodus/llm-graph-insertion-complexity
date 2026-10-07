"""graph_insertion package — shared infrastructure for LLM graph-insertion complexity experiments."""

from graph_insertion.embedding import (
    Embedder,
    FakeEmbedder,
    MeteredEmbedder,
)
from graph_insertion.graph_representation import (
    ConceptGraph,
    GoldJudgmentSet,
    SourceKind,
    embed_text,
    oriented_edge,
)
from graph_insertion.loader import (
    CORPUS_DOMAIN_CONTEXT_MAP,
    DEFAULT_DATASET_ROOT,
    TAG_DOMAIN_CONTEXT_MAP,
    CorpusSpec,
    CorpusStats,
    LoadedCorpus,
    derive_domain_context,
    discover_corpora,
    load_corpus,
)
from graph_insertion.strategy import (
    DecisionOutcome,
    DecisionStep,
    InsertionMetrics,
    InsertionResult,
    NarrowingStrategy,
    Shortlist,
    candidate_upper_bound,
    insert_node,
)

__all__ = [
    # Graph Representation
    "ConceptGraph",
    "GoldJudgmentSet",
    "SourceKind",
    "embed_text",
    "oriented_edge",
    # Embedding
    "Embedder",
    "MeteredEmbedder",
    "FakeEmbedder",
    # Strategy Interface
    "Shortlist",
    "DecisionOutcome",
    "InsertionMetrics",
    "InsertionResult",
    "DecisionStep",
    "NarrowingStrategy",
    "candidate_upper_bound",
    "insert_node",
    # Loader
    "CorpusSpec",
    "CorpusStats",
    "LoadedCorpus",
    "discover_corpora",
    "load_corpus",
    "derive_domain_context",
    "DEFAULT_DATASET_ROOT",
    "CORPUS_DOMAIN_CONTEXT_MAP",
    "TAG_DOMAIN_CONTEXT_MAP",
    # LLM & Decision Step
    "LLMResponse",
    "LLMSnapshot",
    "LLMClient",
    "MeteredLLMClient",
    "DeepSeekClient",
    "FakeLLMClient",
    "LLMTransportError",
    "resolve_model_alias",
    "PairwiseDecisionStep",
    "DecisionParseError",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "CALLS_PER_CANDIDATE",
    # Harness Helpers
    "sweep_trial_key",
    "accuracy_trial_key",
    "sample_heldout_nodes",
]

from graph_insertion.harness import (
    accuracy_trial_key,
    sample_heldout_nodes,
    sweep_trial_key,
)
from graph_insertion.llm import (
    DeepSeekClient,
    FakeLLMClient,
    LLMClient,
    LLMResponse,
    LLMSnapshot,
    LLMTransportError,
    MeteredLLMClient,
    resolve_model_alias,
)
from graph_insertion.decision import (
    CALLS_PER_CANDIDATE,
    DecisionParseError,
    PROMPT_VERSION,
    PairwiseDecisionStep,
    SYSTEM_PROMPT,
)

