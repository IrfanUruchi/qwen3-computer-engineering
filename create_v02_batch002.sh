#!/usr/bin/env bash
set -euo pipefail

cd ~/qwen3-computer-engineering

mkdir -p data/staging/v0.2 configs

python3 - <<'PY'
import json
from pathlib import Path
from textwrap import dedent

OUT = Path("data/staging/v0.2/batch-002.jsonl")
PLAN = Path("configs/dataset-v0.2-batch-002.json")

def s(x):
    return dedent(x).strip()

records = [
{
"id":"ce-software-aba-lockfree-stack-000311",
"version":1,
"split":"train",
"domain":"software-engineering",
"subdomain":"lock-free-concurrency",
"task_type":"failure-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A lock-free stack uses an atomic pointer `head`. Thread A reads `head == X` and is
descheduled. Thread B pops X, pops another node, then later pushes X back so the pointer
value is again X. Thread A resumes and its compare-and-swap succeeds.

Explain the bug and give two standard ways to prevent it.
""")},
{"role":"assistant","content":s("""
This is the ABA problem. Thread A checks only that the pointer value is still X, but the
stack changed from A to B and back to A while it was paused. The compare-and-swap cannot
detect that intervening history, so A may act on assumptions that are no longer valid,
for example linking through a node whose successor changed or whose lifetime ended.

Two standard defenses are:

1. attach a version/tag counter to the pointer and compare both pointer and tag, so
   X@version1 differs from X@version3 even when the address is the same;
2. use a safe memory-reclamation scheme such as hazard pointers or epoch-based
   reclamation so a removed node cannot be recycled while another thread may still
   hold a reference to it.

The exact fix depends on the data structure. A tagged pointer detects ABA transitions;
reclamation prevents dangerous address reuse. In some algorithms both concerns must be
handled.

Simply making `head` atomic is insufficient because atomicity of the pointer does not
encode the intermediate modifications.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify ABA as an undetected A→B→A transition, explain why pointer equality alone is insufficient, and give valid mitigations such as tagged/versioned pointers and safe memory reclamation."
},
"source":{"type":"original"},
"tags":["aba-problem","lock-free","cas","hazard-pointers","concurrency"]
},

{
"id":"ce-systems-scm-rights-leak-000312",
"version":1,
"split":"train",
"domain":"systems-programming",
"subdomain":"unix-domain-sockets",
"task_type":"code-repair",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A privileged daemon receives file descriptors over a Unix-domain socket using
`SCM_RIGHTS`. It accepts every descriptor and stores it without checking what object it
refers to. It also forgets to close descriptors when later validation fails.

Identify the resource and security problems and describe a safer receive path.
""")},
{"role":"assistant","content":s("""
Receiving a descriptor transfers a live reference to a kernel object into the daemon.
If the daemon never closes rejected or unused descriptors, an attacker can exhaust its
descriptor table and keep underlying objects alive. Blindly trusting the received
descriptor can also violate the daemon's policy because the sender may pass a file,
socket, device, directory, or other object the daemon did not intend to operate on.

A safer path should:

- receive ancillary data with enough control-buffer space and reject malformed or
  truncated control messages;
- extract only the expected `SCM_RIGHTS` entries;
- immediately place every received descriptor under clear ownership so all failure
  paths close it;
- set close-on-exec, preferably atomically with `MSG_CMSG_CLOEXEC` where supported;
- validate the opened object itself using descriptor-based inspection such as
  `fstat()`, `getsockopt()`, or other type-specific checks;
- enforce the daemon's policy before storing or using the descriptor;
- bound how many descriptors a client can submit.

The important rule is that a received file descriptor is an authority-bearing kernel
reference. It must be validated and either deliberately adopted or promptly closed.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must cover descriptor leaks/resource exhaustion, policy risk from accepting arbitrary kernel objects, cleanup on all failure paths, close-on-exec, and descriptor-based validation."
},
"source":{"type":"original"},
"tags":["SCM_RIGHTS","unix-sockets","file-descriptors","resource-leak","capability-security"]
},

