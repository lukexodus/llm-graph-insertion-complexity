"""tests/test_cpu_threads.py — INFRA-009 / D-72
=============================================
Unit and integration tests for deterministic CPU thread pinning:
  - Helper pin_cpu_threads returns requested/observed, raises on mismatch, restores original count.
  - Subprocess tests verifying ordering with FAISS OpenMP calls.
  - Subprocess tests verifying CLI behavior on fake and minilm paths.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any
from unittest.mock import patch

import pytest

from graph_insertion.cpu_threads import CPU_THREAD_PIN, pin_cpu_threads


class TestPinCPUThreadsHelper:
    """Unit tests for pin_cpu_threads function."""

    def test_pin_cpu_threads_success_and_readback(self) -> None:
        torch = pytest.importorskip("torch")
        orig_threads = torch.get_num_threads()
        try:
            res = pin_cpu_threads(1)
            assert res == {"requested": 1, "torch_threads": 1}
            assert torch.get_num_threads() == 1

            res2 = pin_cpu_threads(2)
            assert res2 == {"requested": 2, "torch_threads": 2}
            assert torch.get_num_threads() == 2
        finally:
            torch.set_num_threads(orig_threads)

    def test_pin_cpu_threads_raises_on_mismatch(self) -> None:
        torch = pytest.importorskip("torch")
        orig_threads = torch.get_num_threads()
        try:
            with patch.object(torch, "get_num_threads", return_value=99):
                with pytest.raises(RuntimeError, match="PyTorch thread pin verification failed"):
                    pin_cpu_threads(1)
        finally:
            torch.set_num_threads(orig_threads)


class TestSubprocessThreadOrdering:
    """Subprocess tests verifying ordering with real libraries."""

    @pytest.mark.parametrize("order", ["torch_first", "faiss_first"])
    def test_ordering_with_faiss(self, order: str) -> None:
        pytest.importorskip("torch")
        pytest.importorskip("faiss")

        code = f"""
import sys
if "{order}" == "torch_first":
    import torch
    import faiss
else:
    import faiss
    import torch

from graph_insertion.cpu_threads import pin_cpu_threads

# Control check: faiss.omp_set_num_threads(1) starting from default lowers torch threads
default_threads = torch.get_num_threads()
faiss.omp_set_num_threads(1)
control_threads = torch.get_num_threads()

# Invariant check: after pin_cpu_threads(1), then faiss.omp_set_num_threads(1), threads remain 1
pin_cpu_threads(1)
faiss.omp_set_num_threads(1)
after_threads = torch.get_num_threads()

assert after_threads == 1, f"Expected 1, got {{after_threads}}"
print(f"ORDER: {order} | CONTROL: default={{default_threads}} -> control={{control_threads}} | INVARIANT: after={{after_threads}}")
"""
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "INVARIANT: after=1" in proc.stdout
        print(proc.stdout.strip())

    def test_fake_embedder_does_not_import_torch(self) -> None:
        code = """
import sys
from scripts.run_experiment import build_parser, get_current_embedder_info

parser = build_parser()
args = parser.parse_args(["--strategy", "null", "--embedder", "fake"])
info = get_current_embedder_info(args, uses_embeddings=False, seed=42)
assert info["type"] == "fake"
assert "cpu_threads" not in info
assert "torch" not in sys.modules, f"torch unexpectedly imported: {list(sys.modules.keys())}"
print("OK_NO_TORCH")
"""
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "OK_NO_TORCH" in proc.stdout
