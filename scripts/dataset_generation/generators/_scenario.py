from __future__ import annotations

from dataclasses import dataclass
import random
import re

from ..record import Candidate
from ..registry import generator


GROUPS = (
    "implementation-code",
    "debug-failure",
    "performance",
    "architecture-design",
    "testing-config",
)


@dataclass(frozen=True)
class Scenario:
    key: str
    subdomain: str
    focus: str
    mechanism: str
    evidence: str
    action: str
    pitfall: str
    contexts: tuple[str, ...]


PERF_MARKERS = (
    "latency", "throughput", "bandwidth", "cache", "tlb", "prefetch",
    "contention", "saturation", "scaling efficiency", "queue depth",
    "batch size", "numa", "readahead", "writeback", "reclaim",
    "compaction", "throttling", "migration", "false sharing", "branch",
    "atomic hotspot", "pcie", "dram", "bank conflict", "frontend",
    "pipeline bubble", "straggler", "kernel launch", "fusion", "offload",
    "receive window", "bandwidth delay", "bufferbloat", "rss", "rps",
    "rebuild", "utilization", "energy", "cost per", "little's law",
    "amdahl", "gustafson", "capacity", "tail latency",
)

IMPL_MARKERS = (
    "read", "write", "file", "socket", "signal", "mutex", "lock", "timer",
    "dma", "i2c", "spi", "uart", "can", "flash", "boot", "path", "auth",
    "token", "retry", "transaction", "outbox", "checkpoint", "snapshot",
    "rcu", "futex", "event", "epoll", "mmap", "descriptor", "process",
    "fork", "pipe", "memory ordering", "protocol", "tls", "dns", "mmio",
    "io uring", "allocation", "realloc", "errno", "seccomp",
    "deserialization",
)

FAIL_MARKERS = (
    "race", "fault", "failure", "stall", "deadlock", "starvation",
    "overflow", "thrash", "corrupt", "stale", "blackhole", "exhaust",
    "drop", "drift", "mismatch", "pressure", "split brain", "lag",
    "overrun", "alias", "bounce", "throttle", "truncation", "reuse",
    "stuck", "loss", "wrap", "owner death", "oom", "reclaim", "watchdog",
)

DESIGN_MARKERS = (
    "policy", "placement", "shard", "partition", "quorum", "replica",
    "consistency", "isolation", "sandbox", "security", "rollout",
    "recovery", "availability", "redundancy", "scheduling", "affinity",
    "topology", "layout", "migration", "admission", "backpressure",
    "fencing", "lease", "hashing", "checkpoint", "congestion", "routing",
    "namespace", "cgroup", "capability", "membership", "idempotency",
    "key rotation",
)

CONFIG_MARKERS = (
    "systemd", "sysctl", "cgroup", "timeout", "limit", "watchdog", "mtu",
    "tls", "irq", "affinity", "mount", "journald", "keepalive",
    "rate limiting", "clock stretching", "window limits", "restart",
    "hugepage",
)


DOMAIN_CONTEXTS = {
    "software-engineering": (
        "In a production backend service",
        "During a controlled service canary",
        "In an integration environment that reproduces production traffic",
    ),
    "systems-programming": (
        "In a POSIX/Linux userspace component",
        "During a syscall-level integration test",
        "In a multithreaded native service",
    ),
    "operating-systems": (
        "On a Linux host under reproducible load",
        "During a controlled kernel/runtime investigation",
        "On a host where scheduler and memory telemetry are available",
    ),
    "computer-architecture": (
        "On a multicore system under a controlled benchmark",
        "During a hardware-counter performance study",
        "On a system where the memory hierarchy and topology are known",
    ),
    "linux-infrastructure": (
        "On a Linux production host",
        "During a controlled service rollout",
        "In a reproducible Linux operations test",
    ),
    "embedded-systems": (
        "On an embedded target with logic-analyzer or scope access",
        "During a firmware hardware-in-the-loop test",
        "On an MCU-based device under controlled timing and power conditions",
    ),
    "networking": (
        "On a controlled production-like network path",
        "During a packet-capture-backed integration test",
        "On a service where endpoint and network telemetry are available",
    ),
    "distributed-systems": (
        "In a replicated service during a controlled failure test",
        "During a partition/recovery exercise in a distributed system",
        "In a production-like cluster with per-node traces",
    ),
    "compute-model-infrastructure": (
        "In a GPU/ML workload under profiler capture",
        "During a controlled training or inference benchmark",
        "On a compute node with host, accelerator, and interconnect telemetry",
    ),
    "secure-engineering": (
        "During a security review of a service",
        "In an adversarial integration test",
        "During a controlled validation of a security boundary",
    ),
    "engineering-reasoning": (
        "During a capacity and reliability review",
        "In a controlled engineering A/B study",
        "While evaluating an operational design against an explicit SLO",
    ),
}



