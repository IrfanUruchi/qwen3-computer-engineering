from __future__ import annotations

from pathlib import Path
import json
import os
import re
import tempfile


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def scan_staging(root: Path) -> list[dict]:
    staging = root / "data" / "staging" / "v0.2"
    rows = []
    for path in sorted(staging.glob("batch-*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def next_record_number(rows: list[dict]) -> int:
    best = 300
    for r in rows:
        m = re.search(r"(\d{6})$", r["id"])
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def next_batch_number(root: Path) -> int:
    staging = root / "data" / "staging" / "v0.2"
    best = 0
    for p in staging.glob("batch-*.jsonl"):
        m = re.search(r"batch-(\d+)\.jsonl$", p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def atomic_write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
