from generators.common import R, P


RECORDS = [
    R(
        71,
        "software-feature-rollout",
        "software-engineering",
        "feature-rollouts",
        "design",
        "advanced",
        "A rewritten production request path is ready. The old implementation can remain available. Design a rollout that detects failures early and can be reversed without an emergency deployment.",
        P(
            "Separate deployment from exposure. Ship both implementations while the new path remains disabled by default, then control exposure through a server-side feature flag or equivalent mechanism.",
            "Start with internal traffic or a small representative cohort. Define measurable gates such as error rate, latency, resource use, and correctness signals, and expand only while those remain healthy.",
            "Keep the old path immediately selectable so rollback is a configuration action rather than another build. The rollout should also record which implementation handled each request.",
            "Preserve state and schema compatibility during the rollback window. A safe rollout is progressive, measurable, reversible, and independent from code deployment.",
        ),
        "rubric",
        "Requires deployment/exposure separation, progressive cohorts, measurable gates, rapid rollback, and state compatibility.",
        ["feature-flags","rollout","canary","rollback"],
    ),

    R(
        72,
        "systems-varint-decode",
        "systems-programming",
        "binary-parsing",
        "implementation",
        "advanced",
        "Implement an unsigned 32-bit base-128 varint decoder. Return the decoded value and consumed byte count, reject truncation, and reject overlong encodings.",
        P(
            "Consume seven payload bits from each byte and stop when the continuation bit is clear. Reject an encoding that still continues beyond five bytes or produces a value larger than 0xFFFFFFFF.",
            """A checked implementation is:

```python
def decode_varint(data):
    value = 0
    shift = 0

    for i, byte in enumerate(data):
        if i >= 5:
            raise ValueError("varint too long")

        value |= (byte & 0x7F) << shift

        if byte < 0x80:
            if value > 0xFFFFFFFF:
                raise ValueError("varint exceeds uint32")
            return value, i + 1

        shift += 7

    raise ValueError("truncated varint")
```""",
            "The explicit byte and numeric bounds prevent malformed data from extending the shift indefinitely or escaping the protocol's intended integer width.",
        ),
        "unit-test",
        "Verified by verification/000072_test.py for zero, one- and two-byte values, truncation, and overlong input.",
        ["varint","binary-parsing","uint32","bounds"],
    ),

    R(
        73,
        "os-fsync-durability",
        "operating-systems",
        "filesystem-durability",
        "technical-decision",
        "advanced",
        "An application receives success from write() and immediately reports that an important record is durable. Explain why that conclusion may be wrong.",
        P(
            "Successful write completion commonly means the kernel accepted the bytes, not that every required data and metadata block has reached persistent storage. Buffered writes may remain in memory.",
            "When a real durability boundary is required, use the filesystem's documented durability mechanism such as fsync() and check its result.",
            "Operations involving file creation or rename can also require syncing the containing directory when the crash-consistency protocol depends on the namespace update being durable.",
            "The exact guarantee depends on the filesystem and storage stack, so application protocols must use documented durability semantics rather than treating buffered write success as stable-storage commit.",
        ),
        "reference-answer",
        "Reviewed against Linux write(2), fsync(2), buffered-I/O, and filesystem durability semantics.",
        ["fsync","durability","filesystem","write"],
        "documentation",
        "Linux write(2) and fsync(2)",
    ),

    R(
        74,
        "architecture-simd-tail",
        "computer-architecture",
        "simd",
        "code-repair",
        "intermediate",
        "A vector loop processes four elements per iteration but assumes the input length is divisible by four. Repair handling of a one-to-three element tail.",
        P(
            "Run the vector path only while a complete vector remains, then process the remaining elements with a scalar cleanup loop.",
            "Native SIMD code may alternatively use masked operations where the ISA supports them efficiently. In either case, the final partial vector must not be treated as though every lane references valid input.",
        ),
        "unit-test",
        "Verified by verification/000074_test.py for exact-width, tail, shorter-than-vector, and empty inputs.",
        ["simd","vectorization","tail","bounds"],
    ),

    R(
        75,
        "embedded-moving-average",
        "embedded-systems",
        "signal-filtering",
        "implementation",
        "basic",
        "Implement a simple arithmetic moving average for supplied sensor samples and reject empty input. Explain the responsiveness tradeoff.",
        P(
            "The arithmetic mean is the sum divided by the number of samples; empty input must be rejected because the divisor would be zero.",
            "A larger averaging window normally smooths short-term variation more strongly but reacts more slowly to real signal changes because older samples influence the result longer.",
            "Continuous firmware can maintain a rolling sum instead of recomputing the complete window, while integer implementations must choose an accumulator wide enough to avoid overflow.",
        ),
        "unit-test",
        "Verified by verification/000075_test.py for single, multiple, negative-valued, and empty inputs.",
        ["embedded","moving-average","sensor","filter"],
    ),

    R(
        76,
        "networking-dns-negative-cache",
        "networking",
        "dns-caching",
        "troubleshooting",
        "intermediate",
        "A DNS name was initially nonexistent. The record is added, but some clients still receive not-found while others resolve it. Explain the likely caching behavior.",
        P(
            "Resolvers can cache negative answers such as NXDOMAIN. A resolver that cached the original negative response may continue serving it after the authoritative zone changes.",
            "Compare the authoritative answer with the recursive path and determine which resolver, local stub, or application cache the failing client actually uses. Inspect the negative caching lifetime as well.",
            "If authoritative data is correct, waiting for the negative entry to expire or flushing an appropriate administrative cache can resolve the discrepancy. Editing the new record repeatedly does not invalidate an older cached negative answer.",
        ),
        "reference-answer",
        "Reviewed against standard DNS negative-caching and NXDOMAIN semantics.",
        ["dns","negative-cache","nxdomain","resolver"],
        "documentation",
        "DNS negative-caching semantics",
    ),

    R(
        77,
        "distributed-saga-compensation",
        "distributed-systems",
        "sagas",
        "design",
        "expert",
        "An order workflow reserves inventory, charges payment, and schedules shipment across independent services. Design failure handling without pretending all steps can be rolled back atomically.",
        P(
            "Treat each remote step as an independently committed operation and maintain durable orchestration state describing which steps completed.",
            "Define compensating business actions where possible, such as refunding payment or releasing inventory. Compensation must itself tolerate retries and failure.",
            "Track states such as pending, completed, compensating, compensated, and manual-intervention-required. Ambiguous timeouts must be reconciled before blindly repeating an external action.",
            "Compensation is not database rollback: observers may already have seen the original action and some effects may be irreversible. Durable state, idempotency or deduplication, and explicit recovery semantics are therefore required.",
        ),
        "rubric",
        "Requires durable workflow state, retry-safe compensation, ambiguous-outcome handling, failed-compensation handling, and recognition that compensation is not atomic rollback.",
        ["saga","compensation","distributed-systems","recovery"],
    ),

    R(
        78,
        "linux-unlinked-open-file",
        "linux-infrastructure",
        "filesystem-space",
        "failure-analysis",
        "advanced",
        "A Linux log file was deleted, but filesystem free space did not increase and the writer process is still running. Explain the cause and diagnosis.",
        P(
            "Unlinking removes the pathname, but the underlying file remains alive while an open file descriptor still references it. Its blocks are reclaimed only after the final reference closes.",
            "Inspect `/proc/<pid>/fd` or tools such as `lsof +L1`; a descriptor can point to a pathname marked `(deleted)` while the process continues using the file.",
            "Prefer the application's supported log reopen mechanism or a controlled restart. Creating another file at the same pathname does not change the old descriptor, which still references the unlinked inode.",
        ),
        "execute",
        "Verified by verification/000078_test.sh by opening, unlinking, and retaining a descriptor to a temporary file.",
        ["linux","filesystem","deleted-file","file-descriptor"],
    ),

    R(
        79,
        "compute-kv-fragmentation",
        "compute-model-infrastructure",
        "kv-memory-management",
        "performance-analysis",
        "advanced",
        "An LLM server reports substantial aggregate free GPU memory but sometimes cannot allocate KV cache for a long request after many differently sized requests. Analyze fragmentation as one hypothesis.",
        P(
            "Aggregate free bytes do not guarantee that memory exists in the layout required by the allocator. Variable-size lifetimes can leave holes that are individually unsuitable for a large allocation.",
            "Measure active versus reserved allocator memory, KV page or block utilization, request-size distribution, allocation failures, and any exposed largest-block or fragmentation metrics.",
            "Paged or fixed-block KV managers can reduce external fragmentation, while admission control and block reuse can avoid pathological layouts.",
            "Do not assume fragmentation automatically: weights, workspaces, concurrent batches, or ordinary KV growth can produce genuine capacity exhaustion. Compare clean-start behavior with long-running mixed workloads.",
        ),
        "rubric",
        "Requires distinction between aggregate free memory and allocatable layout, allocator/KV evidence, paged allocation discussion, and ruling out genuine exhaustion.",
        ["llm","kv-cache","fragmentation","gpu-memory"],
    ),

    R(
        80,
        "security-webhook-replay",
        "secure-engineering",
        "webhook-authentication",
        "code-repair",
        "expert",
        "A webhook receiver authenticates only an HMAC of the body, so a captured valid request can be replayed. Repair the protocol.",
        P(
            "Authenticate freshness and uniqueness together with the body. A sender can include a timestamp and nonce and compute the HMAC over a canonical representation containing timestamp, nonce, and body.",
            "The receiver verifies the MAC with constant-time comparison, rejects timestamps outside the allowed window, and atomically rejects nonce or event identifiers already accepted during that window.",
            "The MAC protects integrity, the timestamp bounds age, and the nonce provides duplicate detection. TLS is still required for transport confidentiality, and canonicalization must be precisely defined.",
        ),
        "unit-test",
        "Verified by verification/000080_test.py for valid input, modified body, stale timestamp, and replay.",
        ["security","webhook","hmac","replay","nonce"],
    ),
]


