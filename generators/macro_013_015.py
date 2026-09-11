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
    Q(121,"software-graceful-shutdown","software-engineering","service-lifecycle","design","advanced",
      "A service receives SIGTERM during deployment while requests and background jobs are active. Design graceful shutdown.",
      [
        "Stop accepting new work before terminating active work.",
        "Allow bounded time for in-flight requests and jobs to finish.",
        "Release resources and force termination after a documented deadline.",
        "Make shutdown state observable so load balancers stop routing traffic."
      ], tags=("shutdown","deployment","lifecycle")),

    Q(122,"systems-signed-decode","systems-programming","binary-parsing","implementation","advanced",
      "Decode a signed 16-bit big-endian field from two protocol bytes without relying on host byte order.",
      [
        "Combine bytes explicitly into an unsigned 16-bit value.",
        "Interpret values with bit 15 set using two's-complement signed conversion.",
        "Reject inputs whose length is not exactly two bytes."
      ], verification="unit-test",
      details="Verified by verification/000122_test.py for positive, negative, minimum, maximum, zero, and malformed inputs.",
      tags=("binary","endianness","int16")),

    Q(123,"reasoning-baseline-selection","engineering-reasoning","experimental-design","technical-decision","advanced",
      "A proposed optimization is compared only with an obsolete implementation. Decide what baseline is needed.",
      [
        "Compare against the current production or strongest relevant implementation.",
        "Keep workload, hardware, configuration, and correctness criteria equivalent.",
        "Report absolute results as well as relative improvement.",
        "Use multiple baselines when the engineering question has more than one realistic alternative."
      ], tags=("baseline","benchmark","experiment")),

    Q(124,"os-thundering-wakeup","operating-systems","synchronization","performance-analysis","advanced",
      "Many worker threads wake for one newly available item, but only one can consume it. Explain the performance problem.",
      [
        "Waking unnecessary waiters creates scheduler activity and lock contention.",
        "Measure wakeups, runnable threads, context switches, lock wait, and useful work.",
        "Prefer targeted notification or work-distribution mechanisms when only limited concurrency can proceed."
      ], tags=("scheduler","wakeups","contention")),

    Q(125,"architecture-release-sequence","computer-architecture","memory-ordering","architecture-analysis","expert",
      "A producer publishes initialized data through an atomic ready flag. Explain release/acquire ordering.",
      [
        "Publish the flag with release semantics after initializing the shared state.",
        "Observe the publication with acquire semantics before consuming that state.",
        "The synchronization creates the required happens-before relationship.",
        "Do not rely only on source-code ordering on weakly ordered hardware."
      ], tags=("memory-ordering","release","acquire")),

    Q(126,"linux-sparse-file","linux-infrastructure","filesystem-space","troubleshooting","intermediate",
      "A file reports a logical size of several gigabytes but consumes very little filesystem space. Explain sparse files.",
      [
        "Logical file length and allocated data blocks are different quantities.",
        "Holes read as zero without requiring physical blocks for every byte.",
        "Compare apparent size with allocated blocks using stat or du before diagnosing a storage leak."
      ], verification="execute",
      details="Verified by verification/000126_test.sh using a sparse temporary file whose logical size greatly exceeds allocated space.",
      tags=("linux","sparse-file","filesystem")),

    Q(127,"software-retry-budget","software-engineering","retries","design","advanced",
      "A dependency outage causes every service layer to retry independently, multiplying load. Design a retry budget.",
      [
        "Bound retries across the end-to-end operation instead of allowing unlimited retries at every layer.",
        "Use deadlines, exponential backoff, and jitter.",
        "Retry only operations whose semantics are safe or idempotent.",
        "Measure retry amplification and stop retrying when additional work harms recovery."
      ], tags=("retries","backoff","overload")),

    Q(128,"systems-realloc-safe","systems-programming","memory-allocation","code-repair","advanced",
      "C code assigns realloc directly back to the only pointer and can lose the original allocation on failure. Repair it.",
      [
        "Store realloc's result in a temporary pointer.",
        "Replace the original pointer only after successful allocation.",
        "Preserve the original allocation when realloc returns NULL.",
        "Check size arithmetic before requesting the new allocation."
      ], verification="execute",
      details="Verified by verification/000128_test.sh with a safe temporary-pointer realloc pattern.",
      tags=("c","realloc","memory")),

    Q(129,"compute-pinned-memory","compute-model-infrastructure","host-device-transfer","performance-analysis","advanced",
      "GPU transfers are slower than expected when inputs originate in pageable host memory. Explain why pinned memory may help.",
      [
        "Asynchronous DMA commonly works best from page-locked host buffers.",
        "Pageable transfers may require staging or additional synchronization.",
        "Pinned memory has system-wide cost and should not be allocated without bounds.",
        "Measure transfer bandwidth and overlap rather than assuming pinning improves every workload."
      ], tags=("gpu","pinned-memory","dma")),

    Q(130,"security-password-storage","secure-engineering","password-storage","design","expert",
      "A service stores SHA-256(password) in its database. Design safer password storage.",
      [
        "Use a password-specific adaptive KDF such as Argon2id, scrypt, or an appropriately configured bcrypt/PBKDF2 deployment.",
        "Generate a unique salt for each password.",
        "Choose cost parameters that are intentionally expensive but operationally acceptable.",
        "Support parameter upgrades and never store reversible plaintext-equivalent credentials."
      ], tags=("security","password","kdf","argon2")),

    Q(131,"software-index-selectivity","software-engineering","database-indexing","performance-analysis","advanced",
      "A database index exists but a query planner still chooses a table scan. Explain why index existence alone proves little.",
      [
        "Low selectivity can make scanning cheaper than many indexed lookups.",
        "Planner statistics, result cardinality, clustering, and query predicates affect the decision.",
        "Use the actual execution plan and measured I/O or timing before forcing an index."
      ], tags=("database","index","query-plan")),

    Q(132,"systems-length-overflow","systems-programming","integer-overflow","code-repair","expert",
      "A parser allocates `count * element_size` bytes from an untrusted count. Repair the overflow boundary.",
      [
        "Check count against SIZE_MAX divided by element size before multiplication.",
        "Reject values whose product is not representable.",
        "Validate protocol-level limits even when arithmetic itself is safe."
      ], verification="execute",
      details="Verified by verification/000132_test.sh using checked size multiplication.",
      tags=("c","overflow","allocation")),

    Q(133,"reasoning-hypothesis-ranking","engineering-reasoning","debugging-methodology","debugging","advanced",
      "A performance regression has five plausible causes. Design a way to investigate without randomly changing settings.",
      [
        "Rank hypotheses by consistency with observed evidence and cost of testing.",
        "Choose measurements that distinguish competing explanations rather than merely collecting more metrics.",
        "Change one meaningful variable at a time when testing causality.",
        "Update the hypothesis ranking after each result."
      ], tags=("debugging","hypothesis","measurement")),

    Q(134,"os-mmap-truncate","operating-systems","virtual-memory","failure-analysis","expert",
      "A process maps a file and another process truncates the file below a page the first process later accesses. Explain the possible failure.",
      [
        "A mapping does not make bytes beyond the new file extent permanently valid.",
        "Access to mapped pages whose backing file region no longer exists can fault, commonly surfacing as SIGBUS on Unix-like systems.",
        "Coordinate file lifetime and size with mapping users rather than assuming mmap snapshots the complete file."
      ], verification="reference-answer",
      source_type="documentation",
      reference="Linux mmap(2) semantics",
      tags=("mmap","sigbus","truncate")),

    Q(135,"architecture-unaligned-access","computer-architecture","memory-alignment","technical-decision","advanced",
      "Code performs unaligned integer loads by casting arbitrary byte pointers. Explain portability and performance concerns.",
      [
        "Some architectures tolerate unaligned accesses while others trap or require special handling.",
        "Pointer casts can also violate language alignment or aliasing requirements.",
        "Use memcpy or explicit decoding for portable binary parsing, and benchmark architecture-specific optimized paths separately."
      ], tags=("alignment","unaligned","portability")),

    Q(136,"linux-apparent-size","linux-infrastructure","filesystem-space","troubleshooting","intermediate",
      "Two tools report very different sizes for the same directory tree. Explain why apparent bytes and allocated filesystem blocks can differ.",
      [
        "Sparse files, compression, deduplication, hard links, and block allocation can separate logical size from physical consumption.",
        "Clarify whether the question is file length, allocated blocks, or filesystem free-space impact.",
        "Use tools and options that measure the intended quantity before comparing results."
      ], verification="reference-answer",
      source_type="documentation",
      reference="Linux stat(2) and filesystem allocation semantics",
      tags=("linux","du","filesystem","blocks")),

    Q(137,"software-circuit-breaker","software-engineering","resilience","design","advanced",
      "A failing dependency causes callers to wait for timeout after timeout. Design a circuit breaker without hiding recovery.",
      [
        "Open the circuit after a defined failure signal so calls fail quickly instead of consuming resources on known-bad attempts.",
        "After a cooldown, allow limited probes in a half-open state.",
        "Close only after recovery evidence, and expose breaker state and rejected-call metrics.",
        "A circuit breaker complements rather than replaces timeout and retry policy."
      ], tags=("circuit-breaker","resilience","timeouts")),

    Q(138,"systems-errno-preservation","systems-programming","error-handling","debugging","intermediate",
      "C cleanup code calls another function after a failure and then reports errno, accidentally reporting the cleanup call's error. Repair it.",
      [
        "Save errno immediately after the operation whose failure is being reported.",
        "Perform cleanup after preserving the value.",
        "Restore or report the saved error rather than assuming errno remains unchanged across unrelated calls."
      ], verification="reference-answer",
      source_type="documentation",
      reference="POSIX errno semantics",
      tags=("c","errno","error-handling")),

    Q(139,"compute-quantization-latency","compute-model-infrastructure","quantization","performance-analysis","advanced",
      "A quantized model uses less memory but does not improve latency. Explain why memory reduction does not guarantee faster inference.",
      [
        "Quantized kernels can have different hardware support, conversion cost, packing overhead, and arithmetic throughput.",
        "A workload may be compute-bound, memory-bound, launch-bound, or communication-bound.",
        "Measure kernel time, bandwidth, occupancy, batch size, and end-to-end latency rather than inferring speed from model size."
      ], tags=("quantization","latency","gpu","inference")),

    Q(140,"reasoning-confounded-benchmark","engineering-reasoning","experimental-design","testing","advanced",
      "A new build looks faster, but it was tested after reboot while the old build was tested after hours of background workload. Evaluate the comparison.",
      [
        "The treatment is confounded with machine state, so the observed difference cannot cleanly be attributed to the build.",
        "Control or randomize environmental factors and repeat both treatments under comparable conditions.",
        "Record distributions and system telemetry instead of relying on one before/after pair."
      ], tags=("benchmark","confounding","experiment")),

    Q(141,"software-event-schema","software-engineering","event-schema","design","advanced",
      "Event producers and consumers are deployed independently. A producer needs to evolve an event schema without breaking older consumers.",
      [
        "Prefer additive fields with defined defaults or optional semantics during the compatibility window.",
        "Do not repurpose an existing field with incompatible meaning.",
        "Measure consumer adoption and preserve old fields until supported consumers migrate.",
        "Use explicit versioning when additive compatibility cannot express the new semantics."
      ], tags=("events","schema","compatibility")),

    Q(142,"systems-narrowing-conversion","systems-programming","integer-conversions","code-repair","advanced",
      "A 64-bit externally supplied length is cast to uint32_t before validation. Repair the order of operations.",
      [
        "Validate the original wide value against UINT32_MAX before narrowing.",
        "Perform the cast only after representability is established.",
        "Also enforce application-level maximum lengths rather than treating the type limit as the only valid bound."
      ], verification="unit-test",
      details="Verified by verification/000142_test.py for valid bounds and rejection above UINT32_MAX.",
      tags=("integer","narrowing","uint32","bounds")),

    Q(143,"reasoning-canary-causality","engineering-reasoning","experimental-design","technical-decision","advanced",
      "A canary deployment has higher latency than the control pool, but it also receives a different traffic mix. Decide whether the new build is responsible.",
      [
        "Different workload composition is a confounder, so raw pool averages do not establish causality.",
        "Compare matched request classes or randomize traffic assignment where operationally safe.",
        "Control hardware and capacity differences and inspect per-request or stratified latency distributions."
      ], tags=("canary","causality","traffic","latency")),

    Q(144,"os-load-average-io","operating-systems","scheduling","troubleshooting","intermediate",
      "Linux load average is high while CPU utilization is modest. Explain why load average is not simply CPU percentage.",
      [
        "Linux load includes runnable work and tasks in certain uninterruptible waits, commonly including storage-related waits.",
        "Inspect run queues, blocked tasks, I/O latency, CPU utilization, and process states together.",
        "High load therefore does not prove CPUs themselves are saturated."
      ], verification="reference-answer",
      source_type="documentation",
      reference="Linux load-average and task-state semantics",
      tags=("linux","load-average","io","scheduler")),

    Q(145,"architecture-prefetch-overfetch","computer-architecture","hardware-prefetching","performance-analysis","advanced",
      "Disabling a hardware prefetcher unexpectedly improves a sparse-access workload. Explain how prefetching can hurt.",
      [
        "Incorrect predictions can consume memory bandwidth and bring unused lines into caches.",
        "Prefetched lines can evict useful data and increase contention for shared memory resources.",
        "Measure useful versus wasted traffic, cache misses, bandwidth, and performance across representative access patterns."
      ], tags=("prefetch","bandwidth","cache","performance")),

    Q(146,"linux-symlink-config-swap","linux-infrastructure","deployment-files","technical-decision","advanced",
      "A service reads a versioned configuration directory selected through a symlink. Design an update that avoids exposing a half-written directory.",
      [
        "Prepare the new version completely under a separate path.",
        "Switch the selector only after the new tree is ready, using an atomic rename-style transition where filesystem semantics permit it.",
        "Keep rollback targets until the new configuration is validated.",
        "Do not update individual live files piecemeal when readers require a consistent set."
      ], tags=("linux","symlink","atomic-update","configuration")),

    Q(147,"software-pool-timeout","software-engineering","connection-pooling","design","advanced",
      "A service has a database pool, but requests can wait indefinitely for a connection during overload. Design bounded acquisition behavior.",
      [
        "Set an acquisition deadline or timeout so pool exhaustion becomes an explicit failure rather than unbounded queueing.",
        "Measure pool occupancy, wait duration, query service time, and request deadlines.",
        "Size the pool based on database capacity rather than only application concurrency, and apply admission control when demand exceeds sustainable throughput."
      ], tags=("database","pool","timeout","backpressure")),

    Q(148,"distributed-consumer-dedup","distributed-systems","message-processing","design","expert",
      "A message broker can redeliver events after consumer failure. Prevent the consumer from applying the same logical event twice.",
      [
        "Give each event a stable unique identity and record processed identities in durable state.",
        "Make the deduplication decision atomic with the local state transition where possible.",
        "If an external side effect is involved, use downstream idempotency or a durable outbox/reconciliation strategy.",
        "Retention of deduplication state must cover the broker's possible redelivery horizon."
      ], tags=("distributed-systems","deduplication","events","idempotency")),

    Q(149,"networking-mss-tunnel","networking","tcp-mss","troubleshooting","advanced",
      "TCP connections establish through a tunnel but large transfers stall while small requests succeed. Analyze MTU and MSS as a hypothesis.",
      [
        "Encapsulation reduces effective path MTU, so large packets may require PMTU discovery or segmentation compatible with the tunnel.",
        "Blocked ICMP or incorrect MSS handling can create black-hole behavior where small traffic succeeds but larger packets disappear.",
        "Inspect packet sizes, retransmissions, ICMP feedback, tunnel MTU, and TCP MSS before applying clamps."
      ], verification="reference-answer",
      source_type="documentation",
      reference="TCP MSS and Path MTU Discovery semantics",
      tags=("tcp","mss","mtu","tunnel")),

    Q(150,"embedded-i2c-pullup","embedded-systems","i2c","troubleshooting","intermediate",
      "An I2C bus works at low speed but develops rounded edges and communication errors when clock rate increases. Explain the role of pull-up resistance and bus capacitance.",
      [
        "I2C lines are open-drain and rise through pull-up resistors rather than active high drivers.",
        "Pull-up resistance and total bus capacitance determine rise time, which can become too slow at higher clock rates.",
        "Measure electrical rise time and compare it with the bus-mode timing requirements before changing firmware retries."
      ], verification="reference-answer",
      source_type="documentation",
      reference="I2C open-drain and rise-time behavior",
      tags=("embedded","i2c","pullup","capacitance")),
]