{
"id":"ce-os-tlb-shootdown-000313",
"version":1,
"split":"train",
"domain":"operating-systems",
"subdomain":"virtual-memory",
"task_type":"performance-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A multithreaded service repeatedly changes page protections in a large shared mapping.
As thread count rises, CPU time in kernel code grows and throughput collapses even
though the application performs little I/O.

Explain how TLB shootdowns can cause this scaling failure and state what evidence would
support the diagnosis.
""")},
{"role":"assistant","content":s("""
Changing a mapping or its permissions can invalidate translations that other CPUs may
still hold in their TLBs. The kernel therefore has to coordinate invalidation across
the CPUs that could have cached those translations. That operation is commonly called
a TLB shootdown.

With many threads running the same address space on many cores, frequent mapping
changes can cause repeated cross-CPU interrupts or equivalent synchronization. The
cost grows beyond the local page-table update because remote CPUs must participate
before stale translations are considered unusable.

Useful evidence includes:

- profiling that attributes time to page-table/TLB invalidation paths;
- elevated inter-processor interrupt or TLB-shootdown counters where the platform
  exposes them;
- a strong relationship between mapping/protection-change frequency, CPU count, and
  the throughput collapse;
- improvement when the application batches or avoids repeated mapping changes.

The mitigation is workload-specific: reduce unnecessary `mprotect()`/unmap/remap
operations, batch changes, reuse mappings, or redesign allocation so hot paths do not
continually invalidate translations shared across many cores.

A TLB miss by itself is not a shootdown; the defining issue is coordinated invalidation
of potentially stale translations after page-table state changes.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must connect page-table/protection changes to cross-CPU TLB invalidation, explain why cost grows with active CPUs, distinguish ordinary TLB misses from shootdowns, and cite profiling/counter evidence."
},
"source":{"type":"original"},
"tags":["tlb","shootdown","virtual-memory","mprotect","scalability"]
},

{
"id":"ce-architecture-numa-first-touch-000314",
"version":1,
"split":"train",
"domain":"computer-architecture",
"subdomain":"numa",
"task_type":"performance-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A dual-socket NUMA server allocates a 200 GB array in one initialization thread pinned
to socket 0. Later, worker threads on both sockets process disjoint halves of the
array. Workers on socket 1 show much lower memory bandwidth.

Explain the likely placement problem and propose a better initialization strategy.
""")},
{"role":"assistant","content":s("""
On a typical first-touch NUMA policy, physical pages are allocated on the NUMA node of
the CPU that first faults/writes them. If one initialization thread on socket 0 touches
the entire array, most pages can end up backed by memory attached to socket 0.

Workers on socket 1 then access their half remotely across the inter-socket fabric,
which increases latency and consumes interconnect bandwidth.

A better strategy is parallel first-touch initialization: pin workers according to the
intended processing placement and have each worker initialize the pages it will later
use. That causes the two halves to be allocated near their owning sockets under
first-touch policy.

Other valid strategies include an explicit NUMA allocation policy or interleaving when
the workload benefits from it.

Verification should use NUMA-placement tools/counters together with local-versus-remote
memory traffic and bandwidth measurements. CPU affinity alone does not migrate already
placed pages.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain first-touch page placement, remote memory access from socket 1, parallel first-touch or explicit NUMA placement as a fix, and note that CPU affinity alone does not relocate existing pages."
},
"source":{"type":"original"},
"tags":["numa","first-touch","memory-bandwidth","affinity","multisocket"]
},

