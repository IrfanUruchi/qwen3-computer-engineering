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
# BATCH 016 — 151..160
# =====================================================================

Q(
151, "software-config-validation",
"software-engineering", "configuration", "design", "advanced",
"A service receives a new runtime configuration containing timeouts, queue limits, and feature switches. Design configuration loading so invalid values cannot partially reach production state.",
[
"Parse and validate the complete candidate configuration before replacing the active configuration.",
"Check ranges, cross-field invariants, required values, and unknown or deprecated fields explicitly.",
"Apply the validated configuration atomically so readers never observe a partially updated mixture of old and new values.",
"Keep the previous known-good configuration available when reload validation fails."
],
tags=("configuration","validation","reload","atomic-update")
),

Q(
152, "systems-buffer-offset",
"systems-programming", "binary-parsing", "code-repair", "advanced",
"A parser reads a 32-bit little-endian field at a caller-supplied byte offset. Repair it so negative or out-of-range offsets cannot read beyond the buffer.",
[
"Validate the offset before slicing or pointer arithmetic.",
"Require offset >= 0 and at least four bytes remaining.",
"Decode explicitly as little endian rather than relying on host representation."
],
verification="unit-test",
details="Verified by verification/000152_test.py for valid decoding, negative offsets, truncated buffers, and boolean offsets.",
tags=("binary-parsing","offset","bounds","little-endian")
),

Q(
153, "reasoning-noisy-benchmark",
"engineering-reasoning", "benchmark-methodology",
"performance-analysis", "intermediate",
"Repeated benchmark runs vary by 8%, while a proposed optimization appears 3% faster in one run. Decide whether the improvement is established.",
[
"A change smaller than uncontrolled run-to-run variation is not established by one comparison.",
"Collect repeated measurements under controlled conditions and report the distribution rather than only the fastest result.",
"Investigate noise sources such as background work, clocks, thermal state, cache state, and scheduling.",
"Compare effect size with measurement uncertainty before claiming improvement."
],
tags=("benchmark","variance","measurement","performance")
),

Q(
154, "os-pipe-backpressure",
"operating-systems", "pipes", "failure-analysis", "advanced",
"A producer writes continuously to a pipe while the consumer becomes slow. Explain why the producer eventually blocks despite having plenty of RAM.",
[
"A pipe has finite kernel buffering; it is not an unbounded in-memory queue.",
"When the buffer fills, a blocking writer waits until the reader frees capacity.",
"This naturally propagates backpressure from the slow consumer to the producer.",
"Measure producer rate, consumer rate, blocked-write time, and queueing before attempting to enlarge buffers."
],
verification="reference-answer",
source_type="documentation",
reference="POSIX/Linux pipe buffering and blocking semantics",
tags=("pipe","backpressure","blocking","ipc")
),

Q(
155, "architecture-store-forwarding",
"computer-architecture", "memory-dependencies",
"performance-analysis", "advanced",
"A tight loop stores a value and immediately performs a partially overlapping load. Throughput is worse than expected. Analyze store-to-load forwarding as a hypothesis.",
[
"Processors may forward data from an earlier store to a dependent load without waiting for cache visibility when alignment and overlap permit it.",
"Partial overlap, size mismatch, or awkward alignment can prevent efficient forwarding and introduce stalls.",
"Measure cycles, load latency, relevant dependency or forwarding-stall counters, and performance after controlled layout changes.",
"Do not infer the mechanism solely from source order because microarchitectural behavior is implementation-specific."
],
tags=("store-forwarding","load","memory","performance")
),

Q(
156, "linux-tmpfs-capacity",
"linux-infrastructure", "tmpfs", "troubleshooting", "intermediate",
"A service writes temporary data to tmpfs and receives ENOSPC even though the disk containing `/` has substantial free capacity. Explain why.",
[
"tmpfs has its own capacity and memory-backed accounting independent of free blocks on the root disk.",
"Inspect the actual mount, its size limit, current usage, available memory, and any container or cgroup constraints.",
"Deleting unrelated files from the root filesystem does not increase capacity of a separately limited tmpfs."
],
verification="reference-answer",
source_type="documentation",
reference="Linux tmpfs and mount capacity semantics",
tags=("linux","tmpfs","enospc","memory")
),

