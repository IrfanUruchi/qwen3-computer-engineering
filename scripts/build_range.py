#!/usr/bin/env python3

import subprocess
import sys


if len(sys.argv) < 2:
    raise SystemExit(
        "usage: build_range.py <batch> [batch...]"
    )

batches = [int(x) for x in sys.argv[1:]]


def run(*cmd):
    print()
    print("$", " ".join(map(str, cmd)))

    subprocess.run(
        list(map(str, cmd)),
        check=True,
    )


for batch in batches:
    run(
        "python3",
        "scripts/generate_batch.py",
        batch,
    )

run(
    "python3",
    "scripts/run_verification.py",
    *batches,
)

for batch in batches:
    run(
        "python3",
        "scripts/append_records.py",
        f"data/raw/v0.1/staging-batch-{batch:03d}.json",
    )

run(
    "python3",
    "scripts/validate_dataset.py",
    "data/raw/v0.1/train.jsonl",
)

for batch in batches:
    run(
        "python3",
        "scripts/audit_batch.py",
        batch,
    )

print()
print("=" * 72)
print("BUILD RANGE: PASS")
print("Batches:", ", ".join(f"{b:03d}" for b in batches))
print("=" * 72)

import json
from pathlib import Path

dataset = Path("data/raw/v0.1/train.jsonl")

records = [
    json.loads(line)
    for line in dataset.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

print()
print("=" * 72)
print(f"TRAINING DATASET: {len(records)}/200")
print(f"PROGRESS:         {len(records) / 200 * 100:.1f}%")
print(f"LAST RECORD:      {records[-1]['id']}")
print("=" * 72)