{
"id":"ce-linux-io-uring-buffer-lifetime-000315",
"version":1,
"split":"train",
"domain":"linux-infrastructure",
"subdomain":"io-uring",
"task_type":"failure-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A program submits an asynchronous `io_uring` write using a buffer allocated on a
function's stack. The function returns immediately after submission. Under light load
the write often looks correct, but under load the file occasionally contains corrupted
bytes.

Explain the lifetime bug and give a safe ownership rule for asynchronous buffers.
""")},
{"role":"assistant","content":s("""
Submission does not imply that the kernel has completed using the user buffer. If the
function returns while the write is still outstanding, the stack storage can be reused
for unrelated data. The asynchronous operation can then read bytes from memory whose
lifetime, contents, or ownership has changed.

The buffer must remain valid and unmodified for as long as the specific operation/API
requires it. A safe design gives each in-flight request ownership of storage with a
lifetime extending through completion, for example a heap allocation, pooled request
buffer, or registered-buffer slot that is not recycled until the matching completion
queue entry is processed.

The application should associate completion metadata with the request so it knows
exactly which buffer can be released or returned to the pool.

The same principle applies broadly to asynchronous I/O: do not infer buffer lifetime
from submission. Release/reuse is governed by completion semantics of the operation.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify use-after-lifetime/reuse of an asynchronous user buffer, require buffer validity through the operation's completion semantics, and describe request ownership or pooling tied to CQE completion."
},
"source":{"type":"original"},
"tags":["io_uring","async-io","buffer-lifetime","linux","completion"]
},

{
"id":"ce-embedded-volatile-isr-shared-state-000316",
"version":1,
"split":"train",
"domain":"embedded-systems",
"subdomain":"interrupt-concurrency",
"task_type":"code-repair",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
Firmware has a 32-bit counter updated in an interrupt handler and read/reset by the main
loop. A developer marks it `volatile` and claims that this makes the access atomic and
thread-safe on every MCU.

Explain why that claim is wrong and describe a portable synchronization approach.
""")},
{"role":"assistant","content":s("""
`volatile` mainly constrains compiler treatment of accesses; it does not generally make
a read-modify-write operation atomic, create mutual exclusion, or establish the
language-level synchronization guarantees needed for concurrent access.

On some MCUs a naturally aligned 32-bit load/store may happen to be indivisible, while
on narrower machines it may require multiple instructions and can tear. Even if each
individual load/store is atomic, a sequence such as read-then-reset can still race with
an interrupt increment.

A portable design should use synchronization appropriate to the platform and language.
For example:

- use an atomic integer type if the implementation provides suitable lock-free or
  otherwise ISR-safe atomics; or
- briefly mask/disable the relevant interrupt around the main-loop critical section,
  copy/reset the counter, then restore the previous interrupt state.

Keep the critical section short.

`volatile` may still be required for certain memory-mapped I/O semantics on embedded
targets, but that is a different concern from inter-context synchronization.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must state that volatile does not guarantee atomicity or mutual exclusion, mention tearing/read-modify-write races, and give an appropriate atomic or short interrupt-masking solution."
},
"source":{"type":"original"},
"tags":["volatile","interrupts","atomics","embedded","race-condition"]
},

