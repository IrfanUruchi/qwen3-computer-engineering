from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "data" / "staging" / "v0.2"
RAW_V01 = ROOT / "data" / "raw" / "v0.1"

V02_TARGET_RECORDS = 700

DOMAIN_TARGETS = {
    "software-engineering": 90,
    "systems-programming": 85,
    "operating-systems": 80,
    "computer-architecture": 75,
    "linux-infrastructure": 70,
    "embedded-systems": 60,
    "networking": 60,
    "distributed-systems": 60,
    "compute-model-infrastructure": 50,
    "secure-engineering": 35,
    "engineering-reasoning": 35,
}

DIFFICULTY_TARGETS = {
    "intermediate": 140,
    "advanced": 385,
    "expert": 175,
}

def record(
    rid: str,
    domain: str,
    subdomain: str,
    task_type: str,
    difficulty: str,
    question: str,
    answer: str,
    verification_method: str,
    verification_details: str,
    tags: list[str],
) -> dict:
    return {
        "id": rid,
        "version": 1,
        "split": "train",
        "domain": domain,
        "subdomain": subdomain,
        "task_type": task_type,
        "difficulty": difficulty,
        "messages": [
            {"role": "user", "content": question.strip()},
            {"role": "assistant", "content": answer.strip()},
        ],
        "verification": {
            "method": verification_method,
            "status": "verified",
            "details": verification_details.strip(),
        },
        "source": {"type": "original"},
        "tags": tags,
    }

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def scan_all() -> list[dict]:
    out = []
    for base in (RAW_V01, STAGING):
        if not base.exists():
            continue
        for p in sorted(base.glob("*.jsonl")):
            if p.name.startswith("."):
                continue
            out.extend(read_jsonl(p))
    return out

def scan_v02() -> list[dict]:
    out = []
    if not STAGING.exists():
        return out
    for p in sorted(STAGING.glob("batch-*.jsonl")):
        out.extend(read_jsonl(p))
    return out

def next_record_number(rows: list[dict]) -> int:
    nums = []
    for r in rows:
        m = re.search(r"-(\d{6})$", r.get("id", ""))
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=300) + 1