Q(
157, "software-webhook-idempotency",
"software-engineering", "webhook-processing", "design", "advanced",
"A webhook provider retries delivery until it receives success. Design the receiver so repeated delivery does not duplicate the business action.",
[
"Use the provider event ID or another stable logical identifier as the idempotency key.",
"Persist the deduplication decision durably and coordinate it with the local state transition.",
"Return the previously established result for a repeated event rather than performing the side effect again.",
"Retention of deduplication state must cover the provider's documented retry horizon."
],
tags=("webhook","idempotency","retry","deduplication")
),

Q(
158, "networking-syn-retransmission",
"networking", "tcp-handshake", "troubleshooting", "intermediate",
"A client sends SYN packets repeatedly and never receives SYN-ACK or RST. Explain what this evidence means and what to inspect.",
[
"Repeated SYN retransmission indicates connection establishment is receiving no usable response.",
"Possible causes include packet loss, filtering, routing failure, an unreachable host, or return-path failure.",
"Capture on both client and server sides where possible and inspect routes, firewall policy, listening state, and reverse traffic.",
"A timeout differs diagnostically from an immediate explicit RST."
],
verification="reference-answer",
source_type="documentation",
reference="TCP connection establishment and retransmission semantics",
tags=("tcp","syn","retransmission","timeout")
),

Q(
159, "distributed-fencing-token",
"distributed-systems", "leader-fencing", "design", "expert",
"A lease-based leader temporarily loses connectivity, a replacement leader is elected, and the old process later resumes. Prevent the stale leader from modifying shared storage.",
[
"Leadership must carry a monotonically increasing epoch or fencing token.",
"Downstream resources accept an operation only when its token is at least as new as the latest accepted authority.",
"A stale process can therefore continue running but cannot successfully mutate protected state.",
"Lease expiration alone is insufficient when an old process can resume after losing authority."
],
tags=("distributed-systems","fencing","lease","leadership")
),

Q(
160, "compute-load-deserialization",
"compute-model-infrastructure", "model-loading",
"performance-analysis", "advanced",
"Model startup remains slow after moving the checkpoint to faster storage. CPU utilization spikes during loading. Analyze the next likely stages.",
[
"Checkpoint startup can include parsing, deserialization, decompression, dequantization, tensor allocation, copies, and device initialization after storage reads finish.",
"Profile startup as separate stages rather than treating model loading as one timer.",
"Measure storage throughput, CPU time, allocation time, host-to-device transfer, and synchronization.",
"Optimize whichever stage dominates after the storage improvement."
],
tags=("model-loading","deserialization","startup","performance")
),

# =====================================================================
# BATCH 017 — 161..170
# =====================================================================

Q(
161, "software-async-cancellation",
"software-engineering", "async-lifecycle", "design", "advanced",
"An asynchronous request is cancelled while child tasks and external operations are still active. Design cancellation semantics that avoid leaked work.",
[
"Propagate cancellation through owned child tasks instead of abandoning them silently.",
"Define cleanup with bounded deadlines and ensure resources are released even when cancellation interrupts normal control flow.",
"External operations need explicit semantics because cancelling the local waiter does not necessarily cancel remote work.",
"Record ambiguous remote outcomes for later reconciliation."
],
tags=("async","cancellation","cleanup","lifecycle")
),

Q(
162, "systems-fd-ownership",
"systems-programming", "file-descriptors", "code-repair", "advanced",
"A component stores a caller-owned file descriptor for later use, but the caller closes it after the call. Repair the ownership contract.",
[
"If the component needs an independent lifetime, duplicate the descriptor and own the duplicate.",
"Closing the caller's original descriptor must not invalidate the retained duplicate.",
"Document which side closes each descriptor and handle duplication failure explicitly."
],
verification="execute",
details="Verified by verification/000162_test.sh: dup creates an independent descriptor that remains valid after the original descriptor is closed.",
tags=("c","file-descriptor","dup","ownership")
),

