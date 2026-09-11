# Dataset v0.1

## Purpose

Dataset v0.1 is the first pilot dataset for the project.

Its purpose is to validate the complete workflow before scaling:

- dataset design
- validation
- technical review
- fine-tuning
- baseline comparison
- regression testing

## Target

| Split | Records |
|---|---:|
| Train | 200 |
| Validation | 40 |
| Evaluation | 60 |
| **Total** | **300** |

The evaluation split must remain separate from training.

## Training Distribution

| Domain | Records |
|---|---:|
| Software engineering | 30 |
| Systems programming | 25 |
| Operating systems | 20 |
| Computer architecture | 20 |
| Embedded systems | 15 |
| Networking | 15 |
| Distributed systems | 15 |
| Linux and infrastructure | 20 |
| Compute and model infrastructure | 15 |
| Secure engineering | 10 |
| Engineering reasoning | 15 |
| **Total** | **200** |

## Quality Rules

Every accepted record must:

- pass the dataset schema
- have a unique ID
- be technically correct
- have verification status `verified`
- be relevant to the project scope
- provide useful training signal
- record its source
- avoid unnecessary duplication

Quality takes priority over reaching the target record count.

## Difficulty

The dataset will contain:

- basic
- intermediate
- advanced
- expert

Intermediate and advanced examples should form the majority.

## Task Types

The pilot should include a mixture of:

- debugging
- troubleshooting
- implementation
- code repair
- testing
- architecture analysis
- performance analysis
- failure analysis
- technical comparison
- engineering decisions

Realistic engineering scenarios are preferred over simple textbook questions.

## Baseline

Before fine-tuning, the original Qwen3 checkpoint must be evaluated on the same evaluation set used for the fine-tuned checkpoint.

Dataset v0.1 should tell us what improved, what regressed, and what should change before creating v0.2.

## Status

Planning.
