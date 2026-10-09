"""tests/test_controllable_embedder.py
===================================
Unit tests for ControllableEmbedder and vector_with_cosine test helper.
"""

from __future__ import annotations

import numpy as np
import pytest

from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import embed_text
from tests.controllable_embedder import ControllableEmbedder, vector_with_cosine


class TestControllableEmbedder:
    def test_protocol_compliance(self):
        emb = ControllableEmbedder(dim=16)
        assert isinstance(emb, Embedder)

    def test_key_mapping_via_embed_text(self):
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        emb = ControllableEmbedder({"hash_table": v})
        # Strategy passes embed_text("hash_table") == "hash table"
        retrieved = emb.embed("hash table")
        assert np.array_equal(retrieved, v)

    def test_key_collision_raises_value_error(self):
        v1 = np.array([1.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0], dtype=np.float32)
        with pytest.raises(ValueError, match="Key collision"):
            ControllableEmbedder({"hash_table": v1, "hash table": v2})

    def test_dim_validation_errors(self):
        # Missing dim when vectors empty
        with pytest.raises(ValueError, match="dim is required"):
            ControllableEmbedder()

        # Invalid dim
        with pytest.raises(ValueError, match="dim must be a positive integer"):
            ControllableEmbedder(dim=-1)
        with pytest.raises(ValueError, match="dim must be a positive integer"):
            ControllableEmbedder(dim=True)  # bool check

        # Vector dimension mismatch with explicit dim
        with pytest.raises(ValueError, match="dimension 3, expected 4"):
            ControllableEmbedder({"a": [1.0, 2.0, 3.0]}, dim=4)

        # Inconsistent vector dimensions
        with pytest.raises(ValueError, match="dimension 2, expected 3"):
            ControllableEmbedder({"a": [1.0, 2.0, 3.0], "b": [1.0, 2.0]})

        # Non-1D vector
        with pytest.raises(ValueError, match="must be 1-D"):
            ControllableEmbedder({"a": [[1.0, 2.0]]})

        # Non-finite vector
        with pytest.raises(ValueError, match="finite"):
            ControllableEmbedder({"a": [1.0, float("nan")]})

    def test_unnormalised_passthrough(self):
        v = np.array([7.3, 0.0, 0.0], dtype=np.float32)
        emb = ControllableEmbedder({"c": v})
        out = emb.embed("c")
        assert np.array_equal(out, v)
        assert np.isclose(np.linalg.norm(out), 7.3)

    def test_copy_semantics(self):
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        emb = ControllableEmbedder({"c": v})

        out = emb.embed("c")
        out[0] = 999.0

        out2 = emb.embed("c")
        assert out2[0] == 1.0

    def test_set_vector(self):
        emb = ControllableEmbedder(dim=3)
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        emb.set_vector("binary_search_tree", v)

        assert np.array_equal(emb.embed("binary search tree"), v)

        # Replacement
        v2 = np.array([4.0, 5.0, 6.0], dtype=np.float32)
        emb.set_vector("binary_search_tree", v2)
        assert np.array_equal(emb.embed("binary search tree"), v2)

        # Validation in set_vector
        with pytest.raises(ValueError, match="dimension 2, expected 3"):
            emb.set_vector("bad_dim", [1.0, 2.0])

    def test_strict_mode(self):
        emb_strict = ControllableEmbedder({"c": [1.0, 0.0]}, strict=True)
        assert np.array_equal(emb_strict.embed("c"), np.array([1.0, 0.0], dtype=np.float32))
        with pytest.raises(KeyError, match="not configured in strict"):
            emb_strict.embed("unknown")

    def test_fallback_determinism_and_unit_norm(self):
        emb = ControllableEmbedder(dim=16, seed=42, strict=False)
        ref = FakeEmbedder(dim=16, seed=42)

        v1 = emb.embed("unknown text")
        v_ref = ref.embed("unknown text")

        assert np.array_equal(v1, v_ref)
        assert np.isclose(np.linalg.norm(v1), 1.0, atol=1e-5)

    def test_embed_many_equals_stacked_embed(self):
        emb = ControllableEmbedder(
            {
                "alpha": [1.0, 0.0, 0.0],
                "beta": [0.0, 1.0, 0.0],
            },
            dim=3,
        )

        empty = emb.embed_many([])
        assert empty.shape == (0, 3)
        assert empty.dtype == np.float32

        texts = ["alpha", "beta", "gamma_fallback"]
        mat = emb.embed_many(texts)
        stacked = np.vstack([emb.embed(t) for t in texts])

        assert np.array_equal(mat, stacked)

    def test_wrapped_in_metered_embedder(self):
        raw = ControllableEmbedder({"node_a": [1.0, 0.0]}, dim=2)
        meter = MeteredEmbedder(raw, record_texts=True)

        assert isinstance(meter.underlying, Embedder)
        out = meter.embed(embed_text("node_a"))
        assert np.array_equal(out, np.array([1.0, 0.0], dtype=np.float32))
        assert meter.calls == 1
        assert meter.texts_log == ["node a"]


class TestVectorWithCosine:
    @pytest.mark.parametrize("cos", [1.0, 0.9, 0.6, 0.0, -0.5, -1.0])
    def test_accuracy_and_unit_norm(self, cos: float):
        # Non-axis-aligned base
        base = np.array([1.2, -3.4, 5.6, 0.7], dtype=np.float32)
        u_base = base / np.linalg.norm(base)

        v = vector_with_cosine(base, cos)
        assert isinstance(v, np.ndarray)
        assert v.dtype == np.float32
        assert np.isclose(np.linalg.norm(v), 1.0, atol=1e-6)

        actual_cos = float(np.dot(v, u_base))
        assert abs(actual_cos - cos) < 1e-6, f"Cosine error {abs(actual_cos - cos)} for target {cos}"

    def test_validation(self):
        with pytest.raises(ValueError, match="cosine must be a real number"):
            vector_with_cosine([1.0, 0.0], True)

        with pytest.raises(ValueError, match="within \\[-1.0, 1.0\\]"):
            vector_with_cosine([1.0, 0.0], 1.5)

        with pytest.raises(ValueError, match="base must be 1-D"):
            vector_with_cosine([[1.0, 0.0]], 0.5)

        with pytest.raises(ValueError, match="non-zero norm"):
            vector_with_cosine([0.0, 0.0], 0.5)

        with pytest.raises(ValueError, match="dim must be >= 2"):
            vector_with_cosine([1.0], 0.5)
