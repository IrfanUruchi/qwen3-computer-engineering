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
EVALUATION = ROOT / "data/raw/v0.1/evaluation.jsonl"

TRAIN_MANIFEST = ROOT / "configs/dataset-v0.1-train-freeze.json"
VALIDATION_MANIFEST = ROOT / "configs/dataset-v0.1-validation-freeze.json"

# Intentionally ignored by Git: evaluation remains private.
MANIFEST = ROOT / "configs/dataset-v0.1-evaluation-freeze.json"

VERIFIER_DIR = ROOT / "data/raw/v0.1/verification-evaluation"
LOG = ROOT / "logs/v0.1-evaluation-freeze-verification.txt"

EXPECTED_DOMAINS = {
    "software-engineering": 9,
    "systems-programming": 8,
    "operating-systems": 6,
    "computer-architecture": 6,
    "embedded-systems": 5,
    "networking": 5,
    "distributed-systems": 4,
    "linux-infrastructure": 6,
    "compute-model-infrastructure": 4,
    "secure-engineering": 3,
    "engineering-reasoning": 4,
}


def fail(message):
    raise SystemExit(
        f"EVALUATION FREEZE FAILED: {message}"
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
    return " ".join(text.split()).casefold()


def message(record, role):
    return "\n".join(
        m["content"]
        for m in record["messages"]
        if m["role"] == role
    )


def duplicate_values(values):
    counts = Counter(values)
    return [
        value
        for value, count in counts.items()
        if count > 1
    ]


print("=" * 72)
print("QWEN3 CE — v0.1 PRIVATE EVALUATION FREEZE GATE")
print("=" * 72)

# ------------------------------------------------------------------
# 1. Prove frozen train + validation did not change
# ------------------------------------------------------------------

train_manifest = json.loads(
    TRAIN_MANIFEST.read_text(encoding="utf-8")
)

validation_manifest = json.loads(
    VALIDATION_MANIFEST.read_text(encoding="utf-8")
)

train_sha = sha256(TRAIN)
validation_sha = sha256(VALIDATION)

if train_sha != train_manifest["sha256"]:
    fail("training corpus no longer matches freeze manifest")

if validation_sha != validation_manifest["sha256"]:
    fail("validation corpus no longer matches freeze manifest")

if validation_manifest["train_sha256"] != train_sha:
    fail("validation freeze was not tied to current frozen train")

print("Frozen train SHA:      PASS")
print("Frozen validation SHA: PASS")

# ------------------------------------------------------------------
# 2. Schema / dataset validation
# ------------------------------------------------------------------

result = subprocess.run(
    [
        sys.executable,
        "scripts/validate_dataset.py",
        "data/raw/v0.1/evaluation.jsonl",
    ],
    cwd=ROOT,
)

if result.returncode != 0:
    fail("evaluation schema/dataset validation")

train = load_jsonl(TRAIN)
validation = load_jsonl(VALIDATION)
evaluation = load_jsonl(EVALUATION)

if len(evaluation) != 60:
    fail(
        f"expected 60 evaluation records, "
        f"found {len(evaluation)}"
    )

print("Record count:          PASS (60)")

# ------------------------------------------------------------------
# 3. Exact global ID range
# ------------------------------------------------------------------

suffixes = [
    int(record["id"][-6:])
    for record in evaluation
]

if suffixes != list(range(241, 301)):
    fail("expected exact ID sequence 000241–000300")

print("Sequential IDs:        PASS (000241–000300)")

# ------------------------------------------------------------------
# 4. Split/status/domain invariants
# ------------------------------------------------------------------

if any(
    record["split"] != "evaluation"
    for record in evaluation
):
    fail("non-evaluation record found")

print("Split:                 PASS")

if any(
    record["verification"]["status"] != "verified"
    for record in evaluation
):
    fail("unverified evaluation record found")

print("Verification status:   PASS (60 verified)")

domain_counts = Counter(
    record["domain"]
    for record in evaluation
)

if dict(domain_counts) != EXPECTED_DOMAINS:
    print("Expected:", EXPECTED_DOMAINS)
    print("Actual:  ", dict(domain_counts))
    fail("evaluation domain quota mismatch")

print("Domain quotas:         PASS (EXACT)")

# ------------------------------------------------------------------
# 5. Internal duplicate checks
# ------------------------------------------------------------------

eval_ids = [
    r["id"]
    for r in evaluation
]

eval_prompts = [
    norm(message(r, "user"))
    for r in evaluation
]

eval_answers = [
    norm(message(r, "assistant"))
    for r in evaluation
]

if duplicate_values(eval_ids):
    fail("duplicate evaluation IDs")

if duplicate_values(eval_prompts):
    fail("duplicate evaluation prompts")

if duplicate_values(eval_answers):
    fail("duplicate evaluation answers")

print("Internal duplicates:   PASS (0)")

# ------------------------------------------------------------------
# 6. Full 300-record cross-split collision check
# ------------------------------------------------------------------

all_records = train + validation + evaluation

all_ids = [
    r["id"]
    for r in all_records
]

all_prompts = [
    norm(message(r, "user"))
    for r in all_records
]

all_answers = [
    norm(message(r, "assistant"))
    for r in all_records
]

if duplicate_values(all_ids):
    fail("global duplicate IDs")

if duplicate_values(all_prompts):
    fail("global normalized prompt collision")

if duplicate_values(all_answers):
    fail("global normalized answer collision")

print("Global IDs:            PASS (300 unique)")
print("Global prompts:        PASS (300 unique)")
print("Global answers:        PASS (300 unique)")

# ------------------------------------------------------------------
# 7. Exact global split structure
# ------------------------------------------------------------------

if len(train) != 200:
    fail("training count changed")

if len(validation) != 40:
    fail("validation count changed")

if len(all_records) != 300:
    fail("global corpus count is not 300")

global_suffixes = [
    int(r["id"][-6:])
    for r in all_records
]

if global_suffixes != list(range(1, 301)):
    fail("global corpus is not exactly 000001–000300")

print("Global corpus:         PASS (300/300)")
print("Global ID range:       PASS (000001–000300)")

# ------------------------------------------------------------------
# 8. Batch-plan alignment: evaluation batches 001–006
# ------------------------------------------------------------------

for batch in range(1, 7):
    start = 241 + (batch - 1) * 10
    end = start + 9

    plan_path = (
        ROOT
        / "configs"
        / (
            "dataset-v0.1-evaluation-"
            f"batch-{batch:03d}.json"
        )
    )

    plan = json.loads(
        plan_path.read_text(encoding="utf-8")
    )

    expected = {
        item["id"]: item
        for item in plan["records"]
    }

    records = [
        r
        for r in evaluation
        if start <= int(r["id"][-6:]) <= end
    ]

    if len(records) != 10:
        fail(
            f"evaluation batch {batch:03d}: "
            "record count mismatch"
        )

    if {
        r["id"]
        for r in records
    } != set(expected):
        fail(
            f"evaluation batch {batch:03d}: "
            "plan ID mismatch"
        )

    for record in records:
        planned = expected[record["id"]]

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
            if planned[field] != value:
                fail(
                    f"{record['id']}: "
                    f"{field} plan mismatch"
                )

    print(
        f"Evaluation Batch {batch:03d}: PASS"
    )

# ------------------------------------------------------------------
# 9. Re-run every private executable verifier
# ------------------------------------------------------------------

paths = sorted(
    list(VERIFIER_DIR.glob("*_test.py"))
    + list(VERIFIER_DIR.glob("*_test.sh"))
)

if not paths:
    fail("no private evaluation verifiers found")

LOG.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output = []

for path in paths:
    print(
        f"VERIFY: {path.relative_to(ROOT)}"
    )

    if path.suffix == ".py":
        cmd = [
            sys.executable,
            "-u",
            str(path),
            "-v",
        ]
    elif path.suffix == ".sh":
        cmd = [
            "bash",
            str(path),
        ]
    else:
        fail(f"unsupported verifier: {path}")

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
            f"verifier failed: {path.name}"
        )

