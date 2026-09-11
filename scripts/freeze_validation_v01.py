#!/usr/bin/env python3

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TRAIN = ROOT / "data/raw/v0.1/train.jsonl"
VALIDATION = ROOT / "data/raw/v0.1/validation.jsonl"

TRAIN_MANIFEST = (
    ROOT / "configs/dataset-v0.1-train-freeze.json"
)

MANIFEST = (
    ROOT / "configs/dataset-v0.1-validation-freeze.json"
)

VERIFIER_DIR = (
    ROOT / "data/raw/v0.1/verification-validation"
)

LOG = (
    ROOT / "logs/v0.1-validation-freeze-verification.txt"
)

EXPECTED_DOMAINS = {
    "software-engineering": 6,
    "systems-programming": 5,
    "operating-systems": 4,
    "computer-architecture": 4,
    "embedded-systems": 3,
    "networking": 3,
    "distributed-systems": 3,
    "linux-infrastructure": 4,
    "compute-model-infrastructure": 3,
    "secure-engineering": 2,
    "engineering-reasoning": 3,
}


def fail(message):
    raise SystemExit(
        f"VALIDATION FREEZE FAILED: {message}"
    )


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def norm(text):
    return " ".join(
        text.split()
    ).casefold()


def message(record, role):
    return "\n".join(
        m["content"]
        for m in record["messages"]
        if m["role"] == role
    )


def duplicates(values):
    counts = Counter(values)
    return [
        value
        for value, count in counts.items()
        if count > 1
    ]


print("=" * 72)
print("QWEN3 CE — v0.1 VALIDATION FREEZE GATE")
print("=" * 72)

# ------------------------------------------------------------------
# Frozen training integrity
# ------------------------------------------------------------------

train_manifest = json.loads(
    TRAIN_MANIFEST.read_text(
        encoding="utf-8"
    )
)

train_sha = sha256(TRAIN)

if train_sha != train_manifest["sha256"]:
    fail(
        "frozen training SHA no longer matches "
        "training freeze manifest"
    )

print("Frozen train SHA:     PASS")

# ------------------------------------------------------------------
# Schema validation
# ------------------------------------------------------------------

result = subprocess.run(
    [
        sys.executable,
        "scripts/validate_dataset.py",
        "data/raw/v0.1/validation.jsonl",
    ],
    cwd=ROOT,
)

if result.returncode != 0:
    fail("schema/dataset validation")

validation = load_jsonl(VALIDATION)
train = load_jsonl(TRAIN)

# ------------------------------------------------------------------
# Core validation invariants
# ------------------------------------------------------------------

if len(validation) != 40:
    fail(
        f"expected 40 records, "
        f"found {len(validation)}"
    )

print("Record count:         PASS (40)")

suffixes = [
    int(record["id"][-6:])
    for record in validation
]

if suffixes != list(range(201, 241)):
    fail("expected exact ID sequence 000201–000240")

print("Sequential IDs:       PASS (000201–000240)")

if any(
    record["split"] != "validation"
    for record in validation
):
    fail("non-validation split found")

print("Split:                PASS")

if any(
    record["verification"]["status"]
    != "verified"
    for record in validation
):
    fail("unverified validation record found")

print("Verification status:  PASS (40 verified)")

domain_counts = Counter(
    record["domain"]
    for record in validation
)

if dict(domain_counts) != EXPECTED_DOMAINS:
    print("Expected:", EXPECTED_DOMAINS)
    print("Actual:  ", dict(domain_counts))
    fail("domain quotas")

print("Domain quotas:        PASS (EXACT)")

# ------------------------------------------------------------------
# Internal + cross-split collision checks
# ------------------------------------------------------------------

val_ids = [
    r["id"]
    for r in validation
]

val_prompts = [
    norm(message(r, "user"))
    for r in validation
]

val_answers = [
    norm(message(r, "assistant"))
    for r in validation
]

if duplicates(val_ids):
    fail("duplicate validation IDs")

if duplicates(val_prompts):
    fail("duplicate validation prompts")

if duplicates(val_answers):
    fail("duplicate validation answers")

print("Internal duplicates:  PASS (0)")

train_ids = {
    r["id"]
    for r in train
}

train_prompts = {
    norm(message(r, "user"))
    for r in train
}

train_answers = {
    norm(message(r, "assistant"))
    for r in train
}

if train_ids.intersection(val_ids):
    fail("train/validation ID collision")

