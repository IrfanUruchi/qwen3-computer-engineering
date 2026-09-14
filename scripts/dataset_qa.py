#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from dataset_generation.generators import MODULES
for _name in MODULES:
    importlib.import_module(f"dataset_generation.generators.{_name}")

from dataset_generation.registry import all_generators
from dataset_generation.planner import task_group
from dataset_generation.io import scan_staging, read_jsonl
from dataset_generation.validation import validate_batch
from dataset_generation.dedupe import DedupeIndex
from dataset_generation.lineage import generator_id
from dataset_generation.quality import lint_record, lint_batch
from dataset_generation.targets import (
    DOMAIN_TARGETS,
    DIFFICULTY_TARGETS,
    TASK_GROUP_TARGETS,
)
from dataset_generation.generators._scenario import GROUP_OVERRIDES, RISK_OVERRIDES

try:
    from dataset_generation.quality import SEMANTIC_FORBIDDEN
except ImportError:
    SEMANTIC_FORBIDDEN = {}


DIFFICULTIES = ("intermediate", "advanced", "expert")


def stable_seed(*parts: str) -> int:
    raw = "|".join(parts).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:16], 16)


def fail(message: str):
    raise RuntimeError(message)


def generator_matrix() -> tuple[list[dict], list[str]]:
    records = []
    errors = []
    specs = all_generators()
    seen_ids = set()

    for index, spec in enumerate(specs, 1):
        if spec.id in seen_ids:
            errors.append(f"duplicate generator id: {spec.id}")
        seen_ids.add(spec.id)

        if not spec.groups:
            errors.append(f"{spec.id}: no supported task groups")
            continue

        unknown_costs = set(spec.group_costs) - set(spec.groups)
        if unknown_costs:
            errors.append(
                f"{spec.id}: group_costs contains unsupported groups: "
                f"{sorted(unknown_costs)}"
            )

        key = spec.id.rsplit(".", 1)[-1]
        override = GROUP_OVERRIDES.get((spec.domain, key))
        if override is not None:
            expected = set(override)
            actual = set(spec.groups)
            if actual != expected:
                errors.append(
                    f"{spec.id}: override not registered: "
                    f"expected groups={sorted(expected)} actual={sorted(actual)}"
                )

        for group in spec.groups:
            for difficulty in DIFFICULTIES:
                seed = stable_seed(spec.id, group, difficulty)
                try:
                    candidate = spec.fn(seed, difficulty, group)
                except Exception as exc:
                    errors.append(
                        f"{spec.id}/{group}/{difficulty}: generator raised "
                        f"{type(exc).__name__}: {exc}"
                    )
                    continue

                if candidate.domain != spec.domain:
                    errors.append(
                        f"{spec.id}/{group}/{difficulty}: candidate domain "
                        f"{candidate.domain!r} != registry domain {spec.domain!r}"
                    )

                actual_group = task_group(candidate.task_type)
                if actual_group != group:
                    errors.append(
                        f"{spec.id}/{group}/{difficulty}: task_type "
                        f"{candidate.task_type!r} maps to {actual_group!r}"
                    )

                forbidden = SEMANTIC_FORBIDDEN.get(
                    (spec.id, candidate.task_type)
                )
                if forbidden:
                    errors.append(
                        f"{spec.id}/{group}/{difficulty}: forbidden semantic "
                        f"pair produced: {candidate.task_type}: {forbidden}"
                    )

                record = candidate.to_record(f"ce-qa-{index:04d}-{len(records):05d}")
                record_errors = lint_record(record)
                if record_errors:
                    errors.append(
                        f"{spec.id}/{group}/{difficulty}: lint failed: "
                        + "; ".join(record_errors)
                    )
                records.append(record)

    return records, errors


def forbidden_rule_self_test() -> list[str]:
    errors = []
    by_id = {s.id: s for s in all_generators()}

    for (gid, forbidden_task), expected_message in SEMANTIC_FORBIDDEN.items():
        spec = by_id.get(gid)
        if spec is None:
            errors.append(
                f"semantic-forbidden rule references unknown generator: {gid}"
            )
            continue

        group = spec.groups[0]
        candidate = spec.fn(
            stable_seed(gid, "negative-lint"),
            "intermediate",
            group,
        )
        record = candidate.to_record("ce-qa-negative-000001")
        record["task_type"] = forbidden_task

        got = lint_record(record)
        if expected_message not in got:
            errors.append(
                f"{gid}/{forbidden_task}: linter does not enforce its own "
                f"SEMANTIC_FORBIDDEN rule; expected {expected_message!r}, got {got!r}"
            )

    return errors


