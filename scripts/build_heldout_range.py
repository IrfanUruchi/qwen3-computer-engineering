#!/usr/bin/env python3

import hashlib
import importlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_PATH = ROOT / "configs/dataset-record.schema.json"
RAW_ROOT = ROOT / "data/raw/v0.1"

SPLITS = {
    "validation": {
        "base": 201,
        "target": 40,
        "cross_files": [
            RAW_ROOT / "train.jsonl",
        ],
    },
    "evaluation": {
        "base": 241,
        "target": 60,
        "cross_files": [
            RAW_ROOT / "train.jsonl",
            RAW_ROOT / "validation.jsonl",
        ],
    },
}


def die(message):
    raise SystemExit(f"HELDOUT BUILD FAILED: {message}")


def norm(text):
    return " ".join(text.split()).casefold()


def msg(record, role):
    return "\n".join(
        m["content"]
        for m in record["messages"]
        if m["role"] == role
    )


def load_jsonl(path):
    if not path.exists():
        return []

    out = []

    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if not line.strip():
            continue

        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            die(f"{path}:{lineno}: {exc}")

        if not isinstance(item, dict):
            die(f"{path}:{lineno}: record is not an object")

        out.append(item)

    return out


def schema_validate(records, label):
    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(schema)

    for index, record in enumerate(records, 1):
        errors = sorted(
            validator.iter_errors(record),
            key=lambda e: list(e.path),
        )

        if errors:
            print()
            print(f"SCHEMA ERROR: {label} record {index}")

            for error in errors:
                path = ".".join(map(str, error.path))
                print(f"- {path or '<root>'}: {error.message}")

            die("schema validation failed")


def duplicate_values(values):
    counts = Counter(values)

    return [
        value
        for value, count in counts.items()
        if count > 1
    ]


def verify_no_cross_split_collisions(
    split,
    candidate,
):
    other = []

    for path in SPLITS[split]["cross_files"]:
        other.extend(load_jsonl(path))

    combined = other + candidate

    ids = [r["id"] for r in combined]
    prompts = [
        norm(msg(r, "user"))
        for r in combined
    ]
    answers = [
        norm(msg(r, "assistant"))
        for r in combined
    ]

    dup_ids = duplicate_values(ids)
    dup_prompts = duplicate_values(prompts)
    dup_answers = duplicate_values(answers)

    if dup_ids:
        die(
            f"cross-split duplicate IDs found: "
            f"{dup_ids[:5]}"
        )

    if dup_prompts:
        die(
            f"cross-split normalized prompt duplicates: "
            f"{len(dup_prompts)}"
        )

    if dup_answers:
        die(
            f"cross-split normalized answer duplicates: "
            f"{len(dup_answers)}"
        )

    print("Cross-split IDs:      PASS")
    print("Cross-split prompts:  PASS")
    print("Cross-split answers:  PASS")


def materialize_verifiers(
    split,
    verifiers,
):
    root = RAW_ROOT / f"verification-{split}"
    root.mkdir(parents=True, exist_ok=True)

    paths = []

    for name, content in verifiers.items():
        path = root / name

        path.write_text(
            content.strip() + "\n",
            encoding="utf-8",
        )

        if path.suffix == ".sh":
            path.chmod(path.stat().st_mode | 0o111)

        paths.append(path)

    return paths


def run_verifiers(paths):
    failed = []

    for path in paths:
        print()
        print("=" * 72)
        print(f"VERIFY: {path.relative_to(ROOT)}")
        print("=" * 72)

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
            die(f"unsupported verifier: {path}")

        result = subprocess.run(
            cmd,
            cwd=ROOT,
        )

        if result.returncode != 0:
            failed.append(path)

    if failed:
        print()
        print("FAILED:")

        for path in failed:
            print("-", path.relative_to(ROOT))

        die("executable verification failed")

    print()
    print(
        f"ALL DISCOVERED VERIFIERS PASSED "
        f"({len(paths)})"
    )


def batch_numbers(split, batch):
    start = SPLITS[split]["base"] + (batch - 1) * 10
    return start, start + 9


