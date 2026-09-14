#!/usr/bin/env python3
from dataset_generation.quality import has_explicit_falsifier
from dataset_generation.generators._scenario import Scenario, falsifier

s = Scenario(
    key="lint-self-test",
    subdomain="test",
    focus="test mechanism",
    mechanism="a controlled mechanism exists",
    evidence="controlled counters and traces",
    action="apply the bounded remediation",
    pitfall="one symptom is not sufficient proof",
    contexts=("test context",),
)

groups = (
    "performance",
    "debug-failure",
    "implementation-code",
    "architecture-design",
    "testing-config",
)

# _variant() deterministically selects one form, so also directly test every
# signature family accepted by the linter.
samples = [
    "The performance hypothesis is weakened if the expected evidence is absent.",
    "This mechanism is unlikely to be the limiting path.",
    "A falsifying result would be unchanged poor performance.",
    "This diagnosis is weakened if the failure reproduces.",
    "Investigate another cause.",
    "A falsifying observation would be the same failure.",
    "This mechanism does not fully explain the remaining failure.",
    "A falsifying result would be recurrence of the defect.",
    "The investigation must move beyond this mechanism.",
    "Reconsider the design premise if the relationship is absent.",
    "The premise is weakened by the controlled result.",
    "The protected property changes independently of the mechanism.",
    "The selected control is unlikely to be causal.",
    "A falsifying result is a correctly applied change with no improvement.",
    "Reject the setting/test premise rather than widening rollout.",
]

for text in samples:
    assert has_explicit_falsifier(text), text

for group in groups:
    text = falsifier(s, group)
    assert has_explicit_falsifier(text), (group, text)

print("dataset quality lint self-test: PASS")
