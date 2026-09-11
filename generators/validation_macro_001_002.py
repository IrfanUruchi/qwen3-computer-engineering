from generators.common import S


def Q(
    n, slug, domain, subdomain, task, difficulty,
    prompt, points,
    verification="rubric",
    details=None,
    tags=(),
    source_type="original",
    reference=None,
):
    if details is None:
        details = "Review requires: " + "; ".join(points)

    return S(
        n, slug, domain, subdomain, task, difficulty,
        prompt, points,
        verification, details, list(tags),
        source_type, reference,
    )


ALL_RECORDS = [

# =====================================================================
# VALIDATION BATCH 001 — 201..210
# =====================================================================

Q(
201, "software-pagination-delete",
"software-engineering", "pagination",
"failure-analysis", "advanced",
"A cursor-paginated API orders rows by `(created_at, id)`. Between two page requests, some rows already returned are deleted. Explain what properties the cursor design should preserve.",
[
"Deletion of already returned rows should not shift an offset because the cursor identifies an ordering position rather than a numeric row count.",
"The next query should continue strictly after the last returned ordering key.",
"The ordering key must be deterministic and unique enough to prevent ambiguity between rows with equal timestamps.",
"Cursor pagination does not itself provide snapshot isolation; concurrent inserts and deletes still need explicitly documented semantics."
],
tags=("pagination","cursor","deletion","api")
),

Q(
202, "systems-strtol-validation",
"systems-programming", "numeric-parsing",
"code-repair", "advanced",
"C code parses an untrusted decimal string with atoi and accepts the result without detecting malformed input or overflow. Design a checked replacement.",
[
"Use a conversion interface such as strtol or strtoll that exposes an end pointer and range errors.",
"Reject strings with no digits, unexpected trailing characters, and values outside the application range.",
"Check conversion overflow before narrowing to a smaller destination type.",
"Do not treat a returned zero as sufficient evidence that the input was the valid string zero."
],
verification="reference-answer",
source_type="documentation",
reference="C/POSIX strtol conversion semantics",
tags=("c","strtol","parsing","overflow")
),

Q(
203, "os-thread-stack-overflow",
"operating-systems", "thread-stacks",
"failure-analysis", "advanced",
"A recursive worker crashes only on threads configured with unusually small stacks. Explain how stack exhaustion differs from heap exhaustion and how to investigate it.",
[
"Each thread normally has a bounded stack region used for call frames, automatic storage, and saved execution state.",
"Deep recursion or large automatic objects can exhaust that region even while substantial heap memory remains available.",
"Inspect configured thread stack size, recursion depth, frame size, guard-page faults, and crash location.",
"Repair the excessive stack demand or choose an appropriate stack size rather than assuming total free RAM determines safety."
],
tags=("thread","stack","recursion","memory")
),

Q(
204, "architecture-rob-latency",
"computer-architecture", "out-of-order-execution",
"performance-analysis", "advanced",
"A loop contains one long-latency dependency chain and many independent arithmetic instructions, yet performance stops improving after adding more independent work. Explain one out-of-order execution limit.",
[
"An out-of-order core can overlap independent instructions only while its finite instruction window and structures such as the reorder buffer have capacity.",
"If a long-latency dependency blocks retirement, younger independent operations can eventually fill those resources.",
"Measure cycles, IPC, backend stalls, outstanding work, and relevant reorder or scheduler pressure where counters exist.",
"Additional source-level independence does not imply unlimited latency hiding."
],
tags=("reorder-buffer","latency","ilp","architecture")
),

Q(
205, "linux-inotify-overflow",
"linux-infrastructure", "filesystem-events",
"troubleshooting", "advanced",
"A filesystem watcher misses changes during a burst and reports an inotify queue overflow. Explain the recovery requirement.",
[
"An overflow means individual event history is no longer complete, so the watcher cannot reconstruct exact state solely from subsequent queued events.",
"Treat overflow as a signal to rescan authoritative filesystem state and rebuild the watcher's model.",
"Continue watching after reconciliation and design event handling so a temporary event-rate burst does not silently produce permanently stale state."
],
verification="reference-answer",
source_type="documentation",
reference="Linux inotify queue overflow semantics",
tags=("linux","inotify","overflow","filesystem")
),

Q(
206, "reasoning-littles-law",
"engineering-reasoning", "queueing-analysis",
"technical-decision", "advanced",
"A stable service completes about 500 requests per second and requests spend about 40 ms in the system on average. Estimate average concurrency and explain what assumptions make the estimate useful.",
[
"Under stable long-run conditions, Little's Law gives L = lambda × W.",
"Using 500 requests/s and 0.040 s gives about 20 requests in the system on average.",
"The relationship concerns matching averages over a stable observation interval and does not predict tail latency or transient burst behavior.",
"Use consistent boundaries for what counts as arrival, completion, and time in system."
],
verification="unit-test",
details="Verified by verification-validation/000206_test.py for the dimensional calculation and representative values.",
tags=("queueing","little-law","concurrency","capacity")
),

Q(
207, "software-lease-renewal",
"software-engineering", "distributed-locking",
"design", "expert",
"A worker holds a time-limited distributed lease while performing a long operation. Design behavior for lease renewal failure.",
[
"The worker must not assume ownership continues merely because local work is still running.",
"Renew with enough margin before expiry to tolerate ordinary latency, but define a point after which authority is considered lost.",
"Use fencing or another downstream ownership check when stale workers could otherwise commit after lease loss.",
"Cancellation and cleanup should distinguish local operation state from continuing distributed authority."
],
tags=("lease","distributed-lock","renewal","fencing")
),

Q(
208, "networking-nagle-delayed-ack",
"networking", "tcp-latency",
"performance-analysis", "advanced",
"A request-response protocol sends many tiny TCP writes and shows periodic latency spikes. Analyze an interaction between small writes, Nagle's algorithm, and delayed acknowledgements.",
[
"Nagle-style coalescing can delay a small send while unacknowledged data remains outstanding.",
"A peer using delayed acknowledgements may itself wait briefly before sending an ACK, creating an unfortunate latency interaction for tiny request patterns.",
"Capture packet timing and segment sizes before changing socket options.",
"TCP_NODELAY may reduce this latency pattern but can increase small-packet traffic, so validate the actual workload."
],
tags=("tcp","nagle","delayed-ack","latency")
),

Q(
209, "distributed-consistent-hash-churn",
"distributed-systems", "partitioning",
"architecture-analysis", "advanced",
"A sharded cache changes from N to N+1 servers. Compare naive modulo hashing with consistent hashing for key movement.",
[
"With modulo hashing, changing the divisor can remap a large fraction of keys even though only one server was added.",
"Consistent hashing arranges ownership so membership changes primarily affect neighboring portions of the key space.",
"Virtual nodes or equivalent techniques help distribute ownership more evenly across physical nodes.",
"Reduced remapping does not eliminate the need to handle replication, hot keys, and temporary rebalance load."
],
tags=("consistent-hashing","sharding","rebalance","distributed-systems")
),

Q(
210, "compute-activation-checkpoint",
"compute-model-infrastructure", "training-memory",
"technical-decision", "advanced",
"A model training job exceeds accelerator memory because saved forward activations dominate usage. Explain activation checkpointing as a tradeoff.",
[
"Activation checkpointing stores only selected intermediate states and recomputes omitted forward work during backpropagation.",
"This reduces activation memory at the cost of additional computation and potentially longer step time.",
"Measure peak memory, recomputation overhead, throughput, and whether the saved memory enables a better batch or model configuration.",
"It addresses activation storage rather than every source of memory use such as parameters, optimizer state, and communication buffers."
],
tags=("activation-checkpointing","training","memory","compute")
),

# =====================================================================
# VALIDATION BATCH 002 — 211..220
# =====================================================================

Q(
211, "software-partial-response",
"software-engineering", "api-failures",
"design", "advanced",
"An API aggregates independent data from several backends. One optional backend times out. Decide when partial success is preferable to failing the entire response.",
[
"Classify which fields are required for the contract and which can be absent without making the response misleading.",
"Represent missing optional data explicitly rather than fabricating defaults that look authoritative.",
"Respect the request deadline instead of waiting indefinitely for an optional dependency.",
"Expose degradation metrics so partial success does not hide a chronically failing backend."
],
tags=("api","partial-success","timeout","resilience")
),

Q(
212, "systems-writev-partial",
"systems-programming", "posix-io",
"implementation", "advanced",
"A nonblocking socket writev call may consume only part of several buffers. Explain how the caller should maintain progress.",
[
"Treat the returned byte count as progress across the concatenated logical iovec sequence rather than assuming every vector was fully sent.",
"Advance past completely written vectors and adjust the base pointer and length of the partially written vector.",
"Retry remaining data only when the descriptor is writable again.",
"Handle interruption, EAGAIN, closure, and other errors according to the socket contract."
],
verification="rubric",
tags=("writev","partial-write","socket","posix")
),

Q(
213, "systems-shift-signed",
"systems-programming", "bit-operations",
"code-repair", "advanced",
"C code left-shifts a signed integer supplied by an external caller to create a bit mask. Repair the operation so invalid shifts and signed-overflow behavior are avoided.",
[
"Validate the shift count against the width of the chosen unsigned type.",
"Perform bit construction in an unsigned type, for example `UINT32_C(1) << index` for a validated 0..31 index.",
"Convert afterward only if the destination representation and semantics are explicitly valid.",
"Do not rely on signed left-shift behavior when the result is not representable."
],
verification="unit-test",
details="Verified by verification-validation/000213_test.py for valid endpoints and rejection of invalid shift counts.",
tags=("c","shift","unsigned","bit-mask")
),

Q(
214, "os-pipe-atomic-write",
"operating-systems", "pipes",
"technical-decision", "advanced",
"Several processes write short records to the same pipe. Explain why record size relative to PIPE_BUF matters for preserving write boundaries between writers.",
[
"POSIX requires writes no larger than PIPE_BUF to a pipe to be atomic with respect to other writers under the defined blocking conditions.",
"Larger writes may be interleaved with data from other writers.",
"This atomicity concerns each write operation, not an arbitrary multi-write application record.",
"Design record framing and maximum record size around the actual guarantee when multiple writers share the pipe."
],
verification="reference-answer",
source_type="documentation",
reference="POSIX pipe PIPE_BUF atomic-write semantics",
tags=("pipe","pipe-buf","atomicity","ipc")
),

Q(
215, "architecture-btb-pressure",
"computer-architecture", "branch-prediction",
"performance-analysis", "advanced",
"A large dispatcher with many indirect control-flow targets has worse instruction throughput than a smaller version even though branch direction accuracy remains high. Analyze branch-target prediction pressure.",
[
"Predicting whether a branch is taken and predicting its target are distinct front-end problems.",
"Many branch or indirect-call sites can pressure structures that remember target information and increase front-end redirection cost.",
"Inspect branch-target or indirect-prediction counters where available, front-end stalls, instruction footprint, and controlled code-layout variants.",
"Do not infer the exact hardware structure from one counter because implementations differ."
],
tags=("branch-target","btb","frontend","performance")
),

Q(
216, "embedded-brownout-state",
"embedded-systems", "power-failure",
"failure-analysis", "advanced",
"A microcontroller intermittently corrupts persistent configuration when supply voltage collapses slowly. Design a safer brownout strategy.",
[
"Use brownout detection or reset thresholds so firmware does not continue unsafe writes below the voltage required for reliable operation.",
"Make persistent updates power-loss tolerant, for example with versioned records, CRCs, or commit markers rather than overwriting the only valid copy in place.",
"Measure supply decay, write duration, storage voltage requirements, and reset behavior.",
"On reboot, validate stored state and select the last complete record."
],
tags=("embedded","brownout","persistent-storage","power-loss")
),

Q(
217, "linux-pid-reuse",
"linux-infrastructure", "process-management",
"failure-analysis", "advanced",
"A supervisor stores only a numeric PID and much later sends a signal to it. Explain the danger of PID reuse.",
[
"A PID identifies a process only for the lifetime of that process and can later be assigned to an unrelated process.",
"Long-lived references should use stronger identity mechanisms where available, such as pidfds on suitable Linux systems, or validate process identity before acting.",
"A stale numeric PID can therefore target the wrong process even though the number itself still exists."
],
verification="reference-answer",
source_type="documentation",
reference="Linux process ID reuse and pidfd semantics",
tags=("linux","pid","pidfd","process")
),

Q(
218, "reasoning-dimensional-bandwidth",
"engineering-reasoning", "dimensional-analysis",
"performance-analysis", "intermediate",
"A job transfers 12 GiB across an interface sustaining 4 GiB/s. Estimate the transfer floor and explain why measured end-to-end time may be larger.",
[
"Pure transfer time at the stated sustained rate is approximately 12 GiB / 4 GiB/s = 3 seconds.",
"End-to-end time can additionally include setup, synchronization, serialization, allocation, protocol overhead, or other work.",
"Keep byte units and time units consistent before comparing theoretical and measured results."
],
verification="unit-test",
details="Verified by verification-validation/000218_test.py for bandwidth/time dimensional calculations.",
tags=("bandwidth","units","performance","reasoning")
),

Q(
219, "compute-host-sync",
"compute-model-infrastructure", "accelerator-synchronization",
"performance-analysis", "advanced",
"A GPU workload contains frequent host-side reads of individual tensor results. Kernels appear serialized despite being launched asynchronously. Explain the synchronization hazard.",
[
"A host read that requires a device-produced value can force the host to wait until preceding accelerator work producing that value completes.",
"Frequent scalar extraction or synchronization points can therefore destroy overlap between queued device operations.",
"Profile the timeline for host waits and device gaps, batch reductions or reads when possible, and keep values on-device while they remain part of device computation.",
"Confirm semantics before removing synchronization because some reads are required for control flow or correctness."
],
tags=("gpu","synchronization","host-device","latency")
),

Q(
220, "secure-ssrf-egress",
"secure-engineering", "ssrf",
"design", "expert",
"A server accepts a user-provided URL and fetches it from a network environment that can reach private infrastructure. Design SSRF defenses.",
[
"Do not treat URL syntax validation alone as authorization to access the resolved destination.",
"Restrict allowed schemes and destinations according to product need and block private, loopback, link-local, metadata, and otherwise sensitive ranges when they are not explicitly required.",
"Account for DNS resolution changes, redirects, alternate address representations, and IPv6 as part of destination enforcement.",
"Use network-level egress controls as an additional boundary rather than relying solely on application filtering."
],
tags=("security","ssrf","egress","url")
),
]


