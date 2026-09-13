# EXP-001 Batch-2 Stochastic Reproducibility

## Purpose

Determine whether stochastic batch-size-2 inference is exactly
repeatable under the frozen EXP-001 evaluation environment before
allowing batched generation into the benchmark harness.

## Configuration

- Model: Qwen/Qwen3-1.7B
- Revision:
  70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
- Batch size: 2
- Seed: 17
- Thinking mode: enabled
- do_sample: true
- temperature: 0.6
- top-p: 0.95
- top-k: 20
- max_new_tokens: 2048
- dtype: BF16
- attention: SDPA
- GPU: NVIDIA GeForce RTX 5060
- execution: two independent Python processes

Records:

- ce-software-pagination-delete-000201
- ce-os-thread-stack-overflow-000203

## Run A

- elapsed: 84.90 s
- aggregate throughput: 48.25 tok/s
- peak CUDA allocated: 3.72 GiB
- batch token SHA-256:
  9c207065c840046e696f19e36f98c9fbef0db6ac40de65f0668d7d3624512bbd

Record token SHA-256:

- 000201:
  fa5ec8e46b90488e0c9b47d039d0aaba55ddecff4f4c35023072e859500f5ce6
- 000203:
  07f44e00b7b4f12a55eae9cea57cdbb2e2d03b2cddbb06d145c33fa2c8acdddc

## Run B

- elapsed: 80.69 s
- aggregate throughput: 50.76 tok/s
- peak CUDA allocated: 3.72 GiB
- batch token SHA-256:
  9c207065c840046e696f19e36f98c9fbef0db6ac40de65f0668d7d3624512bbd

Record token SHA-256:

- 000201:
  fa5ec8e46b90488e0c9b47d039d0aaba55ddecff4f4c35023072e859500f5ce6
- 000203:
  07f44e00b7b4f12a55eae9cea57cdbb2e2d03b2cddbb06d145c33fa2c8acdddc

## Result

Exact generated-token equality was observed across the two independent
processes for both individual records and the complete batch.

Status:

EXACT STOCHASTIC REPRODUCIBILITY: PASS

## Scope

This result establishes repeatability for the frozen EXP-001 Eagle
environment.

It does not assert bit-exact reproducibility across different GPU
architectures, drivers, CUDA versions, PyTorch versions, or other
software environments.

## Decision

Batch size 2 is eligible for integration into the EXP-001 evaluator,
provided that:

- record ordering is fixed
- batch composition is fixed
- batch seeding is deterministic
- resume occurs only at completed batch boundaries
- baseline and fine-tuned models use identical batching semantics
