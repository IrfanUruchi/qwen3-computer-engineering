#!/usr/bin/env python3

import json
import re
import sys
from collections import Counter
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: audit_batch.py <batch-number>")

batch_num = f"{int(sys.argv[1]):03d}"

start = (int(batch_num) - 1) * 10 + 1
end = start + 9

dataset = Path("data/raw/v0.1/train.jsonl")
plan_path = Path(f"configs/dataset-v0.1-batch-{batch_num}.json")
review_path = Path(f"configs/dataset-v0.1-batch-{batch_num}-review.json")

records = [
    json.loads(x)
    for x in dataset.read_text(encoding="utf-8").splitlines()
    if x.strip()
]

plan = json.loads(plan_path.read_text(encoding="utf-8"))
if isinstance(plan, dict):
    plan_records = plan.get("records")
elif isinstance(plan, list):
    plan_records = plan
else:
    raise SystemExit(
        f"Unsupported batch-plan format: {type(plan).__name__}"
    )

if not isinstance(plan_records, list):
    raise SystemExit(
        "Batch plan must contain a records list"
    )

expected = {r["id"]: r for r in plan_records}

def num(record):
    match = re.search(r"(\d{6})$", record["id"])
    if not match:
        raise ValueError(record["id"])
    return int(match.group(1))

batch = sorted(
    [r for r in records if start <= num(r) <= end],
    key=num,
)

errors = []

if len(batch) != 10:
    errors.append(f"expected 10 records, got {len(batch)}")

if [num(r) for r in batch] != list(range(start, end + 1)):
    errors.append("ID sequence mismatch")

if {r["id"] for r in batch} != set(expected):
    errors.append("batch IDs do not match plan")

for r in batch:
    planned = expected.get(r["id"])

    if not planned:
        continue

    actual = (
        r["domain"],
        r["subdomain"],
        r["task_type"],
        r["difficulty"],
        r["verification"]["method"],
    )

    wanted = (
        planned["domain"],
        planned["subdomain"],
        planned["task_type"],
        planned["difficulty"],
        planned["verification"],
    )

    if actual != wanted:
        errors.append(f"plan mismatch: {r['id']}")

    if r["verification"]["status"] != "verified":
        errors.append(f"not verified: {r['id']}")

all_ids = [r["id"] for r in records]
prompts = [r["messages"][0]["content"].strip() for r in records]
answers = [r["messages"][-1]["content"].strip() for r in records]

dup_ids = sum(v > 1 for v in Counter(all_ids).values())
dup_prompts = sum(v > 1 for v in Counter(prompts).values())
dup_answers = sum(v > 1 for v in Counter(answers).values())

difficulty = Counter(r["difficulty"] for r in batch)
verification = Counter(r["verification"]["method"] for r in batch)
domains = Counter(r["domain"] for r in batch)
tasks = Counter(r["task_type"] for r in batch)

if dup_ids:
    errors.append("duplicate IDs")
if dup_prompts:
    errors.append("duplicate prompts")
if dup_answers:
    errors.append("duplicate answers")

print("=" * 72)
print(f"BATCH {batch_num} AUDIT")
print("=" * 72)
print("Range:            ", f"{start:06d}-{end:06d}")
print("Records:          ", len(batch))
print("Unique domains:   ", len(domains))
print("Difficulty:       ", dict(difficulty))
print("Verification:     ", dict(verification))
print("Task types:       ", dict(tasks))
print("Duplicate IDs:    ", dup_ids)
print("Duplicate prompts:", dup_prompts)
print("Duplicate answers:", dup_answers)

if errors:
    print("\nRESULT: FAIL")
    for e in errors:
        print("-", e)
    raise SystemExit(1)

review = {
    "batch": batch_num,
    "dataset_version": "0.1",
    "records": 10,
    "status": "reviewed",
    "result": "pass",
    "range": {
        "first": batch[0]["id"],
        "last": batch[-1]["id"],
    },
    "findings": {
        "unique_ids": True,
        "plan_alignment": True,
        "all_verified": True,
        "exact_prompt_duplicates": 0,
        "exact_answer_duplicates": 0,
        "unique_domains": len(domains),
    },
    "difficulty": dict(sorted(difficulty.items())),
    "verification": dict(sorted(verification.items())),
    "task_types": dict(sorted(tasks.items())),
}

review_path.write_text(
    json.dumps(review, indent=2) + "\n",
    encoding="utf-8",
)

print("\nRESULT: PASS")
print("Review:", review_path)