# Explicit audit-proven task semantics. Broad inference remains useful, but it
# must not override scenarios whose correct task family is known.
GROUP_OVERRIDES = {
    ("embedded-systems", "dma_cache"): {
        "implementation-code": 0,
        "debug-failure": 0,
        "testing-config": 2,
    },
    ("networking", "syn_cookies"): {
        "architecture-design": 0,
        "debug-failure": 1,
        "testing-config": 1,
    },
    ("distributed-systems", "log_compaction"): {
        "architecture-design": 0,
        "implementation-code": 1,
        "testing-config": 1,
    },
    ("computer-architecture", "fence_cost"): {
        "performance": 0,
        "architecture-design": 1,
        "testing-config": 2,
    },
    ("linux-infrastructure", "nofile"): {
        "testing-config": 0,
        "architecture-design": 1,
        "debug-failure": 2,
    },
    ("operating-systems", "cow_fault"): {
        "debug-failure": 0,
        "testing-config": 1,
    },
    ("networking", "anycast"): {
        "architecture-design": 0,
        "testing-config": 1,
        "debug-failure": 2,
    },
    ("computer-architecture", "dma_coherency"): {
        "implementation-code": 0,
        "debug-failure": 0,
        "testing-config": 2,
    },
    ("software-engineering", "cache_key_scope"): {
        "architecture-design": 0,
        "implementation-code": 1,
        "testing-config": 1,
    },
    ("networking", "quic_migration"): {
        "architecture-design": 0,
        "implementation-code": 1,
        "debug-failure": 1,
    },
}

RISK_OVERRIDES = {
    "rtc_drift": (
        "More frequent synchronization or aggressive correction can increase power/network use "
        "and can disturb wall-clock behavior; verify offline behavior, monotonic timers, and the "
        "time-correction policy as well as long-term drift."
    ),
    "mdraid_rebuild": (
        "Throttling rebuild reduces foreground I/O interference but extends the period of degraded "
        "redundancy; accelerating it shortens exposure while increasing device load and foreground "
        "latency. Measure both rebuild completion time and application SLOs."
    ),
    "nofile": (
        "Raising the descriptor limit can let leaks or runaway connection growth consume kernel "
        "memory and downstream capacity, so descriptor growth, memory pressure, and dependency "
        "limits must be monitored after the change."
    ),
    "sysctl_scope": (
        "Changing a host-global sysctl for one workload can alter unrelated services, while a "
        "namespaced setting may not exist for every tunable; validate effective scope and rollback "
        "impact before rollout."
    ),
    "watchdog_progress": (
        "A progress rule that is too strict can trigger false resets during legitimate long work, "
        "while one that is too permissive can still mask hangs; validate both worst-case healthy "
        "latency and induced deadlock behavior."
    ),
    "dns_negative": (
        "Lowering negative-cache TTLs or flushing caches can increase resolver/query load, and "
        "other resolver/runtime caches may still retain stale answers; measure query rate and "
        "refresh behavior at every cache layer."
    ),
    "election_timeout": (
        "Longer election timeouts reduce false elections but slow leader-failure detection and "
        "failover; shorter values improve detection time while risking instability under normal "
        "latency and pause variance."
    ),
    "failover_headroom": (
        "Extra failover headroom increases idle capacity cost, while insufficient reserve can "
        "overload survivors during a fault; validate both normal-efficiency cost and degraded-mode SLOs."
    ),
    "bitfield_layout": (
        "Explicit masks/shifts improve portability but can duplicate register/protocol definitions "
        "and drift from the specification if constants are maintained in multiple places; keep one "
        "authoritative definition and test known encodings across compilers/architectures."
    ),
    "checkpoint_atomic": (
        "Atomic publication can increase temporary storage use and checkpoint I/O latency because old "
        "and new state may coexist until commit; validate free-space headroom, interruption recovery, "
        "and checkpoint-time impact."
    ),
    "rcu_grace": (
        "Deferring reclamation until a grace period completes can retain removed objects longer and "
        "increase memory pressure when readers stall; monitor grace-period latency, callback backlog, "
        "and resident memory under worst-case reader behavior."
    ),
    "gossip": (
        "Increasing fanout or shortening gossip intervals can improve convergence while increasing "
        "network traffic and per-node processing; reducing them saves overhead but extends convergence "
        "time and stale-membership exposure. Measure both convergence and traffic cost."
    ),
    "continuous_batch": (
        "Tighter fairness or memory-admission limits can protect tail latency and KV-cache capacity "
        "while reducing peak batching efficiency or rejecting bursts; measure throughput, queue age, "
        "tail latency, and rejection rate together."
    ),

    "retry_storm": (
        "Backoff that is too conservative can slow recovery after the dependency is healthy, "
        "while backoff that is too aggressive can recreate the storm; measure both retry volume "
        "and recovery latency."
    ),
    "circuit_probe": (
        "Too few or too-slow probes can delay recovery, while reopening too quickly can overload "
        "the dependency again; validate both recovery time and dependency saturation."
    ),
    "prefetch_pollution": (
        "Reducing prefetch too aggressively can increase demand misses and expose memory latency, "
        "so recheck miss rate, bandwidth, and end-to-end runtime after the change."
    ),
    "mmap_shared": (
        "Stronger synchronization or durability operations can add write latency and reduce "
        "throughput, so crash safety and steady-state performance must both be measured."
    ),
    "io_uring_lifetime": (
        "Keeping buffers alive or registered for longer can increase pinned/resident memory and "
        "reduce allocator flexibility, so memory pressure must be measured with the fix enabled."
    ),
    "short_write": (
        "A repair that retries without correct readiness handling can busy-spin on EAGAIN; verify "
        "CPU use and progress under backpressure."
    ),
    "sendfile_partial": (
        "A repair that retries without correct readiness handling can busy-spin on EAGAIN; verify "
        "CPU use and transfer progress under a deliberately slow receiver."
    ),
    "sigpipe": (
        "Changing SIGPIPE handling process-wide can affect unrelated libraries or threads, so keep "
        "the policy as scoped as the platform permits and test other write paths."
    ),
    "aligned_alloc": (
        "Stricter alignment can waste memory or increase allocator fragmentation, so measure "
        "resident memory and allocation failure rate as well as correctness."
    ),
    "eventfd_counter": (
        "Replacing counter semantics with a per-event queue can increase memory use and introduce "
        "new backpressure, so queue depth and consumer lag must remain bounded."
    ),
    "journald_rate": (
        "Stronger log suppression can hide the diagnostics needed during an incident, so critical "
        "health signals need a separately reliable path and suppression counters must be monitored."
    ),
    "cgroup_pids": (
        "Tighter process limits can reject legitimate burst workers, while looser limits increase "
        "the blast radius of runaway spawning; validate both peak demand and failure containment."
    ),
    "oom_score": (
        "Protecting one process from OOM shifts victim risk to other eligible processes; verify that "
        "the remaining victim set still allows the system to recover safely."
    ),
    "flash_wear": (
        "Wear-leveling and log rotation consume extra metadata/space and complicate power-loss "
        "recovery, so endurance gains must be tested together with recovery correctness."
    ),
    "bdp_window": (
        "Larger socket buffers consume more memory and can increase standing queues; tune only to "
        "the amount of in-flight data needed for the path and recheck latency under congestion."
    ),
    "loss_scaler": (
        "A scale policy that is too conservative can skip useful updates or slow convergence, while "
        "aggressive regrowth can reintroduce overflow; monitor skipped steps and training progress."
    ),
}


