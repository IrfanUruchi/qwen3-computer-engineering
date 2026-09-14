from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .record import Candidate

GeneratorFn = Callable[[int, str, str], Candidate]


@dataclass(frozen=True)
class GeneratorSpec:
    id: str
    domain: str
    groups: tuple[str, ...]
    group_costs: dict[str, int]
    weight: float
    max_records: int
    fn: GeneratorFn


_REGISTRY: dict[str, GeneratorSpec] = {}


def generator(
    *,
    id: str,
    domain: str,
    groups: tuple[str, ...],
    group_costs: dict[str, int],
    weight: float = 1.0,
    max_records: int = 1,
):
    def wrap(fn: GeneratorFn):
        if id in _REGISTRY:
            raise RuntimeError(f"duplicate generator id: {id}")
        _REGISTRY[id] = GeneratorSpec(
            id=id,
            domain=domain,
            groups=tuple(groups),
            group_costs=dict(group_costs),
            weight=float(weight),
            max_records=int(max_records),
            fn=fn,
        )
        return fn
    return wrap


def all_generators() -> list[GeneratorSpec]:
    return list(_REGISTRY.values())
