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
# VALIDATION BATCH 003 — 221..230
# =====================================================================

Q(
221, "software-job-heartbeat",
"software-engineering", "background-jobs",
"design", "advanced",
"A worker claims a long-running job from a shared queue. If the worker crashes, another worker must eventually recover the job without routinely executing it twice. Design the ownership protocol.",
[
"Represent ownership with a bounded lease or visibility timeout rather than permanent assignment.",
"Renew ownership while useful progress continues and stop committing work after ownership is lost.",
"Make job effects idempotent or checkpointed because failure near the ownership boundary can still create ambiguous completion.",
"Expose lease age, renewal failure, recovery count, and duplicate-attempt metrics."
],
tags=("jobs","lease","recovery","idempotency")
),

Q(
222, "systems-size-addition",
"systems-programming", "integer-overflow",
"code-repair", "advanced",
"C code computes `header_len + payload_len` using size_t before allocating a message buffer. Repair the addition so wraparound cannot create an undersized allocation.",
[
"Check whether payload_len is greater than SIZE_MAX minus header_len before performing the addition.",
"Reject the operation when the mathematical sum is not representable in size_t.",
"After arithmetic safety is established, enforce protocol-level maximum message sizes as a separate resource limit."
],
verification="unit-test",
details="Verified by verification-validation/000222_test.py for ordinary sums, boundary values, and overflow rejection.",
tags=("c","size-t","overflow","allocation")
),

Q(
223, "os-futex-spurious",
"operating-systems", "futexes",
"debugging", "advanced",
"A Linux synchronization primitive built on futex wait assumes every return means the protected condition is now true. Explain why the higher-level condition still needs to be rechecked.",
[
"A futex wait is a blocking mechanism, not the application predicate itself.",
"Wakeups, interruptions, races, or changed state can cause the waiter to resume without the desired logical condition being satisfied.",
"Recheck the protected predicate under the synchronization protocol and wait again when necessary.",
"Correctness must come from the shared-state protocol rather than the mere fact that a wait syscall returned."
],
verification="reference-answer",
source_type="documentation",
reference="Linux futex wait/wake semantics",
tags=("linux","futex","synchronization","predicate")
),

Q(
224, "architecture-stride-conflict",
"computer-architecture", "cache-indexing",
"performance-analysis", "advanced",
"An array traversal becomes dramatically slower when its stride changes from 63 cache lines to 64 cache lines. Analyze cache-set conflict as a hypothesis.",
[
"Power-of-two stride relationships can map repeated accesses onto a small subset of cache sets depending on cache indexing.",
"Limited associativity can then evict useful lines even when the total working set would nominally fit in the cache.",
"Compare miss rates and runtime across nearby strides and controlled alignments.",
"Do not attribute the effect solely to capacity without testing indexing and conflict behavior."
],
tags=("cache","stride","associativity","conflict")
),

Q(
225, "embedded-sensor-clamp",
"embedded-systems", "sensor-processing",
"implementation", "basic",
"A sensor-processing stage converts raw readings to an allowed engineering range of -40 to 125. Implement clamping without modifying values already inside the range.",
[
"Return -40 for values below the lower bound.",
"Return 125 for values above the upper bound.",
"Return the original value when it already lies inside the allowed interval.",
"Keep clamping separate from validation when out-of-range input should instead be treated as a sensor fault."
],
verification="unit-test",
details="Verified by verification-validation/000225_test.py for low, high, boundary, and in-range values.",
tags=("embedded","sensor","clamp","bounds")
),

Q(
226, "networking-arp-stale",
"networking", "neighbor-discovery",
"troubleshooting", "intermediate",
"A host changes its Ethernet interface but keeps the same IPv4 address. Some peers briefly continue sending frames to the old MAC address. Explain the stale-neighbor state.",
[
"Peers can cache the IP-to-MAC mapping and continue using the old link-layer destination until the neighbor entry is updated or expires.",
"Inspect ARP or neighbor tables and packet captures on affected peers.",
"Gratuitous ARP can help advertise the new mapping, but network devices and security policy may affect propagation.",
"The IP route can remain correct while delivery still fails at the local link-layer resolution step."
],
verification="reference-answer",
source_type="documentation",
reference="ARP neighbor-cache behavior",
tags=("arp","neighbor-cache","mac","ipv4")
),

