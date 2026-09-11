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
# BATCH 019 — 181..190
# =====================================================================

Q(
181, "software-request-deadline",
"software-engineering", "request-deadlines",
"design", "advanced",
"A service calls three downstream dependencies in sequence. Each client library has its own 5-second timeout, but the user-facing request budget is only 6 seconds. Design deadline propagation.",
[
"Use one end-to-end deadline derived from the user-facing request budget rather than giving every downstream call an independent full timeout.",
"Before each downstream call, compute the remaining budget and refuse or shorten work that cannot finish within it.",
"Propagate deadline or cancellation information across service boundaries where the protocol supports it.",
"Reserve time for local cleanup and response handling instead of consuming the entire budget downstream."
],
tags=("deadline","timeout","distributed-api","latency")
),

Q(
182, "systems-ring-index",
"systems-programming", "ring-buffer",
"implementation", "intermediate",
"Implement index advancement for a fixed-capacity ring buffer and reject zero capacity.",
[
"Advance the index modulo capacity.",
"Reject capacity zero because modulo zero is invalid and a zero-slot ring cannot store elements.",
"Keep index values normalized to the range 0 through capacity-1."
],
verification="unit-test",
details="Verified by verification/000182_test.py for normal advancement, wraparound, capacity one, and zero-capacity rejection.",
tags=("ring-buffer","index","modulo","systems-programming")
),

Q(
183, "os-fork-buffer-duplication",
"operating-systems", "process-io",
"failure-analysis", "intermediate",
"A program writes text to a buffered stdio stream, calls fork(), and then both parent and child exit normally. The buffered text appears twice. Explain why.",
[
"fork duplicates the process address space, including userspace stdio buffer state.",
"If buffered output had not been flushed before fork, both parent and child can later flush their copied buffer.",
"Flush or otherwise establish the intended buffering state before forking when duplicate output would be incorrect.",
"This differs from duplication inside the kernel file description itself; the duplicated bytes came from userspace buffering."
],
verification="reference-answer",
source_type="documentation",
reference="POSIX fork and stdio buffering semantics",
tags=("fork","stdio","buffering","process")
),

Q(
184, "architecture-cache-line-straddle",
"computer-architecture", "memory-layout",
"performance-analysis", "advanced",
"A frequently accessed object sometimes straddles two cache lines after a layout change. Explain why that can increase memory traffic.",
[
"An access spanning two cache lines can require two cache-line lookups or fills where an aligned placement might require one.",
"The impact depends on access size, alignment, cache state, instruction support, and whether the object is shared.",
"Measure cache misses, memory transactions, load latency, and the effect of controlled alignment before changing layout globally."
],
tags=("cache-line","alignment","memory-layout","performance")
),

Q(
185, "embedded-wrap-timeout",
"embedded-systems", "timers",
"implementation", "advanced",
"A 32-bit free-running millisecond counter wraps naturally. Implement elapsed-time timeout checking without breaking at wraparound.",
[
"Use unsigned subtraction: elapsed = now - start in the same fixed-width unsigned type.",
"Modulo arithmetic makes the difference correct across one natural wrap as long as the timeout interval is within the representable half/range assumptions of the design.",
"Compare elapsed against the timeout rather than comparing absolute timestamps with naive greater-than logic."
],
verification="unit-test",
details="Verified by verification/000185_test.py for ordinary elapsed time, wraparound, boundary equality, and pre-timeout behavior.",
tags=("embedded","timer","wraparound","uint32")
),

Q(
186, "software-outbox-publication",
"software-engineering", "transactional-outbox",
"design", "expert",
"A service commits database state and then publishes an event to a broker. A crash between those operations can leave committed state without its event. Design a safer publication flow.",
[
"Write the business state change and an outbox record in the same local database transaction.",
"A separate publisher reads committed outbox records and sends them to the broker.",
"Mark or checkpoint successful publication durably, while allowing retries after crashes.",
"Consumers should still tolerate duplicate delivery because publish acknowledgement can itself be ambiguous."
],
tags=("outbox","events","transactions","reliability")
),

