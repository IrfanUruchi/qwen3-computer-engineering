# EXP-001 Final Batch-2 Reproducibility Gate

## Purpose

Validate deterministic stochastic batch-size-2 inference using the
actual candidate 8192-token evaluation ceiling before running the full
validation split.

## Configuration

- Model: Qwen/Qwen3-1.7B
- Revision:
  70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
- GPU: NVIDIA GeForce RTX 5060
- Dtype: BF16
- Attention: SDPA
- Batch size: 2
- Run seed: 17
- Thinking mode: enabled
- Sampling: enabled
- Temperature: 0.6
- Top-p: 0.95
- Top-k: 20
- Maximum generated tokens: 8192
- Execution: two independent Python processes

## Run A

- records: 4
- batches: 2
- generated tokens: 13,414
- aggregate throughput: 40.10 tok/s
- truncated records: 0/4
- completed final answers: 4/4

## Run B

- records: 4
- batches: 2
- generated tokens: 13,414
- aggregate throughput: 37.88 tok/s
- truncated records: 0/4
- completed final answers: 4/4

## Token reproducibility

### ce-software-pagination-delete-000201

SHA-256:

72a53bed14d22e0c34b37f879e2d47fd1b60bd1edc82b05a503f67dc82a83e8e

Result: exact match

### ce-systems-strtol-validation-000202

SHA-256:

35934a3b281327bb1c13de6c5e99d10a4c8fb16fefec0c7a1c6dc132bdbf0019

Result: exact match

### ce-os-thread-stack-overflow-000203

SHA-256:

d18d3997164d4629fb10216b7d27280b4a7db56ef9a31c4c19ba9268f99c7f0b

Result: exact match

### ce-architecture-rob-latency-000204

SHA-256:

3b30246ed49441f995dc3bf4d60c7d372eca688d487c217bf0a3d2870fcfa5ac

Result: exact match

## Result

BATCH-2 REPRODUCIBILITY: PASS

Exact generated-token equality was observed across independent
processes for all four records.

## Methodological note

Batching changes the stochastic sampling trajectory relative to the
earlier single-sequence calibration runner because the random-number
stream and batch seed are different.

Therefore results produced by the earlier single-record runner must
not be mixed with results from the batch-2 protocol.

All baseline and fine-tuned comparisons using this protocol must use
the same:

- record ordering
- batch composition
- batch-size semantics
- seed derivation
- generation policy
- software/hardware environment where exact repeatability is claimed

The earlier single-record runs remain calibration evidence only.
