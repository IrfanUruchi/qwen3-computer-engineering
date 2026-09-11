from generators.common import S


ALL_RECORDS = [

# ---------------------------------------------------------------------
# BATCH 010 — 091..100
# ---------------------------------------------------------------------

S(
91, "software-api-compatibility",
"software-engineering", "api-evolution", "design", "advanced",
"An API field must change during a rolling deployment where old and new clients coexist. Design a migration that avoids breaking either generation.",
[
"Prefer an additive compatibility phase: introduce the new representation while preserving the old contract long enough for mixed versions to operate.",
"Define how writes map between representations, measure remaining use of the deprecated field, and remove it only after supported clients have migrated.",
"Do not silently reinterpret an old field when the new field has different semantics; version or explicitly translate the contract instead."
],
"rubric",
"Requires additive compatibility, mixed-version handling, migration telemetry, explicit semantic translation, and delayed removal.",
["api","compatibility","rolling-deployment","versioning"]
),

S(
92, "software-queue-backpressure",
"software-engineering", "backpressure", "failure-analysis", "advanced",
"A producer accepts work faster than workers can process it. An unbounded in-memory queue grows for hours while throughput stays almost constant. Diagnose and redesign the system.",
[
"The growing queue indicates arrival rate exceeds sustainable service rate; accepting more work increases memory use and queueing latency without increasing completed throughput.",
"Measure arrival rate, service rate, queue depth, queue age, rejection rate, and tail latency.",
"Use a bounded queue with admission control or backpressure, and define overload behavior such as rejection, shedding, or upstream flow control rather than converting overload into eventual process failure."
],
"rubric",
"Requires arrival-versus-service reasoning, queue measurements, bounded buffering, and explicit overload behavior.",
["queues","backpressure","overload","latency"]
),

S(
93, "systems-snprintf-boundary",
"systems-programming", "string-formatting", "code-repair", "intermediate",
"C code writes an externally supplied name into a fixed 16-byte array using sprintf. Repair it so overflow and truncation are detected.",
[
"Use a bounded formatting interface such as snprintf and check its return value rather than assuming the destination is large enough.",
"For a 16-byte destination, a nonnegative return value greater than or equal to 16 means the complete formatted result did not fit.",
"The caller should decide whether truncation is acceptable; silently using a truncated identifier can create a second correctness or security bug."
],
"execute",
"Verified by verification/000093_test.sh using a bounded 16-byte destination and explicit truncation detection.",
["c","snprintf","buffer","bounds","strings"]
),

S(
94, "os-condition-predicate",
"operating-systems", "synchronization", "debugging", "advanced",
"A thread waits on a condition variable using `if (!ready) wait(...)` and occasionally continues even though the required predicate is false. Explain the repair.",
[
"A condition variable notification is not the protected state itself. The shared predicate must be checked while holding its mutex.",
"Wait in a loop, not a one-time if statement: after every wakeup reacquire the mutex and test the predicate again.",
"This handles spurious wakeups and cases where another thread consumes or changes the condition before the awakened thread runs."
],
"reference-answer",
"Reviewed against standard POSIX condition-variable predicate and spurious-wakeup semantics.",
["condition-variable","mutex","predicate","synchronization"],
"documentation",
"POSIX condition-variable semantics"
),

S(
95, "architecture-release-acquire",
"computer-architecture", "memory-ordering", "architecture-analysis", "expert",
"A producer writes shared data and then sets a ready flag. A consumer sees the flag but must also be guaranteed to observe the preceding data writes on weakly ordered hardware. Explain the required ordering.",
[
"The flag is a publication mechanism, so ordinary source-code order alone is insufficient for a portable cross-thread guarantee.",
"Use a release operation when publishing the ready flag and an acquire operation when the consumer observes it. When the acquire reads from the corresponding release sequence, earlier producer writes happen-before subsequent consumer reads.",
"Stronger sequential consistency can also provide ordering but may impose semantics beyond what this producer-consumer handoff requires."
],
"rubric",
"Requires release publication, acquire observation, happens-before reasoning, and distinction from relying on source order alone.",
["memory-ordering","acquire","release","concurrency"]
),

S(
96, "linux-cgroup-cpu-throttle",
"linux-infrastructure", "cgroup-cpu", "troubleshooting", "advanced",
"A Linux service has poor throughput although host-wide CPU utilization is low. It runs inside a cgroup with CPU controls. Explain how cgroup throttling can produce this symptom.",
[
"Host idle capacity does not imply a cgroup may consume it; cpu.max can impose a quota within each scheduling period.",
"Inspect the process cgroup, cpu.max, and cpu.stat counters such as nr_throttled and throttled_usec, together with application latency and runnable work.",
"If throttling is confirmed, decide whether the quota is intentional or undersized instead of treating low host utilization as proof that CPU cannot be the bottleneck."
],
"execute",
"Verified by verification/000096_test.sh, which resolves the current cgroup-v2 path and reads cpu.max and cpu.stat.",
["linux","cgroups","cpu","throttling"]
),

S(
97, "security-secret-compare",
"secure-engineering", "constant-time-comparison", "code-repair", "advanced",
"Authentication code compares a supplied MAC with the expected MAC using a normal equality operation. Replace the comparison with an interface intended for secret verification and explain its scope.",
[
"Use a constant-time comparison primitive supplied by the language or cryptographic library, such as hmac.compare_digest for suitable Python byte or string values.",
"This avoids deliberately exiting the comparison at the first mismatching position.",
"A timing-safe comparison protects only this comparison step; parsing, lookup behavior, error messages, rate limits, and the surrounding authentication protocol still need independent review."
],
"unit-test",
"Verified by verification/000097_test.py for accepted equal values and rejected unequal values using hmac.compare_digest.",
["security","mac","constant-time","authentication"]
),

S(
98, "reasoning-benchmark-warmup",
"engineering-reasoning", "benchmark-methodology", "performance-analysis", "intermediate",
"The first benchmark iteration is much slower than later iterations. Decide how to determine whether the difference is meaningful rather than simply deleting the first result.",
[
"Identify mechanisms that differ between cold and warm execution: page cache, JIT compilation, allocator state, connection setup, CPU frequency, or application caches.",
"Measure cold-start and steady-state performance as separate workloads when both matter operationally.",
"Use repeated trials and distributions, and document the warmup policy so benchmark results are reproducible rather than selectively discarding inconvenient samples."
],
"rubric",
"Requires hypotheses for warmup, separate cold/steady-state measurement, repeated trials, and an explicit reproducible policy.",
["benchmark","warmup","measurement","performance"]
),

S(
99, "reasoning-thermal-throttle",
"engineering-reasoning", "performance-diagnosis", "failure-analysis", "advanced",
"A compute benchmark starts fast but becomes 20% slower after sustained load while reported utilization stays high. Design an investigation before blaming software regression.",
[
"High utilization does not guarantee constant operating frequency. Record temperature, clocks, power limits, fan behavior, and per-iteration performance over time.",
"Control ambient conditions and compare short cold runs with sustained runs so thermal or power-limit behavior can be separated from software changes.",
"Correlate the performance transition with hardware telemetry before attributing causality."
],
"rubric",
"Requires time-series clocks, temperature and power evidence, controlled sustained tests, and correlation before causal claims.",
["thermal","benchmark","clocks","power","diagnosis"]
),

S(
100, "embedded-pwm-scaling",
"embedded-systems", "pwm", "implementation", "basic",
"A firmware API accepts a duty cycle from 0 to 100 percent and converts it to a timer period of 1000 abstract ticks. Implement checked scaling.",
[
"Validate that the requested percentage lies in the documented 0..100 range before converting it.",
"For an abstract 1000-tick period, compute round(period_ticks * percent / 100), giving 0, 500, and 1000 for 0%, 50%, and 100%.",
"Real timer peripherals can encode 100% duty differently depending on PWM mode, so hardware-specific register semantics must still be checked."
],
"unit-test",
"Verified by verification/000100_test.py for 0%, 50%, 100%, and out-of-range inputs.",
["embedded","pwm","scaling","timer"]
),

# ---------------------------------------------------------------------
# BATCH 011 — 101..110
# ---------------------------------------------------------------------

S(
101, "software-transaction-retry",
"software-engineering", "database-transactions", "debugging", "advanced",
"A serializable database transaction occasionally aborts because of a serialization conflict. The application treats every abort as a permanent error. Design safer retry behavior.",
[
"Serialization failure can be an expected consequence of concurrent serializable transactions rather than evidence that the database is broken.",
"Retry the complete transaction from a clean transactional state with a bounded retry policy and appropriate backoff.",
"Keep irreversible external side effects outside an automatically repeated transaction or protect them with idempotency so a retry cannot duplicate them."
],
"rubric",
"Requires whole-transaction retry, bounded policy, fresh transactional state, and safe handling of external side effects.",
["database","transaction","serialization","retry"]
),

S(
102, "software-cache-stampede",
"software-engineering", "caching", "design", "advanced",
"A popular cache key expires and hundreds of requests simultaneously recompute the same expensive value. Design a cache-stampede mitigation.",
[
"Coordinate refresh so one request or a limited group performs regeneration while others reuse existing data, wait, or receive a controlled fallback.",
"TTL jitter can prevent many independent keys from expiring simultaneously, while stale-while-revalidate can preserve service during refresh.",
"Bound refresh work and measure cache misses, regeneration concurrency, backend load, and stale-serving behavior."
],
"rubric",
"Requires coordinated regeneration, expiration spreading or stale serving, bounded work, and measurable backend impact.",
["cache","stampede","singleflight","ttl"]
),

S(
103, "systems-string-termination",
"systems-programming", "string-handling", "code-repair", "advanced",
"C code uses strncpy into a fixed buffer and assumes the result is always NUL terminated. Repair the copy contract.",
[
"Do not rely on strncpy to append a terminator when the source length is at least the destination size.",
"Check the source length against capacity, then copy the bytes including the terminator, or use another interface whose truncation semantics are explicitly checked.",
"Rejecting oversized input is often safer than silently converting two distinct long identifiers into the same truncated string."
],
"execute",
"Verified by verification/000103_test.sh with a checked copy that accepts fitting input, rejects oversized input, and preserves termination.",
["c","strings","nul","bounds"]
),

S(
104, "systems-short-read-loop",
"systems-programming", "posix-io", "implementation", "advanced",
"Implement a helper that needs exactly N bytes from a stream-like reader even though each read may return fewer bytes than requested.",
[
"Accumulate bytes until the requested count is satisfied rather than assuming one read fills the buffer.",
"Retry an interrupted operation where the interface documents that retry is appropriate, but distinguish interruption from EOF.",
"If EOF arrives before N bytes, return a short-input failure instead of passing a partially initialized logical message to the parser."
],
"unit-test",
"Verified by verification/000104_test.py using a reader that deliberately returns partial chunks and premature EOF.",
["io","short-read","stream","systems-programming"]
),

S(
105, "os-priority-inversion",
"operating-systems", "scheduling", "failure-analysis", "advanced",
"A high-priority real-time task blocks on a mutex held by a low-priority task while medium-priority CPU work keeps preempting the lock holder. Explain the failure.",
[
"This is priority inversion: the high-priority task is indirectly delayed by medium-priority work because the low-priority mutex owner cannot run long enough to release the resource.",
"Priority inheritance can temporarily raise the lock holder toward the waiting task's priority, allowing the critical section to finish.",
"Measure blocking duration, lock ownership, runnable priorities, and critical-section length before changing scheduler policy."
],
"rubric",
"Requires the low/high/medium inversion chain, priority inheritance, and lock/scheduler measurements.",
["scheduler","priority-inversion","mutex","real-time"]
),

S(
106, "architecture-branchless-tradeoff",
"computer-architecture", "branch-prediction", "technical-decision", "advanced",
"An engineer rewrites predictable branches as branchless arithmetic and assumes the result must be faster. Explain why that conclusion is unsafe.",
[
"A well-predicted branch can be cheap, while branchless code may execute extra instructions for outcomes that would otherwise be skipped.",
"Branchless forms can help with unpredictable control flow or enable vectorization, but they can also increase dependency chains, register pressure, or instruction count.",
"Benchmark the representative data distribution and inspect branch misses, cycles, instructions, and vectorization rather than choosing from source appearance alone."
],
"rubric",
"Requires predictor behavior, branchless overheads, workload dependence, and counter-based comparison.",
["branch","branchless","prediction","performance"]
),

S(
107, "linux-systemd-socket-activation",
"linux-infrastructure", "systemd-socket-activation", "configuration", "intermediate",
"A small Linux service should be started on demand when a client connects to its Unix socket. Explain the systemd socket-activation relationship.",
[
"A `.socket` unit owns the listening endpoint and identifies the service that should handle activation.",
"The matching `.service` starts when traffic arrives, allowing systemd to create the socket before the process exists.",
"The service must be written or configured to consume the socket in the way its activation mode expects; merely defining a socket unit does not make arbitrary software socket-aware."
],
"execute",
"Verified by verification/000107_test.sh using systemd-analyze verify on a temporary matching socket/service pair.",
["linux","systemd","socket-activation","configuration"]
),

S(
108, "networking-tcp-half-close",
"networking", "tcp-half-close", "troubleshooting", "intermediate",
"A TCP recv call returns zero bytes, but the local application may still have data to send. Explain what zero-length receive means and why it is not automatically equivalent to a reset.",
[
"For a connected stream socket, receiving zero after prior connection establishment normally indicates orderly EOF: the peer has sent FIN for its sending direction.",
"TCP is full duplex, so the local endpoint may still be able to transmit until it closes its own sending direction or another error occurs.",
"A reset is different: it aborts connection state and is normally surfaced as an error rather than orderly EOF."
],
"reference-answer",
"Reviewed against standard TCP half-close, FIN, EOF, and reset semantics.",
["tcp","fin","half-close","eof"],
"documentation",
"TCP stream shutdown semantics"
),

S(
109, "reasoning-p99-queue-delay",
"engineering-reasoning", "latency-analysis", "performance-analysis", "advanced",
"p99 request latency doubles while average CPU remains below 50%. Queue depth also rises. Decide what evidence is needed before concluding that more CPU is irrelevant.",
[
"Average utilization can hide short saturation windows, per-core imbalance, locks, downstream waits, or queueing bursts that dominate tail latency.",
"Correlate request latency with queue wait, service time, per-core utilization, concurrency, downstream latency, and arrival bursts at matching timestamps.",
"Then change one suspected constraint experimentally and observe whether queueing and p99 move together."
],
"rubric",
"Requires separation of queue and service time, granular utilization, synchronized evidence, and a causal experiment.",
["p99","queueing","latency","measurement"]
),

S(
110, "reasoning-heisenbug-logging",
"engineering-reasoning", "concurrency-debugging", "debugging", "expert",
"Adding debug logging makes an intermittent concurrency failure disappear. Explain why this is evidence, not a fix, and design a better investigation.",
[
"Logging changes timing, scheduling, cache effects, and synchronization, so it can perturb the race condition being investigated.",
"Preserve the observation as evidence of timing sensitivity and use lower-perturbation tracing, race detectors, deterministic stress, or deliberate schedule perturbation.",
"Do not declare the defect fixed simply because instrumentation changes its reproduction rate."
],
"rubric",
"Requires recognition of observer perturbation, timing sensitivity, lower-impact evidence collection, and reproducible stress methods.",
["heisenbug","race","logging","debugging"]
),

# ---------------------------------------------------------------------
# BATCH 012 — 111..120
# ---------------------------------------------------------------------

S(
111, "software-optimistic-lock",
"software-engineering", "optimistic-concurrency", "design", "advanced",
"Two API clients read version 7 of the same object and both submit updates. Prevent the second stale writer from silently overwriting the first.",
[
"Store a version or equivalent concurrency token and make the update conditional on the version originally read.",
"An update such as `... WHERE id=? AND version=?` should increment the version atomically and verify that exactly one row changed.",
"If zero rows change, report a conflict and require the caller to reload or deliberately merge rather than silently applying stale state."
],
"unit-test",
"Verified by verification/000111_test.py: the first versioned update succeeds and a second stale update is rejected.",
["optimistic-locking","lost-update","version","concurrency"]
),

S(
112, "software-atleast-once-job",
"software-engineering", "job-processing", "design", "advanced",
"A queue provides at-least-once delivery and a worker performs an external side effect. Design the worker so redelivery does not duplicate the logical operation.",
[
"Give each logical job a stable identity and durably record completion or accepted processing for that identity.",
"Make the external operation idempotent where the remote system supports an idempotency key; otherwise coordinate durable local state with a recovery mechanism such as an outbox.",
"Acknowledge the queue only at a point consistent with the chosen durability semantics, and handle ambiguous remote outcomes explicitly."
],
"rubric",
"Requires stable identity, durable deduplication, external idempotency or outbox-style recovery, and explicit acknowledgement semantics.",
["jobs","at-least-once","idempotency","queue"]
),

S(
113, "systems-buffer-ownership",
"systems-programming", "memory-ownership", "code-repair", "advanced",
"A C function stores a pointer to caller-owned mutable text for later use even though the caller may reuse or destroy that storage. Repair the ownership contract.",
[
"If the callee needs the bytes after the caller's ownership period ends, create an owned copy whose lifetime is controlled by the receiving object.",
"Check allocation and copy bounds, document who frees the memory, and release the old owned value when replacing it.",
"Borrowing can be valid only when the lifetime relationship is explicit and guaranteed by the API."
],
"execute",
"Verified by verification/000113_test.sh: an owned heap copy remains unchanged after the caller buffer is modified.",
["c","ownership","lifetime","heap"]
),

S(
114, "os-dirty-writeback",
"operating-systems", "page-cache-writeback", "performance-analysis", "advanced",
"A process writes quickly for several seconds and then experiences long write stalls although application code is unchanged. Explain dirty-page writeback as one hypothesis.",
[
"Buffered writes can initially accumulate dirty pages in memory, making early writes appear faster than the storage device can sustain.",
"As dirty memory reaches writeback thresholds, the kernel must flush data and may throttle writers, exposing storage throughput or latency.",
"Measure dirty-page levels, writeback activity, device latency and bandwidth, and per-write timing over the full run rather than extrapolating from the initial burst."
],
"reference-answer",
"Reviewed against Linux buffered writeback and dirty-page throttling behavior.",
["page-cache","writeback","dirty-pages","storage"],
"documentation",
"Linux dirty-page and writeback semantics"
),

S(
115, "architecture-icache-bloat",
"computer-architecture", "instruction-cache", "performance-analysis", "advanced",
"A build with aggressive inlining executes fewer calls in a microbenchmark but becomes slower in the full application. Analyze instruction-cache pressure.",
[
"Inlining can remove call overhead and expose optimization opportunities, but it also increases code footprint.",
"A larger hot footprint can increase instruction-cache and instruction-TLB misses or reduce locality between frequently executed paths.",
"Compare cycles, instructions, i-cache or front-end stall counters, iTLB behavior, binary layout, and representative workload performance before deciding the inlining policy."
],
"rubric",
"Requires code-size versus call-overhead tradeoff, front-end/i-cache evidence, and representative workload measurement.",
["instruction-cache","inlining","itlb","performance"]
),

S(
116, "linux-cpu-affinity",
"linux-infrastructure", "cpu-affinity", "troubleshooting", "intermediate",
"A compute process uses only one logical CPU even though many CPUs are idle. Explain how CPU affinity can create this symptom.",
[
"A process or its containing environment can restrict the CPUs on which its threads are eligible to run, so host-wide idle CPUs may be unavailable to that workload.",
"Inspect Cpus_allowed_list in `/proc/<pid>/status`, scheduler affinity tools, container or cpuset configuration, and per-thread placement.",
"Change affinity only after determining whether the restriction is intentional for isolation, locality, licensing, or real-time behavior."
],
"execute",
"Verified by verification/000116_test.sh, which reads and validates the current process Cpus_allowed_list.",
["linux","cpu-affinity","cpuset","scheduler"]
),

S(
117, "distributed-monotonic-read",
"distributed-systems", "session-consistency", "technical-decision", "expert",
"A user reads object version 10, then a later request routed to a lagging replica returns version 8. Design a monotonic-read guarantee for the session.",
[
"Track the minimum version or replication position already observed by the session.",
"A later read can use a replica known to have reached at least that position, wait for catch-up, or fall back to a sufficiently current authority such as the primary.",
"Random replica selection without freshness constraints cannot provide monotonic reads merely because every replica eventually converges."
],
"rubric",
"Requires a session freshness token or version, replica eligibility or waiting, fallback behavior, and distinction from eventual convergence.",
["distributed-systems","monotonic-reads","replicas","consistency"]
),

S(
118, "compute-continuous-batching",
"compute-model-infrastructure", "continuous-batching", "performance-analysis", "advanced",
"An LLM server gains throughput from continuous batching but a few requests suffer extreme tail latency. Analyze scheduler fairness.",
[
"Throughput-oriented admission can continually favor requests that fit current batches while older or large requests wait disproportionately.",
"Measure queue age, time-to-first-token, inter-token latency, batch composition, token budget, preemption, and completion latency by request class.",
"Introduce fairness or aging constraints, bounded waiting, or scheduling classes while measuring the throughput cost instead of optimizing aggregate tokens per second alone."
],
"rubric",
"Requires request-level queue/fairness evidence, TTFT and completion metrics, scheduler controls, and explicit throughput-versus-tail tradeoff.",
["llm","continuous-batching","scheduler","tail-latency"]
),

S(
119, "reasoning-capacity-headroom",
"engineering-reasoning", "capacity-planning", "technical-decision", "advanced",
"A service averages only 50% resource utilization, so a team proposes cutting capacity almost in half. Evaluate the decision.",
[
"Average utilization hides peaks, correlated bursts, maintenance events, failover requirements, skew, and the nonlinear queueing cost of operating near saturation.",
"Use percentile demand, per-resource bottlenecks, growth forecasts, failure scenarios, queueing behavior, and recovery time rather than one average number.",
"Define explicit headroom based on the service objective and required failure tolerance, then validate it with load and failover tests."
],
"rubric",
"Requires peak/percentile demand, failure reserve, queueing effects, growth, and SLO-based headroom rather than average-only reasoning.",
["capacity","headroom","slo","queueing"]
),

S(
120, "reasoning-optimization-validation",
"engineering-reasoning", "experimental-design", "testing", "advanced",
"An optimization is claimed to improve throughput by 15% based on one before run and one after run. Design a stronger validation.",
[
"Control workload, input data, software version, power policy, background activity, and other environmental variables that can affect performance.",
"Run repeated trials, randomize or alternate treatment order where practical, report distributions and uncertainty, and inspect relevant hardware or system counters.",
"Confirm the change improves the intended workload without shifting cost into latency, memory, energy, correctness, or another important metric."
],
"rubric",
"Requires controlled repeated trials, order-bias reduction, uncertainty reporting, supporting counters, and regression checks beyond the headline metric.",
["benchmark","experiment","validation","performance"]
),
]


