from __future__ import annotations

from collections import Counter
from .targets import DOMAIN_TARGETS, DIFFICULTY_TARGETS


REQUIRED = {
    "id","version","split","domain","subdomain","task_type",
    "difficulty","messages","verification","source","tags"
}


def validate_record(r: dict):
    missing = REQUIRED - set(r)
    if missing:
        raise ValueError(f"{r.get('id','<no id>')}: missing {sorted(missing)}")
    if r["domain"] not in DOMAIN_TARGETS:
        raise ValueError(f"{r['id']}: invalid domain")
    if r["difficulty"] not in DIFFICULTY_TARGETS:
        raise ValueError(f"{r['id']}: invalid difficulty")
    if len(r["messages"]) != 2:
        raise ValueError(f"{r['id']}: expected 2 messages")
    if not r["messages"][0]["content"].strip():
        raise ValueError(f"{r['id']}: empty question")
    if not r["messages"][1]["content"].strip():
        raise ValueError(f"{r['id']}: empty answer")


def validate_batch(rows: list[dict]):
    ids = set()
    for r in rows:
        validate_record(r)
        if r["id"] in ids:
            raise ValueError(f"duplicate id {r['id']}")
        ids.add(r["id"])


def target_report(rows: list[dict]) -> dict:
    return {
        "records": len(rows),
        "domains": dict(Counter(r["domain"] for r in rows)),
        "difficulties": dict(Counter(r["difficulty"] for r in rows)),
        "task_types": dict(Counter(r["task_type"] for r in rows)),
    }
