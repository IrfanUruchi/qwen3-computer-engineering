from __future__ import annotations

import re


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\d+(?:\.\d+)?", "<n>", text)
    text = re.sub(r"[^a-z0-9<>_+./ -]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> set[str]:
    return set(normalize(text).split())


def jaccard(a: str, b: str) -> float:
    A, B = tokens(a), tokens(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


class DedupeIndex:
    def __init__(self, existing: list[dict], threshold: float = 0.92):
        self.threshold = threshold
        self.exact = set()
        self.by_domain_task: dict[tuple[str, str], list[str]] = {}

        for r in existing:
            q = r["messages"][0]["content"]
            self.exact.add(normalize(q))
            key = (r["domain"], r["task_type"])
            self.by_domain_task.setdefault(key, []).append(q)

    def reason(self, candidate: dict) -> str | None:
        q = candidate["messages"][0]["content"]
        nq = normalize(q)
        if nq in self.exact:
            return "exact-normalized-duplicate"

        key = (candidate["domain"], candidate["task_type"])
        for old in self.by_domain_task.get(key, []):
            if jaccard(q, old) >= self.threshold:
                return "same-domain-task-near-duplicate"
        return None

    def add(self, record: dict):
        q = record["messages"][0]["content"]
        self.exact.add(normalize(q))
        key = (record["domain"], record["task_type"])
        self.by_domain_task.setdefault(key, []).append(q)