Q(
187, "systems-frame-count-limit",
"systems-programming", "protocol-parsing",
"code-repair", "advanced",
"A parser reads a 16-bit element count from an untrusted frame and allocates a list of that many objects without any protocol-level maximum. Repair the boundary.",
[
"Decode the count safely, then compare it against an explicit protocol or application maximum before allocation.",
"Type width alone is not a sufficient resource limit; even a representable count may be operationally unreasonable.",
"Reject oversized frames before performing allocation or iteration proportional to attacker-controlled input."
],
verification="unit-test",
details="Verified by verification/000187_test.py for accepted counts at the limit and rejection above the configured maximum.",
tags=("parser","resource-limit","count","bounds")
),

Q(
188, "networking-udp-truncation",
"networking", "udp",
"troubleshooting", "intermediate",
"A UDP receiver provides a buffer smaller than some incoming datagrams and later discovers the missing bytes cannot be read with another recv call. Explain why.",
[
"UDP preserves datagram message boundaries rather than presenting one continuous byte stream.",
"If the receive buffer is too small, the excess portion of that datagram can be discarded according to the socket API semantics.",
"A second receive obtains the next datagram, not the remainder of the previous one.",
"Size buffers for expected datagrams or use APIs that expose truncation information when the application needs to detect it."
],
verification="reference-answer",
source_type="documentation",
reference="POSIX/Linux UDP datagram receive semantics",
tags=("udp","datagram","truncation","networking")
),

Q(
189, "distributed-read-repair",
"distributed-systems", "replication",
"technical-decision", "expert",
"A replicated key-value store reads several replicas and discovers one returning an older version than the others. Explain read repair and its limitations.",
[
"A read path can compare version metadata from replicas and asynchronously update a stale replica with a newer authoritative value.",
"Version ordering must be well defined; wall-clock timestamp comparison alone may be unsafe under concurrent writes or clock skew.",
"Read repair improves convergence for keys that are actually read but does not guarantee timely repair of cold data.",
"Background anti-entropy remains useful when the system requires convergence independent of read traffic."
],
tags=("distributed-systems","read-repair","replication","anti-entropy")
),

Q(
190, "linux-bind-mount",
"linux-infrastructure", "mounts",
"architecture-analysis", "intermediate",
"Explain what a Linux bind mount does when one existing directory tree is exposed at another pathname.",
[
"A bind mount creates another mount-point view of the same underlying filesystem subtree rather than copying its files.",
"Changes made through either path refer to the same underlying objects.",
"Mount options and namespace visibility can still differ, so path identity alone does not imply an independent copy."
],
verification="reference-answer",
source_type="documentation",
reference="Linux mount(8) bind-mount semantics",
tags=("linux","bind-mount","filesystem","namespace")
),

# =====================================================================
# BATCH 020 — 191..200
# =====================================================================

Q(
191, "software-health-check",
"software-engineering", "service-health",
"design", "advanced",
"A service exposes one health endpoint that reports success whenever the process is alive, even before initialization completes. Design separate liveness and readiness semantics.",
[
"Liveness should answer whether the process is fundamentally alive enough that restarting it could help.",
"Readiness should answer whether the instance can currently serve traffic correctly, including required initialization and critical dependency state.",
"A temporary downstream failure should not automatically cause restart loops if removing the instance from traffic is sufficient.",
"Keep checks cheap, bounded, and aligned with orchestrator behavior."
],
tags=("health-check","liveness","readiness","deployment")
),

Q(
192, "systems-overlap-range",
"systems-programming", "memory-ranges",
"implementation", "advanced",
"Implement a helper that determines whether two half-open byte ranges [start,end) overlap, rejecting malformed ranges.",
[
"Require each start to be less than or equal to its corresponding end.",
"If either range is empty, they do not overlap; otherwise two valid half-open ranges overlap when a_start < b_end and b_start < a_end.",
"Touching boundaries such as [0,4) and [4,8) do not overlap."
],
verification="unit-test",
details="Verified by verification/000192_test.py for overlap, containment, touching boundaries, empty ranges, and malformed ranges.",
tags=("memory","range","overlap","bounds")
),

Q(
193, "os-zombie-process",
"operating-systems", "process-lifecycle",
"troubleshooting", "intermediate",
"A child process has exited but still appears in the process table as a zombie. Explain what resources remain and how it is removed.",
[
"After exit, most execution resources are released, but a small process-table record remains so the parent can collect termination status.",
"The parent removes the zombie by calling wait or a related wait interface.",
"Killing the zombie itself is not meaningful because it has already terminated; investigate why the parent is not reaping children."
],
verification="reference-answer",
source_type="documentation",
reference="POSIX/Linux wait and zombie process semantics",
tags=("process","zombie","wait","linux")
),

