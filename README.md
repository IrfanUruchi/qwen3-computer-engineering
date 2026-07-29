# Qwen3 Computer Engineering

A practical fine-tuning project focused on computer engineering, software systems, infrastructure, and technical problem-solving.

The work will begin with smaller Qwen3 checkpoints and scale only after the dataset, training setup, and evaluation process are proven to work reliably.

> **Status:** Early development  
> **Target window for the 235B-A22B release:** January–March 2027

## Scope

The project is focused on technical work across:

- Software engineering
- Systems programming
- Operating systems
- Computer architecture
- Distributed systems
- Networking
- Linux, containers, and virtualization
- GPU and multi-GPU computing
- Model training and inference infrastructure
- Debugging, testing, and secure development
- Engineering design and technical decision-making

The project is based on Qwen3 pretrained checkpoints. It does not introduce a new model architecture and does not claim pretraining from scratch.

## Development approach

The project will be developed in stages.

| Stage | Model size | Main purpose |
|---|---:|---|
| Initial experiments | 1B–3B | Validate the dataset, training pipeline, and evaluation setup |
| Intermediate models | 4B–8B | Improve quality, coverage, and reliability |
| Large-model validation | 30B-class | Test distributed and mixture-of-experts fine-tuning |
| Flagship | 235B-A22B | Final large-scale release |

A larger checkpoint will only be used when the previous stage produces clear and repeatable improvements.

The goal is not to reach 235B as quickly as possible. The goal is to reach it with a training process that has already been tested properly.

## Dataset

The dataset will be built and reviewed throughout development.

Planned task types include:

- Code generation and repair
- Debugging
- Systems design
- Architecture analysis
- Operating-system problems
- Distributed-system scenarios
- Infrastructure troubleshooting
- Computer architecture
- Testing and verification
- Engineering trade-off analysis

The dataset will be evaluated for:

- Technical correctness
- Difficulty
- Coverage
- Clarity
- Uniqueness
- Executability
- Licensing and provenance
- Benchmark contamination

Training and evaluation data will remain separate.

## Evaluation

Each fine-tuned model will be compared with its original Qwen3 checkpoint.

Evaluation will include:

- Code correctness
- Compilation and unit-test results
- Debugging accuracy
- Systems reasoning
- Technical instruction following
- Architecture decisions
- General capability retention
- Error and hallucination analysis

Where possible, tasks will be verified through unit tests, compilation checks, static analysis, or reproducible execution environments.

## Roadmap

### Phase 1 — Preparation

- Define the main technical domains
- Finalize the dataset format
- Build the first evaluation set
- Establish baseline Qwen3 results
- Prepare reproducible training environments

### Phase 2 — Small models

- Fine-tune the first 1B–3B checkpoint
- Compare training configurations
- Measure improvements and regressions
- Expand and clean the dataset

### Phase 3 — Intermediate models

- Train 4B and 8B variants
- Increase dataset size and difficulty
- Improve evaluation coverage
- Publish checkpoints and technical results

### Phase 4 — Large-model validation

- Test distributed training
- Validate mixture-of-experts fine-tuning
- Identify memory, networking, storage, and training bottlenecks
- Prepare the final training pipeline

### Phase 5 — 235B-A22B

The current target window is:

> **January–March 2027**

This is a target window rather than a fixed deadline.

The release may happen earlier if the dataset, training, evaluation, and documentation are ready. If a major bottleneck appears, the work will continue until the model is ready rather than being released only to meet a date.

## Repository structure

```text
configs/        Training and evaluation configurations
data/           Dataset schemas and preparation tools
docs/           Development notes and technical reports
evaluation/     Benchmarks, tests, and scoring tools
scripts/        Training and utility scripts
src/            Project source code
tests/          Automated tests
```

The structure may change as the project develops.

## Releases

Model checkpoints are expected to be published on Hugging Face.

Each release will include:

- Base checkpoint
- Training configuration
- Dataset summary
- Evaluation results
- Known limitations
- Inference instructions
- Licensing information

This repository will remain the main development and documentation repository.

## Attribution

This project uses Qwen3 pretrained models developed by the Qwen team.

Each release will preserve the attribution and licensing requirements of its upstream checkpoint. Training code, datasets, adapters, evaluation tools, and model weights may use separate licenses.

## Current status

Work is currently focused on the dataset, evaluation setup, and initial small-model experiments.
