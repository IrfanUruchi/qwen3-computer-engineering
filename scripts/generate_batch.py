#!/usr/bin/env python3

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator


if len(sys.argv) != 2:
    raise SystemExit("usage: generate_batch.py <batch>")

batch = int(sys.argv[1])

module = importlib.import_module(
    f"generators.batch_{batch:03d}"
)

records = [
    r.materialize()
    for r in module.RECORDS
]

start = (batch - 1) * 10 + 1
end = start + 9

if len(records) != 10:
    raise SystemExit(
        f"expected 10 records, got {len(records)}"
    )

numbers = [
    int(r["id"].rsplit("-", 1)[-1])
    for r in records
]

if numbers != list(range(start, end + 1)):
    raise SystemExit(
        f"bad sequence: {numbers}"
    )

ids = [r["id"] for r in records]

if len(ids) != len(set(ids)):
    raise SystemExit("duplicate IDs in generated batch")

schema = json.loads(
    Path(
        "configs/dataset-record.schema.json"
    ).read_text()
)

validator = Draft202012Validator(schema)

for record in records:
    errors = sorted(
        validator.iter_errors(record),
        key=lambda e: list(e.path),
    )

    if errors:
        print("INVALID:", record["id"])

        for error in errors:
            print("-", error.message)

        raise SystemExit(1)

out = Path(
    f"data/raw/v0.1/staging-batch-{batch:03d}.json"
)

out.write_text(
    json.dumps(records, indent=2) + "\n",
    encoding="utf-8",
)

plan = {
    "batch": f"{batch:03d}",
    "dataset_version": "0.1",
    "records": [
        {
            "id": r["id"],
            "domain": r["domain"],
            "subdomain": r["subdomain"],
            "task_type": r["task_type"],
            "difficulty": r["difficulty"],
            "verification": r["verification"]["method"],
        }
        for r in records
    ],
}

plan_path = Path(
    f"configs/dataset-v0.1-batch-{batch:03d}.json"
)

plan_path.write_text(
    json.dumps(plan, indent=2) + "\n",
    encoding="utf-8",
)

print("Plan:    ", plan_path)

verification_root = Path("data/raw/v0.1/verification")
verification_root.mkdir(parents=True, exist_ok=True)

for name, content in getattr(module, "VERIFIERS", {}).items():
    target = verification_root / name
    target.write_text(content.strip() + "\n", encoding="utf-8")

    if target.suffix == ".sh":
        target.chmod(0o755)

    print("Verifier:", target)

print(f"Generated Batch {batch:03d}: VALID")
print("Records:", len(records))
print("First:  ", records[0]["id"])
print("Last:   ", records[-1]["id"])
print("Output: ", out)