Q(
194, "architecture-memory-level-parallelism",
"computer-architecture", "memory-level-parallelism",
"performance-analysis", "advanced",
"Two workloads have similar cache-miss counts, but one is much faster because it can issue several independent misses at once. Explain memory-level parallelism.",
[
"Cache-miss count alone does not reveal how much miss latency is exposed to the critical path.",
"Independent misses can overlap in flight, while pointer-dependent misses often serialize because the next address is unavailable until the prior load completes.",
"Measure outstanding misses, load latency, bandwidth, dependency structure, and cycles stalled on memory where counters permit."
],
tags=("memory-level-parallelism","cache-miss","latency","architecture")
),

Q(
195, "embedded-adc-calibration",
"embedded-systems", "adc-calibration",
"implementation", "intermediate",
"An ADC has a measured zero offset and gain correction. Apply a simple linear calibration to raw readings.",
[
"Subtract the measured offset from the raw sample before applying gain correction.",
"Keep enough intermediate precision to avoid unnecessary rounding loss.",
"Define the calibration equation and units explicitly so firmware and test tooling use the same convention."
],
verification="unit-test",
details="Verified by verification/000195_test.py for zero-offset correction, gain application, and representative raw samples.",
tags=("embedded","adc","calibration","sensor")
),

Q(
196, "software-token-bucket",
"software-engineering", "rate-limiting",
"implementation", "advanced",
"Design a token-bucket rate limiter that permits short bursts while enforcing a long-term request rate.",
[
"Maintain a bucket with finite token capacity and replenish tokens according to elapsed time up to that capacity.",
"Each accepted request consumes the required token amount; reject or delay requests when insufficient tokens are available.",
"Use a monotonic time source and update state atomically when concurrent callers share the limiter.",
"Burst capacity and refill rate represent separate policy controls."
],
tags=("rate-limit","token-bucket","burst","concurrency")
),

Q(
197, "linux-atomic-symlink",
"linux-infrastructure", "deployment-files",
"configuration", "advanced",
"A deployment selects the active release through a symlink. Replace the selector without exposing a partially written symlink state.",
[
"Create the new symlink under a temporary pathname in the same filesystem directory.",
"Atomically rename the completed temporary link over the selector.",
"Prepare and validate the target release before switching the selector.",
"Keep rollback targets available until the new release is confirmed healthy."
],
verification="execute",
details="Verified by verification/000197_test.sh using a temporary symlink followed by atomic rename replacement.",
tags=("linux","symlink","rename","deployment")
),

Q(
198, "networking-dns-tcp-fallback",
"networking", "dns-transport",
"troubleshooting", "advanced",
"Small DNS queries succeed but larger responses fail through a firewall. Explain why TCP support may matter even when DNS normally uses UDP.",
[
"DNS commonly uses UDP for ordinary queries, but responses can be truncated or exceed practical UDP limits.",
"A resolver may retry over TCP when the UDP response indicates truncation or when protocol behavior otherwise requires it.",
"A firewall that permits UDP port 53 but blocks TCP port 53 can therefore create size-dependent resolution failures.",
"Capture the exchange and inspect truncation flags, EDNS behavior, response size, and TCP reachability."
],
verification="reference-answer",
source_type="documentation",
reference="DNS UDP/TCP fallback semantics",
tags=("dns","tcp","udp","firewall")
),

Q(
199, "distributed-quorum-loss",
"distributed-systems", "consensus",
"failure-analysis", "expert",
"A five-node majority-based cluster loses communication with three nodes. The two remaining nodes are healthy and still contain recent data. Explain why they should normally refuse new committed writes.",
[
"A two-node minority cannot form the required majority of three.",
"Allowing that minority to commit independently would permit another disjoint majority to make conflicting decisions.",
"Preserving consistency therefore sacrifices write availability until quorum is restored.",
"Read behavior may have separate rules, but stale local data is not proof of current commit authority."
],
tags=("distributed-systems","quorum","partition","consensus")
),