Q(
163, "embedded-saturating-counter",
"embedded-systems", "counters", "implementation", "basic",
"An 8-bit fault counter should stop at 255 instead of wrapping back to zero. Implement saturating increment.",
[
"Increment only when the current value is below 255.",
"At 255, retain 255 rather than allowing unsigned wraparound.",
"Use saturation when wraparound would falsely make a severe accumulated condition appear small."
],
verification="unit-test",
details="Verified by verification/000163_test.py for normal increment, boundary transition, and repeated increments at saturation.",
tags=("embedded","counter","saturation","uint8")
),

Q(
164, "os-epoll-edge-triggered",
"operating-systems", "event-notification", "debugging", "advanced",
"An edge-triggered epoll server reads only one message per readiness event and occasionally leaves unread data stuck indefinitely. Explain the repair.",
[
"Edge-triggered notification reports state transitions rather than repeatedly reminding the application while unread data remains.",
"After an event, drain the nonblocking descriptor until the operation reports that no more data is currently available.",
"Stopping after one logical message can leave bytes buffered without another edge to wake the process."
],
verification="reference-answer",
source_type="documentation",
reference="Linux epoll(7) edge-triggered semantics",
tags=("linux","epoll","edge-triggered","nonblocking")
),

Q(
165, "architecture-numa-first-touch",
"computer-architecture", "numa",
"performance-analysis", "advanced",
"A multithreaded application allocates a large array on one thread before remote workers process it. Explain how first-touch placement can affect performance.",
[
"Many NUMA systems place physical pages according to where they are first faulted or initialized.",
"Initializing the entire array on one NUMA node can leave remote worker threads repeatedly accessing nonlocal memory.",
"Measure NUMA placement, remote versus local accesses, memory bandwidth, latency, and thread affinity.",
"Parallel first-touch or explicit NUMA policy can improve locality when it matches the later access pattern."
],
tags=("numa","first-touch","memory-locality","performance")
),

Q(
166, "linux-hard-link-inode",
"linux-infrastructure", "filesystem-links",
"architecture-analysis", "intermediate",
"Two different pathnames are hard links to the same regular file. Explain what is shared and what happens when one name is deleted.",
[
"Hard links are directory entries referencing the same underlying inode.",
"The file contents, ownership, permissions, and inode identity are shared rather than copied.",
"Removing one pathname decreases the link count but does not remove the file data while another hard link or open reference remains."
],
verification="execute",
details="Verified by verification/000166_test.sh using two hard links with the same inode and observing link-count reduction after unlink.",
tags=("linux","hard-link","inode","filesystem")
),

Q(
167, "reasoning-saturation-test",
"engineering-reasoning", "capacity-testing", "testing", "advanced",
"A service degrades sharply above a particular request rate. Design an experiment to identify the first saturated resource.",
[
"Increase offered load in controlled steps while recording throughput, queueing, latency, errors, and resource-specific utilization.",
"Look for the point where throughput stops scaling while queueing or one resource metric rises sharply.",
"Repeat near the transition and alter one suspected capacity constraint to test causality.",
"Do not infer the bottleneck solely from the resource with the highest average percentage."
],
tags=("capacity","saturation","load-test","measurement")
),

Q(
168, "software-retry-partial-success",
"software-engineering", "distributed-api", "failure-analysis", "expert",
"A request times out after the remote service may already have committed the operation. The caller cannot tell whether retrying will duplicate the action. Design recovery.",
[
"Treat timeout as an ambiguous outcome rather than proof of failure.",
"Use a stable idempotency key or operation identifier that the remote service can query or deduplicate.",
"Reconcile the existing operation state before repeating a non-idempotent side effect.",
"Separate transport failure from business-operation state."
],
tags=("timeout","idempotency","ambiguity","recovery")
),

Q(
169, "distributed-snapshot-install",
"distributed-systems", "replicated-log",
"architecture-analysis", "expert",
"A follower is so far behind that replaying the entire retained log is impractical. Explain safe snapshot installation in a replicated state machine.",
[
"A snapshot must represent state at a specific committed log position together with metadata needed to continue replication.",
"Install it atomically enough that the follower never combines incompatible snapshot and log state.",
"After installation, resume from entries following the included position and discard obsolete earlier log segments according to the protocol.",
"Verify integrity and leadership or term rules during transfer rather than treating snapshots as arbitrary file copies."
],
tags=("distributed-systems","snapshot","replication","log")
),

