#!/usr/bin/env python3

import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: append_records.py <records.json>")

source = Path(sys.argv[1])
dataset = Path("data/raw/v0.1/train.jsonl")

incoming = json.loads(source.read_text(encoding="utf-8"))

if not isinstance(incoming, list):
    raise SystemExit("input must be a JSON array")

existing_records = [
    json.loads(x)
    for x in dataset.read_text(encoding="utf-8").splitlines()
    if x.strip()
]

existing = {r["id"] for r in existing_records}

added = 0

with dataset.open("a", encoding="utf-8") as f:
    for record in incoming:
        rid = record["id"]

        if rid in existing:
            print("SKIP:", rid)
            continue

        f.write(json.dumps(record, separators=(",", ":")) + "\n")
        existing.add(rid)
        added += 1
        print("ADD: ", rid)

print()
print("Added:", added)
print("Total:", len(existing_records) + added)