def next_batch_number() -> int:
    nums = []
    STAGING.mkdir(parents=True, exist_ok=True)
    for p in STAGING.glob("batch-*.jsonl"):
        m = re.fullmatch(r"batch-(\d+)\.jsonl", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1

def normalized_question(r: dict) -> str:
    q = r["messages"][0]["content"].lower()
    q = re.sub(r"\d+(?:\.\d+)?", "<n>", q)
    q = re.sub(r"[^a-z0-9<>_+./ -]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q

def token_jaccard(a: str, b: str) -> float:
    aa, bb = set(a.split()), set(b.split())
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)

def validate_file(path: Path) -> None:
    p = subprocess.run(
        [sys.executable, "scripts/validate_dataset.py", str(path)],
        cwd=ROOT,
    )
    if p.returncode:
        raise SystemExit(f"Validator failed: {path}")

def current_counts():
    rows = scan_v02()
    domains = Counter(r["domain"] for r in rows)
    difficulties = Counter(r["difficulty"] for r in rows)
    tasks = Counter(r["task_type"] for r in rows)
    return rows, domains, difficulties, tasks

def choose_difficulty(rng: random.Random, current: Counter) -> str:
    deficits = {
        d: max(0, target - current[d])
        for d, target in DIFFICULTY_TARGETS.items()
    }
    viable = [d for d, n in deficits.items() if n > 0]
    if not viable:
        return "advanced"
    return max(
        viable,
        key=lambda d: (deficits[d] / DIFFICULTY_TARGETS[d], deficits[d])
    )


def family_concept(family: dict) -> str:
    """Stable semantic lineage key. New production families should set `concept`."""
    return family.get("concept") or family["id"]

def load_used_concepts() -> set[str]:
    path = STAGING / ".used-concepts.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("used_concepts", []))

def save_used_concepts(concepts: set[str]) -> None:
    path = STAGING / ".used-concepts.json"
    path.write_text(
        json.dumps({"used_concepts": sorted(concepts)}, indent=2) + "\n",
        encoding="utf-8",
    )

def choose_family(
    rng: random.Random,
    families: list[dict],
    domain_counts: Counter,
    used_family_ids: set[str],
    used_concepts: set[str],
) -> dict:
    candidates = [
        f for f in families
        if f["id"] not in used_family_ids
        and family_concept(f) not in used_concepts
        and domain_counts[f["domain"]] < DOMAIN_TARGETS.get(f["domain"], 0)
    ]
    if not candidates:
        raise SystemExit(
            "No unused generator families remain for this purpose "
            "without exceeding a domain target."
        )

    def score(f):
        domain = f["domain"]
        target = DOMAIN_TARGETS[domain]
        deficit = target - domain_counts[domain]
        return (deficit / target, deficit, rng.random())

    return max(candidates, key=score)

def run_purpose(
    *,
    purpose: str,
    families: list[dict],
    build: Callable[[dict, random.Random, str, str], dict],
    records_requested: int,
    seed: int,
) -> None:
    STAGING.mkdir(parents=True, exist_ok=True)

    all_rows = scan_all()
    v02_rows, domain_counts, difficulty_counts, task_counts = current_counts()
    next_id = next_record_number(all_rows)
    batch_no = next_batch_number()

    existing_ids = {r["id"] for r in all_rows}
    existing_norm = [normalized_question(r) for r in all_rows if r.get("messages")]

    state_path = STAGING / f".purpose-{purpose}-state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"used_family_ids": [], "seed": seed}

    used = set(state.get("used_family_ids", []))
    used_concepts = load_used_concepts()
    rng = random.Random(seed + len(used) * 1009 + len(v02_rows) * 17)

    # Maximum records this purpose can still contribute without exceeding
    # configured domain targets or reusing a semantic concept.
    unused_by_domain = Counter(
        f["domain"]
        for f in families
        if f["id"] not in used and family_concept(f) not in used_concepts
    )
    max_viable = sum(
        min(
            unused_by_domain[d],
            max(0, DOMAIN_TARGETS.get(d, 0) - domain_counts[d]),
        )
        for d in unused_by_domain
    )

    if records_requested > max_viable:
        raise SystemExit(
            f"{purpose}: requested {records_requested}, but only {max_viable} "
            "unused family slots remain without exceeding domain targets."
        )

    generated = []
    batch_family_ids = []
    batch_concepts = []
    for _ in range(records_requested):
        family = choose_family(
            rng, families, domain_counts, used, used_concepts
        )
        difficulty = choose_difficulty(rng, difficulty_counts)

        rid = f"ce-{purpose}-{next_id:06d}"
        candidate = build(family, rng, rid, difficulty)

        if candidate["id"] in existing_ids:
            raise SystemExit(f"ID collision: {candidate['id']}")

        nq = normalized_question(candidate)
        worst = 0.0
        for old in existing_norm:
            worst = max(worst, token_jaccard(nq, old))
        if worst >= 0.72:
            raise SystemExit(
                f"Near-duplicate generated by family {family['id']}: "
                f"Jaccard={worst:.3f}. Expand/rewrite that family."
            )

        generated.append(candidate)
        used.add(family["id"])
        concept = family_concept(family)
        used_concepts.add(concept)
        batch_family_ids.append(family["id"])
        batch_concepts.append(concept)
        existing_ids.add(candidate["id"])
        existing_norm.append(nq)
        domain_counts[candidate["domain"]] += 1
        difficulty_counts[candidate["difficulty"]] += 1
        next_id += 1

        print(
            f"ACCEPT {candidate['id']} | {family['id']} | "
            f"{candidate['domain']} | {candidate['task_type']} | "
            f"{candidate['difficulty']}"
        )

    data_path = STAGING / f"batch-{batch_no:03d}.jsonl"
    with data_path.open("w", encoding="utf-8") as f:
        for r in generated:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    validate_file(data_path)

    manifest = {
        "batch": f"{batch_no:03d}",
        "purpose": purpose,
        "generator_module": getattr(build, "__module__", None),
        "records": len(generated),
        "record_ids": [r["id"] for r in generated],
        "generator_seed": seed,
        "family_ids": batch_family_ids,
        "concept_ids": batch_concepts,
        "all_used_family_count": len(used),
        "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
    }
    manifest_path = STAGING / f"batch-{batch_no:03d}.sha256.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    state["used_family_ids"] = sorted(used)
    state["seed"] = seed
    state_path.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )
    save_used_concepts(used_concepts)

    print()
    print(f"FROZEN: {data_path}")
    print("SHA256:", manifest["data_sha256"])
    print("Purpose:", purpose)
    print("Records:", len(generated))
