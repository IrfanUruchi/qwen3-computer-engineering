from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import random

from .targets import (
    DOMAIN_TARGETS,
    DIFFICULTY_TARGETS,
    TASK_GROUP_TARGETS,
    TASK_GROUPS,
)
from .registry import GeneratorSpec
from .lineage import generator_id


def task_group(task_type: str) -> str:
    for group, members in TASK_GROUPS.items():
        if task_type in members:
            return group
    return "other"


class _MinCostFlow:
    def __init__(self):
        self.g = defaultdict(list)

    def add(self, u, v, cap: int, cost: int):
        a = [v, cap, cost, None, cap]
        b = [u, 0, -cost, a, 0]
        a[3] = b
        self.g[u].append(a)
        self.g[v].append(b)
        return a

    def flow(self, source, sink, required: int):
        sent = 0
        total_cost = 0

        while sent < required:
            dist = {source: 0}
            prev = {}
            inq = {source}
            q = deque([source])

            while q:
                u = q.popleft()
                inq.discard(u)
                for edge in self.g[u]:
                    v, cap, cost, rev, original = edge
                    if cap <= 0:
                        continue
                    nd = dist[u] + cost
                    if v not in dist or nd < dist[v]:
                        dist[v] = nd
                        prev[v] = (u, edge)
                        if v not in inq:
                            q.append(v)
                            inq.add(v)

            if sink not in dist:
                break

            add = required - sent
            v = sink
            while v != source:
                u, edge = prev[v]
                add = min(add, edge[1])
                v = u

            v = sink
            while v != source:
                u, edge = prev[v]
                edge[1] -= add
                edge[3][1] += add
                total_cost += add * edge[2]
                v = u

            sent += add

        return sent, total_cost


@dataclass
class ExactPlanner:
    existing: list[dict]
    specs: list[GeneratorSpec]
    seed: int
    excluded_ids: set[str] | None = None

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        self.excluded_ids = set(self.excluded_ids or ())
        self.domain_counts = Counter(r["domain"] for r in self.existing)
        self.difficulty_counts = Counter(r["difficulty"] for r in self.existing)
        self.group_counts = Counter(task_group(r["task_type"]) for r in self.existing)
        self.generator_counts = Counter()
        for r in self.existing:
            gid = generator_id(r)
            if gid:
                self.generator_counts[gid] += 1

    def available_specs(self):
        return [
            s for s in self.specs
            if s.id not in self.excluded_ids
            and self.generator_counts[s.id] < s.max_records
        ]

    def remaining_domains(self):
        return {
            d: max(0, t - self.domain_counts[d])
            for d, t in DOMAIN_TARGETS.items()
        }

    def remaining_groups(self):
        return {
            g: max(0, t - self.group_counts[g])
            for g, t in TASK_GROUP_TARGETS.items()
        }

    def remaining_difficulties(self):
        return {
            d: max(0, t - self.difficulty_counts[d])
            for d, t in DIFFICULTY_TARGETS.items()
        }

    def select_exact(self) -> list[tuple[GeneratorSpec, str]]:
        domain_need = self.remaining_domains()
        group_need = self.remaining_groups()
        needed = sum(domain_need.values())

        if sum(group_need.values()) != needed:
            raise RuntimeError(
                f"remaining task-group total {sum(group_need.values())} "
                f"does not equal remaining domain total {needed}"
            )

        flow = _MinCostFlow()
        S = ("source",)
        T = ("sink",)

        for d, n in domain_need.items():
            flow.add(S, ("domain", d), n, 0)

        assignment_edges = {}

        specs = list(self.available_specs())
        self.rng.shuffle(specs)

        for spec in specs:
            snode = ("scenario", spec.id)
            flow.add(("domain", spec.domain), snode, 1, 0)

            for group in spec.groups:
                if group not in group_need:
                    continue
                edge = flow.add(
                    snode,
                    ("group", group),
                    1,
                    int(spec.group_costs.get(group, 3)),
                )
                assignment_edges[(spec.id, group)] = edge

        for g, n in group_need.items():
            flow.add(("group", g), T, n, 0)

        sent, cost = flow.flow(S, T, needed)
        if sent != needed:
            raise RuntimeError(
                f"semantic task allocation infeasible: need {needed}, flow {sent}"
            )

        by_id = {s.id: s for s in specs}
        selected = []
        for (sid, group), edge in assignment_edges.items():
            # Original capacity was one. A used forward edge has residual zero.
            if edge[4] == 1 and edge[1] == 0:
                selected.append((by_id[sid], group))

        if len(selected) != needed:
            raise RuntimeError(
                f"planner internal error: selected {len(selected)} != {needed}"
            )

        self.rng.shuffle(selected)
        self.last_cost = cost
        return selected

    def assign_difficulties(
        self,
        selected: list[tuple[GeneratorSpec, str]],
    ) -> dict[str, str]:
        rem = self.remaining_difficulties()
        if sum(rem.values()) != len(selected):
            raise RuntimeError(
                f"remaining difficulty total {sum(rem.values())} "
                f"does not equal selected records {len(selected)}"
            )

        labels = []
        for d, n in rem.items():
            labels.extend([d] * n)
        self.rng.shuffle(labels)

        shuffled = list(selected)
        self.rng.shuffle(shuffled)

        return {
            spec.id: difficulty
            for (spec, group), difficulty in zip(shuffled, labels)
        }

    def capacity_report(self):
        available = self.available_specs()
        domain_capacity = Counter(s.domain for s in available)
        group_capacity = Counter()
        for s in available:
            for g in s.groups:
                group_capacity[g] += 1
        return {
            "available": len(available),
            "domain_capacity": dict(domain_capacity),
            "group_capacity": dict(group_capacity),
            "domain_need": self.remaining_domains(),
            "group_need": self.remaining_groups(),
            "difficulty_need": self.remaining_difficulties(),
        }