def run_generator_tests():
    records, errors = generator_matrix()
    errors.extend(forbidden_rule_self_test())

    if errors:
        print("GENERATOR CONTRACT TESTS: FAIL")
        for e in errors[:80]:
            print("  -", e)
        if len(errors) > 80:
            print(f"  ... {len(errors)-80} more")
        fail(f"{len(errors)} generator/semantic contract failures")

    # Batch lint catches cross-record policy if more checks are added later.
    lint_batch(records)

    print(
        "GENERATOR CONTRACT TESTS: PASS "
        f"({len(all_generators())} generators, {len(records)} render cases)"
    )


def run_preflight(target: int, seed: int, sample: int):
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_dataset.py"),
        "generate",
        "--target", str(target),
        "--seed", str(seed),
        "--dry-run",
        "--audit-sample", str(sample),
    ]
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(p.stdout.rstrip())
    if p.returncode:
        fail("dataset dry-run failed")


def verify_candidate(target: int):
    preflight = (
        ROOT / ".research-local" / "dataset-generation" / "preflight"
        / f"candidate-{target:04d}.jsonl"
    )
    if not preflight.exists():
        fail(f"missing preflight candidate: {preflight}")

    candidates = read_jsonl(preflight)
    existing = scan_staging(ROOT)

    validate_batch(candidates)
    lint_batch(candidates)

    # Dedupe again independently of the generation loop.
    dedupe = DedupeIndex(existing, threshold=0.92)
    for r in candidates:
        reason = dedupe.reason(r)
        if reason:
            fail(f"{r['id']}: independent dedupe failed: {reason}")
        dedupe.add(r)

    final = existing + candidates

    domain_counts = Counter(r["domain"] for r in final)
    difficulty_counts = Counter(r["difficulty"] for r in final)
    group_counts = Counter(task_group(r["task_type"]) for r in final)

    if domain_counts != Counter(DOMAIN_TARGETS):
        fail(
            "domain target mismatch: "
            f"got={dict(domain_counts)} expected={DOMAIN_TARGETS}"
        )
    if difficulty_counts != Counter(DIFFICULTY_TARGETS):
        fail(
            "difficulty target mismatch: "
            f"got={dict(difficulty_counts)} expected={DIFFICULTY_TARGETS}"
        )
    if group_counts != Counter(TASK_GROUP_TARGETS):
        fail(
            "task-group target mismatch: "
            f"got={dict(group_counts)} expected={TASK_GROUP_TARGETS}"
        )

    # Actual candidate semantic pair check, independent of lint implementation.
    bad = []
    for r in candidates:
        gid = generator_id(r) or ""
        pair = (gid, r["task_type"])
        if pair in SEMANTIC_FORBIDDEN:
            bad.append((r["id"], gid, r["task_type"], SEMANTIC_FORBIDDEN[pair]))
    if bad:
        lines = [
            f"{rid}: {gid}/{task}: {msg}"
            for rid, gid, task, msg in bad
        ]
        fail("candidate contains forbidden semantic mappings:\n" + "\n".join(lines))

    print(
        "FULL CANDIDATE TESTS: PASS "
        f"({len(candidates)} candidates, final={len(final)})"
    )
    return candidates


