# Qwen3 Computer Engineering — Research Paper

This directory contains the paper-facing documentation for the
Qwen3 Computer Engineering research project.

The authoritative experimental evidence is stored under `research/`.

## Current dataset milestone

Dataset version: v0.1

- Training: 200 records
- Validation: 40 records
- Private evaluation: 60 records
- Total: 300 records

The evaluation split remains private and is not committed publicly.

## Research principles

- Freeze datasets before training.
- Preserve exact dataset hashes.
- Preserve model and checkpoint revisions.
- Record Git commit for every experiment.
- Record hardware and software environment.
- Record random seeds and generation/training configuration.
- Select checkpoints using validation only.
- Keep final evaluation held out.
- Preserve negative and failed experiments.
- Report per-domain, per-task, and per-difficulty results.
- Prefer reproducible evidence over manually reconstructed results.
