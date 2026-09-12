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

## 8192-token long-context stress test

The final evaluation candidate ceiling of 8192 generated tokens was
used to test long-context batching.

### Batch size 2

- aggregate throughput: 38.42 tok/s
- per-sequence throughput: 19.21 tok/s
- peak CUDA allocated memory: 5.13 GiB
- peak CUDA reserved memory: 6.59 GiB
- status: PASS

The batch completed normally.

### Batch size 4

The batch-size-4 run did not complete after more than one hour and was
manually terminated.

For comparison, a healthy batch-size-2 run completed the same
8192-token-per-sequence stress test in approximately seven minutes.

The extreme slowdown at batch size 4 is consistent with the memory
pressure observed in the 4096-token sweep becoming substantially worse
at 8192 tokens.

### Long-context conclusion

Batch-size optimum is strongly sequence-length dependent:

- 1024 tokens: batch 8 produced the highest tested throughput
- 4096 tokens: batch 4 produced the highest tested throughput
- 8192 tokens: batch 2 remained stable while batch 4 became impractical

This demonstrates a clear throughput/memory operating-point shift as
KV-cache requirements increase.

Batch size 2 is currently the safe candidate for the final 8192-token
evaluation workload.

### Batch size 3 at 8192 tokens

A separate batch-size-3 stress test was executed with a hard
20-minute timeout.

The run did not complete within 20 minutes and was interrupted while
executing a Qwen3 decoder-layer forward pass.

Status:

- batch size: 3
- generated-token target per sequence: 8192
- completion: NO
- timeout: 20 minutes
- process exit code: 124

Together with the batch-size-4 run, which remained incomplete after
more than one hour, this establishes a sharp long-context operating
boundary on the tested RTX 5060 system.

### Final long-context batching conclusion

At the 8192-token evaluation ceiling:

- batch 2: practical and stable
- batch 3: impractical (>20-minute timeout)
- batch 4: impractical (>60 minutes)

Batch size 2 is therefore the selected practical long-context batch
size for further evaluation-engineering work on this system.

This result also demonstrates that the throughput-optimal batch size
decreases substantially as generated sequence length increases.
