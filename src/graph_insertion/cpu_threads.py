"""cpu_threads.py — INFRA-009 / D-72
==================================
Deterministic CPU thread-count pinning for PyTorch inference.

Under [D-71] (INFRA-008), calling faiss.omp_set_num_threads(1) changes PyTorch's
intra-op thread count from default (physical cores, e.g. 4) down to 1 due to a shared
OpenMP runtime thread setting across the process. Under [D-72], PyTorch intra-op
CPU threads are pinned to CPU_THREAD_PIN (1) for every execution that constructs
MiniLMEmbedder (covering Strategies 2, 3, and 4), eliminating cross-strategy
embedding latency bias while keeping FAISS single-threaded ([D-47]).
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
