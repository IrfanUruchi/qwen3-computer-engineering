#!/usr/bin/env bash
set -euo pipefail

cd ~/qwen3-computer-engineering

mkdir -p .research-local/dataset-v0.2-A

python3 - <<'PY'
from pathlib import Path
from collections import Counter
import hashlib, json, re, subprocess, sys

ROOT = Path.cwd()
STAGING = ROOT / "data" / "staging" / "v0.2"
OUTDIR = ROOT / ".research-local" / "dataset-v0.2-A"

DOMAIN_TARGETS = {
    "software-engineering": 13,
    "systems-programming": 12,
    "operating-systems": 12,
    "computer-architecture": 11,
    "linux-infrastructure": 10,
    "embedded-systems": 9,
    "networking": 9,
    "distributed-systems": 8,
    "compute-model-infrastructure": 7,
    "secure-engineering": 5,
    "engineering-reasoning": 4,
}
DIFFICULTY_TARGETS = {
    "intermediate": 20,
    "advanced": 55,
    "expert": 25,
}

def read_jsonl(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def norm_question(r):
    q = r["messages"][0]["content"].lower()
    q = re.sub(r"\d+(?:\.\d+)?", "<n>", q)
    q = re.sub(r"[^a-z0-9<>_+./ -]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q

batch_paths = sorted(STAGING.glob("batch-*.jsonl"))
if not batch_paths:
    raise SystemExit("No v0.2 staging batches found.")

rows = []
batch_manifest = []

for path in batch_paths:
    p = subprocess.run(
        [sys.executable, "scripts/validate_dataset.py", str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(p.stdout.strip())
    if p.returncode:
        raise SystemExit(f"Validator failed: {path}")

    batch_rows = read_jsonl(path)
    rows.extend(batch_rows)

    batch_manifest.append({
        "file": str(path.relative_to(ROOT)),
        "records": len(batch_rows),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })

if len(rows) != 100:
    raise SystemExit(f"Expected 100 records, found {len(rows)}")

ids = [r["id"] for r in rows]
if len(ids) != len(set(ids)):
    dupes = [x for x, n in Counter(ids).items() if n > 1]
    raise SystemExit(f"Duplicate IDs: {dupes}")

norms = [norm_question(r) for r in rows]
if len(norms) != len(set(norms)):
    dupes = [x for x, n in Counter(norms).items() if n > 1]
    raise SystemExit(f"Exact normalized-question duplicates: {len(dupes)}")

domains = Counter(r["domain"] for r in rows)
difficulties = Counter(r["difficulty"] for r in rows)
tasks = Counter(r["task_type"] for r in rows)

if dict(domains) != DOMAIN_TARGETS:
    raise SystemExit(
        "Domain distribution mismatch:\n"
        f"expected={DOMAIN_TARGETS}\nactual={dict(domains)}"
    )

if dict(difficulties) != DIFFICULTY_TARGETS:
    raise SystemExit(
        "Difficulty distribution mismatch:\n"
        f"expected={DIFFICULTY_TARGETS}\nactual={dict(difficulties)}"
    )

# Canonical combined stream: stable batch order, stable record order.
combined = OUTDIR / "v0.2-A-100.jsonl"
with combined.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

combined_sha = hashlib.sha256(combined.read_bytes()).hexdigest()

summary = {
    "checkpoint": "v0.2-A",
    "status": "frozen-local-quality-gate",
    "records": len(rows),
    "combined_sha256": combined_sha,
    "domains": dict(sorted(domains.items())),
    "difficulties": dict(sorted(difficulties.items())),
    "task_types": dict(sorted(tasks.items())),
    "batches": batch_manifest,
}

summary_path = OUTDIR / "FREEZE.json"
summary_path.write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print()
print("=" * 78)
print("v0.2-A FREEZE PASS")
print("=" * 78)
print("records:", len(rows))
print("unique IDs:", len(set(ids)))
print("normalized-question duplicates: 0")
print("combined SHA256:", combined_sha)
print("freeze manifest:", summary_path)
print("combined snapshot:", combined)
print()
print("Task types:")
for k, v in sorted(tasks.items()):
    print(f"  {k:30s} {v:3d}")
PY
