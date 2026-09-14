#!/usr/bin/env bash
set -euo pipefail

cd ~/qwen3-computer-engineering

python3 - <<'PY'
import json
from pathlib import Path

DATA = Path("data/staging/v0.2/batch-002.jsonl")
PLAN = Path("configs/dataset-v0.2-batch-002.json")

TARGET = "ce-reasoning-bottleneck-throughput-000320"

rows = [
    json.loads(line)
    for line in DATA.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

found = False
for r in rows:
    if r["id"] == TARGET:
        r["task_type"] = "performance-analysis"
        r["verification"]["method"] = "reference-answer"
        found = True

if not found:
    raise SystemExit(f"Target record not found: {TARGET}")

with DATA.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

plan = json.loads(PLAN.read_text(encoding="utf-8"))

found = False
for r in plan["records"]:
    if r["id"] == TARGET:
        r["task_type"] = "performance-analysis"
        r["verification"] = "reference-answer"
        found = True

if not found:
    raise SystemExit(f"Target plan record not found: {TARGET}")

PLAN.write_text(
    json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("Patched:", TARGET)
print("  task_type -> performance-analysis")
print("  verification.method -> reference-answer")
PY

python3 -m json.tool configs/dataset-v0.2-batch-002.json >/dev/null \
  && echo "Batch plan: VALID JSON"

python3 scripts/validate_dataset.py \
  data/staging/v0.2/batch-002.jsonl