Q(
170, "compute-padding-waste",
"compute-model-infrastructure", "batching",
"performance-analysis", "advanced",
"A transformer batch contains sequences of very different lengths and substantial compute is spent on padding. Explain the performance issue and alternatives.",
[
"Padding a batch to the longest sequence can execute work for token positions containing no useful input.",
"Measure real tokens versus padded tokens, batch composition, throughput, latency, and accelerator utilization.",
"Length bucketing, dynamic batching, packing, or kernels that handle variable lengths can reduce wasted work.",
"Any batching change must still respect latency and scheduling objectives."
],
tags=("transformer","padding","batching","performance")
),

# =====================================================================
# BATCH 018 — 171..180
# =====================================================================

Q(
171, "software-pagination-snapshot",
"software-engineering", "pagination-consistency", "design", "advanced",
"A client needs to paginate through a changing dataset while seeing one logically stable export rather than live inserts appearing between pages. Design the semantics.",
[
"Cursor ordering alone prevents offset shifting but does not automatically create a frozen snapshot.",
"Associate the export with a snapshot version, transaction snapshot, or immutable high-water mark.",
"Every page must read under compatible snapshot semantics until the export completes.",
"Define retention and expiration so snapshot state is not held indefinitely."
],
tags=("pagination","snapshot","consistency","api")
),

Q(
172, "systems-unaligned-u32",
"systems-programming", "binary-decoding", "implementation", "advanced",
"Decode a 32-bit little-endian integer from four bytes at an arbitrary byte position without performing an unaligned pointer cast.",
[
"Validate that four bytes are available before decoding.",
"Combine bytes explicitly or use a safe copy into a properly aligned integer followed by endian conversion.",
"Avoid casting arbitrary byte pointers to integer pointers because alignment and aliasing requirements may be violated."
],
verification="unit-test",
details="Verified by verification/000172_test.py for valid little-endian decoding and malformed lengths.",
tags=("binary","alignment","little-endian","uint32")
),

Q(
173, "embedded-hysteresis-switch",
"embedded-systems", "hysteresis", "implementation", "intermediate",
"A noisy sensor controls an on/off output around a threshold and chatters rapidly. Implement two-threshold hysteresis.",
[
"Use a higher threshold to transition from off to on and a lower threshold to transition from on to off.",
"Between the two thresholds, preserve the previous state.",
"The separation prevents small noise around one threshold from repeatedly toggling the actuator."
],
verification="unit-test",
details="Verified by verification/000173_test.py for on transition, hold region, off transition, and noise inside the hysteresis band.",
tags=("embedded","hysteresis","sensor","control")
),

Q(
174, "networking-nat-idle-timeout",
"networking", "nat-state", "troubleshooting", "advanced",
"A long-lived TCP connection becomes unusable after sitting idle behind a NAT, although both endpoints still believe the connection exists. Explain the likely state loss.",
[
"NAT or stateful firewall mappings can expire after an idle timeout even while endpoint TCP state remains established.",
"Later packets may no longer match the old translation and can be dropped or mapped incorrectly.",
"Inspect middlebox timeout policy, packet captures, keepalive behavior, and reconnect handling.",
"Application keepalives should be chosen with awareness of infrastructure policy rather than at arbitrary high frequency."
],
verification="reference-answer",
source_type="documentation",
reference="Stateful NAT mapping and TCP idle-timeout behavior",
tags=("nat","tcp","idle-timeout","keepalive")
),

Q(
175, "os-cloexec-inheritance",
"operating-systems", "process-exec", "troubleshooting", "intermediate",
"A child process unexpectedly inherits a sensitive file descriptor across exec. Explain how close-on-exec prevents the leak.",
[
"Descriptors normally remain across exec unless their close-on-exec flag is set.",
"Create descriptors with an atomic CLOEXEC-capable interface where available or set FD_CLOEXEC before another thread can fork and exec.",
"Audit inherited descriptors rather than assuming process replacement closes every open descriptor."
],
verification="execute",
details="Verified by verification/000175_test.sh using O_CLOEXEC and checking FD_CLOEXEC with fcntl.",
tags=("exec","cloexec","file-descriptor","process")
),

