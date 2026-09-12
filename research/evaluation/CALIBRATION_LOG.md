# Qwen3 CE v0.1 Evaluation Calibration Log

Calibration uses the frozen validation split only.

No private evaluation records are used during calibration.

## CAL-001 — Initial output-budget smoke test

Configuration:

- model: Qwen/Qwen3-1.7B
- thinking mode: enabled
- seed: 17
- records: first 2 validation records
- max_new_tokens: 4096

Observed:

- record 000201: EOS at 2609 generated tokens
- record 000202: reached the 4096-token limit
- truncation: 1/2 records
- truncation rate: 50%
- record 000202 contained an opening `<think>` tag but no closing
  `</think>` tag
- therefore the model had not reached its final answer

Decision:

The 4096-token output budget is rejected for the v0.1 evaluation
protocol.

The validation-calibration budget is increased to 8192 tokens.

The response parser is also hardened so an unfinished thinking block
cannot be misclassified as a final answer.

The original smoke artifacts are retained as calibration evidence.

## CAL-002 — 8192-token follow-up

Configuration:

- model: Qwen/Qwen3-1.7B
- thinking mode: enabled
- seed: 17
- records: same first 2 validation records
- max_new_tokens: 8192

Observed:

- record 000201 again terminated normally at 2609 generated tokens
- record 000202 again reached the generation limit
- record 000202 never emitted a closing `</think>` tag
- no final answer was produced
- unfinished reasoning length: 34,312 characters
- duplicate 8-gram rate: 24.78%
- manual tail inspection showed repeated reformulation of the same
  overflow/parsing reasoning rather than clear forward progress

Decision:

Do not increase the benchmark output budget solely to accommodate this
record.

Record 000202 is treated as a candidate pathological-reasoning /
non-answer failure rather than evidence that 8192 tokens is inherently
insufficient.

The 8192-token limit remains the candidate calibration ceiling pending
a wider validation sample.

## CAL-003 — Wider 10-record validation calibration

Configuration:

- model: Qwen/Qwen3-1.7B
- thinking mode: enabled
- seed: 17
- records: first 10 validation records
- max_new_tokens: 8192

Observed:

- 8/10 records terminated normally with EOS
- 2/10 records reached the 8192-token generation limit
- both truncated records failed to emit a closing `</think>` tag
- neither truncated record produced a final answer

Truncated records:

### ce-systems-strtol-validation-000202

- duplicate 8-gram rate: 24.78%
- reasoning showed repeated reformulation of the same parsing and
  overflow-detection approach
- no completed final answer

### ce-reasoning-littles-law-000206

- duplicate 8-gram rate: 34.32%
- reasoning repeatedly recalculated and reconsidered the same
  Little's Law relationship
- the reasoning reached the value 20 but continued looping over units
  and alternative formulations
- no completed final answer

Decision:

The observed 8192-token failures are classified as pathological
reasoning / non-answer behavior rather than evidence that the output
budget is too small.

Do not increase the generation budget solely to accommodate these
failures.

8192 remains the candidate final generation ceiling pending the full
40-record validation calibration.