VERIFIERS = {
    "000072_test.py": r'''
import unittest

def decode_varint(data):
    value = 0
    shift = 0
    for i, byte in enumerate(data):
        if i >= 5:
            raise ValueError("varint too long")
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            if value > 0xFFFFFFFF:
                raise ValueError("varint exceeds uint32")
            return value, i + 1
        shift += 7
    raise ValueError("truncated varint")

class Tests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(decode_varint(b"\x00"), (0, 1))
    def test_300(self):
        self.assertEqual(decode_varint(b"\xac\x02"), (300, 2))
    def test_truncated(self):
        with self.assertRaises(ValueError):
            decode_varint(b"\x80")
    def test_overlong(self):
        with self.assertRaises(ValueError):
            decode_varint(b"\x81\x81\x81\x81\x81\x00")

if __name__ == "__main__":
    unittest.main()
''',

    "000074_test.py": r'''
import unittest

def f(v, width=4):
    total = 0
    i = 0
    while i + width <= len(v):
        total += sum(v[i:i+width])
        i += width
    while i < len(v):
        total += v[i]
        i += 1
    return total

class Tests(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(f([1,2,3,4]), 10)
    def test_tail(self):
        self.assertEqual(f([1,2,3,4,5,6]), 21)
    def test_short(self):
        self.assertEqual(f([7,8]), 15)
    def test_empty(self):
        self.assertEqual(f([]), 0)

if __name__ == "__main__":
    unittest.main()
''',

    "000075_test.py": r'''
import unittest

def avg(v):
    if not v:
        raise ValueError("empty")
    return sum(v) / len(v)

class Tests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(avg([10,20,30,40]), 25)
        self.assertEqual(avg([-10,10]), 0)
    def test_empty(self):
        with self.assertRaises(ValueError):
            avg([])

if __name__ == "__main__":
    unittest.main()
''',

    "000078_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'exec 3>&- 2>/dev/null || true; rm -rf "$tmp"' EXIT
file="$tmp/app.log"
exec 3>"$file"
printf 'data\n' >&3
rm "$file"
test ! -e "$file"
target="$(readlink "/proc/$$/fd/3")"
[[ "$target" == *"(deleted)"* ]]
echo "unlinked-but-open file verified"
''',

    "000080_test.py": r'''
import hashlib
import hmac
import unittest

SECRET = b"secret"

def sign(ts, nonce, body):
    m = str(ts).encode() + b"." + nonce.encode() + b"." + body
    return hmac.new(SECRET, m, hashlib.sha256).hexdigest()

def verify(ts, nonce, body, sig, now, seen):
    if abs(now - ts) > 300:
        raise ValueError("stale")
    if not hmac.compare_digest(sign(ts, nonce, body), sig):
        raise ValueError("signature")
    key = (ts, nonce)
    if key in seen:
        raise ValueError("replay")
    seen.add(key)

class Tests(unittest.TestCase):
    def test_valid_and_replay(self):
        seen=set()
        sig=sign(1000,"n",b"x")
        verify(1000,"n",b"x",sig,1000,seen)
        with self.assertRaises(ValueError):
            verify(1000,"n",b"x",sig,1000,seen)

    def test_modified(self):
        with self.assertRaises(ValueError):
            verify(1000,"n",b"y",sign(1000,"n",b"x"),1000,set())

    def test_stale(self):
        with self.assertRaises(ValueError):
            verify(1000,"n",b"x",sign(1000,"n",b"x"),2000,set())

if __name__ == "__main__":
    unittest.main()
''',
}