Q(
176, "architecture-write-combining",
"computer-architecture", "memory-stores",
"performance-analysis", "advanced",
"A workload streams stores to a large output buffer but performs poorly when stores are scattered and repeatedly revisit partial cache lines. Analyze write behavior.",
[
"Streaming contiguous stores can use cache-line locality and hardware write-combining mechanisms more effectively than scattered partial writes.",
"Poor locality can increase read-for-ownership traffic, cache pollution, and memory transactions.",
"Measure bandwidth, cache-line traffic, store stalls, write allocation behavior, and performance after controlled layout changes."
],
tags=("stores","write-combining","cache-line","bandwidth")
),

Q(
177, "linux-umask-mode",
"linux-infrastructure", "permissions", "configuration", "basic",
"A service creates files expecting mode 0666 but they appear as 0640 when its umask is 0027. Explain the calculation.",
[
"Creation mode is filtered by the process umask rather than applied verbatim.",
"For ordinary files, 0666 with umask 0027 yields 0640.",
"Changing chmod later is different from selecting a creation mask, and service managers can set a process-specific umask."
],
verification="execute",
details="Verified by verification/000177_test.sh: umask 0027 applied to a newly created file produces mode 0640.",
tags=("linux","umask","permissions","mode")
),

Q(
178, "reasoning-bottleneck-shift",
"engineering-reasoning", "optimization-methodology",
"technical-decision", "advanced",
"After a successful CPU optimization, overall speed improves only slightly and GPU utilization rises substantially. Explain the next engineering step.",
[
"Removing one bottleneck can expose another, so the original profile is no longer sufficient.",
"Re-profile the optimized system and recompute where end-to-end time is now spent.",
"Use the new critical path to choose the next optimization rather than continuing to optimize the component that was previously dominant."
],
tags=("bottleneck","profiling","optimization","critical-path")
),

Q(
179, "reasoning-measurement-resolution",
"engineering-reasoning", "measurement",
"testing", "advanced",
"A benchmark tries to distinguish 20-microsecond operations using a timer and harness whose own variability is tens of microseconds. Design a better measurement.",
[
"Measurement resolution and harness noise must be substantially smaller than the effect being estimated.",
"Batch many operations per timed interval, subtract or characterize harness overhead, and use a suitable monotonic high-resolution clock.",
"Repeat measurements and report distributions rather than interpreting quantization noise as workload variance."
],
tags=("measurement","timer","benchmark","resolution")
),

Q(
180, "systems-frame-length",
"systems-programming", "protocol-framing",
"implementation", "advanced",
"A byte-stream protocol prefixes each frame with a 16-bit big-endian payload length. Implement a parser that rejects incomplete headers and truncated payloads.",
[
"Require two bytes before decoding the length.",
"Decode the length explicitly as big endian.",
"Require the complete declared payload before returning a frame.",
"Return the number of consumed bytes so additional stream data can remain buffered for the next frame."
],
verification="unit-test",
details="Verified by verification/000180_test.py for complete frames, zero-length payload, incomplete header, and truncated payload.",
tags=("protocol","framing","length-prefix","parser")
),
]


VERIFIERS = {

"000152_test.py": r'''
import unittest

def read_u32_le(data, offset):
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ValueError("offset")
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("bounds")
    b = data[offset:offset+4]
    return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24

class Tests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(
            read_u32_le(b"\xff\x78\x56\x34\x12", 1),
            0x12345678
        )

    def test_invalid(self):
        for offset in (-1, 2, True):
            with self.assertRaises(ValueError):
                read_u32_le(b"\x00\x01\x02\x03\x04", offset)

if __name__ == "__main__":
    unittest.main()
''',

"000162_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    int fd = open("/dev/null", O_RDONLY);
    if (fd < 0) return 1;

    int owned = dup(fd);
    if (owned < 0) {
        close(fd);
        return 2;
    }

    close(fd);

    if (fcntl(owned, F_GETFD) < 0) {
        close(owned);
        return 3;
    }

    close(owned);
    puts("independent duplicated descriptor verified");
    return 0;
}
C

