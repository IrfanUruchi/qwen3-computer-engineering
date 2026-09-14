from __future__ import annotations

from .lineage import generator_id



SEMANTIC_FORBIDDEN = {
    ("embedded.dma_cache", "performance-analysis"): "DMA coherency is a correctness/diagnosis scenario, not performance-analysis",
    ("networking.syn_cookies", "performance-analysis"): "SYN-cookie scenario is admission/design/diagnosis, not a performance bottleneck task",
    ("distributed.log_compaction", "performance-analysis"): "log-compaction boundaries are recovery/correctness design, not performance-analysis",
    ("architecture.fence_cost", "code-repair"): "memory-fence cost should be performance/design oriented, not generic code-repair",
    ("linux.nofile", "implementation"): "LimitNOFILE headroom is configuration/capacity, not implementation code",
    ("os.cow_fault", "code-repair"): "copy-on-write fault classification is diagnosis/analysis, not a code-repair task",
    ("os.cow_fault", "implementation"): "copy-on-write fault classification is diagnosis/analysis, not an implementation task",
    ("networking.anycast", "implementation"): "anycast path/session handling is an architecture/design concern, not generic implementation",
    ("networking.anycast", "code-repair"): "anycast path/session handling is an architecture/design concern, not generic code-repair",
    ("architecture.dma_coherency", "performance-analysis"): "DMA coherency is correctness/ownership handling, not a performance-analysis task",
    ("software.cache_key_scope", "performance-analysis"): "cache-key tenant/variant isolation is a correctness/design concern, not a performance bottleneck task",
    ("networking.quic_migration", "performance-analysis"): "QUIC path migration is protocol/path-validation design, not a generic performance-analysis task",
}

GRAMMAR_SMELLS = (
    " tests shows ", " tests does ",
    " counters shows ", " counters does ",
    " timelines shows ", " timelines does ",
    " counts shows ", " counts does ",
    " values shows ", " values does ",
)

FORBIDDEN_PHRASES = (
    "A result that would weaken this diagnosis is reproducing the problem while",
    "The recommendation is valid only when",
    "A common mistake is ",
    "Avoid assuming ",
)


def has_explicit_falsifier(answer: str) -> bool:
    """Recognize the falsifier forms emitted by the content renderer.

    This intentionally checks semantic phrases rather than one exact template so
    style diversity does not make the quality gate reject valid records.
    """
    text = answer.lower()

    signatures = (
        # Performance variants.
        "performance hypothesis is weakened",
        "mechanism is unlikely to be the limiting path",
        "falsifying result would be unchanged poor performance",
        "interpretation is weakened",
        "measurements from",
        "do not use this model as the decision basis",

        # Debug/failure variants.
        "diagnosis is weakened",
        "investigate another cause",
        "falsifying observation would be the same failure",

        # Implementation/code-repair variants.
        "does not fully explain the remaining failure",
        "falsifying result would be recurrence of the defect",
        "investigation must move beyond this mechanism",

        # Architecture/design variants.
        "reconsider the design premise",
        "premise is weakened",
        "protected property changes independently of the mechanism",

        # Testing/configuration variants.
        "selected control is unlikely to be causal",
        "falsifying result is a correctly applied change",
        "reject the setting/test premise",
    )
    return any(signature in text for signature in signatures)


def lint_record(record: dict) -> list[str]:
    errors = []
    answer = record["messages"][1]["content"]
    question = record["messages"][0]["content"]
    domain = record["domain"]
    task = record["task_type"]
    subdomain = record["subdomain"]
    difficulty = record["difficulty"]
    gid = generator_id(record) or ""

    for phrase in FORBIDDEN_PHRASES:
        if phrase in answer:
            errors.append(f"forbidden legacy template phrase: {phrase!r}")

    if domain == "secure-engineering" and task == "performance-analysis":
        errors.append("secure-engineering scenario misclassified as performance-analysis")

    if (
        domain == "compute-model-infrastructure"
        and subdomain == "numerics"
        and task == "performance-analysis"
    ):
        errors.append("numerics scenario misclassified as performance-analysis")

    if domain == "engineering-reasoning" and task == "configuration":
        errors.append("engineering-reasoning scenario should be testing/decision/performance, not configuration")

    if difficulty in {"advanced", "expert"}:
        if "falsif" not in question.lower() and "invalidate" not in question.lower():
            errors.append("advanced/expert question does not request a falsifier")
        if not has_explicit_falsifier(answer):
            errors.append("advanced/expert answer lacks an explicit falsifier")

    if difficulty == "expert":
        if "failure boundary" not in question.lower():
            errors.append("expert question does not request failure boundary")
        if "second-order risk" not in question.lower():
            errors.append("expert question does not request second-order risk")
        if len(answer.split()) < 75:
            errors.append("expert answer is too short for requested depth")

    if gid == "security.jwt_alg" and task == "performance-analysis":
        errors.append("JWT algorithm-confusion task must not be performance-analysis")

    if gid == "compute.loss_scaler" and task == "performance-analysis":
        errors.append("loss-scaler correctness task must not be performance-analysis")

    semantic_error = SEMANTIC_FORBIDDEN.get((gid, task))
    if semantic_error:
        errors.append(semantic_error)

    answer_lower = " " + answer.lower() + " "
    for smell in GRAMMAR_SMELLS:
        if smell in answer_lower:
            errors.append(f"grammar smell in generated evidence sentence: {smell.strip()!r}")

    if gid == "embedded.rtc_drift" and "serialization" in answer.lower():
        errors.append("RTC drift expert risk incorrectly mentions serialization")
    if gid == "linux.mdraid_rebuild" and "accepted throughput" in answer.lower():
        errors.append("RAID rebuild expert risk incorrectly uses generic admission wording")
    if gid == "architecture.bitfield_layout" and "microarchitectural bottleneck" in answer.lower():
        errors.append("bitfield portability expert risk incorrectly uses generic microarchitecture wording")
    if gid == "compute.checkpoint_atomic" and "bottleneck between accelerator compute" in answer.lower():
        errors.append("checkpoint atomicity expert risk incorrectly uses generic accelerator bottleneck wording")
    if gid == "os.rcu_grace" and "stronger serialization" in answer.lower():
        errors.append("RCU grace-period expert risk incorrectly describes serialization instead of deferred reclamation")

    return errors


def lint_batch(records: list[dict]):
    failures = []
    for record in records:
        errs = lint_record(record)
        if errs:
            failures.append((record["id"], errs))

    if failures:
        lines = ["CONTENT QUALITY LINT FAILED"]
        for rid, errs in failures[:30]:
            lines.append(f"{rid}:")
            for err in errs:
                lines.append(f"  - {err}")
        if len(failures) > 30:
            lines.append(f"... {len(failures)-30} more failing records")
        raise RuntimeError("\n".join(lines))
