#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from dataset_generation.generators import MODULES
for name in MODULES:
    importlib.import_module(f"dataset_generation.generators.{name}")

from dataset_generation.registry import all_generators
from dataset_generation.planner import ExactPlanner, task_group
from dataset_generation.dedupe import DedupeIndex
from dataset_generation.io import (
    scan_staging,
    next_record_number,
    next_batch_number,
    atomic_write_jsonl,
)
from dataset_generation.validation import validate_batch, target_report
from dataset_generation.audit import write_audit
from dataset_generation.targets import (
    DOMAIN_TARGETS,
    DIFFICULTY_TARGETS,
    TASK_GROUP_TARGETS,
)
from dataset_generation.lineage import generator_id
from dataset_generation.quality import lint_batch


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status():
    rows = scan_staging(ROOT)
    rep = target_report(rows)
    groups = Counter(task_group(r["task_type"]) for r in rows)

    print(f"records: {len(rows)}/{sum(DOMAIN_TARGETS.values())}")
    print("domains:")
    for d, t in DOMAIN_TARGETS.items():
        n = rep["domains"].get(d, 0)
        print(f"  {d:30s} {n:3d}/{t:3d} remaining {max(0,t-n):3d}")
    print("difficulty:")
    for d, t in DIFFICULTY_TARGETS.items():
        n = rep["difficulties"].get(d, 0)
        print(f"  {d:30s} {n:3d}/{t:3d} remaining {max(0,t-n):3d}")
    print("task groups:")
    for g, t in TASK_GROUP_TARGETS.items():
        n = groups[g]
        print(f"  {g:30s} {n:3d}/{t:3d} remaining {max(0,t-n):3d}")
    print("registered generators:", len(all_generators()))


def build_planner(existing, seed, excluded=None):
    return ExactPlanner(
        existing=existing,
        specs=all_generators(),
        seed=seed,
        excluded_ids=set(excluded or ()),
    )


def plan(target: int, seed: int):
    rows = scan_staging(ROOT)
    target = min(target, sum(DOMAIN_TARGETS.values()))
    print(f"current: {len(rows)}")
    print(f"target:  {target}")
    print(f"needed:  {max(0,target-len(rows))}")

    if target != sum(DOMAIN_TARGETS.values()):
        print("Exact planner currently targets the complete v0.2 target (700).")
        return

    planner = build_planner(rows, seed)
    report = planner.capacity_report()

    print("remaining domain quota:")
    for d, n in report["domain_need"].items():
        print(f"  {d:30s} need {n:3d} available {report['domain_capacity'].get(d,0):3d}")
    print("remaining task-group quota:")
    for g, n in report["group_need"].items():
        print(f"  {g:30s} need {n:3d} available {report['group_capacity'].get(g,0):3d}")
    print("remaining difficulty quota:")
    for d, n in report["difficulty_need"].items():
        print(f"  {d:30s} need {n:3d}")

    selected = planner.select_exact()
    diffs = planner.assign_difficulties(selected)

    print("EXACT PLAN FEASIBLE")
    print("selected generators:", len(selected))
    print("selected task groups:", dict(Counter(group for _, group in selected)))
    print("assigned difficulty:", dict(Counter(diffs.values())))