gcc -std=c11 -Wall -Wextra -Werror \
    "$tmp/t.c" -o "$tmp/t"

"$tmp/t"
''',

"000163_test.py": r'''
import unittest

def sat_inc_u8(value):
    if value < 0 or value > 255:
        raise ValueError("range")
    return value if value == 255 else value + 1

class Tests(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(sat_inc_u8(10), 11)

    def test_boundary(self):
        self.assertEqual(sat_inc_u8(254), 255)

    def test_saturated(self):
        self.assertEqual(sat_inc_u8(255), 255)
        self.assertEqual(sat_inc_u8(sat_inc_u8(255)), 255)

if __name__ == "__main__":
    unittest.main()
''',

"000166_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

printf 'hello\n' > "$tmp/a"
ln "$tmp/a" "$tmp/b"

inode_a="$(stat -c '%i' "$tmp/a")"
inode_b="$(stat -c '%i' "$tmp/b")"
links="$(stat -c '%h' "$tmp/a")"

test "$inode_a" = "$inode_b"
test "$links" -eq 2

rm "$tmp/a"

test -f "$tmp/b"
test "$(stat -c '%h' "$tmp/b")" -eq 1

echo "hard-link inode semantics verified"
''',

"000172_test.py": r'''
import unittest

def decode_u32_le(data):
    if len(data) != 4:
        raise ValueError("length")
    return (
        data[0]
        | data[1] << 8
        | data[2] << 16
        | data[3] << 24
    )

class Tests(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(
            decode_u32_le(b"\x78\x56\x34\x12"),
            0x12345678
        )

    def test_length(self):
        for data in (b"", b"\x00", b"\x00\x01\x02"):
            with self.assertRaises(ValueError):
                decode_u32_le(data)

if __name__ == "__main__":
    unittest.main()
''',

"000173_test.py": r'''
import unittest

def hysteresis(state, value, low=40, high=60):
    if not state and value >= high:
        return True
    if state and value <= low:
        return False
    return state

class Tests(unittest.TestCase):
    def test_on(self):
        self.assertTrue(hysteresis(False, 60))

    def test_hold(self):
        self.assertFalse(hysteresis(False, 50))
        self.assertTrue(hysteresis(True, 50))

    def test_off(self):
        self.assertFalse(hysteresis(True, 40))

    def test_noise_inside_band(self):
        state = True
        for value in (49, 51, 48, 52):
            state = hysteresis(state, value)
        self.assertTrue(state)

if __name__ == "__main__":
    unittest.main()
''',

"000175_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/t.c" <<'C'
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    int fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
    if (fd < 0) return 1;

    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) {
        close(fd);
        return 2;
    }

    if (!(flags & FD_CLOEXEC)) {
        close(fd);
        return 3;
    }

    close(fd);
    puts("close-on-exec verified");
    return 0;
}
C

gcc -D_GNU_SOURCE -std=c11 -Wall -Wextra -Werror \
    "$tmp/t.c" -o "$tmp/t"

"$tmp/t"
''',

"000177_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

(
    umask 0027
    touch "$tmp/file"
)

mode="$(stat -c '%a' "$tmp/file")"
test "$mode" = "640"

echo "umask mode verified: $mode"
''',

"000180_test.py": r'''
import unittest

def parse_frame(data):
    if len(data) < 2:
        raise ValueError("incomplete header")

    length = (data[0] << 8) | data[1]
    end = 2 + length

    if len(data) < end:
        raise ValueError("truncated payload")

    return data[2:end], end

class Tests(unittest.TestCase):
    def test_frame(self):
        payload, used = parse_frame(b"\x00\x03abcZZ")
        self.assertEqual(payload, b"abc")
        self.assertEqual(used, 5)

    def test_zero(self):
        self.assertEqual(parse_frame(b"\x00\x00"), (b"", 2))

    def test_header(self):
        with self.assertRaises(ValueError):
            parse_frame(b"\x00")

    def test_payload(self):
        with self.assertRaises(ValueError):
            parse_frame(b"\x00\x04abc")

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
