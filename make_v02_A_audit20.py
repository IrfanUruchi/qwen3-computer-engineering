#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path.home() / "qwen3-computer-engineering"
SNAPSHOT = ROOT / ".research-local" / "dataset-v0.2-A" / "v0.2-A-100.jsonl"
OUTDIR = ROOT / ".research-local" / "dataset-v0.2-A" / "audit-20"

TARGET_N = 20
DIFFICULTY_TARGET = {
    "intermediate": 4,
    "advanced": 11,
    "expert": 5,
}

def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def stable_key(record: dict) -> str:
    # Deterministic ordering independent of source-file order.
    return hashlib.sha256(record["id"].encode("utf-8")).hexdigest()

def features(record: dict) -> set[str]:
    return {
        "domain:" + record["domain"],
        "task:" + record["task_type"],
    }

def choose_cover(rows: list[dict]) -> list[dict]:
    all_domains = sorted({r["domain"] for r in rows})
    all_tasks = sorted({r["task_type"] for r in rows})

    uncovered = {
        *("domain:" + x for x in all_domains),
        *("task:" + x for x in all_tasks),
    }

    selected: list[dict] = []
    remaining = list(rows)

    # Greedy deterministic set cover: explicitly cover every domain and every task type.
    while uncovered:
        best = max(
            remaining,
            key=lambda r: (
                len(features(r) & uncovered),
                1 if r["difficulty"] == "expert" else 0,
                -int(stable_key(r), 16),
            ),
        )

        gain = features(best) & uncovered
        if not gain:
            raise RuntimeError(f"Could not cover remaining features: {sorted(uncovered)}")

        selected.append(best)
        uncovered -= features(best)
        remaining.remove(best)

    if len(selected) > TARGET_N:
        raise RuntimeError(
            f"Coverage unexpectedly required {len(selected)} records (> {TARGET_N})."
        )

    # Fill to 20 while moving difficulty counts toward 4/11/5 and avoiding
    # repeatedly sampling the same domain/task when choices are otherwise equal.
    dcount = Counter(r["difficulty"] for r in selected)
    domain_count = Counter(r["domain"] for r in selected)
    task_count = Counter(r["task_type"] for r in selected)

    while len(selected) < TARGET_N:
        def score(r):
            diff_need = max(
                0,
                DIFFICULTY_TARGET.get(r["difficulty"], 0) - dcount[r["difficulty"]],
            )
            return (
                diff_need,
                -domain_count[r["domain"]],
                -task_count[r["task_type"]],
                -int(stable_key(r), 16),
            )

        best = max(remaining, key=score)
        selected.append(best)
        remaining.remove(best)
        dcount[best["difficulty"]] += 1
        domain_count[best["domain"]] += 1
        task_count[best["task_type"]] += 1

    return sorted(selected, key=lambda r: r["id"])

def main() -> None:
    if not SNAPSHOT.exists():
        raise SystemExit(f"Missing frozen snapshot: {SNAPSHOT}")

    OUTDIR.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(SNAPSHOT)
    if len(rows) != 100:
        raise SystemExit(f"Expected frozen 100-record snapshot, got {len(rows)}")

    snapshot_sha = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    expected_sha = "e14cd61a0c12f888afe110c3eb676ee27b17c06c7c8cfaa49cc770cf1852a9b2"
    if snapshot_sha != expected_sha:
        raise SystemExit(
            "Frozen snapshot hash mismatch.\n"
            f"expected: {expected_sha}\n"
            f"actual:   {snapshot_sha}"
        )

    selected = choose_cover(rows)

    # Freeze packet as canonical compact JSONL.
    packet_jsonl = OUTDIR / "audit-v0.2-A-20.jsonl"
    with packet_jsonl.open("w", encoding="utf-8") as f:
        for r in selected:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    # Human-readable packet for direct review/upload.
    packet_md = OUTDIR / "audit-v0.2-A-20.md"
    md = []
    md.append("# v0.2-A quality audit — 20-record stratified sample\n")
    md.append(f"Frozen source SHA-256: `{snapshot_sha}`\n")
    md.append("Selection: deterministic coverage of every domain and task type, then "
              "filled toward the 20/55/25 difficulty distribution.\n")

    for i, r in enumerate(selected, 1):
        md.append(f"\n## {i}. {r['id']}\n")
        md.append(
            f"- Domain: `{r['domain']}`\n"
            f"- Subdomain: `{r['subdomain']}`\n"
            f"- Task: `{r['task_type']}`\n"
            f"- Difficulty: `{r['difficulty']}`\n"
            f"- Verification: `{r['verification']['method']}`\n"
        )
        md.append("\n### Question\n\n")
        md.append(r["messages"][0]["content"].strip() + "\n")
        md.append("\n### Reference answer\n\n")
        md.append(r["messages"][1]["content"].strip() + "\n")
        md.append("\n### Verification criterion\n\n")
        md.append(r["verification"]["details"].strip() + "\n")

    packet_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    domains = Counter(r["domain"] for r in selected)
    tasks = Counter(r["task_type"] for r in selected)
    difficulties = Counter(r["difficulty"] for r in selected)

    manifest = {
        "source_snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "source_sha256": snapshot_sha,
        "sample_records": len(selected),
        "sample_ids": [r["id"] for r in selected],
        "sample_jsonl_sha256": hashlib.sha256(packet_jsonl.read_bytes()).hexdigest(),
        "sample_md_sha256": hashlib.sha256(packet_md.read_bytes()).hexdigest(),
        "domains": dict(sorted(domains.items())),
        "task_types": dict(sorted(tasks.items())),
        "difficulties": dict(sorted(difficulties.items())),
    }

    manifest_path = OUTDIR / "AUDIT_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 78)
    print("v0.2-A 20-RECORD AUDIT PACKET READY")
    print("=" * 78)
    print("source SHA256:", snapshot_sha)
    print("sample JSONL:", packet_jsonl)
    print("sample MD:", packet_md)
    print("manifest:", manifest_path)
    print("sample JSONL SHA256:", manifest["sample_jsonl_sha256"])
    print()
    print("Difficulty:", dict(sorted(difficulties.items())))
    print("Domains covered:", len(domains), "/", len({r["domain"] for r in rows}))
    print("Task types covered:", len(tasks), "/", len({r["task_type"] for r in rows}))
    print()
    print("Selected IDs:")
    for r in selected:
        print(" ", r["id"])

if __name__ == "__main__":
    main()