def _normalized_text(value: str) -> str:
    return re.sub(r"[_-]+", " ", value.lower())


def _contains(text: str, markers) -> bool:
    text = _normalized_text(text)
    for marker in markers:
        marker = _normalized_text(marker)
        if re.search(r"(?<![a-z0-9])" + re.escape(marker) + r"(?![a-z0-9])", text):
            return True
    return False


def _text(s: Scenario) -> str:
    return " ".join((s.key, s.subdomain, s.focus)).lower()


def supported_groups(
    s: Scenario,
    domain: str,
) -> tuple[tuple[str, ...], dict[str, int]]:
    override = GROUP_OVERRIDES.get((domain, s.key))
    if override is not None:
        ordered = tuple(
            sorted(override, key=lambda g: (override[g], GROUPS.index(g)))
        )
        return ordered, dict(override)

    text = _text(s)
    groups = {"testing-config"}
    costs = {"testing-config": 2}

    # Broad domain-appropriate fallbacks. These are lower priority than an
    # explicit semantic marker but keep the exact planner feasible.
    if domain == "engineering-reasoning":
        groups.update({"performance", "architecture-design"})
        costs.update({"performance": 1, "architecture-design": 1})
    elif domain == "secure-engineering":
        groups.update({"implementation-code", "debug-failure", "architecture-design"})
        costs.update({
            "implementation-code": 1,
            "debug-failure": 1,
            "architecture-design": 1,
        })
    else:
        groups.update({"implementation-code", "debug-failure"})
        costs.update({"implementation-code": 1, "debug-failure": 1})

    if _contains(text, IMPL_MARKERS):
        groups.add("implementation-code")
        costs["implementation-code"] = 0

    if _contains(text, FAIL_MARKERS):
        groups.add("debug-failure")
        costs["debug-failure"] = 0

    performance_candidate = (
        _contains(text, PERF_MARKERS)
        or s.subdomain in {
            "performance-modeling", "queueing", "capacity", "efficiency", "measurement"
        }
    )
    if domain == "secure-engineering":
        performance_candidate = False
    if domain == "compute-model-infrastructure" and s.subdomain == "numerics":
        performance_candidate = False

    if performance_candidate:
        groups.add("performance")
        costs["performance"] = 0

    if (
        _contains(text, DESIGN_MARKERS)
        or domain in {"distributed-systems", "secure-engineering", "engineering-reasoning"}
    ):
        groups.add("architecture-design")
        costs["architecture-design"] = 0 if _contains(text, DESIGN_MARKERS) else 1

    if _contains(text, CONFIG_MARKERS):
        costs["testing-config"] = 0
    elif domain == "linux-infrastructure":
        costs["testing-config"] = 1

    ordered = tuple(sorted(groups, key=lambda g: (costs[g], GROUPS.index(g))))
    return ordered, costs


