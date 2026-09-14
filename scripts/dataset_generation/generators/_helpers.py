from __future__ import annotations

import random


def pick(seed: int, values):
    return random.Random(seed).choice(list(values))


def rng(seed: int):
    return random.Random(seed)
