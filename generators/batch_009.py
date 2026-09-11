from generators.common import R, P


RECORDS = [
    R(
        81,
        "software-cursor-pagination",
        "software-engineering",
        "pagination",
        "design",
        "advanced",
        "A changing API uses LIMIT/OFFSET pagination and clients sometimes see duplicate or missing rows when inserts occur between requests. Design a cursor-based alternative.",
        P(
            "Use a deterministic ordering and encode the last returned ordering key in an opaque cursor rather than storing an absolute row offset.",
            "For example, order by `(created_at, id)` and request the next page strictly after that tuple. The unique `id` breaks ties between equal timestamps.",
            "Inserts before the cursor no longer shift every later position. If ordering fields can mutate, use an immutable sequence key or define snapshot semantics instead.",
            "Keep cursors opaque so their encoding can evolve without exposing database implementation details.",
        ),
        "rubric",
        "Requires deterministic ordering, a unique tie-breaker, strict continuation semantics, opaque cursors, and consideration of mutable ordering fields.",
        ["pagination","cursor","api","database","consistency"],
    ),

    R(
        82,
        "systems-shift-width",
        "systems-programming",
        "bit-operations",
        "code-repair",
        "advanced",
        "C code computes a 32-bit mask with `1u << index`, where index comes from external input. Repair the interface so invalid shift counts are rejected before evaluation.",
        P(
            "Validate the index before shifting. If the external value is signed, reject negative input first, then require the value to be less than 32.",
            """For example:

```c
uint32_t bit32(unsigned index, int *ok)
{
    if (index >= 32) {
        *ok = 0;
        return 0;
    }

    *ok = 1;
    return UINT32_C(1) << index;
}
```""",
            "In C, a negative shift count or a count greater than or equal to the width of the promoted left operand is undefined behavior. The validation therefore must happen before the shift expression.",
        ),
        "unit-test",
        "Verified by verification/000082_test.py for bit positions 0 and 31 and rejection of negative, 32, and invalid inputs.",
        ["c","bit-shift","uint32","undefined-behavior","bounds"],
    ),

    R(
        83,
        "os-signal-interruption",
        "operating-systems",
        "signals",
        "troubleshooting",
        "intermediate",
        "A blocking Unix system call occasionally returns early when a signal is delivered. An engineer treats every such return as a permanent I/O failure. Explain the correct handling.",
        P(
            "Some blocking interfaces can report interruption through EINTR when a signal is delivered before the operation completes.",
            "Whether a call is automatically restarted depends on the interface and signal configuration, so callers should follow the documented semantics rather than assuming one universal behavior.",
            "Retry only when doing so is safe, and preserve partial progress. If bytes were already transferred, blindly restarting from the beginning can duplicate work.",
            "The caller must distinguish interruption from genuine failure and account for any completed portion of the operation.",
        ),
        "reference-answer",
        "Reviewed against POSIX/Linux EINTR, signal interruption, partial-I/O, and restart semantics.",
        ["signals","eintr","posix","system-call"],
        "documentation",
        "POSIX/Linux signal and EINTR semantics",
    ),

    R(
        84,
        "architecture-cache-associativity",
        "computer-architecture",
        "cache-associativity",
        "performance-analysis",
        "advanced",
        "A benchmark repeatedly accesses several addresses mapping to the same small set of cache sets. Its total working set is modest, yet misses remain high. Explain the likely mechanism.",
        P(
            "A set-associative cache can hold only a fixed number of lines per set. If more simultaneously useful lines map to one set than there are available ways, they repeatedly evict one another.",
            "These conflict misses can occur even when unused capacity exists elsewhere in the cache, so total working-set size alone does not explain residency.",
            "Measure cache miss counters, address or stride patterns, cache geometry where available, and the effect of changing alignment, padding, stride, or allocation placement.",
            "Because exact indexing is architecture-specific, demonstrate the conflict experimentally rather than assuming it from source code alone.",
        ),
        "rubric",
        "Requires explanation of associativity and conflict eviction, distinction from capacity misses, and cache-counter or layout evidence.",
        ["cache","associativity","conflict-miss","performance"],
    ),

    R(
        85,
        "embedded-crc-frame",
        "embedded-systems",
        "crc",
        "implementation",
        "intermediate",
        "Implement CRC-8 using polynomial 0x07, initial value zero, no reflection, and no final XOR. State the expected check value for ASCII `123456789`.",
        P(
            """A direct bitwise implementation is:

```python
def crc8(data, polynomial=0x07):
    crc = 0

    for byte in data:
        crc ^= byte

        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ polynomial) & 0xFF
            else:
                crc = (crc << 1) & 0xFF

    return crc
```""",
            "With these exact parameters, `crc8(b'123456789')` is `0xF4`.",
            "CRC names alone are insufficient protocol specifications: polynomial, initial value, reflection, final XOR, and byte ordering must all agree between implementations.",
        ),
        "unit-test",
        "Verified by verification/000085_test.py using the 123456789 check vector, empty input, and changed payload.",
        ["embedded","crc8","protocol","error-detection"],
    ),

    R(
        86,
        "networking-asymmetric-routing",
        "networking",
        "routing",
        "troubleshooting",
        "advanced",
        "A multihomed Linux server receives traffic on one interface but policy routing selects another interface for replies. Connectivity fails only for some sources and stateful firewalls are present. Diagnose the situation.",
        P(
            "Asymmetric paths are legal at the IP layer, but stateful devices or host policies can require both directions to follow compatible paths.",
            "A firewall may observe only one direction and reject the return traffic. Reverse-path filtering can also reject received packets when the route back to the source does not satisfy its configured policy.",
            "Inspect `ip route`, `ip rule`, source address selection, interface-specific tables, reverse-path-filter settings, firewall state, and packet captures on all relevant interfaces.",
            "Establish the actual path in both directions before changing security controls. Globally disabling filtering is not the first diagnostic or design fix.",
        ),
        "reference-answer",
        "Reviewed against Linux policy routing, reverse-path filtering, and stateful firewall behavior.",
        ["routing","asymmetric-routing","rp-filter","firewall"],
        "documentation",
        "Linux policy routing and reverse-path filtering semantics",
    ),

    R(
        87,
        "distributed-commit-index",
        "distributed-systems",
        "consensus",
        "architecture-analysis",
        "expert",
        "A leader in a five-node replicated consensus system has an entry on itself and one follower. Explain why this is not enough to report the entry committed.",
        P(
            "Leader-local persistence or replication to an arbitrary minority does not ensure that the entry survives a future leadership change. Another majority could elect a leader whose log lacks it.",
            "Commitment must follow the consensus protocol's quorum and log-ordering rules. In a five-node majority system, a quorum normally involves three nodes, but merely counting copies is still insufficient if protocol term rules are ignored.",
            "Consensus algorithms constrain leader election and the treatment of entries from different terms so committed history intersects future valid leadership.",
            "The client should receive success at the service's documented commit point, not simply when the current leader has locally appended the entry.",
        ),
        "rubric",
        "Requires distinction between minority replication and commitment, quorum intersection, term/log-ordering rules, and survival across leadership changes.",
        ["consensus","commit-index","quorum","replication"],
    ),

    R(
        88,
        "linux-file-retention",
        "linux-infrastructure",
        "filesystem-cleanup",
        "configuration",
        "basic",
        "A dedicated Linux directory contains disposable `.log` files. Delete matching regular files older than seven days while preserving newer files.",
        P(
            """A basic rule is:

```bash
find /var/lib/myapp/logs \
  -type f \
  -name '*.log' \
  -mtime +7 \
  -delete
```""",
            "`-type f` limits deletion to regular files and the name predicate restricts the target set. The starting directory is critical because `-delete` is destructive.",
            "Test the same expression without `-delete` first. Production systems may prefer logrotate, systemd-tmpfiles, or an application-owned lifecycle mechanism when those better describe retention.",
        ),
        "execute",
        "Verified by verification/000088_test.sh: an old temporary log is deleted while a recent log remains.",
        ["linux","find","retention","cleanup"],
    ),

    R(
        89,
        "compute-pcie-transfer",
        "compute-model-infrastructure",
        "host-device-transfer",
        "performance-analysis",
        "advanced",
        "A GPU kernel takes 2 ms but total request latency is 14 ms because every request transfers large inputs to the GPU and results back. Explain where optimization effort should go.",
        P(
            "End-to-end time includes host-to-device transfer, device execution, device-to-host transfer, synchronization, and queueing. Optimizing a 2 ms kernel can remove only a small fraction of a 14 ms request.",
            "Measure transfer durations and sizes, achieved interconnect bandwidth, kernel time, synchronization, PCIe topology, NUMA placement, and whether communication overlaps computation.",
            "Potential improvements include retaining reusable data on the device, batching operations, reducing transferred representation size, using appropriate pinned memory, and overlapping asynchronous transfers with computation when dependencies permit.",
            "Optimize the measured dominant component rather than assuming arithmetic kernels dominate because they perform the principal computation.",
        ),
        "rubric",
        "Requires decomposition of kernel and transfer time, interconnect measurements, and discussion of residency, batching, representation size, or overlap.",
        ["gpu","pcie","transfer","latency","performance"],
    ),

    R(
        90,
        "security-csrf-defense",
        "secure-engineering",
        "csrf",
        "code-repair",
        "expert",
        "A cookie-authenticated web application accepts state-changing POST requests without CSRF protection. Repair the design and explain how tokens, SameSite, and Origin validation fit together.",
        P(
            "Require a cryptographically random session-bound CSRF token for unsafe browser requests and reject missing or mismatched values.",
            "SameSite cookies provide useful browser-level protection but should be treated as defense in depth because legitimate cross-site flows and compatibility requirements can affect the chosen policy.",
            "For appropriate HTTPS endpoints, validate the Origin header against an explicit allowlist as another signal. Proxy configuration must preserve the origin semantics the application expects.",
            "CSRF defenses address credentials automatically attached by the browser. They do not replace XSS defenses, because same-origin injected script may be able to obtain a valid token.",
        ),
        "unit-test",
        "Verified by verification/000090_test.py for correct, missing, incorrect, and invalid token values.",
        ["security","csrf","cookies","samesite","origin"],
    ),
]


