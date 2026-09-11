# Qwen3 CE v0.1 Generation Policy

## Purpose

Define inference behavior before private evaluation so baseline and
fine-tuned models are compared under the same generation protocol.

## Primary mode

Qwen3 thinking mode is enabled.

The initial sampling configuration follows the upstream Qwen3
recommendation:

- temperature: 0.6
- top-p: 0.95
- top-k: 20
- min-p: 0
- sampling enabled

Greedy decoding is not used.

## Seeds

The fixed experiment seeds are:

- 17
- 42
- 2026

Every compared model will use the same seed set.

## Output budget

Initial validation calibration uses:

- max_new_tokens: 4096

This limit may be changed only while developing the evaluator against
the validation split.

Before any private evaluation is executed, the generation policy will
be frozen.

After private evaluation begins, the policy must not be modified in
response to evaluation results.

## Prompt policy

Dataset user/system messages are passed through the model's native chat
template.

No extra performance-oriented prompt is added.

Reference answers and verification rubrics are never provided to the
model.

## Measurements

Every generation run should preserve:

- model revision
- dataset split and SHA-256
- seed
- input token count
- generated token count
- elapsed generation time
- tokens per second
- truncation status
- raw model response
- extracted final response where applicable
