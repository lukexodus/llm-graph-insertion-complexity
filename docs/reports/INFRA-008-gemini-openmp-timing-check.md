# INFRA-008 — OpenMP / PyTorch Thread-Timing Check Outcome and Analysis

- **Task ID:** INFRA-008
- **Date:** 2026-10-14 19:20 PH (UTC+8) (Amended 2026-10-15 under INFRA-009)
- **Agent / Model:** Gemini (Antigravity, Gemini 3.8 Flash (Medium))
- **Execution Context:** Luke's workstation host environment, Python virtual environment `.venv-ann` (Python 3.14.7, torch 2.14.1+cu130, faiss-cpu 1.15.1, sentence-transformers 6.1.0).
- **Hardware Profile:** Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz, 4 cores (8 logical threads, 2 threads per core, `nproc` = 8).

---

## 1. Objective & Background

Under `[D-68](5)` and `scripts/README.md` lines 272–287, a standalone diagnostic check was specified to evaluate whether calling `faiss.omp_set_num_threads(1)` (invoked by Strategy 3 in `src/graph_insertion/strategies/ann_retrieval.py` for deterministic HNSW index construction and query per `[D-47]`) impacts CPU inference latency in PyTorch / SentenceTransformers (`all-MiniLM-L6-v2`) via shared OpenMP thread controls.

Prior to launching live runs of the embedding strategies (Strategies 2, 3, and 4) under `RUN-001`, this benchmark must determine whether thread-count reduction in FAISS introduces cross-strategy latency bias.

---

## 2. Benchmark Execution

The benchmark was executed directly in terminal from repository root using the exact interleaved script from `scripts/README.md`:

```bash
for mode in default omp1 default omp1 default omp1; do
  .venv-ann/bin/python - "$mode" <<'EOF'
import sys, time, statistics as st
import torch, faiss
from graph_insertion.embedding_minilm import MiniLMEmbedder

mode = sys.argv[1]
emb = MiniLMEmbedder()
for i in range(20):
    emb.embed(f"warmup_{i}")
if mode == "omp1":
    faiss.omp_set_num_threads(1)
ts = []
for i in range(200):
    t0 = time.perf_counter()
    emb.embed(f"concept_name_{i:04d}")
    ts.append((time.perf_counter() - t0) * 1000)
print(f"{mode:8s} torch_threads={torch.get_num_threads()} median={st.median(ts):.3f} ms p95={sorted(ts)[190]:.3f} ms")
EOF
done
```

### Raw Observed Output

```text
default  torch_threads=4 median=16.379 ms p95=19.346 ms
omp1     torch_threads=1 median=24.952 ms p95=28.049 ms
default  torch_threads=4 median=18.189 ms p95=23.152 ms
omp1     torch_threads=1 median=24.362 ms p95=27.542 ms
default  torch_threads=4 median=16.856 ms p95=22.107 ms
omp1     torch_threads=1 median=23.982 ms p95=27.751 ms
```

*(Note: During model initialisation in Luke's terminal run, an informational warning appeared: `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.` The local cache directory `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` exists on disk).*

---

## 3. Data & Statistical Evaluation

Per the pre-fixed decision rule defined in `[D-68](5)`:

1. **Condition Statistics:**
   - **`default` (3 independent processes):**
     - Medians: $[16.379, 18.189, 16.856]$ ms
     - $M_{\text{default}} = \text{median}(16.379, 18.189, 16.856) = \mathbf{16.856\text{ ms}}$
     - $\text{spread}_{\text{default}} = \max(16.379, 18.189, 16.856) - \min(16.379, 18.189, 16.856) = 18.189 - 16.379 = \mathbf{1.810\text{ ms}}$
     - `torch.get_num_threads()`: **4** across all processes (on an 8-logical-core host, PyTorch defaults to physical core count 4).
   - **`omp1` (3 independent processes):**
     - Medians: $[24.952, 24.362, 23.982]$ ms
     - $M_{\text{omp1}} = \text{median}(24.952, 24.362, 23.982) = \mathbf{24.362\text{ ms}}$
     - $\text{spread}_{\text{omp1}} = \max(24.952, 24.362, 23.982) - \min(24.952, 24.362, 23.982) = 24.952 - 23.982 = \mathbf{0.970\text{ ms}}$
     - `torch.get_num_threads()`: **1** across all processes.

2. **Shift and Spread Comparison:**
   - Absolute shift: $|M_{\text{omp1}} - M_{\text{default}}| = 24.362 - 16.856 = \mathbf{7.506\text{ ms}}$
   - Relative shift: $\frac{7.506}{16.856} = 0.44530... \rightarrow \mathbf{+44.53\%}$
   - Noise threshold: $\max(\text{spread}_{\text{default}}, \text{spread}_{\text{omp1}}) = \mathbf{1.810\text{ ms}}$
   - Since $7.506\text{ ms} > 1.810\text{ ms}$, the observed shift strongly exceeds within-condition measurement spread.

---

## 4. Pre-Fixed Decision Rule Determination

`[D-68](5)` specifies that the effect is **material** if:
1. `torch.get_num_threads()` differs between `default` and `omp1`; **OR**
2. $\frac{|M_{\text{omp1}} - M_{\text{default}}|}{M_{\text{default}}} > 0.10$ AND $|M_{\text{omp1}} - M_{\text{default}}| > \max(\text{spread}_{\text{default}}, \text{spread}_{\text{omp1}})$.

**Outcome:**
- Criterion 1 is **triggered**: `torch.get_num_threads()` drops from 4 to 1.
- Criterion 2 is **triggered**: Relative shift (+44.53%) exceeds 10%, and absolute difference ($7.506\text{ ms}$) exceeds maximum spread ($1.810\text{ ms}$).

**Verdict:** The side-effect is **MATERIAL**. The measurement shows that calling `faiss.omp_set_num_threads(1)` changes PyTorch's thread count, which is consistent with FAISS and PyTorch sharing one OpenMP thread setting in this process. This reduces PyTorch thread concurrency to a single thread and increases CPU sentence embedding latency by ~44.5%.

Inspection of `/proc/self/maps` reveals that both `faiss_cpu.libs/libgomp-e985bcbb.so.1.0.0` and `torch/lib/libgomp.so.1` are loaded into memory. While multiple dynamic OpenMP library files are mapped, global OpenMP runtime thread control symbols or vendor interop resolve to a shared thread setting across the process.

---

## 5. Consequences & Follow-Up Action

Under `[D-68](5)`:
> *"If material: a follow-up task explicitly sets PyTorch thread count across all embedding strategies while keeping FAISS single-threaded ([D-47]). Non-pilot live runs of Strategies 2, 3, and 4 wait for this determination; brute force does not."*

To ensure parity in CPU embedding latency across Strategies 2, 3, and 4:
1. Record **`[D-71]`** capturing the empirical benchmark measurements and the materiality determination.
2. The follow-up policy required by `[D-68](5)` is specified in `[D-72]` (INFRA-009).
