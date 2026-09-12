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