def generate_batch(split, batch, validator):
    module_name = (
        f"generators.{split}_batch_{batch:03d}"
    )

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        die(
            f"missing generator module: {module_name} "
            f"({exc})"
        )

    if not hasattr(module, "RECORDS"):
        die(f"{module_name} has no RECORDS")

    records = []

    for source_record in module.RECORDS:
        record = source_record.materialize()

        # Important: frozen common.py still defaults to train.
        # Held-out builder owns the split assignment.
        record["split"] = split

        records.append(record)

    if len(records) != 10:
        die(
            f"{module_name}: expected 10 records, "
            f"found {len(records)}"
        )

    start, end = batch_numbers(split, batch)

    expected_numbers = list(
        range(start, end + 1)
    )

    actual_numbers = [
        int(r["id"][-6:])
        for r in records
    ]

    if actual_numbers != expected_numbers:
        die(
            f"{module_name}: expected suffixes "
            f"{start:06d}-{end:06d}, got "
            f"{actual_numbers}"
        )

    ids = [r["id"] for r in records]

    if len(ids) != len(set(ids)):
        die(f"{module_name}: duplicate IDs")

    for record in records:
        errors = sorted(
            validator.iter_errors(record),
            key=lambda e: list(e.path),
        )

        if errors:
            for error in errors:
                where = ".".join(map(str, error.path))
                print(
                    f"{record['id']}: "
                    f"{where or '<root>'}: "
                    f"{error.message}"
                )

            die(
                f"{module_name}: generated record "
                f"failed schema"
            )

    staging = (
        RAW_ROOT
        / f"staging-{split}-batch-{batch:03d}.json"
    )

    staging.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    plan = {
        "dataset_version": "0.1",
        "split": split,
        "batch": f"{batch:03d}",
        "records": [
            {
                "id": r["id"],
                "domain": r["domain"],
                "subdomain": r["subdomain"],
                "task_type": r["task_type"],
                "difficulty": r["difficulty"],
                "verification": (
                    r["verification"]["method"]
                ),
            }
            for r in records
        ],
    }

    plan_path = (
        ROOT
        / "configs"
        / (
            f"dataset-v0.1-{split}-"
            f"batch-{batch:03d}.json"
        )
    )

    plan_path.write_text(
        json.dumps(
            plan,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    verifiers = getattr(module, "VERIFIERS", {})

    verifier_paths = materialize_verifiers(
        split,
        verifiers,
    )

    print()
    print("=" * 72)
    print(
        f"{split.upper()} BATCH "
        f"{batch:03d}: GENERATED"
    )
    print("=" * 72)
    print(f"Records:    {len(records)}")
    print(f"Range:      {start:06d}-{end:06d}")
    print(f"Verifiers:  {len(verifier_paths)}")
    print(
        "Staging:   ",
        staging.relative_to(ROOT),
    )
    print(
        "Plan:      ",
        plan_path.relative_to(ROOT),
    )

    return records, verifier_paths


def audit_batch(
    split,
    batch,
    dataset_records,
):
    start, end = batch_numbers(split, batch)

    records = [
        r
        for r in dataset_records
        if start <= int(r["id"][-6:]) <= end
    ]

    if len(records) != 10:
        die(
            f"{split} batch {batch:03d}: "
            f"expected 10 records in dataset, "
            f"found {len(records)}"
        )

    plan_path = (
        ROOT
        / "configs"
        / (
            f"dataset-v0.1-{split}-"
            f"batch-{batch:03d}.json"
        )
    )

    plan = json.loads(
        plan_path.read_text(encoding="utf-8")
    )

    expected = {
        r["id"]: r
        for r in plan["records"]
    }

    actual_ids = {r["id"] for r in records}

    if actual_ids != set(expected):
        die(
            f"{split} batch {batch:03d}: "
            f"plan/dataset ID mismatch"
        )

    for record in records:
        expected_record = expected[record["id"]]

        checks = {
            "domain": record["domain"],
            "subdomain": record["subdomain"],
            "task_type": record["task_type"],
            "difficulty": record["difficulty"],
            "verification": (
                record["verification"]["method"]
            ),
        }

        for field, value in checks.items():
            if expected_record[field] != value:
                die(
                    f"{record['id']}: plan mismatch "
                    f"for {field}"
                )

        if record["split"] != split:
            die(
                f"{record['id']}: split is "
                f"{record['split']!r}"
            )

        if (
            record["verification"]["status"]
            != "verified"
        ):
            die(
                f"{record['id']}: not verified"
            )

    prompts = [
        norm(msg(r, "user"))
        for r in dataset_records
    ]

    answers = [
        norm(msg(r, "assistant"))
        for r in dataset_records
    ]

    if duplicate_values(prompts):
        die(
            f"{split}: duplicate prompts "
            f"inside split"
        )

    if duplicate_values(answers):
        die(
            f"{split}: duplicate answers "
            f"inside split"
        )

    domains = Counter(
        r["domain"]
        for r in records
    )

    difficulty = Counter(
        r["difficulty"]
        for r in records
    )

    verification = Counter(
        r["verification"]["method"]
        for r in records
    )

    tasks = Counter(
        r["task_type"]
        for r in records
    )

    review = {
        "dataset_version": "0.1",
        "split": split,
        "batch": f"{batch:03d}",
        "range": [
            f"{start:06d}",
            f"{end:06d}",
        ],
        "records": 10,
        "domain_counts": dict(domains),
        "difficulty_counts": dict(difficulty),
        "verification_method_counts": (
            dict(verification)
        ),
        "task_type_counts": dict(tasks),
        "duplicate_prompts": 0,
        "duplicate_answers": 0,
        "result": "PASS",
    }

    review_path = (
        ROOT
        / "configs"
        / (
            f"dataset-v0.1-{split}-"
            f"batch-{batch:03d}-review.json"
        )
    )

    review_path.write_text(
        json.dumps(
            review,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print(
        f"{split.upper()} BATCH "
        f"{batch:03d} AUDIT"
    )
    print("=" * 72)
    print(f"Range:          {start:06d}-{end:06d}")
    print("Records:        10")
    print(f"Domains:        {dict(domains)}")
    print(f"Difficulty:     {dict(difficulty)}")
    print(f"Verification:   {dict(verification)}")
    print(f"Task types:     {dict(tasks)}")
    print("Duplicates:     0")
    print()
    print("RESULT: PASS")
    print(
        "Review:         ",
        review_path.relative_to(ROOT),
    )


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: build_heldout_range.py "
            "<validation|evaluation> "
            "<batch> [batch ...]"
        )

    split = sys.argv[1]

    if split not in SPLITS:
        die(
            "split must be validation or evaluation"
        )

    try:
        batches = [
            int(x)
            for x in sys.argv[2:]
        ]
    except ValueError:
        die("batch values must be integers")

    if not batches:
        die("no batches supplied")

    if len(set(batches)) != len(batches):
        die("duplicate batch arguments")

    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(schema)

    generated = []
    verifier_paths = []

    # --------------------------------------------------------------
    # Stage all requested batches first.
    # Nothing is appended yet.
    # --------------------------------------------------------------

    for batch in batches:
        records, paths = generate_batch(
            split,
            batch,
            validator,
        )

        generated.extend(records)
        verifier_paths.extend(paths)

    # --------------------------------------------------------------
    # All executable evidence before append.
    # --------------------------------------------------------------

    run_verifiers(verifier_paths)

    # --------------------------------------------------------------
    # Build candidate atomically.
    # Existing same ID is allowed only if byte-equivalent as object.
    # --------------------------------------------------------------

    target = RAW_ROOT / f"{split}.jsonl"
    existing = load_jsonl(target)

    by_id = {
        r["id"]: r
        for r in existing
    }

    added = 0

    for record in generated:
        current = by_id.get(record["id"])

        if current is None:
            by_id[record["id"]] = record
            added += 1
            print(f"ADD:  {record['id']}")
        elif current == record:
            print(f"SKIP: {record['id']}")
        else:
            die(
                f"conflicting existing ID: "
                f"{record['id']}"
            )

    candidate = sorted(
        by_id.values(),
        key=lambda r: int(r["id"][-6:]),
    )

    for record in candidate:
        if record["split"] != split:
            die(
                f"{record['id']}: wrong split "
                f"{record['split']!r}"
            )

    schema_validate(
        candidate,
        f"{split} candidate",
    )

    verify_no_cross_split_collisions(
        split,
        candidate,
    )

    # --------------------------------------------------------------
    # Atomic write.
    # --------------------------------------------------------------

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = target.with_suffix(
        target.suffix + ".tmp"
    )

    temp.write_text(
        "".join(
            json.dumps(
                r,
                ensure_ascii=False,
            ) + "\n"
            for r in candidate
        ),
        encoding="utf-8",
    )

    os.replace(temp, target)

    print()
    print(f"Added: {added}")
    print(f"Total: {len(candidate)}")
    print(
        f"VALID: {target.relative_to(ROOT)} "
        f"({len(candidate)} records)"
    )

    # --------------------------------------------------------------
    # Audit requested batches after atomic commit.
    # --------------------------------------------------------------

    for batch in batches:
        audit_batch(
            split,
            batch,
            candidate,
        )

    target_count = SPLITS[split]["target"]

    sha = hashlib.sha256(
        target.read_bytes()
    ).hexdigest()

    print()
    print("=" * 72)
    print(
        f"{split.upper()} BUILD RANGE: PASS"
    )
    print(
        "Batches:",
        ", ".join(
            f"{b:03d}"
            for b in batches
        ),
    )
    print("=" * 72)

    print()
    print("=" * 72)
    print(
        f"{split.upper()} DATASET: "
        f"{len(candidate)}/{target_count}"
    )
    print(
        "PROGRESS: "
        f"{len(candidate) / target_count * 100:.1f}%"
    )
    print(f"SHA-256: {sha}")

    if candidate:
        print(
            f"LAST RECORD: {candidate[-1]['id']}"
        )

    print("=" * 72)


if __name__ == "__main__":
    main()
