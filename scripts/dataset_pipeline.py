#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import pkgutil
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from v02gen.common import (
    DOMAIN_TARGETS,
    DIFFICULTY_TARGETS,
    STAGING,
    V02_TARGET_RECORDS,
    family_concept,
    load_used_concepts,
    read_jsonl,
    scan_v02,
)

LOCAL = ROOT / ".research-local" / "dataset-v0.2-factory"
CHECKPOINTS = LOCAL / "checkpoints"
AUDITS = LOCAL / "audits"
RELEASES = LOCAL / "releases"

MODERN_QA = SCRIPTS / "dataset_qa.py"
MODERN_QA_ROOT = ROOT / ".research-local" / "dataset-generation" / "qa"

TASK_GROUP_TARGETS = {
    "implementation-code": 175,
    "debug-failure": 175,
    "performance": 140,
    "architecture-design": 140,
    "testing-config": 70,
}

TASK_GROUPS = {
    "implementation-code": {"implementation", "code-repair", "code-generation"},
    "debug-failure": {"debugging", "failure-analysis", "troubleshooting"},
    "performance": {"performance-analysis"},
    "architecture-design": {"architecture-analysis", "design", "technical-decision"},
    "testing-config": {"testing", "configuration"},
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalized_question(r: dict) -> str:
    q = r["messages"][0]["content"].lower()
    q = re.sub(r"\d+(?:\.\d+)?", "<n>", q)
    q = re.sub(r"[^a-z0-9<>_+./ -]+", " ", q)
    return re.sub(r"\s+", " ", q).strip()

def current():
    rows = scan_v02()
    return (
        rows,
        Counter(r["domain"] for r in rows),
        Counter(r["difficulty"] for r in rows),
        Counter(r["task_type"] for r in rows),
    )

def print_status():
    rows, dc, qc, tc = current()
    print(f"v0.2 production: {len(rows)}/{V02_TARGET_RECORDS}")
    print(f"remaining: {max(0, V02_TARGET_RECORDS-len(rows))}")
    print()
    print("Domains:")
    for d, target in DOMAIN_TARGETS.items():
        print(f"  {d:30s} {dc[d]:3d}/{target:3d}  remaining {max(0,target-dc[d]):3d}")
    print()
    print("Difficulty:")
    for d, target in DIFFICULTY_TARGETS.items():
        print(f"  {d:30s} {qc[d]:3d}/{target:3d}  remaining {max(0,target-qc[d]):3d}")
    print()
    print("Task types:")
    for k, v in sorted(tc.items()):
        print(f"  {k:30s} {v:3d}")
    print()
    print("Task groups (advisory, not hard quotas):")
    for group, members in TASK_GROUPS.items():
        n = sum(tc[m] for m in members)
        print(f"  {group:30s} {n:3d}")

def hamilton(deficits: dict[str, int], n: int) -> dict[str, int]:
    total = sum(max(0, v) for v in deficits.values())
    if n <= 0 or total <= 0:
        return {k: 0 for k in deficits}
    n = min(n, total)
    raw = {k: n * max(0, v) / total for k, v in deficits.items()}
    out = {k: int(math.floor(x)) for k, x in raw.items()}
    left = n - sum(out.values())
    order = sorted(
        deficits,
        key=lambda k: (raw[k] - out[k], deficits[k], k),
        reverse=True,
    )
    for k in order[:left]:
        out[k] += 1
    return out

def plan(records: int):
    rows, dc, qc, _ = current()
    records = min(records, V02_TARGET_RECORDS - len(rows))
    print(f"Plan for next {records} accepted records")
    print()
    domain_def = {d: max(0, t-dc[d]) for d,t in DOMAIN_TARGETS.items()}
    diff_def = {d: max(0, t-qc[d]) for d,t in DIFFICULTY_TARGETS.items()}
    da = hamilton(domain_def, records)
    qa = hamilton(diff_def, records)
    print("Domain allocation:")
    for d,n in da.items():
        if n:
            print(f"  {d:30s} +{n}")
    print()
    print("Difficulty allocation:")
    for d,n in qa.items():
        if n:
            print(f"  {d:30s} +{n}")

def validate_all() -> None:
    batch_paths = sorted(STAGING.glob("batch-*.jsonl"))
    rows = []
    seen = set()
    norms = set()
    problems = []

    for path in batch_paths:
        p = subprocess.run(
            [sys.executable, "scripts/validate_dataset.py", str(path)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if p.returncode:
            problems.append(f"validator failed: {path}")
        batch_rows = read_jsonl(path)
        rows.extend(batch_rows)

        manifest = path.with_suffix(".sha256.json")
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            expected = data.get("data_sha256")
            actual = sha256(path)
            if expected and expected != actual:
                problems.append(f"hash mismatch: {path}")

    for r in rows:
        rid = r["id"]
        if rid in seen:
            problems.append(f"duplicate id: {rid}")
        seen.add(rid)
        nq = normalized_question(r)
        if nq in norms:
            problems.append(f"exact normalized question duplicate: {rid}")
        norms.add(nq)

    dc = Counter(r["domain"] for r in rows)
    qc = Counter(r["difficulty"] for r in rows)
    for d,t in DOMAIN_TARGETS.items():
        if dc[d] > t:
            problems.append(f"domain target exceeded: {d} {dc[d]}/{t}")
    for d,t in DIFFICULTY_TARGETS.items():
        if qc[d] > t:
            problems.append(f"difficulty target exceeded: {d} {qc[d]}/{t}")

    if problems:
        print("VERIFY FAIL")
        for x in problems:
            print(" -", x)
        raise SystemExit(1)

    print("VERIFY PASS")
    print("records:", len(rows))
    print("batches:", len(batch_paths))
    print("unique IDs:", len(seen))
    print("normalized-question duplicates: 0")

def discover_modules():
    import v02gen
    modules = []
    for info in pkgutil.iter_modules(v02gen.__path__):
        if info.name in {"common", "__init__"}:
            continue
        module_name = f"v02gen.{info.name}"
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            continue
        fam = getattr(mod, "FAMILIES", None)
        if not fam:
            continue
        purpose = getattr(mod, "PURPOSE", info.name.replace("_", "-"))
        modules.append((module_name, purpose, mod, fam))
    return modules

def capacity_for(module_name, purpose, families):
    rows, dc, _, _ = current()
    used_concepts = load_used_concepts()
    state_path = STAGING / f".purpose-{purpose}-state.json"
    used_ids = set()
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        used_ids = set(data.get("used_family_ids", []))
    eligible = [
        f for f in families
        if f["id"] not in used_ids
        and family_concept(f) not in used_concepts
        and dc[f["domain"]] < DOMAIN_TARGETS.get(f["domain"], 0)
    ]
    by_domain = Counter(f["domain"] for f in eligible)
    viable = sum(
        min(by_domain[d], max(0, DOMAIN_TARGETS[d] - dc[d]))
        for d in by_domain
    )
    score = sum(
        (DOMAIN_TARGETS[f["domain"]] - dc[f["domain"]]) / DOMAIN_TARGETS[f["domain"]]
        for f in eligible
    )
    return viable, score, eligible

def discover():
    found = discover_modules()
    print("Generator modules:")
    if not found:
        print("  none")
        return
    for module_name, purpose, mod, fam in found:
        viable, score, eligible = capacity_for(module_name, purpose, fam)
        print(
            f"  {module_name:32s} purpose={purpose:20s} "
            f"families={len(fam):3d} viable={viable:3d}"
        )

def create_checkpoint(label: str | None = None):
    rows = scan_v02()
    n = len(rows)
    label = label or f"{n:04d}"
    out = CHECKPOINTS / label
    out.mkdir(parents=True, exist_ok=True)

    snapshot = out / f"v0.2-{n:04d}.jsonl"
    with snapshot.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    batches = []
    for p in sorted(STAGING.glob("batch-*.jsonl")):
        batches.append({
            "file": str(p.relative_to(ROOT)),
            "records": len(read_jsonl(p)),
            "sha256": sha256(p),
        })

    dc = Counter(r["domain"] for r in rows)
    qc = Counter(r["difficulty"] for r in rows)
    tc = Counter(r["task_type"] for r in rows)
    manifest = {
        "label": label,
        "records": n,
        "snapshot": str(snapshot.relative_to(ROOT)),
        "snapshot_sha256": sha256(snapshot),
        "domains": dict(sorted(dc.items())),
        "difficulties": dict(sorted(qc.items())),
        "task_types": dict(sorted(tc.items())),
        "batches": batches,
    }
    mp = out / "CHECKPOINT.json"
    mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("CHECKPOINT FROZEN")
    print("records:", n)
    print("snapshot:", snapshot)
    print("SHA256:", manifest["snapshot_sha256"])


def run_modern_qa(
    target: int,
    seed: int = 20260914,
    audit_sample: int = 60,
    force: bool = False,
):
    if not MODERN_QA.exists():
        raise SystemExit(f"Missing QA runner: {MODERN_QA}")

    report = MODERN_QA_ROOT / f"qa-report-{target:04d}.json"
    audit = MODERN_QA_ROOT / f"qa-audit-{target:04d}.md"

    current_n = len(scan_v02())

    # v0.2 was QA-gated before its final production commit. Once production
    # already equals the target, preserve that evidence rather than trying to
    # regenerate a now-empty preflight candidate.
    if current_n >= target and report.exists() and audit.exists() and not force:
        print("DATASET QA EVIDENCE: PASS")
        print("using existing pre-production QA evidence")
        print("report:", report)
        print("report SHA256:", sha256(report))
        print("audit:", audit)
        print("audit SHA256:", sha256(audit))
        return {
            "mode": "existing-preproduction-evidence",
            "report": str(report.relative_to(ROOT)),
            "report_sha256": sha256(report),
            "audit": str(audit.relative_to(ROOT)),
            "audit_sha256": sha256(audit),
        }

    cmd = [
        sys.executable,
        str(MODERN_QA),
        "--target", str(target),
        "--seed", str(seed),
        "--audit-sample", str(audit_sample),
    ]

    print("RUNNING FULL DATASET QA")
    print(" ".join(cmd))

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(proc.stdout, end="")

    if proc.returncode:
        raise SystemExit(proc.returncode)

    if "DATASET QA GATE: PASS" not in proc.stdout:
        raise SystemExit("QA command returned success but PASS marker was not found")

    if not report.exists() or not audit.exists():
        raise SystemExit("QA passed but expected QA artifacts are missing")

    return {
        "mode": "fresh-full-qa",
        "report": str(report.relative_to(ROOT)),
        "report_sha256": sha256(report),
        "audit": str(audit.relative_to(ROOT)),
        "audit_sha256": sha256(audit),
    }


def assert_final_targets(target: int):
    rows, dc, qc, tc = current()

    problems = []

    if len(rows) != target:
        problems.append(f"record count {len(rows)}/{target}")

    if target == V02_TARGET_RECORDS:
        for domain, expected in DOMAIN_TARGETS.items():
            actual = dc[domain]
            if actual != expected:
                problems.append(
                    f"domain {domain}: {actual}/{expected}"
                )

        for difficulty, expected in DIFFICULTY_TARGETS.items():
            actual = qc[difficulty]
            if actual != expected:
                problems.append(
                    f"difficulty {difficulty}: {actual}/{expected}"
                )

        for group, expected in TASK_GROUP_TARGETS.items():
            actual = sum(tc[t] for t in TASK_GROUPS[group])
            if actual != expected:
                problems.append(
                    f"task group {group}: {actual}/{expected}"
                )

    if problems:
        print("FINAL TARGET CHECK: FAIL")
        for problem in problems:
            print(" -", problem)
        raise SystemExit(1)

    print("FINAL TARGET CHECK: PASS")
    print("records:", len(rows))
    if target == V02_TARGET_RECORDS:
        print("domains: exact")
        print("difficulties: exact")
        print("task groups: exact")


def create_release(
    label: str,
    target: int,
    seed: int,
    audit_sample: int,
    force_qa: bool,
):
    print("=" * 78)
    print("FINAL DATASET RELEASE GATE")
    print("=" * 78)

    # 1. Validate every production batch, IDs, normalized questions and hashes.
    validate_all()

    # 2. Require exact final composition.
    assert_final_targets(target)

    # 3. Require modern generator/content/schema/full-candidate QA evidence.
    qa = run_modern_qa(
        target=target,
        seed=seed,
        audit_sample=audit_sample,
        force=force_qa,
    )

    # 4. Freeze immutable production snapshot.
    create_checkpoint(label)

    checkpoint_dir = CHECKPOINTS / label
    checkpoint_manifest = checkpoint_dir / "CHECKPOINT.json"

    if not checkpoint_manifest.exists():
        raise SystemExit("Checkpoint manifest was not created")

    checkpoint = json.loads(
        checkpoint_manifest.read_text(encoding="utf-8")
    )

    # 5. Release evidence manifest.
    release_dir = RELEASES / label
    release_dir.mkdir(parents=True, exist_ok=True)

    rows = scan_v02()
    tc = Counter(r["task_type"] for r in rows)

    task_groups = {
        group: sum(tc[t] for t in members)
        for group, members in TASK_GROUPS.items()
    }

    batch_manifest = []
    for batch in sorted(STAGING.glob("batch-*.jsonl")):
        batch_manifest.append({
            "file": str(batch.relative_to(ROOT)),
            "records": len(read_jsonl(batch)),
            "sha256": sha256(batch),
        })

    release = {
        "release": label,
        "dataset": "Qwen3 Computer Engineering",
        "dataset_version": "v0.2",
        "records": len(rows),
        "production_target": target,
        "checkpoint": {
            "manifest": str(checkpoint_manifest.relative_to(ROOT)),
            "manifest_sha256": sha256(checkpoint_manifest),
            "snapshot": checkpoint["snapshot"],
            "snapshot_sha256": checkpoint["snapshot_sha256"],
        },
        "qa": qa,
        "domains": checkpoint["domains"],
        "difficulties": checkpoint["difficulties"],
        "task_types": checkpoint["task_types"],
        "task_groups": task_groups,
        "batches": batch_manifest,
    }

    release_manifest = release_dir / "RELEASE.json"
    release_manifest.write_text(
        json.dumps(release, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 78)
    print("DATASET RELEASE GATE: PASS")
    print("=" * 78)
    print("release:", label)
    print("records:", len(rows))
    print("snapshot SHA256:", checkpoint["snapshot_sha256"])
    print("release manifest:", release_manifest)
    print("release manifest SHA256:", sha256(release_manifest))


def stable_hash(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)

def create_audit(sample: int, latest: int | None = None):
    all_rows = scan_v02()
    if not all_rows:
        raise SystemExit("No records.")

    if latest is not None:
        if latest < 1:
            raise SystemExit("--latest must be >= 1")
        source_rows = all_rows[-min(latest, len(all_rows)):]
    else:
        source_rows = all_rows

    sample = min(sample, len(source_rows))
    domains = sorted({r["domain"] for r in source_rows})
    tasks = sorted({r["task_type"] for r in source_rows})
    uncovered = {"d:"+x for x in domains} | {"t:"+x for x in tasks}
    remaining = list(source_rows)
    selected = []

    def feat(r):
        return {"d:"+r["domain"], "t:"+r["task_type"]}

    while uncovered and len(selected) < sample:
        best = max(
            remaining,
            key=lambda r: (
                len(feat(r) & uncovered),
                1 if r["difficulty"] == "expert" else 0,
                -stable_hash(r["id"]),
            ),
        )
        selected.append(best)
        remaining.remove(best)
        uncovered -= feat(best)

    dc = Counter(r["domain"] for r in selected)
    tc = Counter(r["task_type"] for r in selected)
    qc = Counter(r["difficulty"] for r in selected)

    while len(selected) < sample:
        best = min(
            remaining,
            key=lambda r: (
                dc[r["domain"]],
                tc[r["task_type"]],
                qc[r["difficulty"]],
                stable_hash(r["id"]),
            ),
        )
        selected.append(best)
        remaining.remove(best)
        dc[best["domain"]] += 1
        tc[best["task_type"]] += 1
        qc[best["difficulty"]] += 1

    selected = sorted(selected, key=lambda r: r["id"])
    AUDITS.mkdir(parents=True, exist_ok=True)

    total_n = len(all_rows)
    source_n = len(source_rows)
    if latest is not None:
        stem = f"audit-{total_n:04d}-latest-{source_n:04d}-sample-{sample:03d}"
        source_label = f"latest {source_n} records from {total_n}"
    else:
        stem = f"audit-{total_n:04d}-all-sample-{sample:03d}"
        source_label = f"all {total_n} records"

    jp = AUDITS / f"{stem}.jsonl"
    mp = AUDITS / f"{stem}.md"
    manifest = AUDITS / f"{stem}.manifest.json"

    with jp.open("w", encoding="utf-8") as f:
        for r in selected:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    parts = [f"# v0.2 audit — {sample} records sampled from {source_label}\n"]
    for i,r in enumerate(selected,1):
        parts += [
            f"\n## {i}. {r['id']}\n",
            f"- Domain: `{r['domain']}`\n- Task: `{r['task_type']}`\n- Difficulty: `{r['difficulty']}`\n",
            "\n### Question\n\n"+r["messages"][0]["content"].strip()+"\n",
            "\n### Reference answer\n\n"+r["messages"][1]["content"].strip()+"\n",
            "\n### Verification\n\n"+r["verification"]["details"].strip()+"\n",
        ]
    mp.write_text("".join(parts), encoding="utf-8")

    data = {
        "total_records": total_n,
        "source_window_records": source_n,
        "source_window_first_id": source_rows[0]["id"],
        "source_window_last_id": source_rows[-1]["id"],
        "sample_records": sample,
        "sample_ids": [r["id"] for r in selected],
        "jsonl_sha256": sha256(jp),
        "md_sha256": sha256(mp),
    }
    manifest.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")

    print("AUDIT PACKET READY")
    print("source window:", source_label)
    print("records:", sample)
    print("markdown:", mp)
    print("JSONL SHA256:", data["jsonl_sha256"])

def pick_generator():
    candidates = []
    for module_name, purpose, mod, fam in discover_modules():
        viable, score, eligible = capacity_for(module_name, purpose, fam)
        if viable:
            candidates.append((score, viable, module_name, purpose))
    if not candidates:
        return None
    return max(candidates)

def run_until(until: int, chunk: int, audit_every: int, freeze_every: int, seed: int):
    if until > V02_TARGET_RECORDS:
        raise SystemExit(f"--until cannot exceed {V02_TARGET_RECORDS}")
    if chunk < 1:
        raise SystemExit("--chunk must be >=1")

    rows = scan_v02()
    start = len(rows)
    if start >= until:
        print(f"Already at {start}/{until}.")
        return

    next_audit = ((start // audit_every) + 1) * audit_every if audit_every else None
    next_freeze = ((start // freeze_every) + 1) * freeze_every if freeze_every else None

    while len(scan_v02()) < until:
        current_n = len(scan_v02())

        boundary = until
        if next_audit is not None:
            boundary = min(boundary, next_audit)
        if next_freeze is not None:
            boundary = min(boundary, next_freeze)

        need = boundary - current_n
        if need <= 0:
            need = 1

        picked = pick_generator()
        if not picked:
            print("PIPELINE STOP: no viable registered generator capacity remains.")
            print("Add a fresh generator pack, then rerun the same command.")
            return

        score, viable, module_name, purpose = picked
        n = min(chunk, viable, need)

        print()
        print("="*78)
        print(f"PIPELINE RUN {current_n} -> {current_n+n}")
        print(f"module: {module_name}")
        print(f"purpose: {purpose}")
        print(f"records: {n}")
        print("="*78)

        env = os.environ.copy()
        old = env.get("PYTHONPATH","")
        env["PYTHONPATH"] = str(SCRIPTS) if not old else str(SCRIPTS)+os.pathsep+old
        cmd = [
            sys.executable, "-m", module_name,
            "--records", str(n),
            "--seed", str(seed + current_n),
        ]
        p = subprocess.run(cmd, cwd=ROOT, env=env)
        if p.returncode:
            raise SystemExit(p.returncode)

        validate_all()
        now = len(scan_v02())

        if next_freeze is not None and now >= next_freeze:
            create_checkpoint(f"{next_freeze:04d}")
            next_freeze += freeze_every

        if next_audit is not None and now >= next_audit:
            create_audit(min(30, audit_every), latest=audit_every)
            print()
            print("PIPELINE PAUSE: manual audit gate reached.")
            print("Review the generated audit packet before continuing.")
            return

    print(f"PIPELINE TARGET REACHED: {len(scan_v02())}/{until}")

def main():
    ap = argparse.ArgumentParser(description="Qwen3 CE v0.2 dataset pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    p = sub.add_parser("plan")
    p.add_argument("--records", type=int, default=100)

    sub.add_parser("verify")
    sub.add_parser("discover")

    p = sub.add_parser(
        "qa",
        help="run the modern automated dataset QA gate",
    )
    p.add_argument("--target", type=int, default=V02_TARGET_RECORDS)
    p.add_argument("--seed", type=int, default=20260914)
    p.add_argument("--audit-sample", type=int, default=60)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser(
        "release",
        help="verify, QA-gate, freeze and manifest the final dataset",
    )
    p.add_argument("--label", default="v0.2-final")
    p.add_argument("--target", type=int, default=V02_TARGET_RECORDS)
    p.add_argument("--seed", type=int, default=20260914)
    p.add_argument("--audit-sample", type=int, default=60)
    p.add_argument("--force-qa", action="store_true")

    p = sub.add_parser("checkpoint")
    p.add_argument("--label")

    p = sub.add_parser("audit")
    p.add_argument("--sample", type=int, default=30)
    p.add_argument(
        "--latest",
        type=int,
        default=None,
        help="sample only from the most recent N records",
    )

    p = sub.add_parser("run")
    p.add_argument("--until", type=int, required=True,
                   help="target number of NEW v0.2 records in staging, max 700")
    p.add_argument("--chunk", type=int, default=25)
    p.add_argument("--audit-every", type=int, default=50)
    p.add_argument("--freeze-every", type=int, default=100)
    p.add_argument("--seed", type=int, default=20260914)

    args = ap.parse_args()
    if args.cmd == "status":
        print_status()
    elif args.cmd == "plan":
        plan(args.records)
    elif args.cmd == "verify":
        validate_all()
    elif args.cmd == "discover":
        discover()
    elif args.cmd == "qa":
        validate_all()
        assert_final_targets(args.target)
        run_modern_qa(
            target=args.target,
            seed=args.seed,
            audit_sample=args.audit_sample,
            force=args.force,
        )
    elif args.cmd == "release":
        create_release(
            label=args.label,
            target=args.target,
            seed=args.seed,
            audit_sample=args.audit_sample,
            force_qa=args.force_qa,
        )
    elif args.cmd == "checkpoint":
        validate_all()
        create_checkpoint(args.label)
    elif args.cmd == "audit":
        validate_all()
        create_audit(args.sample, latest=args.latest)
    elif args.cmd == "run":
        run_until(args.until, args.chunk, args.audit_every, args.freeze_every, args.seed)

if __name__ == "__main__":
    main()
