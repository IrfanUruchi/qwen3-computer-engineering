# EXP-001 — Qwen3 1.7B Baseline

## Objective

Measure the untouched Qwen3 1.7B checkpoint on the frozen
Qwen3 Computer Engineering v0.1 benchmark before any CE fine-tuning.

## Frozen dataset

- Train: 200 records
- Validation: 40 records
- Private evaluation: 60 records

Dataset hashes are recorded in `run-manifest.json`.

## Rules

1. No CE fine-tuning before baseline completion.
2. Generation configuration is frozen before final evaluation.
3. Harness development and debugging use validation only.
4. Private evaluation is not used for prompt engineering,
   checkpoint selection, or hyperparameter tuning.
5. Per-record private evaluation prompts/responses remain uncommitted.
6. Aggregate results may be recorded for later paper analysis.
7. Any failed or interrupted baseline run is preserved as such.

## Metrics

Report:

- overall score
- score by domain
- score by task type
- score by difficulty
- executable verification pass rate
- rubric/reference-answer score
- refusal or non-answer rate
- runtime and generation throughput where available

## Comparison target

This run becomes the fixed baseline against which the first
Qwen3-CE 1.7B v0.1 fine-tune will be compared.
