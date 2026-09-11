#!/usr/bin/env python3

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/raw/v0.1/train.jsonl"
MANIFEST = ROOT / "configs/dataset-v0.1-train-freeze.json"
LOG_DIR = ROOT / "logs"

EXPECTED_DOMAINS = {
    "software-engineering": 30,
    "systems-programming": 25,
    "operating-systems": 20,
    "computer-architecture": 20,
    "embedded-systems": 15,
    "networking": 15,
    "distributed-systems": 15,
    "linux-infrastructure": 20,
    "compute-model-infrastructure": 15,
    "secure-engineering": 10,
    "engineering-reasoning": 15,
}


def fail(message):
    raise SystemExit(f"FREEZE GATE FAILED: {message}")


def run(cmd, capture=False):
    print("$", " ".join(map(str, cmd)))

    result = subprocess.run(
        list(map(str, cmd)),
        cwd=ROOT,
        text=True,
        capture_output=capture,
    )

    if result.returncode != 0:
        if capture:
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

        fail(f"command returned {result.returncode}")

    return result


def norm(text):
    return " ".join(text.split()).casefold()


def message_text(record, role):
    return "\n".join(
        m["content"]
        for m in record["messages"]
        if m["role"] == role
    )


print("=" * 72)
print("QWEN3 COMPUTER ENGINEERING — v0.1 TRAIN FREEZE GATE")
print("=" * 72)

if not DATASET.exists():
    fail(f"missing dataset: {DATASET}")

# ---------------------------------------------------------------------
# 1. Existing schema/dataset validator
# ---------------------------------------------------------------------

run([
    sys.executable,
    "scripts/validate_dataset.py",
    "data/raw/v0.1/train.jsonl",
])

# ---------------------------------------------------------------------
# 2. Load corpus
# ---------------------------------------------------------------------