def choose_task_type(s: Scenario, domain: str, group: str) -> str:
    text = _text(s)

    if group == "implementation-code":
        if _contains(text, FAIL_MARKERS) or _contains(
            text, ("partial", "lifetime", "ordering", "cleanup", "recovery")
        ):
            return "code-repair"
        return "implementation"

    if group == "debug-failure":
        if _contains(
            text,
            (
                "split brain", "corrupt", "overflow", "thrash", "blackhole",
                "oom", "owner death", "alias", "loss", "reuse", "deadlock",
            ),
        ):
            return "failure-analysis"
        if _contains(text, ("mtu", "tls", "dns", "routing", "policy")):
            return "troubleshooting"
        return "debugging"

    if group == "performance":
        return "performance-analysis"

    if group == "architecture-design":
        if _contains(
            text,
            (
                "policy", "quorum", "placement", "capacity", "availability",
                "consistency", "tradeoff",
            ),
        ):
            return "technical-decision"
        if _contains(text, ("topology", "layout", "architecture")):
            return "architecture-analysis"
        return "design"

    if group == "testing-config":
        if domain == "engineering-reasoning":
            return "testing"
        if _contains(text, CONFIG_MARKERS):
            return "configuration"
        return "testing"

    raise ValueError(group)


def _context(domain: str, seed: int) -> str:
    return random.Random(seed).choice(DOMAIN_CONTEXTS[domain])


def _pick(seed: int, choices: tuple[str, ...]) -> str:
    return random.Random(seed ^ 0x5A17D3).choice(choices)


def _variant(s: Scenario, group: str, salt: str, n: int) -> int:
    import hashlib
    raw = f"{s.key}|{group}|{salt}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16) % n


def falsifier(s: Scenario, group: str, domain: str | None = None) -> str:
    i = _variant(s, group, "falsifier", 3)

    if group == "performance" and domain == "engineering-reasoning":
        return (
            f"The interpretation is weakened if the measured evidence ({s.evidence}) does not show the "
            f"relationship predicted by the model.",
            f"A falsifying result would be measurements from {s.evidence} that contradict the model's "
            f"predicted relationship under the tested workload.",
            f"If the evidence ({s.evidence}) changes independently of the model's predicted outcome, "
            f"do not use this model as the decision basis.",
        )[i]

    if group == "performance":
        return (
            f"The performance hypothesis is weakened if the slowdown remains while the expected "
            f"change is absent from the measured evidence ({s.evidence}) relative to a healthy/control run.",
            f"If a controlled A/B run changes the suspected factor but the relevant evidence "
            f"({s.evidence}) and end-to-end slowdown do not move together, this mechanism is unlikely "
            f"to be the limiting path.",
            f"A falsifying result would be unchanged poor performance even though the evidence "
            f"({s.evidence}) no longer shows the predicted bottleneck.",
        )[i]

    if group == "debug-failure":
        return (
            f"This diagnosis is weakened if the failure reproduces while the expected condition is "
            f"absent from the collected evidence ({s.evidence}).",
            f"If the failure still occurs but the evidence ({s.evidence}) remains consistent with a "
            f"healthy/control case, investigate another cause.",
            f"A falsifying observation would be the same failure with no sign of the predicted mechanism "
            f"in the evidence ({s.evidence}).",
        )[i]

    if group == "implementation-code":
        return (
            f"If the repaired path satisfies the intended evidence ({s.evidence}) but the defect still "
            f"reproduces, this mechanism does not fully explain the remaining failure.",
            f"A falsifying result would be recurrence of the defect after the repair while verification "
            f"evidence ({s.evidence}) confirms the targeted invariant is now satisfied.",
            f"If the targeted invariant is verified by the evidence ({s.evidence}) and the failure remains, "
            f"the investigation must move beyond this mechanism.",
        )[i]

    if group == "architecture-design":
        return (
            f"Reconsider the design premise if controlled tests show that the expected relationship is "
            f"absent from the evidence ({s.evidence}).",
            f"The premise is weakened if adversarial or failure testing produces the same outcome without "
            f"the assumed relationship appearing in the evidence ({s.evidence}).",
            f"A falsifying result would show that the protected property changes independently of the "
            f"mechanism indicated by the evidence ({s.evidence}).",
        )[i]

    return (
        f"If the configuration/test changes but neither the expected evidence ({s.evidence}) nor the "
        f"protected outcome improves, the selected control is unlikely to be causal.",
        f"A falsifying result is a correctly applied change with no corresponding improvement in the "
        f"evidence ({s.evidence}) or protected outcome.",
        f"If the expected signal is absent from the evidence ({s.evidence}) after the controlled change, "
        f"reject the setting/test premise rather than widening the rollout.",
    )[i]

