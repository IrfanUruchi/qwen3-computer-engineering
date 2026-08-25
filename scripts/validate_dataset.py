#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "configs" / "dataset-record.schema.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a JSONL dataset against the project schema."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
    )
    args = parser.parse_args()

    try:
        schema = load_json(args.schema)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to load schema: {exc}", file=sys.stderr)
        return 2

    validator = Draft202012Validator(schema)

    seen_ids = set()
    record_count = 0
    error_count = 0

    try:
        with args.dataset.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()

                if not line:
                    continue

                record_count += 1

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(
                        f"line {line_number}: invalid JSON: {exc.msg}"
                    )
                    error_count += 1
                    continue

                if not isinstance(record, dict):
                    print(
                        f"line {line_number}: "
                        "record must be a JSON object"
                    )
                    error_count += 1
                    continue

                errors = sorted(
                    validator.iter_errors(record),
                    key=lambda error: list(error.absolute_path),
                )

                for error in errors:
                    location = ".".join(
                        str(part) for part in error.absolute_path
                    ) or "<root>"

                    print(
                        f"line {line_number}: "
                        f"{location}: {error.message}"
                    )
                    error_count += 1

                record_id = record.get("id")

                if record_id is not None:
                    if record_id in seen_ids:
                        print(
                            f"line {line_number}: "
                            f"duplicate id: {record_id}"
                        )
                        error_count += 1
                    else:
                        seen_ids.add(record_id)

                verification = record.get("verification", {})
                if verification.get("status") == "rejected":
                    print(
                        f"line {line_number}: "
                        "rejected record present in dataset"
                    )
                    error_count += 1

    except FileNotFoundError:
        print(f"ERROR: file not found: {args.dataset}", file=sys.stderr)
        return 2

    if error_count:
        print(
            f"INVALID: {args.dataset} "
            f"({record_count} records, {error_count} errors)"
        )
        return 1

    print(
        f"VALID: {args.dataset} "
        f"({record_count} records)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