VERIFIERS = {
"000122_test.py": r'''
import unittest

def decode_i16_be(data):
    if len(data) != 2:
        raise ValueError("length")
    u = (data[0] << 8) | data[1]
    return u - 0x10000 if u & 0x8000 else u

class Tests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(decode_i16_be(b"\x00\x00"), 0)
        self.assertEqual(decode_i16_be(b"\x7f\xff"), 32767)
        self.assertEqual(decode_i16_be(b"\xff\xff"), -1)
        self.assertEqual(decode_i16_be(b"\x80\x00"), -32768)

    def test_length(self):
        with self.assertRaises(ValueError):
            decode_i16_be(b"\x00")

if __name__ == "__main__":
    unittest.main()
''',

"000126_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

truncate -s 1G "$tmp"

logical="$(stat -c '%s' "$tmp")"
blocks="$(stat -c '%b' "$tmp")"
allocated=$((blocks * 512))

test "$logical" -eq 1073741824
test "$allocated" -lt "$logical"

echo "logical bytes:   $logical"
echo "allocated bytes: $allocated"
echo "sparse file verified"
''',

"000128_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *p = malloc(4);
    if (!p) return 1;
    memcpy(p, "abc", 4);

    char *tmp = realloc(p, 8);
    if (!tmp) {
        free(p);
        return 2;
    }

    p = tmp;

    if (strcmp(p, "abc") != 0) {
        free(p);
        return 3;
    }

    free(p);
    puts("safe realloc pattern verified");
    return 0;
}
C

gcc -std=c11 -Wall -Wextra -Werror "$tmp/t.c" -o "$tmp/t"
"$tmp/t"
''',

"000132_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <stdint.h>
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <stdint.h>

int safe_bytes(size_t count, size_t size, size_t *out) {
    if (size != 0 && count > SIZE_MAX / size)
        return 0;

    *out = count * size;
    return 1;
}

int main(void) {
    size_t out;

    if (!safe_bytes(10, 8, &out) || out != 80)
        return 1;

    if (safe_bytes(SIZE_MAX, 2, &out))
        return 2;

    puts("checked allocation multiplication verified");
    return 0;
}
C

gcc -std=c11 -Wall -Wextra -Werror "$tmp/t.c" -o "$tmp/t"
"$tmp/t"
''',

"000142_test.py": r'''
import unittest

UINT32_MAX = 0xFFFFFFFF

def narrow_u32(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("type")
    if value < 0 or value > UINT32_MAX:
        raise ValueError("range")
    return value

class Tests(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(narrow_u32(0), 0)
        self.assertEqual(narrow_u32(UINT32_MAX), UINT32_MAX)

    def test_invalid(self):
        for value in (-1, UINT32_MAX + 1, True):
            with self.assertRaises(ValueError):
                narrow_u32(value)

if __name__ == "__main__":
    unittest.main()
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