def stratified_sample(rows: list[dict], sample: int, seed: int) -> list[dict]:
    rng = random.Random(seed ^ 0x51A71F1E)
    chosen = []
    seen = set()

    by_gid = {generator_id(r) or "": r for r in rows}
    priority_ids = set()

    # Any scenario with a manual semantic or expert-risk override is automatically
    # high priority for review.
    for r in rows:
        gid = generator_id(r) or ""
        key = gid.rsplit(".", 1)[-1] if gid else ""
        if (r["domain"], key) in GROUP_OVERRIDES or key in RISK_OVERRIDES:
            priority_ids.add(r["id"])

    for r in rows:
        if r["id"] in priority_ids and r["id"] not in seen:
            chosen.append(r)
            seen.add(r["id"])

    def add_one_per(key_fn):
        buckets = defaultdict(list)
        for r in rows:
            if r["id"] not in seen:
                buckets[key_fn(r)].append(r)
        keys = list(buckets)
        rng.shuffle(keys)
        for key in keys:
            if len(chosen) >= sample:
                return
            options = buckets[key]
            r = rng.choice(options)
            if r["id"] not in seen:
                chosen.append(r)
                seen.add(r["id"])

    # Cover broad semantic axes before random fill.
    add_one_per(lambda r: (r["domain"], r["difficulty"]))
    add_one_per(lambda r: (task_group(r["task_type"]), r["difficulty"]))
    add_one_per(lambda r: r["domain"])
    add_one_per(lambda r: task_group(r["task_type"]))

    remaining = [r for r in rows if r["id"] not in seen]
    rng.shuffle(remaining)
    chosen.extend(remaining[: max(0, sample - len(chosen))])

    return chosen[:sample]


def write_qa_audit(rows: list[dict], target: int, sample: int, seed: int):
    selected = stratified_sample(rows, sample, seed)
    out_dir = ROOT / ".research-local" / "dataset-generation" / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)

    md = out_dir / f"qa-audit-{target:04d}.md"
    js = out_dir / f"qa-report-{target:04d}.json"

    parts = [
        f"# Dataset QA audit — {len(selected)} records\n",
        "\nAutomatically prioritized semantic/risk overrides, then stratified by "
        "domain, difficulty, and task group.\n",
    ]
    for i, r in enumerate(selected, 1):
        parts += [
            f"\n## {i}. {r['id']}\n",
            f"- Domain: `{r['domain']}`\n",
            f"- Task: `{r['task_type']}`\n",
            f"- Group: `{task_group(r['task_type'])}`\n",
            f"- Difficulty: `{r['difficulty']}`\n",
            f"- Generator: `{generator_id(r) or 'unknown'}`\n",
            "\n### Question\n\n" + r["messages"][0]["content"].strip() + "\n",
            "\n### Reference answer\n\n" + r["messages"][1]["content"].strip() + "\n",
            "\n### Verification\n\n" + r["verification"]["details"].strip() + "\n",
        ]
    md.write_text("".join(parts), encoding="utf-8")

    report = {
        "target": target,
        "candidate_records": len(rows),
        "audit_records": len(selected),
        "domains": dict(Counter(r["domain"] for r in rows)),
        "difficulties": dict(Counter(r["difficulty"] for r in rows)),
        "task_groups": dict(Counter(task_group(r["task_type"]) for r in rows)),
        "priority_generators_in_audit": sorted({
            generator_id(r) for r in selected
            if generator_id(r)
            and (
                (r["domain"], generator_id(r).rsplit(".", 1)[-1]) in GROUP_OVERRIDES
                or generator_id(r).rsplit(".", 1)[-1] in RISK_OVERRIDES
            )
        }),
    }
    js.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"QA AUDIT: {md}")
    print(f"QA REPORT: {js}")

    windows_downloads = Path("/mnt/c/Users/Irfan/Downloads")
    if windows_downloads.exists():
        dst = windows_downloads / md.name
        dst.write_bytes(md.read_bytes())
        print(f"QA AUDIT COPIED: {dst}")


def main():
    ap = argparse.ArgumentParser(
        description="Automated QA gate for Qwen3 CE dataset generation"
    )
    ap.add_argument("--target", type=int, default=700)
    ap.add_argument("--seed", type=int, default=20260914)
    ap.add_argument("--audit-sample", type=int, default=60)
    ap.add_argument(
        "--skip-preflight",
        action="store_true",
        help="test current preflight candidate without regenerating it",
    )
    args = ap.parse_args()

    run_generator_tests()

    if not args.skip_preflight:
        run_preflight(args.target, args.seed, args.audit_sample)

    rows = verify_candidate(args.target)
    write_qa_audit(rows, args.target, args.audit_sample, args.seed)

    print()
    print("DATASET QA GATE: PASS")


if __name__ == "__main__":
    main()
