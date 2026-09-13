# WSL Automatic Memory Reclaim — Paired Inference Observation

## Purpose

During EXP-001 validation calibration, a partial seed-42 run was executed before changing the WSL automatic-memory-reclaim policy. The run was interrupted after seven completed batches. WSL automatic memory reclaim was then disabled, WSL was fully shut down and restarted, and seed 42 was restarted from batch 0.

Because deterministic batch-level seeding produced identical generation lengths for the first seven batches, these runs provide a useful paired timing observation.

This is an opportunistic systems observation, not a controlled causal benchmark.

## Configuration held constant

- Model: `Qwen/Qwen3-1.7B`
- Revision: `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`
- Seed: `42`
- Batch size: `2`
- Thinking: enabled
- Maximum new tokens: `8192`
- Dtype: `torch.bfloat16`
- Device: RTX 5060 / `cuda:0`
- Evaluation order and batch membership unchanged

The compared seven batches generated exactly 53,075 tokens in both runs.

## Results

| Batch | Earlier run tok/s | Reclaim disabled tok/s |
|---|---:|---:|
| 000 | 32.26 | 30.54 |
| 001 | 46.28 | 43.23 |
| 002 | 25.78 | 24.15 |
| 003 | 44.66 | 42.72 |
| 004 | 26.02 | 24.25 |
| 005 | 40.53 | 37.34 |
| 006 | 25.39 | 25.29 |

Aggregate over the matched seven batches:

- Generated tokens: 53,075 in each run
- Earlier-policy measured time: 1,752.34 s
- Reclaim-disabled measured time: 1,846.83 s
- Earlier-policy aggregate throughput: 30.29 tok/s
- Reclaim-disabled aggregate throughput: 28.74 tok/s
- Reclaim-disabled wall time was approximately 5.39% higher
- Reclaim-disabled aggregate throughput was approximately 5.12% lower

## Interpretation

The observation does not support the initial hypothesis that WSL automatic memory reclaim was responsible for the poor long-context Qwen3 generation throughput.

Disabling reclaim did not improve inference throughput in this paired observation and coincided with somewhat lower throughput.

A causal performance claim must not be made from this comparison because the WSL VM was restarted and uncontrolled factors such as GPU temperature, boost state, Windows host activity, driver state, and other runtime variation may have differed between runs.

The principal long-context throughput behavior remains more consistent with autoregressive generation cost, sequence-length-dependent KV/memory pressure, and stochastic variation in reasoning length.

The reclaim-disabled setting may still be useful operationally for predictable Linux memory residency; that is separate from GPU inference throughput.