Q(
227, "distributed-causal-message",
"distributed-systems", "causal-ordering",
"architecture-analysis", "expert",
"Service A emits event X, service B processes X and emits Y, but another consumer can observe Y before X. Design metadata that allows the consumer to preserve the causal dependency.",
[
"Represent causal dependency using metadata such as logical clocks, vector clocks, or explicit predecessor identifiers appropriate to the system.",
"Delay or buffer Y when its required causal predecessors have not yet been observed.",
"Define how missing predecessors, retention, and permanently unavailable events are handled.",
"Physical timestamps alone do not reliably establish causality across machines."
],
tags=("distributed-systems","causality","logical-clock","events")
),

Q(
228, "linux-openat-path",
"linux-infrastructure", "filesystem-security",
"technical-decision", "advanced",
"A service repeatedly resolves paths relative to a trusted directory and wants to reduce dependence on the process working directory. Explain the value of directory-relative operations such as openat.",
[
"A directory file descriptor provides an explicit anchor for relative pathname resolution.",
"This avoids accidental dependence on a mutable process current working directory.",
"Directory-relative APIs can also compose with stronger pathname-resolution controls on modern Linux.",
"They do not automatically make an untrusted path safe; traversal, symlinks, and policy still require deliberate handling."
],
verification="reference-answer",
source_type="documentation",
reference="Linux openat(2) directory-relative pathname semantics",
tags=("linux","openat","path","filesystem")
),

Q(
229, "software-cache-version-key",
"software-engineering", "cache-consistency",
"design", "advanced",
"A service changes the serialization format of cached objects while old and new application versions run simultaneously. Prevent one version from misinterpreting the other's cached values.",
[
"Include a representation or schema version in the cache key or envelope.",
"Old and new deployments can then coexist without assuming binary or semantic compatibility.",
"Define expiration or migration for obsolete versions rather than relying on every old entry disappearing immediately.",
"Versioning the cache format is separate from versioning the underlying business object."
],
tags=("cache","schema-version","deployment","compatibility")
),

Q(
230, "systems-hex-byte",
"systems-programming", "text-parsing",
"implementation", "intermediate",
"Implement conversion of exactly two hexadecimal ASCII characters into one byte, rejecting malformed characters and incorrect input length.",
[
"Require exactly two input characters.",
"Map decimal and alphabetic hexadecimal digits explicitly and reject any character outside those sets.",
"Combine the high nibble and low nibble only after both characters are validated."
],
verification="unit-test",
details="Verified by verification-validation/000230_test.py for upper/lower case, boundaries, malformed characters, and invalid length.",
tags=("hex","parser","byte","validation")
),

# =====================================================================
# VALIDATION BATCH 004 — 231..240
# =====================================================================

Q(
231, "os-scheduler-affinity-migration",
"operating-systems", "cpu-scheduling",
"performance-analysis", "advanced",
"A latency-sensitive thread is allowed to run on every CPU and frequently migrates between cores. Explain why migration can sometimes hurt even when CPU utilization is low.",
[
"Migration can reduce locality in private caches and translation structures and can alter NUMA locality.",
"Measure migration rate, cache behavior, per-thread latency, CPU topology, and runnable contention.",
"Restricting affinity can improve locality but can also reduce scheduling flexibility or create hotspots.",
"Choose affinity policy from measured workload behavior rather than assuming pinning is always faster."
],
tags=("scheduler","migration","affinity","locality")
),

Q(
232, "architecture-false-dependency",
"computer-architecture", "register-dependencies",
"performance-analysis", "advanced",
"A low-level loop appears to contain independent operations, but one instruction form creates an unnecessary dependency on a previous destination value. Explain why removing the false dependency can improve throughput.",
[
"Processors schedule operations according to dependency relationships, and an unnecessary dependency can serialize otherwise parallel work.",
"Some instruction encodings or partial-register updates can preserve old destination state and create extra dependency constraints.",
"Use architecture-specific profiling and generated-code inspection to identify the dependency.",
"Prefer an equivalent instruction form that communicates independence when correctness permits it."
],
tags=("dependency","register","instruction","performance")
),

Q(
233, "embedded-majority-sample",
"embedded-systems", "digital-input",
"implementation", "intermediate",
"A noisy digital input is sampled three times. Implement a majority vote so one transient flipped sample does not change the logical result.",
[
"Count how many of the three boolean samples are asserted.",
"Return true when at least two samples are true.",
"Return false when at least two samples are false.",
"This filters one disagreeing sample but is not equivalent to time-based debounce for mechanical contacts."
],
verification="unit-test",
details="Verified by verification-validation/000233_test.py across all eight three-sample combinations.",
tags=("embedded","majority-vote","noise","digital-input")
),