if train_prompts.intersection(val_prompts):
    fail("train/validation prompt collision")

if train_answers.intersection(val_answers):
    fail("train/validation answer collision")

print("Cross-split IDs:      PASS")
print("Cross-split prompts:  PASS")
print("Cross-split answers:  PASS")

# ------------------------------------------------------------------
# Batch-plan alignment
# ------------------------------------------------------------------

for batch in range(1, 5):
    start = 201 + (batch - 1) * 10
    end = start + 9

    plan_path = (
        ROOT
        / "configs"
        / (
            "dataset-v0.1-validation-"
            f"batch-{batch:03d}.json"
        )
    )

    plan = json.loads(
        plan_path.read_text(
            encoding="utf-8"
        )
    )

    expected = {
        item["id"]: item
        for item in plan["records"]
    }

    records = [
        r
        for r in validation
        if start <= int(r["id"][-6:]) <= end
    ]

    if len(records) != 10:
        fail(
            f"batch {batch:03d}: "
            f"expected 10 records"
        )

    if {
        r["id"]
        for r in records
    } != set(expected):
        fail(
            f"batch {batch:03d}: "
            f"plan ID mismatch"
        )

    for record in records:
        plan_record = expected[record["id"]]

        actual = {
            "domain": record["domain"],
            "subdomain": record["subdomain"],
            "task_type": record["task_type"],
            "difficulty": record["difficulty"],
            "verification": (
                record["verification"]["method"]
            ),
        }

        for field, value in actual.items():
            if plan_record[field] != value:
                fail(
                    f"{record['id']}: "
                    f"{field} plan mismatch"
                )

    print(
        f"Validation Batch {batch:03d}: PASS"
    )

# ------------------------------------------------------------------
# All executable validation verifiers
# ------------------------------------------------------------------

paths = sorted(
    list(VERIFIER_DIR.glob("*_test.py"))
    + list(VERIFIER_DIR.glob("*_test.sh"))
)

if not paths:
    fail("no executable validation verifiers found")

LOG.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output = []

for path in paths:
    print(
        f"VERIFY: "
        f"{path.relative_to(ROOT)}"
    )

    if path.suffix == ".py":
        cmd = [
            sys.executable,
            "-u",
            str(path),
            "-v",
        ]
    else:
        cmd = [
            "bash",
            str(path),
        ]

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    output.append(
        f"\n{'=' * 72}\n"
        f"{path.relative_to(ROOT)}\n"
        f"{'=' * 72}\n"
        f"{result.stdout}"
        f"{result.stderr}"
    )

    if result.returncode != 0:
        LOG.write_text(
            "".join(output),
            encoding="utf-8",
        )

        print(result.stdout)
        print(
            result.stderr,
            file=sys.stderr,
        )

        fail(
            f"verifier failed: "
            f"{path.name}"
        )

LOG.write_text(
    "".join(output),
    encoding="utf-8",
)

print(
    "Executable verifiers: PASS "
    f"({len(paths)})"
)

# ------------------------------------------------------------------
# Freeze manifest
# ------------------------------------------------------------------

validation_sha = sha256(VALIDATION)

manifest = {
    "dataset_version": "0.1",
    "split": "validation",
    "records": 40,
    "id_range": [
        validation[0]["id"],
        validation[-1]["id"],
    ],
    "sha256": validation_sha,
    "train_sha256": train_sha,
    "domain_counts": dict(
        sorted(domain_counts.items())
    ),
    "difficulty_counts": dict(
        sorted(
            Counter(
                r["difficulty"]
                for r in validation
            ).items()
        )
    ),
    "task_type_counts": dict(
        sorted(
            Counter(
                r["task_type"]
                for r in validation
            ).items()
        )
    ),
    "verification_method_counts": dict(
        sorted(
            Counter(
                r["verification"]["method"]
                for r in validation
            ).items()
        )
    ),
    "verification_status": {
        "verified": 40,
    },
    "schema": (
        "configs/dataset-record.schema.json"
    ),
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
print("VALIDATION v0.1 FREEZE: PASS")
print("=" * 72)
print("Records:       40/40")
print("Progress:      100.0%")
print(f"SHA-256:       {validation_sha}")
print(f"Train SHA:     {train_sha}")
print(
    "Manifest:      "
    "configs/dataset-v0.1-validation-freeze.json"
)
print("Domain quotas: EXACT")
print("Batches:       001–004 PASS")
print("Status:        FROZEN CANDIDATE")
print("=" * 72)