VERIFIERS = {

"000206_test.py": r'''
import unittest

def concurrency(rate_per_second, seconds):
    if rate_per_second < 0 or seconds < 0:
        raise ValueError("negative")
    return rate_per_second * seconds

class Tests(unittest.TestCase):
    def test_example(self):
        self.assertEqual(
            concurrency(500, 0.040),
            20.0,
        )

    def test_units(self):
        self.assertEqual(
            concurrency(100, 0.5),
            50.0,
        )

if __name__ == "__main__":
    unittest.main()
''',

"000213_test.py": r'''
import unittest

def bit32(index):
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or index < 0
        or index >= 32
    ):
        raise ValueError("shift")

    return 1 << index

class Tests(unittest.TestCase):
    def test_edges(self):
        self.assertEqual(bit32(0), 1)
        self.assertEqual(bit32(31), 0x80000000)

    def test_invalid(self):
        for value in (-1, 32, True):
            with self.assertRaises(ValueError):
                bit32(value)

if __name__ == "__main__":
    unittest.main()
''',

"000218_test.py": r'''
import unittest

def transfer_seconds(size_gib, rate_gib_s):
    if size_gib < 0 or rate_gib_s <= 0:
        raise ValueError("inputs")
    return size_gib / rate_gib_s

class Tests(unittest.TestCase):
    def test_example(self):
        self.assertEqual(
            transfer_seconds(12, 4),
            3.0,
        )

    def test_fraction(self):
        self.assertEqual(
            transfer_seconds(3, 2),
            1.5,
        )

if __name__ == "__main__":
    unittest.main()
''',
}


def records_for(batch):
    start = 201 + (batch - 1) * 10
    end = start + 9

    return [
        r for r in ALL_RECORDS
        if start <= r.number <= end
    ]


def verifiers_for(batch):
    start = 201 + (batch - 1) * 10
    end = start + 9

    return {
        name: content
        for name, content in VERIFIERS.items()
        if start <= int(name[:6]) <= end
    }