records = [
    json.loads(line)
    for line in DATASET.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

if len(records) != 200:
    fail(f"expected 200 records, found {len(records)}")

print()
print("Record count:       PASS (200)")

# ---------------------------------------------------------------------
# 3. Exact domain quotas
# ---------------------------------------------------------------------

domain_counts = Counter(r["domain"] for r in records)

if dict(domain_counts) != EXPECTED_DOMAINS:
    print("Expected domains:", EXPECTED_DOMAINS)
    print("Actual domains:  ", dict(domain_counts))
    fail("domain distribution mismatch")

print("Domain quotas:      PASS")

# ---------------------------------------------------------------------
# 4. Sequential IDs 000001..000200
# ---------------------------------------------------------------------

suffixes = []

for record in records:
    match = re.search(r"-(\d{6})$", record["id"])

    if not match:
        fail(f"ID lacks numeric suffix: {record['id']}")

    suffixes.append(int(match.group(1)))

expected_suffixes = list(range(1, 201))

if suffixes != expected_suffixes:
    fail("records are not ordered exactly 000001..000200")

print("Sequential IDs:     PASS (000001–000200)")

# ---------------------------------------------------------------------
# 5. Split / version / verification status
# ---------------------------------------------------------------------

split_counts = Counter(r["split"] for r in records)

if split_counts != Counter({"train": 200}):
    fail(f"unexpected split counts: {dict(split_counts)}")

status_counts = Counter(
    r["verification"]["status"]
    for r in records
)

if status_counts != Counter({"verified": 200}):
    fail(
        "not every record has verification.status=verified: "
        f"{dict(status_counts)}"
    )

versions = Counter(str(r["version"]) for r in records)

if len(versions) != 1:
    fail(f"mixed record versions: {dict(versions)}")

print("Split:              PASS (train only)")
print("Verification state: PASS (200 verified)")
print(
    "Record version:     PASS "
    f"({next(iter(versions))})"
)

# ---------------------------------------------------------------------
# 6. Global duplicate checks, normalized for whitespace/case
# ---------------------------------------------------------------------

ids = [r["id"] for r in records]

prompts = [
    norm(message_text(r, "user"))
    for r in records
]

answers = [
    norm(message_text(r, "assistant"))
    for r in records
]


def duplicate_values(values):
    counts = Counter(values)
    return [
        value
        for value, count in counts.items()
        if count > 1
    ]


dup_ids = duplicate_values(ids)
dup_prompts = duplicate_values(prompts)
dup_answers = duplicate_values(answers)

if dup_ids:
    fail(f"duplicate IDs: {dup_ids}")

if dup_prompts:
    fail(
        f"normalized duplicate prompts found: "
        f"{len(dup_prompts)}"
    )

if dup_answers:
    fail(
        f"normalized duplicate answers found: "
        f"{len(dup_answers)}"
    )

print("Duplicate IDs:      PASS (0)")
print("Duplicate prompts:  PASS (0 normalized)")
print("Duplicate answers:  PASS (0 normalized)")

# ---------------------------------------------------------------------
# 7. Rerun ALL discovered executable verifiers
# ---------------------------------------------------------------------

print()
print("=" * 72)
print("EXECUTABLE VERIFICATION — BATCHES 001–020")
print("=" * 72)

LOG_DIR.mkdir(exist_ok=True)

verify_cmd = [
    sys.executable,
    "scripts/run_verification.py",
    *[str(i) for i in range(1, 21)],
]

verify_result = run(
    verify_cmd,
    capture=True,
)

verify_log = LOG_DIR / "v0.1-train-freeze-verification.txt"

verify_log.write_text(
    verify_result.stdout + verify_result.stderr,
    encoding="utf-8",
)

verify_lines = [
    line
    for line in verify_result.stdout.splitlines()
    if line.strip()
]

if verify_lines:
    print(verify_lines[-1])

print(
    "Verification log:  ",
    verify_log.relative_to(ROOT),
)

# ---------------------------------------------------------------------
# 8. Rerun all 20 batch audits
# ---------------------------------------------------------------------

print()
print("=" * 72)
print("BATCH AUDITS — 001–020")
print("=" * 72)

audit_log_parts = []

for batch in range(1, 21):
    result = run(
        [
            sys.executable,
            "scripts/audit_batch.py",
            batch,
        ],
        capture=True,
    )

    audit_log_parts.append(result.stdout)
    audit_log_parts.append(result.stderr)

    if "RESULT: PASS" not in result.stdout:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        fail(f"Batch {batch:03d} did not report PASS")

    print(f"BATCH {batch:03d}: PASS")

audit_log = LOG_DIR / "v0.1-train-freeze-audits.txt"

audit_log.write_text(
    "\n".join(audit_log_parts),
    encoding="utf-8",
)

print(
    "Audit log:         ",
    audit_log.relative_to(ROOT),
)

# ---------------------------------------------------------------------
# 9. Corpus SHA-256 + deterministic freeze manifest
# ---------------------------------------------------------------------

sha256 = hashlib.sha256(
    DATASET.read_bytes()
).hexdigest()

difficulty_counts = Counter(
    r["difficulty"]
    for r in records
)

task_counts = Counter(
    r["task_type"]
    for r in records
)

verification_counts = Counter(
    r["verification"]["method"]
    for r in records
)

source_counts = Counter(
    r["source"]["type"]
    for r in records
)

manifest = {
    "dataset_version": "0.1",
    "split": "train",
    "records": len(records),
    "id_range": [
        records[0]["id"],
        records[-1]["id"],
    ],
    "sha256": sha256,
    "domain_counts": dict(
        sorted(domain_counts.items())
    ),
    "difficulty_counts": dict(
        sorted(difficulty_counts.items())
    ),
    "task_type_counts": dict(
        sorted(task_counts.items())
    ),
    "verification_method_counts": dict(
        sorted(verification_counts.items())
    ),
    "source_type_counts": dict(
        sorted(source_counts.items())
    ),
    "verification_status": {
        "verified": 200,
    },
    "schema": "configs/dataset-record.schema.json",
}

MANIFEST.write_text(
    json.dumps(
        manifest,
        indent=2,
        sort_keys=True,
    ) + "\n",
    encoding="utf-8",
)

print()
print("=" * 72)
print("TRAIN v0.1 FREEZE: PASS")
print("=" * 72)
print(f"Records:       {len(records)}/200")
print("Progress:      100.0%")
print(f"SHA-256:       {sha256}")
print(
    "Manifest:      ",
    MANIFEST.relative_to(ROOT),
)
print("Domain quotas: EXACT")
print("Batches:       001–020 PASS")
print("Duplicates:    0")
print("Status:        FROZEN CANDIDATE")
print("=" * 72)