def failure_boundary(s: Scenario, group: str, domain: str | None = None) -> str:
    i = _variant(s, group, "boundary", 3)

    if group == "performance" and domain == "engineering-reasoning":
        return (
            f"Use the model only inside the workload and assumptions validated by {s.evidence}; outside "
            f"that regime, re-measure rather than extrapolate.",
            f"The reasoning boundary is the regime actually exercised by {s.evidence}; a different workload "
            f"mix or scaling assumption can invalidate the conclusion.",
            f"Treat the conclusion as conditional on the assumptions tested by {s.evidence}, not as a "
            f"universal performance law for every workload.",
        )[i]

    if group == "performance":
        return (
            f"Optimize this path only if the verification evidence ({s.evidence}) shows that the mechanism "
            f"is on the limiting path; otherwise the change targets the wrong layer.",
            f"The optimization boundary is evidence-based: if the measurements from {s.evidence} do not "
            f"identify this mechanism as limiting, do not attribute the regression to it.",
            f"This optimization is justified only while controlled measurements from {s.evidence} support "
            f"the claimed bottleneck under representative load.",
        )[i]

    if group == "debug-failure":
        return (
            f"Apply the remediation only when the evidence ({s.evidence}) identifies this failure mode; "
            f"similar symptoms from another cause require a different fix.",
            f"The diagnosis boundary is the observed mechanism: without supporting evidence from "
            f"{s.evidence}, this remediation should not be treated as causal.",
            f"Do not generalize the fix beyond cases where the evidence from {s.evidence} confirms the "
            f"stated mechanism.",
        )[i]

    if group == "implementation-code":
        return (
            f"The repair is valid only if it preserves surrounding API/resource semantics and the "
            f"verification evidence ({s.evidence}) confirms the targeted invariant.",
            f"The fix must not trade this bug for a different resource or API violation; use the evidence "
            f"from {s.evidence} to confirm the intended invariant after the change.",
            f"The implementation boundary is the stated invariant: the repair is acceptable only when "
            f"the evidence from {s.evidence} confirms it without breaking adjacent semantics.",
        )[i]

    if group == "architecture-design":
        return (
            f"The design remains valid only while its operating assumptions match the observed mechanism "
            f"and the evidence ({s.evidence}) continues to support them.",
            f"Treat the design boundary as conditional on the assumptions verified by {s.evidence}; outside "
            f"that envelope, re-evaluate the architecture.",
            f"The design should not be generalized beyond the workload/failure conditions for which the "
            f"evidence from {s.evidence} supports the stated mechanism.",
        )[i]

    return (
        f"Roll out only when the test workload is representative and the evidence ({s.evidence}) actually "
        f"measures the mechanism being changed.",
        f"The configuration is valid only inside the conditions exercised by the test and supported by "
        f"the evidence ({s.evidence}).",
        f"Do not widen the rollout beyond the workload and failure conditions validated by {s.evidence}.",
    )[i]

