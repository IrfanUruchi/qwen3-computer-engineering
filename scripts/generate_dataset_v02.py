#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from v02gen.common import (
    DOMAIN_TARGETS,
    DIFFICULTY_TARGETS,
    STAGING,
    read_jsonl,
    record,
    scan_v02,
)

MODULES = [
    "software",
    "systems",
    "operating_systems",
    "architecture",
    "linux",
    "embedded",
    "networking",
    "distributed",
    "compute",
    "security",
    "reasoning",
]

STATE_PATH = STAGING / ".procedural-generator-state.json"
LOCAL = ROOT / ".research-local" / "dataset-v0.2-procedural"
AUDITS = LOCAL / "audits"
CHECKPOINTS = LOCAL / "checkpoints"

TASK_GROUP_TARGETS = {
    "implementation-code": 175,
    "debug-failure": 175,
    "performance": 140,
    "architecture-design": 140,
    "testing-config": 70,
}
TASK_GROUPS = {
    "implementation-code": {"implementation","code-repair","code-generation"},
    "debug-failure": {"debugging","failure-analysis","troubleshooting"},
    "performance": {"performance-analysis"},
    "architecture-design": {"architecture-analysis","design","technical-decision"},
    "testing-config": {"testing","configuration"},
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_families():
    out = []
    for name in MODULES:
        mod = importlib.import_module(f"v02procedural.{name}")
        out.extend(mod.FAMILIES)
    return out

def norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\d+(?:\.\d+)?", "<n>", text)
    text = re.sub(r"[^a-z0-9<>_+./ -]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def family_id_from_record(r):
    for tag in r.get("tags", []):
        if isinstance(tag, str) and tag.startswith("family:"):
            return tag.split(":", 1)[1]
    return None

def topic_from_record(r):
    for tag in r.get("tags", []):
        if isinstance(tag, str) and tag.startswith("topic:"):
            return tag.split(":", 1)[1]
    return None

def tokens(text: str) -> set[str]:
    return set(norm(text).split())

def jaccard(a: str, b: str) -> float:
    A, B = tokens(a), tokens(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)

def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"used_variants": [], "seed": None}

def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def max_numeric_id(rows):
    best = 300
    for r in rows:
        m = re.search(r"(\d{6})$", r["id"])
        if m:
            best = max(best, int(m.group(1)))
    return best

def next_batch_no():
    best = 0
    for p in STAGING.glob("batch-*.jsonl"):
        m = re.search(r"batch-(\d+)\.jsonl$", p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1

def task_group(task_type: str) -> str:
    for g, members in TASK_GROUPS.items():
        if task_type in members:
            return g
    return "other"

def difficulty_choice(levels, deficits):
    allowed = [x for x in levels if deficits.get(x, 0) > 0]
    if not allowed:
        return None
    return max(allowed, key=lambda x: (deficits[x] / max(1, DIFFICULTY_TARGETS[x]), deficits[x], x))

def build_pool(seed: int, used: set[str], variants_per_family: int = 12):
    rng = random.Random(seed)
    pool = []
    for fam in load_families():
        variants = fam.variants(limit=variants_per_family)
        rng.shuffle(variants)
        for v in variants:
            key = f"{v['family_id']}:{v['variant_index']}"
            if key in used:
                continue
            pool.append(v)
    rng.shuffle(pool)
    return pool

def current_counts(rows):
    dc = Counter(r["domain"] for r in rows)
    qc = Counter(r["difficulty"] for r in rows)
    tc = Counter(r["task_type"] for r in rows)
    gc = Counter()
    for t,n in tc.items():
        gc[task_group(t)] += n
    return dc,qc,tc,gc

def candidate_score(v, domain_def, diff_def, group_def, family_counts, topic_counts):
    if domain_def.get(v["domain"], 0) <= 0:
        return None
    diff = difficulty_choice(v["levels"], diff_def)
    if diff is None:
        return None
    g = task_group(v["task_type"])
    dscore = domain_def[v["domain"]] / max(1, DOMAIN_TARGETS[v["domain"]])
    qscore = diff_def[diff] / max(1, DIFFICULTY_TARGETS[diff])
    gscore = max(0, group_def.get(g, 0)) / max(1, TASK_GROUP_TARGETS.get(g, 1))
    diversity = -0.03 * family_counts[v["family_id"]] - 0.02 * topic_counts[v["topic"]]
    return (dscore * 5.0 + qscore * 3.0 + gscore * 1.5 + diversity, diff)

def validate_batch(path: Path):
    p = subprocess.run(
        [sys.executable, "scripts/validate_dataset.py", str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(p.stdout.strip())
    if p.returncode:
        raise SystemExit(f"Validator failed for {path}")

def write_checkpoint(rows, label: str):
    out = CHECKPOINTS / label
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"v0.2-{len(rows):04d}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    manifest = {
        "records": len(rows),
        "sha256": sha256(path),
        "domains": dict(sorted(Counter(r["domain"] for r in rows).items())),
        "difficulties": dict(sorted(Counter(r["difficulty"] for r in rows).items())),
        "task_types": dict(sorted(Counter(r["task_type"] for r in rows).items())),
    }
    (out/"CHECKPOINT.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(f"CHECKPOINT {label}: {len(rows)} records SHA256 {manifest['sha256']}")

def write_audit(rows, latest: int, sample: int, seed: int):
    window = rows[-min(latest, len(rows)):]
    rng = random.Random(seed + len(rows) * 97)
    by_domain = defaultdict(list)
    by_task = defaultdict(list)
    for r in window:
        by_domain[r["domain"]].append(r)
        by_task[r["task_type"]].append(r)

    selected = []
    seen = set()
    # First guarantee domain coverage.
    for d in sorted(by_domain):
        r = rng.choice(by_domain[d])
        if r["id"] not in seen:
            selected.append(r); seen.add(r["id"])
    # Then guarantee task coverage.
    for t in sorted(by_task):
        choices = [r for r in by_task[t] if r["id"] not in seen]
        if choices:
            r = rng.choice(choices)
            selected.append(r); seen.add(r["id"])
    remaining = [r for r in window if r["id"] not in seen]
    rng.shuffle(remaining)
    selected += remaining[:max(0, sample-len(selected))]
    selected = sorted(selected[:sample], key=lambda r:r["id"])

    AUDITS.mkdir(parents=True, exist_ok=True)
    stem = f"audit-{len(rows):04d}-latest-{len(window):04d}-sample-{len(selected):03d}"
    md = AUDITS / f"{stem}.md"
    jl = AUDITS / f"{stem}.jsonl"

    with jl.open("w", encoding="utf-8") as f:
        for r in selected:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":"))+"\n")

    parts = [f"# v0.2 audit — {len(selected)} records sampled from latest {len(window)} records from {len(rows)}\n"]
    for i,r in enumerate(selected,1):
        parts += [
            f"\n## {i}. {r['id']}\n",
            f"- Domain: `{r['domain']}`\n- Task: `{r['task_type']}`\n- Difficulty: `{r['difficulty']}`\n",
            "\n### Question\n\n"+r["messages"][0]["content"].strip()+"\n",
            "\n### Reference answer\n\n"+r["messages"][1]["content"].strip()+"\n",
            "\n### Verification\n\n"+r["verification"]["details"].strip()+"\n",
        ]
    md.write_text("".join(parts), encoding="utf-8")
    print(f"AUDIT: {md}")

def generate(args):
    rows = scan_v02()
    start_n = len(rows)
    target_total = min(args.target_total, sum(DOMAIN_TARGETS.values()))
    if start_n >= target_total:
        print(f"Already at {start_n}/{target_total}.")
        return

    state = load_state()
    used = set(state.get("used_variants", []))
    pool = build_pool(args.seed, used, args.variants_per_family)

    existing_norm = {norm(r["messages"][0]["content"]) for r in rows}
    existing_questions = [
        (
            r["id"],
            r["messages"][0]["content"],
            family_id_from_record(r),
            r["task_type"],
            r["domain"],
        )
        for r in rows
    ]

    dc,qc,tc,gc = current_counts(rows)
    domain_def = {d:max(0,t-dc[d]) for d,t in DOMAIN_TARGETS.items()}
    diff_def = {d:max(0,t-qc[d]) for d,t in DIFFICULTY_TARGETS.items()}
    group_def = {g:max(0,t-gc[g]) for g,t in TASK_GROUP_TARGETS.items()}

    family_counts = Counter()
    topic_counts = Counter()
    accepted_buffer = []
    lineage_buffer = []
    next_id = max_numeric_id(rows) + 1
    batch_no = next_batch_no()

    def flush():
        nonlocal accepted_buffer, lineage_buffer, batch_no, rows
        if not accepted_buffer:
            return
        path = STAGING / f"batch-{batch_no:03d}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in accepted_buffer:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        validate_batch(path)
        manifest = {
            "batch": f"{batch_no:03d}",
            "generator": "generate_dataset_v02.py",
            "seed": args.seed,
            "records": len(accepted_buffer),
            "record_ids": [r["id"] for r in accepted_buffer],
            "lineage": lineage_buffer,
            "sha256": sha256(path),
        }
        (STAGING/f"batch-{batch_no:03d}.procedural.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False)+"\n",
            encoding="utf-8",
        )
        print(f"FROZEN {path} ({len(accepted_buffer)} records) SHA256 {manifest['sha256']}")
        rows.extend(accepted_buffer)
        accepted_buffer = []
        lineage_buffer = []
        batch_no += 1

        n = len(rows)
        if args.checkpoint_every and n % args.checkpoint_every == 0:
            write_checkpoint(rows, f"{n:04d}")
        if args.audit_every and n % args.audit_every == 0:
            write_audit(rows, args.audit_every, args.audit_sample, args.seed)

    goal = target_total - start_n
    attempts = 0
    rejects = Counter()

    while len(rows) + len(accepted_buffer) < target_total:
        attempts += 1
        if not pool:
            # Never throw away a valid partial shard. v1 could exit with accepted
            # records still only in memory.
            state["used_variants"] = sorted(used)
            state["seed"] = args.seed
            save_state(state)
            flush()
            raise SystemExit(
                f"Generator capacity exhausted after accepting "
                f"{len(rows)-start_n}/{goal} requested records. "
                f"All accepted records were flushed safely."
            )

        # Recompute candidate scores and pick from the strongest small frontier,
        # then randomize within that frontier for diversity.
        scored = []
        for v in pool:
            s = candidate_score(v, domain_def, diff_def, group_def, family_counts, topic_counts)
            if s is not None:
                scored.append((s[0], s[1], v))
        if not scored:
            state["used_variants"] = sorted(used)
            state["seed"] = args.seed
            save_state(state)
            flush()
            raise SystemExit(
                "No candidate can satisfy remaining domain/difficulty targets. "
                "All accepted records were flushed safely."
            )

        scored.sort(key=lambda x:x[0], reverse=True)
        frontier = scored[:min(12, len(scored))]
        rng = random.Random(args.seed + attempts * 7919)
        score, difficulty, v = rng.choice(frontier)
        pool.remove(v)

        nq = norm(v["question"])
        if nq in existing_norm:
            rejects["normalized-duplicate"] += 1
            continue

        # Near-duplicate guard.
        #
        # v1 compared every new question against every historical task regardless of
        # domain/task type. That produced hundreds of false positives because common
        # engineering wording ("measure", "verify", "under load") is naturally shared.
        # Here we only reject a high-overlap cross-family candidate when it is in the
        # same domain AND the same task type. Exact normalized duplicates are still
        # rejected globally above.
        too_close = False
        for _, q, famid, old_task, old_domain in existing_questions[-args.similarity_window:]:
            if famid == v["family_id"]:
                continue
            if old_domain != v["domain"] or old_task != v["task_type"]:
                continue
            if jaccard(v["question"], q) >= args.jaccard:
                too_close = True
                break
        if too_close:
            rejects["near-duplicate"] += 1
            continue

        rid = f"ce-{v['task_type']}-{next_id:06d}"
        rec = record(
            rid,
            v["domain"],
            v["subdomain"],
            v["task_type"],
            difficulty,
            v["question"],
            v["answer"],
            v["verification_method"],
            v["verification"],
            v["tags"],
        )

        accepted_buffer.append(rec)
        lineage_buffer.append({
            "record_id": rid,
            "family_id": v["family_id"],
            "topic": v["topic"],
            "variant_index": v["variant_index"],
            "difficulty": difficulty,
            "params": v["params"],
        })
        used.add(f"{v['family_id']}:{v['variant_index']}")
        family_counts[v["family_id"]] += 1
        topic_counts[v["topic"]] += 1
        existing_norm.add(nq)
        existing_questions.append(
            (rid, v["question"], v["family_id"], v["task_type"], v["domain"])
        )
        next_id += 1

        domain_def[v["domain"]] -= 1
        diff_def[difficulty] -= 1
        g = task_group(v["task_type"])
        if g in group_def:
            group_def[g] = max(0, group_def[g]-1)

        if len(accepted_buffer) >= args.shard_size:
            state["used_variants"] = sorted(used)
            state["seed"] = args.seed
            save_state(state)
            flush()

    state["used_variants"] = sorted(used)
    state["seed"] = args.seed
    save_state(state)
    flush()

    final_rows = scan_v02()
    print()
    print("="*78)
    print("GENERATION COMPLETE")
    print("="*78)
    print(f"started:  {start_n}")
    print(f"finished: {len(final_rows)}")
    print(f"added:    {len(final_rows)-start_n}")
    print(f"attempts: {attempts}")
    print(f"rejects:  {dict(rejects)}")
    print()
    dc,qc,tc,gc = current_counts(final_rows)
    print("Domains:")
    for d,t in DOMAIN_TARGETS.items():
        print(f"  {d:30s} {dc[d]:3d}/{t:3d}")
    print("Difficulty:")
    for d,t in DIFFICULTY_TARGETS.items():
        print(f"  {d:30s} {qc[d]:3d}/{t:3d}")

def status():
    rows = scan_v02()
    dc,qc,tc,gc = current_counts(rows)
    print(f"v0.2 records: {len(rows)}/{sum(DOMAIN_TARGETS.values())}")
    print("Domains:")
    for d,t in DOMAIN_TARGETS.items():
        print(f"  {d:30s} {dc[d]:3d}/{t:3d} remaining {max(0,t-dc[d]):3d}")
    print("Difficulty:")
    for d,t in DIFFICULTY_TARGETS.items():
        print(f"  {d:30s} {qc[d]:3d}/{t:3d} remaining {max(0,t-qc[d]):3d}")
    print("Task groups:")
    for g,t in TASK_GROUP_TARGETS.items():
        print(f"  {g:30s} {gc[g]:3d}/{t:3d}")
    print("Generator families:", len(load_families()))
    state = load_state()
    procedural_rows = [r for r in rows if family_id_from_record(r)]
    print("Used procedural variants:", len(state.get("used_variants", [])))
    print("Procedural rows with recovered lineage:", len(procedural_rows))

def capacity(seed, variants_per_family=12, jaccard_threshold=0.96, similarity_window=400):
    rows = scan_v02()
    state = load_state()
    pool = build_pool(
        seed,
        set(state.get("used_variants", [])),
        variants_per_family,
    )

    existing_norm = {norm(r["messages"][0]["content"]) for r in rows}
    existing_questions = [
        (
            r["id"],
            r["messages"][0]["content"],
            family_id_from_record(r),
            r["task_type"],
            r["domain"],
        )
        for r in rows
    ]

    effective = []
    rejected = Counter()

    for v in pool:
        nq = norm(v["question"])
        if nq in existing_norm:
            rejected["normalized-duplicate"] += 1
            continue

        too_close = False
        for _, q, famid, old_task, old_domain in existing_questions[-similarity_window:]:
            if famid == v["family_id"]:
                continue
            if old_domain != v["domain"] or old_task != v["task_type"]:
                continue
            if jaccard(v["question"], q) >= jaccard_threshold:
                too_close = True
                break

        if too_close:
            rejected["near-duplicate"] += 1
            continue

        effective.append(v)

    raw = Counter(v["domain"] for v in pool)
    eff = Counter(v["domain"] for v in effective)
    dc = Counter(r["domain"] for r in rows)

    print("Remaining effective procedural capacity by domain:")
    enough = True
    for d,t in DOMAIN_TARGETS.items():
        need = max(0, t-dc[d])
        slack = eff[d]-need
        ok = slack >= 0
        enough = enough and ok
        mark = "OK" if ok else "SHORT"
        print(
            f"  {d:30s} effective {eff[d]:3d} raw {raw[d]:3d} "
            f"need {need:3d} slack {slack:4d} {mark}"
        )
    print("Raw pool:", len(pool))
    print("Effective pool:", len(effective))
    print("Preflight rejects:", dict(rejected))
    print("Records still needed:", max(0, sum(DOMAIN_TARGETS.values())-len(rows)))
    print("Effective domain-capacity check:", "PASS" if enough else "FAIL")

def main():
    ap = argparse.ArgumentParser(description="Procedural Qwen3 CE v0.2 dataset generator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    p = sub.add_parser("capacity")
    p.add_argument("--seed", type=int, default=20260914)
    p.add_argument("--variants-per-family", type=int, default=12)
    p.add_argument("--jaccard", type=float, default=0.96)
    p.add_argument("--similarity-window", type=int, default=400)

    p = sub.add_parser("generate")
    p.add_argument("--target-total", type=int, default=700,
                   help="total NEW v0.2 records in staging; final target is 700")
    p.add_argument("--shard-size", type=int, default=50)
    p.add_argument("--seed", type=int, default=20260914)
    p.add_argument("--checkpoint-every", type=int, default=100)
    p.add_argument("--audit-every", type=int, default=100)
    p.add_argument("--audit-sample", type=int, default=30)
    p.add_argument("--jaccard", type=float, default=0.96)
    p.add_argument("--similarity-window", type=int, default=400)
    p.add_argument("--variants-per-family", type=int, default=12)

    args = ap.parse_args()
    if args.cmd == "status":
        status()
    elif args.cmd == "capacity":
        capacity(
            args.seed,
            args.variants_per_family,
            args.jaccard,
            args.similarity_window,
        )
    elif args.cmd == "generate":
        generate(args)

if __name__ == "__main__":
    main()