{
"id":"ce-networking-pmtud-blackhole-000317",
"version":1,
"split":"train",
"domain":"networking",
"subdomain":"path-mtu-discovery",
"task_type":"troubleshooting",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A TCP connection completes the handshake and small requests work, but large transfers
stall after the first few packets. One path segment has a smaller MTU, and ICMP
messages are being filtered.

Explain the likely failure mode and how to diagnose and mitigate it without simply
disabling MTU discovery everywhere.
""")},
{"role":"assistant","content":s("""
This is consistent with a path-MTU-discovery black hole.

A sender may transmit packets too large for a downstream link. When fragmentation is
not permitted, the router should signal that the packet is too large so the sender can
reduce its packet size. If the required ICMP feedback is filtered, the sender may keep
retransmitting packets that cannot traverse the path. Small packets still succeed,
which makes the connection look partially healthy.

Diagnosis can include:

- packet captures showing successful handshakes/small packets followed by repeated
  retransmissions of larger packets;
- controlled probes with different packet sizes and DF behavior where appropriate;
- checking interface/tunnel MTUs and encapsulation overhead;
- verifying whether the relevant ICMP packet-too-big/fragmentation-needed messages
  arrive.

Preferred fixes are to permit the required control messages, correct inconsistent MTUs,
or configure an appropriate MTU on the tunnel/link. TCP MSS clamping can be a pragmatic
edge mitigation for known paths, especially around tunnels, but it should reflect the
real path constraints rather than hide arbitrary network breakage.

The failure is not caused by TCP's handshake itself; it appears when packet size reaches
the unusable portion of the path.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify a PMTUD black hole caused by missing ICMP feedback, explain why small packets can work while large packets stall, and propose evidence-based fixes such as restoring ICMP, correcting MTUs, or deliberate MSS clamping."
},
"source":{"type":"original"},
"tags":["pmtud","mtu","icmp","tcp","mss"]
},

{
"id":"ce-distributed-fencing-token-000318",
"version":1,
"split":"train",
"domain":"distributed-systems",
"subdomain":"leases-and-locks",
"task_type":"architecture-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A worker acquires a distributed lease and begins writing to shared storage. It pauses
for long enough that the lease expires. Another worker acquires the lease, but the old
worker later resumes and continues writing.

Why is lease ownership alone insufficient, and how can fencing tokens protect the
storage system?
""")},
{"role":"assistant","content":s("""
Lease expiry changes who is allowed to act, but it cannot physically stop a paused or
partitioned old holder from resuming. If the storage system accepts writes solely
because the client once held a lease, stale work can overwrite newer work.

A fencing design assigns a monotonically increasing token each time ownership is
granted. For example, worker A receives token 41 and the later worker B receives token
42. Every write carries its token to the protected resource.

The storage side remembers the highest token it has accepted and rejects operations
with an older token. Once a write with token 42 is accepted, resumed writes carrying 41
are fenced out even if worker A incorrectly believes it may continue.

The crucial property is enforcement at the resource being protected. Generating a
token only in the lock service is insufficient if the storage layer ignores it.

Fencing complements leases; it handles stale actors that survive beyond their lease
validity.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain that an expired lease cannot stop an old process from acting, require monotonically increasing fencing tokens, and require the protected resource to reject stale tokens."
},
"source":{"type":"original"},
"tags":["fencing-token","lease","distributed-lock","stale-writer","consistency"]
},

{
"id":"ce-compute-nccl-topology-000319",
"version":1,
"split":"train",
"domain":"compute-model-infrastructure",
"subdomain":"multi-gpu-communication",
"task_type":"performance-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A two-GPU training job shows low compute utilization during gradient synchronization.
One GPU is attached to the CPU root complex with a wide PCIe link while the other uses
a narrower link through an additional bridge. There is no NVLink.

Give a measurement plan for deciding whether topology and link bandwidth are the
collective bottleneck.
""")},
{"role":"assistant","content":s("""
Treat topology as a hypothesis and measure communication separately from model compute.

First record the physical topology and negotiated link state: PCIe generation, width,
root-complex/bridge relationship, and whether GPU peer-to-peer access is actually
available on the platform.

Then measure:

- point-to-point GPU transfer bandwidth and latency in each direction;
- host-staged transfer performance if direct peer access is unavailable;
- collective performance, for example all-reduce bandwidth across relevant message
  sizes;
- a profiler timeline showing compute kernels, collective calls, and synchronization;
- per-GPU utilization together with link traffic/counters where available.

Compare collective time against the amount of gradient data that must move and against
the achievable bandwidth measured by the microbenchmarks. If large-message collective
throughput tracks the slower path and compute repeatedly waits at collective
boundaries, topology is strong evidence for the bottleneck.

Also test sensitivity to gradient bucket size, overlap between backpropagation and
communication, and a single-GPU baseline.

Do not infer effective bandwidth only from the slot's advertised capability. Negotiated
link width, routing, peer-access support, protocol overhead, and software scheduling
all matter.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must require actual topology/link-state inspection, transfer and collective microbenchmarks, timeline profiling, comparison with communication volume, and avoidance of assuming advertised PCIe bandwidth equals achieved peer bandwidth."
},
"source":{"type":"original"},
"tags":["nccl","pcie","multi-gpu","all-reduce","profiling"]
},

