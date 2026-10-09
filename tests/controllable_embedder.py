"""tests/controllable_embedder.py
==============================
Shared test helper providing a controllable Embedder implementation and
geometric vector utilities for similarity-driven strategy tests.

Purpose
-------
FakeEmbedder generates pseudo-random embeddings where pairwise cosines
concentrate near zero, making it impossible to deterministically test
similarity thresholds, ANN retrieval, or distance-based bucket partitioning.
ControllableEmbedder allows test fixtures to configure exact embedding vectors
for specific concepts, with a deterministic fallback (via FakeEmbedder) for
all other concepts.

Key convention (D-21)
---------------------
Keys provided in `vectors` or passed to `set_vector()` are concept names
(e.g., "hash_table"). They are converted with `embed_text()` at registration
time because narrowing strategies and the driver only ever pass `embed_text()`
payloads (e.g., "hash table") to the embedder. Two keys that collide after
`embed_text()` raise ValueError.

Unnormalised vectors
--------------------
Supplied vectors are returned unnormalised, exactly as given (cast to float32).
This allows tests to verify that strategies perform vector normalisation
themselves and do not assume embedders return unit vectors.

Usage example
-------------
>>> from tests.controllable_embedder import ControllableEmbedder, vector_with_cosine
>>> base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
>>> v_high = vector_with_cosine(base, 0.9)
>>> v_low = vector_with_cosine(base, 0.2)
>>> embedder = ControllableEmbedder(
...     {"high_sim": v_high, "low_sim": v_low},
...     seed=42,
... )
>>> # embed() receives embed_text() representation and finds "high_sim":
>>> res = embedder.embed("high sim")
>>> float(np.dot(res, base)) >= 0.899
True
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from graph_insertion.embedding import FakeEmbedder
from graph_insertion.graph_representation import embed_text


def vector_with_cosine(base: Sequence[float] | np.ndarray, cosine: float) -> np.ndarray:
    """Return a unit-norm float32 vector with dot(v, base / |base|) == cosine to within 1e-6.

    Constructed as:
        v = cosine * u + sqrt(1 - cosine^2) * w
    where u = base / |base| and w is a unit vector orthogonal to u chosen
    deterministically via Gram-Schmidt on the lowest-index standard basis
    vector that is not nearly parallel to u.

    Parameters
    ----------
    base:
        Base direction vector. Must be 1-D, finite, non-zero norm, and dim >= 2 if |cosine| < 1.
    cosine:
        Target cosine similarity in [-1.0, 1.0].

    Returns
    -------
    np.ndarray:
        Unit-norm 1-D float32 array.
    """
    if isinstance(cosine, bool) or not isinstance(cosine, (int, float)):
        raise ValueError(f"cosine must be a real number, got {type(cosine).__name__}")
    if not np.isfinite(cosine) or abs(cosine) > 1.0:
        raise ValueError(f"cosine must be finite and within [-1.0, 1.0], got {cosine!r}")

    base_arr = np.asarray(base, dtype=np.float64)
    if base_arr.ndim != 1:
        raise ValueError(f"base must be 1-D, got ndim={base_arr.ndim}")
    if not np.all(np.isfinite(base_arr)):
        raise ValueError("base must contain finite values")

    norm_base = float(np.linalg.norm(base_arr))
    if norm_base == 0.0:
        raise ValueError("base must have non-zero norm")

    dim = len(base_arr)
    if dim < 2 and abs(cosine) < 1.0:
        raise ValueError(f"dim must be >= 2 when |cosine| < 1.0, got dim={dim}")

    u = base_arr / norm_base

    if abs(cosine) >= 1.0:
        v = (1.0 if cosine > 0 else -1.0) * u
        v32 = v.astype(np.float32)
        return v32 / np.linalg.norm(v32)

    # Find lowest-index standard basis vector that is not nearly parallel to u
    w_idx = None
    for i in range(dim):
        if abs(u[i]) < 0.9:
            w_idx = i
            break
    if w_idx is None:
        w_idx = int(np.argmin(np.abs(u)))

    e = np.zeros(dim, dtype=np.float64)
    e[w_idx] = 1.0

    w_ortho = e - u[w_idx] * u
    w = w_ortho / np.linalg.norm(w_ortho)

    sin_theta = math.sqrt(max(0.0, 1.0 - float(cosine) ** 2))
    v = float(cosine) * u + sin_theta * w
    v = v / np.linalg.norm(v)

    v32 = v.astype(np.float32)
    return (v32 / np.linalg.norm(v32)).astype(np.float32)


class ControllableEmbedder:
    """Embedder returning caller-specified vectors for chosen concept names and fallback for others.

    Parameters
    ----------
    vectors:
        Optional mapping of concept name -> vector. Keys are converted via embed_text().
    dim:
        Vector dimension. Inferred from vectors if provided, otherwise required.
    seed:
        Seed for the fallback FakeEmbedder.
    strict:
        If True, embed() raises KeyError on unconfigured text. If False, delegates to FakeEmbedder.
    """

    def __init__(
        self,
        vectors: Mapping[str, Sequence[float] | np.ndarray] | None = None,
        *,
        dim: int | None = None,
        seed: int = 42,
        strict: bool = False,
    ) -> None:
        if dim is not None:
            if isinstance(dim, bool) or not isinstance(dim, int) or dim <= 0:
                raise ValueError(f"dim must be a positive integer, got {dim!r}")

        self._vectors: dict[str, np.ndarray] = {}
        inferred_dim = dim

        if vectors is not None and len(vectors) > 0:
            for name, vec in vectors.items():
                vec_arr = np.asarray(vec, dtype=np.float32)
                if vec_arr.ndim != 1:
                    raise ValueError(f"Vector for {name!r} must be 1-D, got shape {vec_arr.shape}")
                if not np.all(np.isfinite(vec_arr)):
                    raise ValueError(f"Vector for {name!r} must contain finite values")

                v_len = len(vec_arr)
                if inferred_dim is None:
                    inferred_dim = v_len
                    if inferred_dim <= 0:
                        raise ValueError("Vector dimension must be positive")
                elif v_len != inferred_dim:
                    raise ValueError(
                        f"Vector for {name!r} has dimension {v_len}, expected {inferred_dim}"
                    )

                key = embed_text(name)
                if key in self._vectors:
                    raise ValueError(
                        f"Key collision after embed_text: {name!r} collides with an existing key on {key!r}"
                    )
                self._vectors[key] = vec_arr.copy()

        if inferred_dim is None:
            raise ValueError("dim is required when vectors is empty or None")

        self.dim: int = inferred_dim
        self.seed: int = seed
        self.strict: bool = strict
        self._fallback: FakeEmbedder = FakeEmbedder(dim=self.dim, seed=self.seed)

    def set_vector(self, name: str, vector: Sequence[float] | np.ndarray) -> None:
        """Register or replace a vector for the given concept name."""
        vec_arr = np.asarray(vector, dtype=np.float32)
        if vec_arr.ndim != 1:
            raise ValueError(f"Vector for {name!r} must be 1-D, got shape {vec_arr.shape}")
        if not np.all(np.isfinite(vec_arr)):
            raise ValueError(f"Vector for {name!r} must contain finite values")
        if len(vec_arr) != self.dim:
            raise ValueError(
                f"Vector for {name!r} has dimension {len(vec_arr)}, expected {self.dim}"
            )

        key = embed_text(name)
        self._vectors[key] = vec_arr.copy()

    def embed(self, text: str) -> np.ndarray:
        """Return 1-D float32 embedding copy for text."""
        if text in self._vectors:
            return self._vectors[text].copy()

        if self.strict:
            raise KeyError(f"Text {text!r} not configured in strict ControllableEmbedder")

        return self._fallback.embed(text).copy()

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        """Return 2-D float32 array of shape (len(texts), dim)."""
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        return np.vstack([self.embed(t) for t in texts])