LOG.write_text(
    "".join(output),
    encoding="utf-8",
)

print(
    f"Executable verifiers:  PASS ({len(paths)})"
)

# ------------------------------------------------------------------
# 10. Private evaluation freeze manifest
# ------------------------------------------------------------------

evaluation_sha = sha256(EVALUATION)

manifest = {
    "dataset_version": "0.1",
    "split": "evaluation",
    "private": True,
    "records": 60,
    "id_range": [
        evaluation[0]["id"],
        evaluation[-1]["id"],
    ],
    "sha256": evaluation_sha,
    "train_sha256": train_sha,
    "validation_sha256": validation_sha,
    "domain_counts": dict(
        sorted(domain_counts.items())
    ),
    "difficulty_counts": dict(
        sorted(
            Counter(
                r["difficulty"]
                for r in evaluation
            ).items()
        )
    ),
    "task_type_counts": dict(
        sorted(
            Counter(
                r["task_type"]
                for r in evaluation
            ).items()
        )
    ),
    "verification_method_counts": dict(
        sorted(
            Counter(
                r["verification"]["method"]
                for r in evaluation
            ).items()
        )
    ),
    "verification_status": {
        "verified": 60,
    },
    "global_corpus_records": 300,
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
print("PRIVATE EVALUATION v0.1 FREEZE: PASS")
print("=" * 72)
print("Evaluation:    60/60")
print("Dataset:       300/300")
print("Progress:      100.0%")
print(f"Eval SHA-256:  {evaluation_sha}")
print(f"Train SHA:     {train_sha}")
print(f"Val SHA:       {validation_sha}")
print("Domain quotas: EXACT")
print("Batches:       001–006 PASS")
print("Collisions:    0")
print("Status:        FROZEN PRIVATE")
print("=" * 72)