Q(
234, "networking-ecmp-hash",
"networking", "routing",
"architecture-analysis", "advanced",
"Two hosts traverse different equal-cost network paths even though both destinations are in the same prefix. Explain flow hashing in ECMP.",
[
"Equal-cost multipath routing can select among next hops using a hash of flow fields rather than choosing one fixed path per destination prefix.",
"Different source or destination addresses, ports, or protocol fields can therefore produce different paths.",
"Per-flow hashing helps avoid packet reordering that could occur with arbitrary per-packet balancing.",
"Inspect actual hashing policy and path telemetry before assuming all equal-cost traffic follows the same links."
],
tags=("ecmp","routing","hash","flow")
),

Q(
235, "distributed-tombstone-retention",
"distributed-systems", "replicated-storage",
"failure-analysis", "expert",
"A replicated store represents deletion with tombstones. An offline replica returns after tombstones have already been discarded and resurrects deleted data. Explain the retention problem.",
[
"A deletion marker must remain available long enough for replicas that may contain older values to learn about the deletion.",
"Discarding tombstones before the system's repair or replica-recovery horizon can allow stale values to appear newer simply because the deletion evidence vanished.",
"Retention policy must be coordinated with anti-entropy, maximum tolerated replica downtime, or explicit replica replacement procedures.",
"Garbage collection of tombstones is therefore a distributed consistency decision, not only a local storage optimization."
],
tags=("distributed-systems","tombstone","replication","repair")
),

Q(
236, "linux-fsync-directory",
"linux-infrastructure", "filesystem-durability",
"technical-decision", "advanced",
"A program writes a new file, fsyncs the file contents, and renames it into place. Explain why directory durability may also matter for crash-safe publication.",
[
"Durability of file contents and durability of directory-entry updates are distinct concerns.",
"After rename or creation, syncing the containing directory may be required when the application needs the name-to-inode update to survive a crash according to the filesystem contract.",
"Use a documented crash-safe update sequence appropriate to the target filesystem and operating system.",
"Do not infer namespace durability solely from successfully fsyncing the file data."
],
verification="reference-answer",
source_type="documentation",
reference="POSIX/Linux filesystem fsync and directory-entry durability considerations",
tags=("linux","fsync","rename","durability")
),

Q(
237, "software-bulkhead-pool",
"software-engineering", "resilience",
"design", "advanced",
"One slow downstream dependency consumes every worker thread in a service, causing unrelated endpoints to stop responding. Design a bulkhead.",
[
"Partition concurrency or worker capacity so one dependency or workload class cannot consume every execution slot.",
"Give each partition bounded queues and explicit overload behavior.",
"Size isolation boundaries from measured demand and downstream capacity rather than arbitrary equal division.",
"Monitor rejection, saturation, queue age, and unused capacity because excessive isolation can also waste resources."
],
tags=("bulkhead","resilience","thread-pool","isolation")
),

Q(
238, "compute-tensor-bytes",
"compute-model-infrastructure", "memory-accounting",
"performance-analysis", "intermediate",
"A tensor has shape 32 × 128 × 4096 and uses FP16 elements. Estimate its raw storage requirement before allocator overhead.",
[
"The tensor contains 32 × 128 × 4096 = 16,777,216 elements.",
"FP16 uses two bytes per element, giving 33,554,432 bytes.",
"That is 32 MiB using binary units.",
"Actual process memory can be larger because of allocator metadata, alignment, temporary buffers, replicas, or framework bookkeeping."
],
verification="unit-test",
details="Verified by verification-validation/000238_test.py for element-count and byte-size calculations.",
tags=("tensor","fp16","memory","units")
),

Q(
239, "secure-session-fixation",
"secure-engineering", "session-management",
"failure-analysis", "expert",
"An application keeps the same anonymous session identifier after a user successfully authenticates. Explain the session-fixation risk and repair.",
[
"An attacker who can cause or learn the pre-authentication session identifier may retain access if authentication simply upgrades that same identifier.",
"Rotate to a fresh unpredictable session identifier when privilege level changes, especially at login.",
"Invalidate or sever the old identifier and preserve only intentionally migrated session state.",
"Cookie security attributes and transport protection remain necessary but do not replace identifier rotation."
],
tags=("security","session","fixation","authentication")
),

