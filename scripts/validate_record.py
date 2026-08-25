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
        description="Validate a dataset record against the project JSON schema."
    )
    parser.add_argument("record", type=Path, help="Path to a JSON record")
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help=f"Schema path (default: {DEFAULT_SCHEMA})",
    )
    args = parser.parse_args()

    try:
        schema = load_json(args.schema)
        record = load_json(args.record)
    except FileNotFoundError as exc:
        print(f"ERROR: file not found: {exc.filename}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON in {exc.doc[:0] or 'input'}: {exc}",
            file=sys.stderr,
        )
        return 2

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        print(f"INVALID: {args.record}")

        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path)
            if not location:
                location = "<root>"

            print(f"  {location}: {error.message}")

        return 1

    print(f"VALID: {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
