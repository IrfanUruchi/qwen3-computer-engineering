#!/usr/bin/env python3

import sys
from pathlib import Path


if len(sys.argv) != 3:
    raise SystemExit(
        "usage: create_macro_batches.py <first-batch> <last-batch>"
    )

first = int(sys.argv[1])
last = int(sys.argv[2])

if first > last:
    raise SystemExit("first batch must be <= last batch")

macro_name = f"macro_{first:03d}_{last:03d}"
macro_path = Path("generators") / f"{macro_name}.py"

if not macro_path.exists():
    raise SystemExit(
        f"missing macro generator: {macro_path}"
    )

for batch in range(first, last + 1):
    path = Path("generators") / f"batch_{batch:03d}.py"

    content = f'''from generators.{macro_name} import records_for, verifiers_for

RECORDS = records_for({batch})
VERIFIERS = verifiers_for({batch})
'''

    path.write_text(content, encoding="utf-8")
    print("Created:", path)

print()
print(
    f"Batch adapters ready: "
    f"{first:03d}-{last:03d}"
)