Q(
240, "reasoning-amdahl-bound",
"engineering-reasoning", "performance-modeling",
"technical-decision", "advanced",
"An optimization makes 80% of a program twice as fast while the remaining 20% is unchanged. Estimate the ideal overall speedup and explain the bound.",
[
"Normalize original runtime to 1.0: the optimized portion falls from 0.8 to 0.4 while the unchanged portion remains 0.2.",
"New ideal runtime is therefore 0.6 of the original.",
"Overall speedup is 1 / 0.6, approximately 1.67×.",
"The unchanged fraction limits total speedup even if the optimized component becomes substantially faster."
],
verification="unit-test",
details="Verified by verification-validation/000240_test.py using the Amdahl speedup calculation.",
tags=("amdahl","speedup","performance","reasoning")
),
]


VERIFIERS = {

"000222_test.py": r'''
import unittest

SIZE_MAX = (1 << 64) - 1

def checked_add(a, b):
    if a < 0 or b < 0:
        raise ValueError("negative")
    if b > SIZE_MAX - a:
        raise OverflowError("size overflow")
    return a + b

class Tests(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(checked_add(20, 30), 50)

    def test_boundary(self):
        self.assertEqual(checked_add(SIZE_MAX, 0), SIZE_MAX)

    def test_overflow(self):
        with self.assertRaises(OverflowError):
            checked_add(SIZE_MAX, 1)

if __name__ == "__main__":
    unittest.main()
''',

"000225_test.py": r'''
import unittest

def clamp_sensor(value):
    return max(-40, min(125, value))

class Tests(unittest.TestCase):
    def test_low(self):
        self.assertEqual(clamp_sensor(-100), -40)

    def test_high(self):
        self.assertEqual(clamp_sensor(200), 125)

    def test_bounds(self):
        self.assertEqual(clamp_sensor(-40), -40)
        self.assertEqual(clamp_sensor(125), 125)

    def test_inside(self):
        self.assertEqual(clamp_sensor(37), 37)

if __name__ == "__main__":
    unittest.main()
''',

"000230_test.py": r'''
import unittest

def nibble(ch):
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "a" <= ch <= "f":
        return 10 + ord(ch) - ord("a")
    if "A" <= ch <= "F":
        return 10 + ord(ch) - ord("A")
    raise ValueError("hex")

def hex_byte(text):
    if len(text) != 2:
        raise ValueError("length")
    return (nibble(text[0]) << 4) | nibble(text[1])

class Tests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(hex_byte("00"), 0x00)
        self.assertEqual(hex_byte("ff"), 0xFF)
        self.assertEqual(hex_byte("A5"), 0xA5)

    def test_invalid(self):
        for text in ("", "0", "000", "G0"):
            with self.assertRaises(ValueError):
                hex_byte(text)

if __name__ == "__main__":
    unittest.main()
''',

"000233_test.py": r'''
import itertools
import unittest

def majority3(a, b, c):
    return int(bool(a)) + int(bool(b)) + int(bool(c)) >= 2

class Tests(unittest.TestCase):
    def test_all_combinations(self):
        for values in itertools.product((False, True), repeat=3):
            expected = sum(values) >= 2
            self.assertEqual(
                majority3(*values),
                expected,
                values,
            )

if __name__ == "__main__":
    unittest.main()
''',

"000238_test.py": r'''
import unittest

def tensor_bytes(shape, bytes_per_element):
    count = 1
    for dim in shape:
        if dim < 0:
            raise ValueError("dimension")
        count *= dim
    return count, count * bytes_per_element

class Tests(unittest.TestCase):
    def test_example(self):
        elements, size = tensor_bytes(
            (32, 128, 4096),
            2,
        )
        self.assertEqual(elements, 16_777_216)
        self.assertEqual(size, 33_554_432)
        self.assertEqual(size // (1024 * 1024), 32)

if __name__ == "__main__":
    unittest.main()
''',

"000240_test.py": r'''
import unittest

def amdahl(fraction, component_speedup):
    if not 0 <= fraction <= 1:
        raise ValueError("fraction")
    if component_speedup <= 0:
        raise ValueError("speedup")

    new_time = (
        (1 - fraction)
        + fraction / component_speedup
    )

    return 1 / new_time

class Tests(unittest.TestCase):
    def test_example(self):
        self.assertAlmostEqual(
            amdahl(0.8, 2),
            1 / 0.6,
        )

    def test_no_change(self):
        self.assertEqual(
            amdahl(0.8, 1),
            1.0,
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