def second_order_risk(s: Scenario, domain: str) -> str:
    if s.key in RISK_OVERRIDES:
        return RISK_OVERRIDES[s.key]

    text = _normalized_text(" ".join((s.focus, s.action, s.subdomain, s.key)))

    if _contains(text, ("retry", "backoff")):
        return (
            "Overly conservative retry timing can lengthen recovery and request latency, while "
            "insufficient backoff can recreate overload; measure both recovery time and retry volume."
        )
    if _contains(text, ("prefetch",)):
        return (
            "Changing prefetch aggressiveness can trade memory/bandwidth waste for additional demand "
            "misses, so both memory traffic and end-to-end latency must be rechecked."
        )
    if _contains(text, ("buffer", "queue", "window")):
        return (
            "Larger queues or buffers can consume more memory and convert overload into longer latency, "
            "while overly small limits can reduce throughput; recheck both queue age and useful work."
        )
    if _contains(text, ("lock", "mutex", "fence", "synchronization")):
        return (
            "Stronger serialization can improve correctness while reducing concurrency or increasing "
            "tail latency, so contention and throughput must be remeasured."
        )
    if _contains(text, ("fsync", "durability", "sync")):
        return (
            "Stronger durability synchronization can increase write latency and I/O pressure, so "
            "crash safety and steady-state performance must both be validated."
        )
    if _contains(text, ("affinity", "pin", "placement", "numa")):
        return (
            "Tighter placement can improve locality while creating CPU or NUMA hotspots if the workload "
            "moves, so per-node utilization and tail latency must remain part of the rollout gate."
        )
    if _contains(text, ("mlock", "pinned memory", "hugepage")):
        return (
            "Reserving or pinning more memory reduces allocator/reclaim flexibility and can shift pressure "
            "to other workloads, so system-wide memory pressure must be checked."
        )
    if _contains(text, ("offload", "pcie", "transfer")):
        return (
            "Moving state or work across the interconnect can save local memory while adding transfer "
            "latency and host/interconnect pressure."
        )
    if _contains(text, ("throttle", "admission", "shed", "limit")):
        return (
            "A tighter limit can protect the system while rejecting legitimate bursts or reducing "
            "availability, so accepted throughput and recovery behavior must be measured."
        )
    if _contains(text, ("sample rate", "sampling", "anti alias")):
        return (
            "Higher sampling rates or additional filtering can increase power, CPU, and data-bandwidth "
            "requirements, so resource budgets must be revalidated."
        )

    if domain == "distributed-systems":
        return (
            "The safer coordination choice may increase latency or reduce availability during partitions, "
            "so the same failure test must measure both safety and availability."
        )
    if domain == "secure-engineering":
        return (
            "Tightening the security boundary can block legitimate flows or recovery access, so expected "
            "clients and break-glass procedures must be tested."
        )
    if domain == "embedded-systems":
        return (
            "The change can alter timing, power, or memory margins, so worst-case timing and resource "
            "budgets must be revalidated on hardware."
        )
    if domain == "compute-model-infrastructure":
        return (
            "The change can move the bottleneck between accelerator compute, memory, host input, and "
            "interconnect, so an end-to-end profiler trace must be repeated after the change."
        )
    if domain == "networking":
        return (
            "The change can trade latency, packet rate, memory, or fairness against the original symptom, "
            "so packet-level evidence and end-to-end SLOs must both be rechecked."
        )
    if domain == "operating-systems":
        return (
            "The change can shift pressure to a different scheduler, memory, or I/O path, so host-wide "
            "pressure and tail latency must be rechecked."
        )
    if domain == "computer-architecture":
        return (
            "The change can trade one microarchitectural bottleneck for another, so the same hardware "
            "counters and end-to-end runtime must be measured again."
        )
    if domain == "linux-infrastructure":
        return (
            "The operational change can alter failure recovery or resource isolation elsewhere on the host, "
            "so rollback and host-level pressure signals must be tested."
        )
    if domain == "systems-programming":
        return (
            "The repair can change blocking, resource lifetime, or error-path behavior, so stress tests must "
            "cover backpressure, interruption, and cleanup."
        )
    if domain == "software-engineering":
        return (
            "The change can shift load or failure pressure to another dependency, so downstream saturation "
            "and end-to-end latency must be checked."
        )
    return (
        "The change can improve the target metric while regressing another SLO or resource budget, so "
        "the controlled comparison must include both the target and protected metrics."
    )


