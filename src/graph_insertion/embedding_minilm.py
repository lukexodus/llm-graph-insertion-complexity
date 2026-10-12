"""embedding_minilm.py — INFRA-007
==================================
MiniLMEmbedder: production embedding model for live experiment runs.

Uses sentence-transformers ``all-MiniLM-L6-v2`` on CPU, float32, 384-dim.
Imported lazily so this module loads without sentence-transformers installed.

Decisions:
  - [D-35](4): Fixed local sentence-transformers all-MiniLM-L6-v2 on CPU,
    version pinned.
  - [D-64]: Live runs of embedding strategies require ``--embedder minilm``;
    ``--embedder fake`` is refused for live embedding strategies.
  - [D-66]: Version and model revision pins, runtime check against installed
    package version, fail-closed on unset pins.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np


# ---------------------------------------------------------------------------
# Pins — MUST be set to actual values before any live run.
# If either pin is None or blank, MiniLMEmbedder refuses to initialise (fail-closed).
# ---------------------------------------------------------------------------

# Pin: sentence-transformers package version installed in .venv-ann.
SENTENCE_TRANSFORMERS_VERSION_PIN: Optional[str] = None

# Pin: Hugging Face model revision (commit hash) for all-MiniLM-L6-v2.
MODEL_REVISION_PIN: Optional[str] = None

MODEL_NAME: str = "all-MiniLM-L6-v2"
MODEL_DIM: int = 384

_UNSET: Any = object()


class MiniLMEmbedder:
    """Production embedder using sentence-transformers all-MiniLM-L6-v2.

    Implements the ``Embedder`` protocol (embed, embed_many) exactly as
    ``FakeEmbedder`` does: embed returns 1-D float32 of shape ``(384,)``,
    embed_many returns 2-D float32 of shape ``(len(texts), 384)``.

    Parameters
    ----------
    revision :
        Model revision (commit hash). Defaults to ``MODEL_REVISION_PIN``.
        If ``None`` or empty at construction time, raises ``ValueError``
        (fail-closed).

    Attributes
    ----------
    model_name : str
        Always ``"all-MiniLM-L6-v2"``.
    dim : int
        Always 384.
    revision : str
        Pinned model revision hash.
    installed_version : str
        Installed version of sentence-transformers library.
    """

    model_name: str = MODEL_NAME
    dim: int = MODEL_DIM

    def __init__(self, revision: Any = _UNSET) -> None:
        if (
            not isinstance(SENTENCE_TRANSFORMERS_VERSION_PIN, str)
            or not SENTENCE_TRANSFORMERS_VERSION_PIN.strip()
        ):
            raise ValueError(
                "MiniLMEmbedder requires a pinned sentence-transformers package version. "
                f"SENTENCE_TRANSFORMERS_VERSION_PIN is currently {SENTENCE_TRANSFORMERS_VERSION_PIN!r}. "
                "Cannot proceed without a version pin (fail-closed)."
            )

        actual_revision = MODEL_REVISION_PIN if revision is _UNSET else revision
        if not isinstance(actual_revision, str) or not actual_revision.strip():
            raise ValueError(
                "MiniLMEmbedder requires a pinned model revision. "
                f"MODEL_REVISION_PIN is currently {MODEL_REVISION_PIN!r} (passed revision={revision!r}). "
                "Cannot proceed without a revision pin (fail-closed)."
            )
        self.revision: str = actual_revision

        # Lazy import of sentence_transformers
        try:
            import sentence_transformers
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install with: pip install -e \".[embed]\""
            ) from None

        installed_ver = getattr(sentence_transformers, "__version__", None)
        if installed_ver != SENTENCE_TRANSFORMERS_VERSION_PIN:
            raise ValueError(
                f"sentence-transformers version mismatch: installed={installed_ver!r} "
                f"vs pinned={SENTENCE_TRANSFORMERS_VERSION_PIN!r}."
            )
        self.installed_version: str = str(installed_ver)

        self._model = SentenceTransformer(
            self.model_name,
            revision=self.revision,
            device="cpu",
        )

    def embed(self, text: str) -> np.ndarray:
        """Return 1-D float32 embedding for a single text string."""
        vec = self._model.encode(text, convert_to_numpy=True)
        arr = np.asarray(vec, dtype=np.float32).reshape(-1)
        if arr.shape != (self.dim,):
            raise ValueError(
                f"Expected 1-D embedding of shape ({self.dim},), got {arr.shape}"
            )
        return arr

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        """Return 2-D float32 array of shape (len(texts), dim)."""
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        mat = self._model.encode(list(texts), convert_to_numpy=True)
        arr = np.asarray(mat, dtype=np.float32)
        if arr.ndim == 1 and len(texts) == 1:
            arr = arr.reshape(1, -1)
        if arr.shape != (len(texts), self.dim):
            raise ValueError(
                f"Expected 2-D embedding matrix of shape ({len(texts)}, {self.dim}), got {arr.shape}"
            )
        return arr

    def identity(self) -> dict[str, Any]:
        """Return identifying metadata for sidecar recording."""
        return {
            "model_name": self.model_name,
            "dim": int(self.dim),
            "revision": self.revision,
            "sentence_transformers_version": self.installed_version,
            "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
            "device": "cpu",
            "dtype": "float32",
        }
