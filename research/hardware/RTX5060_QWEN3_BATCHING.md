# RTX 5060 — Qwen3-1.7B Batch Scaling Study

## Purpose

Characterize inference throughput, GPU memory behavior, and practical
batch-size limits for Qwen3-1.7B BF16 on the Eagle RTX 5060 system.

This study is exploratory systems characterization and is separate from
the final model-quality benchmark.

## Hardware / Runtime

- GPU: NVIDIA GeForce RTX 5060
- Dedicated VRAM: 8151 MiB
- Model: Qwen/Qwen3-1.7B
- Model revision:
  70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
- Dtype: BF16
- Attention backend: PyTorch SDPA
- PyTorch: 2.12.0+cu132
- CUDA runtime: 13.2

## 1024-token batch sweep

| Batch | Aggregate tok/s | Per-sequence tok/s | Peak allocated | Peak reserved |
|------:|----------------:|-------------------:|---------------:|--------------:|
| 1 | 28.39 | 28.39 | 3.36 GiB | 4.16 GiB |
| 2 | 50.28 | 25.14 | 3.49 GiB | 4.15 GiB |
| 3 | 74.98 | 24.99 | 3.61 GiB | 4.15 GiB |
| 4 | 103.26 | 25.82 | 3.73 GiB | 4.15 GiB |
| 6 | 153.52 | 25.59 | 3.98 GiB | 4.28 GiB |
| 8 | 206.67 | 25.83 | 4.23 GiB | 4.66 GiB |

Batch size 8 achieved approximately 7.28x the aggregate throughput of
batch size 1 in this short-context test.

## 4096-token batch sweep

| Batch | Aggregate tok/s | Per-sequence tok/s | Peak allocated | Peak reserved |
|------:|----------------:|-------------------:|---------------:|--------------:|
| 2 | 50.08 | 25.04 | 4.19 GiB | 4.72 GiB |
| 4 | 87.93 | 21.98 | 5.14 GiB | 6.60 GiB |
| 6 | 42.79 | 7.13 | 6.09 GiB | 8.63 GiB |
| 8 | 21.52 | 2.69 | 7.04 GiB | 11.24 GiB |

## Observed power / utilization

Approximate manually observed peak GPU power during the 4096-token
sweep:

- batch 2: ~90 W
- batch 4: ~102 W
- batch 6: ~104 W
- batch 8: ~110 W

GPU utilization reached approximately 90-100% at higher batch sizes.

At batch sizes 6 and 8, power draw fluctuated substantially and Windows
reported increased shared GPU memory use. The batch-8 run reached
approximately 12 GB of shared GPU memory according to the observed
Windows GPU telemetry.

These power and shared-memory values were manually observed and should
be treated as exploratory evidence rather than final instrumented
measurements.

## Interpretation

Short-context inference scales nearly linearly through batch size 8.

At 4096 generated tokens, however, batch size 4 is the clear throughput
knee:

- batch 4: 87.93 aggregate tok/s
- batch 6: 42.79 aggregate tok/s
- batch 8: 21.52 aggregate tok/s

The sharp performance collapse above batch 4 coincides with rapidly
increasing memory reservation beyond the GPU's dedicated VRAM capacity
and increased shared-memory usage.

This behavior is consistent with GPU memory oversubscription / paging
becoming the dominant bottleneck.

## Current conclusion

Batch size 4 is the strongest candidate for long-context Qwen3-1.7B
inference on this RTX 5060 system.

Batch sizes 6 and 8 are unsuitable for long-context evaluation despite
higher short-context throughput.

The final evaluation batch size must still be validated at the frozen
8192-token generation ceiling before adoption.