def run_external_validator(path: Path, *, quiet: bool = False):
    validator = ROOT / "scripts" / "validate_dataset.py"
    if not validator.exists():
        raise RuntimeError("scripts/validate_dataset.py is required")
    p = subprocess.run(
        [sys.executable, str(validator), str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if not quiet or p.returncode:
        print(p.stdout.strip())
    if p.returncode:
        raise RuntimeError(f"external validator failed: {path}")


def repair_staging():
    staging = ROOT / "data" / "staging" / "v0.2"
    quarantine = ROOT / ".research-local" / "dataset-generation" / "quarantine"
    invalid = []

    validator = ROOT / "scripts" / "validate_dataset.py"
    if not validator.exists():
        raise RuntimeError("scripts/validate_dataset.py is required")

    for path in sorted(staging.glob("batch-*.jsonl")):
        p = subprocess.run(
            [sys.executable, str(validator), str(path)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if p.returncode:
            invalid.append((path, p.stdout.strip()))

    if not invalid:
        print("STAGING VALID: no invalid batches found.")
        return

    quarantine.mkdir(parents=True, exist_ok=True)
    print(f"INVALID STAGING BATCHES: {len(invalid)}")

    for path, output in invalid:
        print()
        print(f"quarantining: {path}")
        print(output)
        destination = quarantine / path.name
        if destination.exists():
            destination.unlink()
        path.replace(destination)

        manifest = (
            ROOT
            / ".research-local"
            / "dataset-generation"
            / "manifests"
            / f"{path.stem}.json"
        )
        if manifest.exists():
            manifest_destination = quarantine / manifest.name
            if manifest_destination.exists():
                manifest_destination.unlink()
            manifest.replace(manifest_destination)

    print()
    print("REPAIR COMPLETE")
    print(f"quarantine: {quarantine}")
    print("Run `python scripts/generate_dataset.py status` next.")


def make_complete_plan(existing, target, seed):
    if target != sum(DOMAIN_TARGETS.values()):
        raise RuntimeError("exact production planner currently supports target=700")

    excluded = set()
    specs = all_generators()

    for planning_round in range(1, 80):
        planner = ExactPlanner(
            existing=existing,
            specs=specs,
            seed=seed + planning_round * 1009,
            excluded_ids=excluded,
        )
        selected = planner.select_exact()
        diff_by_id = planner.assign_difficulties(selected)

        dedupe = DedupeIndex(existing, threshold=0.92)
        next_num = next_record_number(existing)
        candidates = []
        collision = None

        rng = random.Random(seed + planning_round * 7919)

        for spec, assigned_group in selected:
            difficulty = diff_by_id[spec.id]
            accepted = None
            last_reason = None

            # Different seeds vary only the domain-appropriate operating context.
            # One scenario still contributes at most one accepted v0.2 record.
            for _ in range(8):
                local_seed = rng.getrandbits(63)
                cand = spec.fn(local_seed, difficulty, assigned_group)
                rid = f"ce-{cand.task_type}-{next_num:06d}"
                rec = cand.to_record(rid)
                last_reason = dedupe.reason(rec)
                if last_reason is None:
                    accepted = rec
                    break

            if accepted is None:
                collision = (spec.id, last_reason)
                break

            validate_batch([accepted])
            candidates.append(accepted)
            dedupe.add(accepted)
            next_num += 1

        if collision is not None:
            excluded.add(collision[0])
            print(
                f"planner retry: excluded {collision[0]} "
                f"because of {collision[1]}"
            )
            continue

        return candidates, excluded, planning_round

    raise RuntimeError(
        f"unable to build exact plan after excluding {len(excluded)} colliding generators"
    )


def verify_final_targets(final):
    rep = target_report(final)
    groups = Counter(task_group(r["task_type"]) for r in final)

    for d, t in DOMAIN_TARGETS.items():
        if rep["domains"].get(d, 0) != t:
            raise RuntimeError(
                f"final domain target not met: {d} "
                f"{rep['domains'].get(d,0)}/{t}"
            )

    for d, t in DIFFICULTY_TARGETS.items():
        if rep["difficulties"].get(d, 0) != t:
            raise RuntimeError(
                f"final difficulty target not met: {d} "
                f"{rep['difficulties'].get(d,0)}/{t}"
            )

    for g, t in TASK_GROUP_TARGETS.items():
        if groups[g] != t:
            raise RuntimeError(
                f"final task-group target not met: {g} {groups[g]}/{t}"
            )


def generate(target: int, seed: int, shard_size: int, audit_sample: int, dry_run: bool):
    existing = scan_staging(ROOT)
    if len(existing) >= target:
        print(f"already at {len(existing)}/{target}")
        return

    candidates, excluded, rounds = make_complete_plan(existing, target, seed)
    validate_batch(candidates)
    lint_batch(candidates)
    print("CONTENT QUALITY LINT PASS")

    final = existing + candidates
    verify_final_targets(final)

    # Canonical schema validation happens before anything is written to staging.
    local = ROOT / ".research-local" / "dataset-generation"
    preflight_dir = local / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    preflight_path = preflight_dir / f"candidate-{target:04d}.jsonl"
    atomic_write_jsonl(preflight_path, candidates)
    run_external_validator(preflight_path)
    print(f"SCHEMA PRECOMMIT PASS: {preflight_path}")

    print("PRECOMMIT PLAN PASS")
    print(f"new records:       {len(candidates)}")
    print(f"planning rounds:   {rounds}")
    print(f"excluded collisions: {len(excluded)}")
    print("new domains:", dict(Counter(r["domain"] for r in candidates)))
    print("new difficulty:", dict(Counter(r["difficulty"] for r in candidates)))
    print(
        "new task groups:",
        dict(Counter(task_group(r["task_type"]) for r in candidates)),
    )

    preflight_audit = preflight_dir / f"audit-{target:04d}.md"
    write_audit(
        candidates,
        preflight_audit,
        min(audit_sample, len(candidates)),
        seed,
    )
    print(f"PREFLIGHT AUDIT: {preflight_audit}")

    if dry_run:
        return

    batch_no = next_batch_number(ROOT)
    staging = ROOT / "data" / "staging" / "v0.2"
    local = ROOT / ".research-local" / "dataset-generation"
    manifests = local / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)

    offset = 0
    while offset < len(candidates):
        shard = candidates[offset:offset+shard_size]
        path = staging / f"batch-{batch_no:03d}.jsonl"
        atomic_write_jsonl(path, shard)
        run_external_validator(path)

        manifest = {
            "batch": batch_no,
            "records": len(shard),
            "ids": [r["id"] for r in shard],
            "sha256": sha256(path),
            "generators": dict(
                Counter((generator_id(r) or "unknown") for r in shard)
            ),
        }
        (manifests/f"batch-{batch_no:03d}.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"COMMITTED {path} records={len(shard)} "
            f"SHA256={manifest['sha256']}"
        )
        batch_no += 1
        offset += len(shard)

    audit_path = local / "audits" / f"audit-{target:04d}.md"
    write_audit(
        candidates,
        audit_path,
        min(audit_sample, len(candidates)),
        seed,
    )
    print(f"AUDIT {audit_path}")



def quarantine_batches(first_batch: int, last_batch: int, label: str):
    if first_batch > last_batch:
        raise ValueError("first batch must be <= last batch")

    staging = ROOT / "data" / "staging" / "v0.2"
    local = ROOT / ".research-local" / "dataset-generation"
    destination = local / "quarantine" / label
    destination.mkdir(parents=True, exist_ok=True)

    moved = 0
    for batch in range(first_batch, last_batch + 1):
        path = staging / f"batch-{batch:03d}.jsonl"
        if path.exists():
            target = destination / path.name
            if target.exists():
                raise RuntimeError(f"quarantine target already exists: {target}")
            path.replace(target)
            moved += 1
            print(f"QUARANTINED {path.name}")

        manifest = local / "manifests" / f"batch-{batch:03d}.json"
        if manifest.exists():
            target = destination / manifest.name
            if target.exists():
                raise RuntimeError(f"quarantine target already exists: {target}")
            manifest.replace(target)

    print(f"QUARANTINE COMPLETE: {moved} staging batches")
    print(f"location: {destination}")


def main():
    ap = argparse.ArgumentParser(description="Qwen3 CE dataset generator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("repair")

    p = sub.add_parser("quarantine")
    p.add_argument("--from-batch", type=int, required=True)
    p.add_argument("--to-batch", type=int, required=True)
    p.add_argument("--label", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--target", type=int, default=700)
    p.add_argument("--seed", type=int, default=20260914)

    p = sub.add_parser("generate")
    p.add_argument("--target", type=int, default=700)
    p.add_argument("--seed", type=int, default=20260914)
    p.add_argument("--shard-size", type=int, default=50)
    p.add_argument("--audit-sample", type=int, default=60)
    p.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()

    if args.cmd == "status":
        status()
    elif args.cmd == "repair":
        repair_staging()
    elif args.cmd == "quarantine":
        quarantine_batches(args.from_batch, args.to_batch, args.label)
    elif args.cmd == "plan":
        plan(args.target, args.seed)
    elif args.cmd == "generate":
        generate(
            args.target,
            args.seed,
            args.shard_size,
            args.audit_sample,
            args.dry_run,
        )


if __name__ == "__main__":
    main()