def _base_question_answer(
    s: Scenario,
    domain: str,
    group: str,
    task_type: str,
    seed: int,
) -> tuple[str, str]:
    context = _context(domain, seed)

    if group == "implementation-code":
        questions = (
            f"{context}, repair the handling of {s.focus}. Explain why the failure occurs, what the implementation should do, and how you would prove the repair works.",
            f"{context}, an implementation must handle {s.focus} safely. Describe the relevant failure mechanism, the repair, and a verification test.",
            f"{context}, fix {s.focus} without changing unrelated behavior. What mechanism matters, what should the code do, and what evidence would validate the fix?",
        )
        answers = (
            f"{s.mechanism.capitalize()}. The implementation should {s.action}. Verify the repair with {s.evidence}. Important constraint: {s.pitfall}.",
            f"The failure is possible because {s.mechanism}. Repair it by having the implementation {s.action}. Use {s.evidence} to verify the result. Keep this constraint explicit: {s.pitfall}.",
            f"Correct handling depends on the fact that {s.mechanism}. The code should {s.action}; validation should include {s.evidence}. One important caveat is that {s.pitfall}.",
        )
    elif group == "debug-failure":
        questions = (
            f"{context}, diagnose a failure involving {s.focus}. What mechanism would explain it, what evidence would confirm that mechanism, and what is the first safe remediation?",
            f"{context}, symptoms point toward {s.focus}. Build a diagnosis that separates this cause from nearby alternatives and name the first remediation you would test.",
            f"{context}, investigate {s.focus}. State the expected mechanism, the evidence you would collect, and the action you would take only after the evidence supports it.",
        )
        answers = (
            f"The leading mechanism is that {s.mechanism}. Confirm it with {s.evidence}. If confirmed, {s.action}. Do not lose sight of this constraint: {s.pitfall}.",
            f"Start by checking {s.evidence}. The observed behavior is consistent with this mechanism: {s.mechanism}. Once that evidence is present, {s.action}. A key caveat is that {s.pitfall}.",
            f"{s.mechanism.capitalize()}. Use {s.evidence} to distinguish this from adjacent causes; if the predicted condition is present, {s.action}. Remember that {s.pitfall}.",
        )
    elif group == "performance":
        if domain == "engineering-reasoning":
            questions = (
                f"{context}, evaluate {s.focus}. What measurements would you use, what conclusion follows if the evidence supports the model, and what observation would reject that interpretation?",
                f"{context}, analyze {s.focus} using measured evidence rather than intuition. What would the measurements support, and what engineering decision would follow?",
                f"{context}, test whether {s.focus} is the right model for the observed system behavior. State the evidence, the engineering conclusion, and the limit of the interpretation.",
            )
            answers = (
                f"Use {s.evidence} to evaluate the principle that {s.mechanism}. If the measurements support that relationship, {s.action}. One caveat is that {s.pitfall}.",
                f"The relevant reasoning is that {s.mechanism}. Measure {s.evidence}; when the data supports the model, {s.action}. Keep this boundary explicit: {s.pitfall}.",
                f"Treat {s.evidence} as the decision evidence for the claim that {s.mechanism}. If the evidence is consistent with that claim, {s.action}. Do not lose sight of this caveat: {s.pitfall}.",
            )
        else:
            questions = (
                f"{context}, determine whether {s.focus} is actually limiting performance. Give a controlled measurement plan, the expected evidence, and the remediation you would test if the hypothesis is confirmed.",
                f"{context}, performance has regressed and {s.focus} is one hypothesis. How would you prove or reject it, and what change would you benchmark next if it is causal?",
                f"{context}, evaluate {s.focus} as a bottleneck. Specify the A/B evidence you need and the remediation you would measure rather than assume.",
            )
            answers = (
                f"The hypothesis is that {s.mechanism}. Measure {s.evidence} in a controlled comparison. If the evidence tracks the slowdown, {s.action}. Keep in mind that {s.pitfall}.",
                f"Use {s.evidence} to test the hypothesis that {s.mechanism}. A causal result should move with the performance regression; if it does, {s.action}. One caveat is that {s.pitfall}.",
                f"{s.mechanism.capitalize()}. Compare {s.evidence} between the slow and healthy/control cases. If that difference explains the regression, {s.action}. Do not assume away this constraint: {s.pitfall}.",
            )
    elif group == "architecture-design":
        questions = (
            f"{context}, choose a production approach for {s.focus}. Explain the correctness boundary, the operational tradeoff, and the evidence you would require before adopting it.",
            f"{context}, review the design for {s.focus}. What property must the design preserve, what approach would you take, and how would you validate the choice?",
            f"{context}, design around {s.focus}. State the mechanism that constrains the design, the approach you would use, and the evidence needed before rollout.",
        )
        answers = (
            f"The design has to account for the fact that {s.mechanism}. A sound approach is to {s.action}. Validate it with {s.evidence}. The design must also respect this caveat: {s.pitfall}.",
            f"Because {s.mechanism}, the design should {s.action}. Use {s.evidence} as the acceptance evidence. One boundary that must remain explicit is that {s.pitfall}.",
            f"The constraining mechanism is that {s.mechanism}. I would {s.action} and validate the decision with {s.evidence}. A key tradeoff or caveat is that {s.pitfall}.",
        )
    else:
        if task_type == "configuration":
            questions = (
                f"{context}, review the configuration for {s.focus}. What would you change, how would you validate it, and what result would make you roll it back?",
                f"{context}, propose a safe configuration change for {s.focus}. Define the evidence, pass condition, and rollback condition before rollout.",
                f"{context}, tune {s.focus} without relying on guesswork. What evidence should drive the setting, and how should the rollout be gated?",
            )
        else:
            questions = (
                f"{context}, design a production-safe test for {s.focus}. Define the expected evidence, the pass/fail condition, and what would invalidate the test.",
                f"{context}, write a verification plan for {s.focus}. What should the test exercise, what should it observe, and what result counts as failure?",
                f"{context}, validate {s.focus} before rollout. Describe the controlled test, the evidence to collect, and the rollback or rejection condition.",
            )
        if task_type == "configuration":
            answers = (
                f"The setting must account for the fact that {s.mechanism}. Use {s.evidence} as the primary evidence, then {s.action}. Gate rollout on the expected signal and protected SLOs; roll back if either regresses. Key caveat: {s.pitfall}.",
                f"Base the setting on {s.evidence}, because {s.mechanism}. The safe change is to {s.action}. Define success and rollback thresholds before rollout. Remember that {s.pitfall}.",
                f"The relevant mechanism is that {s.mechanism}. Validate the setting with {s.evidence}, then {s.action}. Reject or roll back the setting if the expected signal is absent or a protected SLO regresses. Important constraint: {s.pitfall}.",
            )
        else:
            answers = (
                f"The test must exercise the fact that {s.mechanism}. Collect {s.evidence} and {s.action}. Pass only if the expected correctness condition is observed; otherwise reject the change. Key caveat: {s.pitfall}.",
                f"Use {s.evidence} to test the mechanism that {s.mechanism}. The test should {s.action}. A passing result must demonstrate the expected invariant or behavior, not merely avoid a crash. Remember that {s.pitfall}.",
                f"The mechanism under test is that {s.mechanism}. Exercise it directly, collect {s.evidence}, and {s.action}. Fail the test if the expected behavior is absent or the protected invariant is violated. Important constraint: {s.pitfall}.",
            )

    idx = random.Random(seed ^ 0x772311).randrange(len(questions))
    return questions[idx], answers[idx]


