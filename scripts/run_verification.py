#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


if len(sys.argv) < 2:
    raise SystemExit(
        "usage: run_verification.py <batch> [batch...]"
    )

root = Path("data/raw/v0.1/verification")
failed = []
ran = 0

for arg in sys.argv[1:]:
    batch = int(arg)

    start = (batch - 1) * 10 + 1
    end = start + 9

    for n in range(start, end + 1):
        stem = f"{n:06d}"

        tests = [
            root / f"{stem}_test.py",
            root / f"{stem}_test.sh",
        ]

        for test in tests:
            if not test.exists():
                continue

            ran += 1

            print()
            print("=" * 72)
            print("VERIFY:", test)
            print("=" * 72)

            if test.suffix == ".py":
                cmd = [
                    "python3",
                    str(test),
                    "-v",
                ]
            else:
                cmd = [
                    "bash",
                    str(test),
                ]

            result = subprocess.run(cmd)

            if result.returncode != 0:
                failed.append(str(test))

if failed:
    print("\nFAILED:")

    for test in failed:
        print("-", test)

    raise SystemExit(1)

print()
print(
    f"ALL DISCOVERED VERIFIERS PASSED ({ran})"
)