Q(
200, "compute-model-shard-balance",
"compute-model-infrastructure", "model-sharding",
"performance-analysis", "advanced",
"A model is split across two accelerators, but one device remains busy much longer than the other during every request. Analyze load imbalance.",
[
"Parallel execution time is constrained by the slowest participating shard, so unequal compute or memory work can leave one accelerator waiting.",
"Measure per-device kernel time, memory use, communication time, synchronization, and layer or tensor assignment.",
"Balance partitioning around measured cost rather than parameter count alone because layers can have different compute, activation, and communication characteristics.",
"After repartitioning, remeasure end-to-end latency because reducing imbalance can expose a new communication bottleneck."
],
verification="rubric",
details="Requires per-device timing, memory and communication evidence, critical-path reasoning, and workload-aware repartitioning.",
tags=("model-sharding","gpu","load-balance","performance")
),
]


VERIFIERS = {

"000182_test.py": r'''
import unittest

def advance(index, capacity):
    if capacity <= 0:
        raise ValueError("capacity")
    if index < 0 or index >= capacity:
        raise ValueError("index")
    return (index + 1) % capacity

class Tests(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(advance(2, 5), 3)

    def test_wrap(self):
        self.assertEqual(advance(4, 5), 0)

    def test_one(self):
        self.assertEqual(advance(0, 1), 0)

    def test_zero_capacity(self):
        with self.assertRaises(ValueError):
            advance(0, 0)

if __name__ == "__main__":
    unittest.main()
''',

"000185_test.py": r'''
import unittest

MASK = 0xFFFFFFFF

def expired(start, now, timeout):
    elapsed = (now - start) & MASK
    return elapsed >= timeout

class Tests(unittest.TestCase):
    def test_normal(self):
        self.assertTrue(expired(100, 150, 50))
        self.assertFalse(expired(100, 149, 50))

    def test_wrap(self):
        start = 0xFFFFFFF0
        now = 0x00000010
        self.assertTrue(expired(start, now, 0x20))

    def test_boundary(self):
        self.assertTrue(expired(1000, 1100, 100))

if __name__ == "__main__":
    unittest.main()
''',

"000187_test.py": r'''
import unittest

MAX_COUNT = 1024

def checked_count(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("type")
    if value < 0 or value > MAX_COUNT:
        raise ValueError("count")
    return value

class Tests(unittest.TestCase):
    def test_limit(self):
        self.assertEqual(checked_count(0), 0)
        self.assertEqual(checked_count(MAX_COUNT), MAX_COUNT)

    def test_too_large(self):
        with self.assertRaises(ValueError):
            checked_count(MAX_COUNT + 1)

if __name__ == "__main__":
    unittest.main()
''',

"000192_test.py": r'''
import unittest

def overlaps(a0, a1, b0, b1):
    if a0 > a1 or b0 > b1:
        raise ValueError("malformed")
    if a0 == a1 or b0 == b1:
        return False
    return a0 < b1 and b0 < a1

class Tests(unittest.TestCase):
    def test_overlap(self):
        self.assertTrue(overlaps(0, 5, 3, 8))

    def test_contained(self):
        self.assertTrue(overlaps(0, 10, 2, 4))

    def test_touching(self):
        self.assertFalse(overlaps(0, 4, 4, 8))

    def test_empty(self):
        self.assertFalse(overlaps(3, 3, 0, 10))

    def test_bad(self):
        with self.assertRaises(ValueError):
            overlaps(5, 4, 0, 1)

if __name__ == "__main__":
    unittest.main()
''',

"000195_test.py": r'''
import unittest

def calibrate(raw, offset, gain):
    return (raw - offset) * gain

class Tests(unittest.TestCase):
    def test_offset(self):
        self.assertEqual(calibrate(100, 100, 1.0), 0.0)

    def test_gain(self):
        self.assertEqual(calibrate(200, 100, 1.5), 150.0)

    def test_negative_corrected(self):
        self.assertEqual(calibrate(90, 100, 2.0), -20.0)

if __name__ == "__main__":
    unittest.main()
''',

"000197_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir "$tmp/release-a" "$tmp/release-b"

ln -s release-a "$tmp/current"

test "$(readlink "$tmp/current")" = "release-a"

ln -s release-b "$tmp/current.new"
mv -Tf "$tmp/current.new" "$tmp/current"

test "$(readlink "$tmp/current")" = "release-b"

echo "atomic symlink replacement verified"
''',
}


def records_for(batch):
    start = (batch - 1) * 10 + 1
    end = start + 9

    return [
        r for r in ALL_RECORDS
        if start <= r.number <= end
    ]


def verifiers_for(batch):
    start = (batch - 1) * 10 + 1
    end = start + 9

    return {
        name: content
        for name, content in VERIFIERS.items()
        if start <= int(name[:6]) <= end
    }
