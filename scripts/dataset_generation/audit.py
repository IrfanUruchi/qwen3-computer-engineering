from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import random

from .lineage import generator_id


def write_audit(rows: list[dict], out: Path, sample: int, seed: int):
    rng = random.Random(seed)
    by_domain = defaultdict(list)
    by_task = defaultdict(list)
    for r in rows:
        by_domain[r["domain"]].append(r)
        by_task[r["task_type"]].append(r)

    selected = []
    seen = set()

    for domain in sorted(by_domain):
        r = rng.choice(by_domain[domain])
        if r["id"] not in seen:
            selected.append(r)
            seen.add(r["id"])

    for task in sorted(by_task):
        choices = [r for r in by_task[task] if r["id"] not in seen]
        if choices:
            r = rng.choice(choices)
            selected.append(r)
            seen.add(r["id"])

    remaining = [r for r in rows if r["id"] not in seen]
    rng.shuffle(remaining)
    selected += remaining[: max(0, sample - len(selected))]
    selected = selected[:sample]

    parts = [f"# Dataset audit — {len(selected)} records\n"]
    for i, r in enumerate(selected, 1):
        parts += [
            f"\n## {i}. {r['id']}\n",
            f"- Domain: `{r['domain']}`\n",
            f"- Task: `{r['task_type']}`\n",
            f"- Difficulty: `{r['difficulty']}`\n",
            f"- Generator: `{generator_id(r) or 'unknown'}`\n",
            "\n### Question\n\n" + r["messages"][0]["content"].strip() + "\n",
            "\n### Reference answer\n\n" + r["messages"][1]["content"].strip() + "\n",
            "\n### Verification\n\n" + r["verification"]["details"].strip() + "\n",
        ]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(parts), encoding="utf-8")
