"""
embedding.py — INFRA-002
========================
Embedder protocol and implementations for LLM graph-insertion complexity experiments.

Decisions:
  - All embedding goes through injected Embedder ([D-24]).
  - Timing and call metering tracked via MeteredEmbedder ([D-25]).
  - Deterministic FakeEmbedder provided for unit testing and offline benchmarking.
"""

from __future__ import annotations

import hashlib
import time
from typing import Protocol, Sequence, runtime_checkable

import numpy as np


@runtime_checkable
class Embedder(Protocol):
    """Protocol for embedding models."""

    def embed(self, text: str) -> np.ndarray:
        """Return a 1D numpy array representing the embedding for the text."""
        ...

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        """Return a 2D numpy array of shape (len(texts), dim)."""
        ...


class MeteredEmbedder:
    """Wraps any Embedder and meters call counts, text counts, and timing.

    Parameters
    ----------
    underlying:
        The wrapped Embedder.

    Attributes
    ----------
    underlying:
        The wrapped Embedder instance.
    calls:
        Total number of calls to embed() or embed_many().
    texts_embedded:
        Total number of individual strings embedded across all calls.
    cumulative_seconds:
        Total wall-clock seconds spent inside the underlying embedder calls.
    """

    def __init__(self, underlying: Embedder, record_texts: bool = False) -> None:
        self.underlying = underlying
        self.record_texts = record_texts
        self.calls: int = 0
        self.texts_embedded: int = 0
        self.cumulative_seconds: float = 0.0
        self.texts_log: Optional[list[str]] = [] if record_texts else None

    def embed(self, text: str) -> np.ndarray:
        t0 = time.perf_counter()
        res = self.underlying.embed(text)
        elapsed = time.perf_counter() - t0
        self.calls += 1
        self.texts_embedded += 1
        self.cumulative_seconds += elapsed
        if self.texts_log is not None:
            self.texts_log.append(text)
        return res

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        t0 = time.perf_counter()
        res = self.underlying.embed_many(texts)
        elapsed = time.perf_counter() - t0
        self.calls += 1
        self.texts_embedded += len(texts)
        self.cumulative_seconds += elapsed
        if self.texts_log is not None:
            self.texts_log.extend(texts)
        return res

    def reset(self) -> None:
        """Reset meters to zero."""
        self.calls = 0
        self.texts_embedded = 0
        self.cumulative_seconds = 0.0
        if self.texts_log is not None:
            self.texts_log.clear()


class FakeEmbedder:
    """Deterministic, network-free embedder for tests and offline validation.

    Generates reproducible, L2-normalized pseudo-embeddings by hashing each
    input string with an optional seed.

    Parameters
    ----------
    dim:
        Dimension of embedding vectors (default: 64).
    seed:
        Seed mixed into the hash for reproducibility.
    """

    def __init__(self, dim: int = 64, seed: int = 42) -> None:
        self.dim = dim
        self.seed = seed

    def _embed_single(self, text: str) -> np.ndarray:
        key = f"{self.seed}:{text}".encode("utf-8")
        h = hashlib.sha256(key).digest()
        seed_int = int.from_bytes(h[:8], "little")
        rng = np.random.default_rng(seed_int)
        vec = rng.standard_normal(self.dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32)

    def embed(self, text: str) -> np.ndarray:
        return self._embed_single(text)

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        return np.vstack([self._embed_single(t) for t in texts])
