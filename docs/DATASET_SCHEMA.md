# Dataset Schema

Dataset records use JSON Lines (`.jsonl`).

Every record must conform to:

`configs/dataset-record.schema.json`

## Splits

- `train`
- `validation`
- `evaluation`

Evaluation data must remain separate from training data.

## Domains

The domain field follows the technical areas defined in `docs/SCOPE.md`.

The `subdomain` field provides a more specific classification without requiring a schema change.

## Verification

Every record must include a verification method and status.

Preferred verification methods include:

- unit tests
- compilation
- execution
- static analysis
- reference answers
- structured rubrics
- manual review

Records marked `rejected` must never be used for training.

## Sources

Every record must record its source type.

External material should include provenance and licensing information whenever available.

Synthetic examples are still required to meet the same technical-quality requirements as manually written examples.

## Rule

Passing the JSON schema is necessary but not sufficient.

A record must also be technically correct, useful, relevant, non-duplicative, and appropriately verified before entering a training dataset.