VERIFIERS = {
"000093_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <stdio.h>
#include <string.h>

int copy_name(char out[16], const char *src) {
    int n = snprintf(out, 16, "%s", src);
    return n >= 0 && n < 16;
}

int main(void) {
    char b[16];

    if (!copy_name(b, "alpha")) return 1;
    if (strcmp(b, "alpha") != 0) return 2;

    if (copy_name(b, "0123456789abcdef")) return 3;
    if (b[15] != '\0') return 4;

    puts("bounded formatting verified");
    return 0;
}
C

gcc -std=c11 -Wall -Wextra -Werror "$tmp/t.c" -o "$tmp/t"
"$tmp/t"
''',

"000096_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

cg="$(awk -F: '$1=="0"{print $3}' /proc/self/cgroup)"
base="/sys/fs/cgroup${cg}"

test -r "$base/cpu.max"
test -r "$base/cpu.stat"

echo "cgroup: $cg"
echo "cpu.max: $(cat "$base/cpu.max")"
echo "cpu.stat:"
cat "$base/cpu.stat"
echo "cgroup CPU accounting verified"
''',

"000097_test.py": r'''
import hmac
import unittest

def verify(expected, supplied):
    return hmac.compare_digest(expected, supplied)

class Tests(unittest.TestCase):
    def test_equal(self):
        self.assertTrue(verify(b"abcdef", b"abcdef"))

    def test_unequal(self):
        self.assertFalse(verify(b"abcdef", b"abcdeg"))

if __name__ == "__main__":
    unittest.main()
''',

"000100_test.py": r'''
import unittest

def ticks(percent, period=1000):
    if isinstance(percent, bool) or not isinstance(percent, (int, float)):
        raise ValueError("percent")
    if percent < 0 or percent > 100:
        raise ValueError("range")
    return round(period * percent / 100)

class Tests(unittest.TestCase):
    def test_scale(self):
        self.assertEqual(ticks(0), 0)
        self.assertEqual(ticks(50), 500)
        self.assertEqual(ticks(100), 1000)

    def test_range(self):
        for x in (-1, 101):
            with self.assertRaises(ValueError):
                ticks(x)

if __name__ == "__main__":
    unittest.main()
''',

"000103_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <stdio.h>
#include <string.h>

int copy_name(char *dst, size_t cap, const char *src) {
    size_t n = strlen(src);
    if (n >= cap) return 0;
    memcpy(dst, src, n + 1);
    return 1;
}

int main(void) {
    char b[8];

    if (!copy_name(b, sizeof b, "abc")) return 1;
    if (strcmp(b, "abc") != 0) return 2;
    if (copy_name(b, sizeof b, "12345678")) return 3;

    puts("checked terminated copy verified");
    return 0;
}
C

gcc -std=c11 -Wall -Wextra -Werror "$tmp/t.c" -o "$tmp/t"
"$tmp/t"
''',

"000104_test.py": r'''
import unittest

class Reader:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def read(self, n):
        if not self.chunks:
            return b""
        chunk = self.chunks.pop(0)
        return chunk[:n]

def read_exact(reader, n):
    out = bytearray()
    while len(out) < n:
        chunk = reader.read(n - len(out))
        if not chunk:
            raise EOFError("short input")
        out.extend(chunk)
    return bytes(out)

class Tests(unittest.TestCase):
    def test_partial(self):
        self.assertEqual(
            read_exact(Reader([b"a", b"bc", b"de"]), 5),
            b"abcde",
        )

    def test_eof(self):
        with self.assertRaises(EOFError):
            read_exact(Reader([b"ab"]), 3)

if __name__ == "__main__":
    unittest.main()
''',

"000107_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/ce107.socket" <<'EOF'
[Socket]
ListenStream=/tmp/ce107.sock
Service=ce107.service
EOF

cat > "$tmp/ce107.service" <<'EOF'
[Service]
ExecStart=/bin/cat
StandardInput=socket
EOF

SYSTEMD_UNIT_PATH="$tmp:/etc/systemd/system:/usr/lib/systemd/system:/lib/systemd/system" \
systemd-analyze verify ce107.socket ce107.service

echo "socket activation units verified"
''',

"000111_test.py": r'''
import unittest

def update(row, expected_version, value):
    if row["version"] != expected_version:
        return False

    row["value"] = value
    row["version"] += 1
    return True

class Tests(unittest.TestCase):
    def test_stale_writer(self):
        row = {"value": "A", "version": 7}

        self.assertTrue(update(row, 7, "B"))
        self.assertFalse(update(row, 7, "C"))

        self.assertEqual(row["value"], "B")
        self.assertEqual(row["version"], 8)

if __name__ == "__main__":
    unittest.main()
''',

"000113_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *own_copy(const char *src) {
    size_t n = strlen(src) + 1;
    char *p = malloc(n);
    if (!p) return NULL;
    memcpy(p, src, n);
    return p;
}

int main(void) {
    char source[16] = "alpha";
    char *owned = own_copy(source);

    if (!owned) return 1;

    strcpy(source, "beta");

    if (strcmp(owned, "alpha") != 0) {
        free(owned);
        return 2;
    }

    free(owned);
    puts("owned copy verified");
    return 0;
}
C

gcc -std=c11 -Wall -Wextra -Werror "$tmp/t.c" -o "$tmp/t"
"$tmp/t"
''',

"000116_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

line="$(grep '^Cpus_allowed_list:' /proc/self/status)"
test -n "$line"

echo "$line"
echo "CPU affinity visibility verified"
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

    result = {}

    for name, content in VERIFIERS.items():
        n = int(name[:6])

        if start <= n <= end:
            result[name] = content

    return result
