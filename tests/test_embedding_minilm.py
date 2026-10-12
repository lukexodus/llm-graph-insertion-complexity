"""tests/test_embedding_minilm.py — INFRA-007
==============================================
Offline unit tests for ``graph_insertion.embedding_minilm.MiniLMEmbedder``.

No network access, no model downloads, and no real ``sentence_transformers``
import.  All tests inject a deterministic stub ``sentence_transformers``
module via ``monkeypatch.setitem(sys.modules, "sentence_transformers", ...)``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pytest

import graph_insertion.embedding_minilm as minilm_mod
from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.embedding_minilm import (
    MODEL_DIM,
    MODEL_NAME,
    MiniLMEmbedder,
)


class _StubSentenceTransformer:
    """Deterministic offline stub for ``sentence_transformers.SentenceTransformer``."""

    instances: list["_StubSentenceTransformer"] = []

    def __init__(
        self,
        model_name_or_path: str,
        *,
        revision: str | None = None,
        device: str | None = None,
        **kwargs: Any,
    ) -> None:
        if revision is None or not isinstance(revision, str) or not revision.strip():
            raise AssertionError("StubSentenceTransformer must never be called with revision=None/empty")
        self.model_name_or_path = model_name_or_path
        self.revision = revision
        self.device = device
        self.kwargs = kwargs
        self.encode_calls: list[tuple[Any, dict[str, Any]]] = []
        _StubSentenceTransformer.instances.append(self)

    @staticmethod
    def _vec_for_text(text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        return rng.standard_normal(MODEL_DIM).astype(np.float32)

    def encode(self, sentences: str | Sequence[str], **kwargs: Any) -> np.ndarray:
        self.encode_calls.append((sentences, dict(kwargs)))
        if isinstance(sentences, str):
            return self._vec_for_text(sentences)
        return np.vstack([self._vec_for_text(s) for s in sentences]).astype(np.float32)


@pytest.fixture
def stub_st_module(monkeypatch: pytest.MonkeyPatch) -> type[_StubSentenceTransformer]:
    """Inject stub ``sentence_transformers`` into ``sys.modules``."""
    _StubSentenceTransformer.instances.clear()
    mod = types.ModuleType("sentence_transformers")
    mod.SentenceTransformer = _StubSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)
    return _StubSentenceTransformer


class TestMiniLMEmbedderOffline:
    """Offline tests for MiniLMEmbedder using injected stub module."""

    def test_module_imports_lazily_without_sentence_transformers(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        src_dir = repo_root / "src"
        code = (
            "import sys\n"
            "sys.modules['sentence_transformers'] = None\n"
            "import graph_insertion.embedding_minilm as m\n"
            "assert m.MODEL_NAME == 'all-MiniLM-L6-v2'\n"
            "assert m.MODEL_DIM == 384\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(repo_root),
            env={"PYTHONPATH": str(src_dir)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"

    def test_refuses_when_pin_is_none_or_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_st_module: type[_StubSentenceTransformer],
    ) -> None:
        # 1. Default when MODEL_REVISION_PIN is None -> raises ValueError
        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", None)
        with pytest.raises(ValueError, match="pinned model revision"):
            MiniLMEmbedder()
        assert len(stub_st_module.instances) == 0

        # 2. Explicit revision=None refused even when MODEL_REVISION_PIN is set (kills I-M13)
        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "abc123456789")
        with pytest.raises(ValueError, match="pinned model revision"):
            MiniLMEmbedder(revision=None)
        assert len(stub_st_module.instances) == 0

        # 3. Empty/whitespace revision string refused
        with pytest.raises(ValueError, match="pinned model revision"):
            MiniLMEmbedder(revision="   ")
        assert len(stub_st_module.instances) == 0

    def test_missing_sentence_transformers_raises_import_error_with_install_hint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "sentence_transformers", None)
        with pytest.raises(ImportError, match=r'pip install -e "\.\[embed\]"'):
            MiniLMEmbedder(revision="test-rev-001")

    def test_embed_and_embed_many_shapes_dtypes_and_call_counts(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_st_module: type[_StubSentenceTransformer],
    ) -> None:
        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev-sha-42")
        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.0.0-test")

        emb = MiniLMEmbedder()
        assert isinstance(emb, Embedder)
        assert len(stub_st_module.instances) == 1
        underlying = stub_st_module.instances[0]
        assert underlying.model_name_or_path == MODEL_NAME
        assert underlying.revision == "rev-sha-42"
        assert underlying.device == "cpu"

        # Single embed: 1D float32 of shape (384,), exactly 1 encode call with str
        v1 = emb.embed("binary search tree")
        assert isinstance(v1, np.ndarray)
        assert v1.dtype == np.float32
        assert v1.shape == (384,)
        assert len(underlying.encode_calls) == 1
        assert underlying.encode_calls[0][0] == "binary search tree"

        # Determinism
        v1_again = emb.embed("binary search tree")
        np.testing.assert_array_equal(v1, v1_again)
        assert len(underlying.encode_calls) == 2

        # Batch embed_many: 2D float32 of shape (3, 384), 1 batch encode call
        texts = ["graph traversal", "dynamic programming", "heap sort"]
        mat = emb.embed_many(texts)
        assert isinstance(mat, np.ndarray)
        assert mat.dtype == np.float32
        assert mat.shape == (3, 384)
        assert len(underlying.encode_calls) == 3
        assert underlying.encode_calls[2][0] == texts

        # Empty embed_many: matches FakeEmbedder shape (0, 384) and dtype float32, 0 encode calls
        empty_mat = emb.embed_many([])
        fake_empty = FakeEmbedder(dim=384).embed_many([])
        assert empty_mat.shape == fake_empty.shape == (0, 384)
        assert empty_mat.dtype == fake_empty.dtype == np.float32
        assert len(underlying.encode_calls) == 3

        # MeteredEmbedder compatibility
        metered = MeteredEmbedder(emb, record_texts=True)
        mv = metered.embed("red black tree")
        assert mv.shape == (384,)
        assert metered.calls == 1
        assert metered.texts_embedded == 1
        assert metered.texts_log == ["red black tree"]

    def test_identity_metadata_content_and_json_serializable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_st_module: type[_StubSentenceTransformer],
    ) -> None:
        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
        emb = MiniLMEmbedder(revision="commit-hash-xyz")
        ident = emb.identity()
        assert ident == {
            "model_name": "all-MiniLM-L6-v2",
            "dim": 384,
            "revision": "commit-hash-xyz",
            "sentence_transformers_version_pin": "3.1.1",
            "device": "cpu",
            "dtype": "float32",
        }
        assert json.loads(json.dumps(ident)) == ident