def render(
    s: Scenario,
    domain: str,
    task_group: str,
    difficulty: str,
    seed: int,
) -> Candidate:
    task_type = choose_task_type(s, domain, task_group)
    question, answer = _base_question_answer(
        s, domain, task_group, task_type, seed
    )

    verification_parts = (
        f"mechanism: {s.mechanism}",
        f"evidence: {s.evidence}",
        f"safe action: {s.action}",
        f"caution: {s.pitfall}",
    )
    verification = list(verification_parts)

    if difficulty in {"advanced", "expert"}:
        f = falsifier(s, task_group, domain)
        question += " Include one observation that would falsify the initial diagnosis or design premise."
        answer += " " + f
        verification.append("must include a concrete falsifier tied to the scenario evidence")

    if difficulty == "expert":
        boundary = failure_boundary(s, task_group, domain)
        risk = second_order_risk(s, domain)
        question += " Also state the failure boundary and one second-order risk of the remediation."
        answer += " " + boundary + " " + risk
        verification.append("must state the failure boundary")
        verification.append("must state one scenario-relevant second-order risk")

    return Candidate(
        domain=domain,
        subdomain=s.subdomain,
        task_type=task_type,
        difficulty=difficulty,
        question=question,
        answer=answer,
        verification_method="rubric",
        verification_details="; ".join(x.rstrip(".") for x in verification) + ".",
        tags=[
            s.subdomain,
            s.key,
            "scenario-generator",
            f"task-group:{task_group}",
            f"depth:{difficulty}",
        ],
        generator_id="",
        recipe={},
    )


def register(domain: str, prefix: str, scenarios: list[Scenario], offset: int = 0):
    # offset remains only for compatibility with the domain modules. Task
    # semantics are no longer assigned by index.
    for s in scenarios:
        gid = f"{prefix}.{s.key}"
        groups, group_costs = supported_groups(s, domain)

        def make(
            seed: int,
            difficulty: str,
            task_group: str,
            *,
            s=s,
            domain=domain,
            gid=gid,
        ):
            supported, _ = supported_groups(s, domain)
            if task_group not in supported:
                raise ValueError(f"{gid} does not support task group {task_group}")

            c = render(s, domain, task_group, difficulty, seed)
            return Candidate(
                domain=c.domain,
                subdomain=c.subdomain,
                task_type=c.task_type,
                difficulty=c.difficulty,
                question=c.question,
                answer=c.answer,
                verification_method=c.verification_method,
                verification_details=c.verification_details,
                tags=c.tags,
                generator_id=gid,
                recipe={
                    "scenario": s.key,
                    "task_group": task_group,
                    "difficulty": difficulty,
                    "context_seed": seed,
                },
            )

        generator(
            id=gid,
            domain=domain,
            groups=groups,
            group_costs=group_costs,
            weight=1.0,
            max_records=1,
        )(make)
