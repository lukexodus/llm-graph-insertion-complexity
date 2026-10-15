"""cpu_threads.py — INFRA-009 / D-72
==================================
Deterministic CPU thread-count pinning for PyTorch inference.

In the INFRA-008 measurement ([D-71]), calling faiss.omp_set_num_threads(1)
was observed to lower torch.get_num_threads() from default (4 on the reference host)
down to 1. The precise underlying mechanism was not identified (inspection of
process mappings showed two distinct OpenMP library files loaded: one bundled with
faiss-cpu and one with PyTorch). Under [D-72], PyTorch intra-op CPU threads are
explicitly pinned to CPU_THREAD_PIN (1) for every execution that constructs
MiniLMEmbedder (covering Strategies 2, 3, and 4), eliminating cross-strategy
embedding latency bias while keeping FAISS single-threaded ([D-47]) regardless of
how OpenMP symbols or runtimes interact.
"""

from __future__ import annotations

from typing import Any, Optional

CPU_THREAD_PIN: int = 1


def pin_cpu_threads(n: int = CPU_THREAD_PIN) -> dict[str, int]:
    """Pin PyTorch intra-op CPU threads to n and verify via read-back.

    Parameters
    ----------
    n : int
        Target PyTorch CPU thread count (default: CPU_THREAD_PIN = 1).

    Returns
    -------
    dict[str, int]
        Mapping with keys 'requested' and 'torch_threads'.

    Raises
    ------
    RuntimeError
        If PyTorch read-back thread count does not match requested n.
    ImportError
        If PyTorch is not installed.
    """
    import torch

    torch.set_num_threads(n)
    observed = torch.get_num_threads()
    if observed != n:
        raise RuntimeError(
            f"PyTorch thread pin verification failed: requested {n}, observed {observed}"
        )
    return {"requested": int(n), "torch_threads": int(observed)}