{
"id":"ce-reasoning-bottleneck-throughput-000320",
"version":1,
"split":"train",
"domain":"engineering-reasoning",
"subdomain":"pipeline-throughput",
"task_type":"quantitative-reasoning",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A three-stage streaming pipeline has steady-state service times of 4 ms, 7 ms, and
5 ms per item. Assume each stage has one worker, stages can operate concurrently on
different items, buffers are large enough, and there is no other overhead.

What is the maximum steady-state throughput? If the 7 ms stage is optimized to 3 ms,
what becomes the new throughput limit? Explain why adding the stage times is not the
steady-state calculation.
""")},
{"role":"assistant","content":s("""
For a concurrent pipeline, steady-state throughput is limited by the slowest stage.

Initially the bottleneck is the 7 ms stage:

\[
T = \frac{1}{0.007\ \text{s}} \approx 142.9\ \text{items/s}.
\]

After that stage is reduced to 3 ms, the stage times are 4 ms, 3 ms, and 5 ms, so the
5 ms stage becomes the bottleneck:

\[
T = \frac{1}{0.005\ \text{s}} = 200\ \text{items/s}.
\]

The sum 4 + 7 + 5 = 16 ms describes the approximate processing latency of one item
through the three stages when queueing is ignored. It does not determine steady-state
throughput because, after the pipeline fills, different stages work on different items
at the same time.

Therefore:

- original maximum steady-state throughput: about 142.9 items/s;
- optimized maximum steady-state throughput: 200 items/s.
""")}
],
"verification":{
"method":"calculation",
"status":"verified",
"details":"Steady-state throughput is the reciprocal of the maximum stage service time: 1/0.007 ≈ 142.9 items/s initially and 1/0.005 = 200 items/s after optimization. Sum of stage times relates to per-item latency, not pipeline throughput."
},
"source":{"type":"original"},
"tags":["pipeline","throughput","bottleneck","latency","quantitative"]
}
]

assert len(records) == 10
assert len({r["id"] for r in records}) == 10

existing_ids = set()

for root in [Path("data/raw/v0.1"), Path("data/staging/v0.2")]:
    if not root.exists():
        continue
    for p in root.glob("*.jsonl"):
        if p == OUT:
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_ids.add(json.loads(line)["id"])

collisions = sorted({r["id"] for r in records} & existing_ids)
if collisions:
    raise SystemExit(f"ID collisions: {collisions}")

with OUT.open("w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

plan = {
    "batch": "002",
    "dataset_version": "0.2",
    "stage": "v0.2-A",
    "split": "train",
    "records": [
        {
            "id": r["id"],
            "domain": r["domain"],
            "subdomain": r["subdomain"],
            "task_type": r["task_type"],
            "difficulty": r["difficulty"],
            "verification": r["verification"]["method"],
        }
        for r in records
    ],
}

PLAN.write_text(
    json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print(f"Wrote: {OUT}")
print(f"Wrote: {PLAN}")
print("Records:", len(records))

for r in records:
    print(
        r["id"],
        "|", r["domain"],
        "|", r["difficulty"],
        "|", r["verification"]["method"]
    )
PY

python3 -m json.tool configs/dataset-v0.2-batch-002.json >/dev/null \
  && echo "Batch plan: VALID JSON"

python3 scripts/validate_dataset.py \
  data/staging/v0.2/batch-002.jsonl