VERIFIERS = {
    "000082_test.py": r'''
import unittest

def bit32(index):
    if not isinstance(index, int) or isinstance(index, bool):
        raise ValueError("index")
    if index < 0 or index >= 32:
        raise ValueError("range")
    return (1 << index) & 0xFFFFFFFF

class Tests(unittest.TestCase):
    def test_edges(self):
        self.assertEqual(bit32(0), 1)
        self.assertEqual(bit32(31), 0x80000000)

    def test_invalid(self):
        for x in (-1, 32, True):
            with self.assertRaises(ValueError):
                bit32(x)

if __name__ == "__main__":
    unittest.main()
''',

    "000085_test.py": r'''
import unittest

def crc8(data, polynomial=0x07):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ polynomial) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

class Tests(unittest.TestCase):
    def test_vector(self):
        self.assertEqual(crc8(b"123456789"), 0xF4)

    def test_empty(self):
        self.assertEqual(crc8(b""), 0)

    def test_change(self):
        self.assertNotEqual(crc8(b"ABC"), crc8(b"ABD"))

if __name__ == "__main__":
    unittest.main()
''',

    "000088_test.sh": r'''
#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

old="$tmp/old.log"
new="$tmp/new.log"

touch "$old" "$new"
touch -d '15 days ago' "$old"
touch -d '1 day ago' "$new"

find "$tmp" \
  -type f \
  -name '*.log' \
  -mtime +7 \
  -delete

test ! -e "$old"
test -e "$new"

echo "old log removed"
echo "recent log preserved"
''',

    "000090_test.py": r'''
import hmac
import secrets
import unittest

def token():
    return secrets.token_urlsafe(32)

def verify(expected, submitted):
    if not isinstance(expected, str):
        return False
    if not isinstance(submitted, str):
        return False
    return hmac.compare_digest(
        expected.encode(),
        submitted.encode(),
    )

class Tests(unittest.TestCase):
    def test_valid(self):
        x = token()
        self.assertTrue(verify(x, x))

    def test_missing(self):
        self.assertFalse(verify(token(), ""))

    def test_wrong(self):
        self.assertFalse(verify(token(), token()))

    def test_invalid_type(self):
        self.assertFalse(verify("abc", None))

if __name__ == "__main__":
    unittest.main()
''',
}
