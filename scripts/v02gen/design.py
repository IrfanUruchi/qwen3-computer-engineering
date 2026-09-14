from __future__ import annotations
import argparse
from .common import record, run_purpose

FAMILIES=[
 {"id":"design-transactional-outbox","domain":"distributed-systems"},
 {"id":"design-bulkhead","domain":"software-engineering"},
 {"id":"design-safe-firmware-ab","domain":"embedded-systems"},
 {"id":"design-systemd-socket-activation","domain":"linux-infrastructure"},
 {"id":"design-quic-migration","domain":"networking"},
 {"id":"design-gpu-double-buffer","domain":"compute-model-infrastructure"},
 {"id":"design-sandbox-broker","domain":"secure-engineering"},
 {"id":"design-numa-first-touch","domain":"computer-architecture"},
 {"id":"design-async-buffer-ownership","domain":"systems-programming"},
 {"id":"design-priority-ceiling","domain":"operating-systems"},
]

def build(f,rng,rid,difficulty):
    fid=f["id"]
    cases={
"design-transactional-outbox":(
"distributed-systems","transactional-messaging","architecture-analysis",
"""An order service must update a relational database and emit an event to a broker.
There is no distributed transaction between the database and broker. Design a protocol
that avoids losing the event when the process crashes after the database commit.""",
"""Write the domain update and an outbox row describing the event in the same local
database transaction. A separate relay reads committed outbox rows and publishes them.

If the relay crashes, the durable outbox row remains and can be retried. Because a crash
can occur after the broker accepts the event but before the relay records completion,
publication is normally at-least-once. Give each event a stable identifier and make
consumers idempotent or deduplicate processed IDs.

Retire outbox rows only according to a defined delivery/retention policy. The design
removes the database-commit/publish gap without pretending the broker boundary became
exactly-once.""",
"Must atomically store domain state and outbox intent, use a retrying relay, acknowledge duplicate publication, and require idempotent/deduplicating consumers.",
["transactional-outbox","messaging","idempotency","retries"]),
"design-bulkhead":(
"software-engineering","resilience","design",
"""A service calls three downstream systems. One dependency can become slow and consume
all request workers, causing unrelated endpoints to fail too. Design a bulkhead strategy
that limits the blast radius.""",
"""Give the slow dependency its own bounded concurrency budget and queue rather than
letting it consume the entire service worker/connection pool. Requests beyond that
budget should fail fast, shed load, or wait only within a defined deadline.

Use separate connection pools/semaphores/worker queues where isolation is required and
preserve capacity for unrelated dependencies. Combine the bulkhead with timeouts and
cancellation so abandoned calls do not continue occupying resources.

Size limits from measured downstream capacity and acceptable queueing latency. A
bulkhead is not merely a larger global pool; its purpose is isolation so one dependency
cannot monopolize all shared resources.""",
"Must isolate dependency concurrency/resources, bound queueing, combine with deadlines/cancellation, and explain blast-radius reduction rather than simply increasing global capacity.",
["bulkhead","resilience","backpressure","dependency"]),
"design-safe-firmware-ab":(
"embedded-systems","firmware-update","architecture-analysis",
"""Design an A/B firmware update process for a device that can lose power at any point
during download or first boot. The device must retain a bootable image.""",
"""Keep the currently known-good slot untouched while writing and validating the inactive
slot. Verify image integrity/authenticity before marking it bootable.

Update boot metadata with a power-loss-safe protocol such as redundant/versioned records
or a mechanism provided by the platform. Boot the candidate with a limited trial count.
Only after the new image reaches a known-good health milestone should it be promoted as
the durable default.

If trial boots fail or reset repeatedly, the bootloader falls back to the prior known-good
slot. Do not erase the old image before the replacement is fully written, verified, and
successfully proven in operation.""",
"Must keep a known-good slot, verify inactive image, update boot metadata power-loss-safely, use trial boot/health milestone, and roll back after failed trials.",
["firmware","a-b-update","rollback","bootloader"]),
"design-systemd-socket-activation":(
"linux-infrastructure","service-supervision","architecture-analysis",
"""A daemon takes several seconds to initialize. Clients should be able to connect during
boot, and the listening endpoint should remain available while the daemon process is
restarted. Design this using systemd.""",
"""Use a systemd socket unit to create and own the listening socket independently of the
service process. Incoming connections can queue in the kernel while systemd starts or
restarts the daemon.

The daemon must detect and adopt the inherited listening descriptor instead of binding a
second socket to the same address. Listener lifetime then belongs to the socket unit,
while process lifetime belongs to the service unit.

This preserves the listening endpoint, not arbitrary in-flight application state.
Accepted connections or process memory may still be lost when the daemon crashes, so the
application protocol needs its own retry/recovery semantics.""",
"Must separate listener lifetime from process lifetime, use systemd-created descriptor inheritance, explain queueing before readiness, and not claim accepted application state survives a crash.",
["systemd","socket-activation","restart","listener"]),
"design-quic-migration":(
"networking","quic","architecture-analysis",
"""A mobile transport must survive a client's switch from Wi-Fi to cellular without
recreating the application session solely because the source IP/UDP port changed.
Explain the QUIC mechanisms the design should rely on.""",
"""QUIC identifies connections using connection IDs rather than binding identity solely to
the network 4-tuple. Packets arriving from a new address can therefore still map to the
existing connection state.

The endpoint validates the new path before fully trusting it and applies the protocol's
anti-amplification, congestion-control, and migration rules. Connection IDs can also be
rotated according to privacy/operational policy.

The design should not assume every address change is automatically accepted; migration
preserves logical connection identity while path validation establishes that the new
network path is usable and belongs to the peer.""",
"Must identify QUIC connection IDs and path validation, explain independence from the 4-tuple, and retain migration/anti-amplification/congestion constraints.",
["quic","migration","connection-id","path-validation"]),
"design-gpu-double-buffer":(
"compute-model-infrastructure","gpu-data-transfer","design",
"""A GPU pipeline alternates host-to-device input copies and kernels, but copies and
compute serialize. Design a double-buffered schedule that can overlap them when hardware
supports concurrent copy/execute.""",
"""Allocate at least two input buffers and use pinned host memory where required for truly
asynchronous host-to-device transfer. Place copy work and compute in streams that can
execute independently.

While the GPU computes buffer A, asynchronously fill/copy buffer B. Use events only for
the dependency that compute B must wait until copy B completes, and similarly before
reusing a buffer whose prior work is still in flight.

Confirm hardware copy-engine/concurrent-execution capability and verify overlap on a
profiler timeline. Multiple streams and `cudaMemcpyAsync()` are enabling conditions, not
proof that overlap actually occurs.""",
"Must describe alternating buffers, pinned host memory where needed, independent streams, event-based buffer dependencies, safe reuse, and profiler verification.",
["gpu","double-buffer","async-copy","streams"]),
"design-sandbox-broker":(
"secure-engineering","sandboxing","architecture-analysis",
"""A sandboxed worker needs to open a small policy-approved set of files, but pathname
policy is too complex to encode in seccomp-BPF. Design a brokered architecture.""",
"""Give the sandboxed worker little or no ambient filesystem authority. It sends a narrow
request to a trusted broker over a controlled IPC channel.

The broker validates the requested operation against policy, performs constrained
descriptor-relative resolution (for example beneath approved directory descriptors with
`openat2()` restrictions where available), opens the object, then passes back only the
approved file descriptor.

Seccomp can then restrict the worker's syscall surface and prevent arbitrary opening,
while the broker owns pathname-sensitive policy. Authenticate/validate IPC requests and
keep the broker interface minimal because it becomes a privileged boundary.""",
"Must move pathname policy into a trusted narrow broker, use constrained descriptor-relative resolution, return approved descriptors, and use seccomp to reduce worker syscall authority.",
["sandbox","broker","seccomp","openat2"]),
"design-numa-first-touch":(
"computer-architecture","numa","architecture-analysis",
"""A 200 GiB array will be processed in disjoint halves by threads pinned to two NUMA
sockets. Design initialization so each socket mostly accesses local memory under a
first-touch allocation policy.""",
"""Do not initialize the entire array from one thread. Pin initialization workers
according to the eventual processing placement and have socket-0 workers first-write the
pages in the first partition while socket-1 workers first-write the pages in the second.

Under first-touch policy, those page faults allocate physical memory near the CPUs that
first access the pages, producing local placement for the later workers.

Verify with NUMA placement/local-vs-remote counters. Explicit NUMA allocation APIs are
another option when placement must be controlled directly. CPU affinity by itself does
not move pages that were already allocated elsewhere.""",
"Must use parallel first-touch or explicit NUMA allocation matching future owners, and distinguish CPU affinity from physical page migration.",
["numa","first-touch","memory-placement","multisocket"]),
"design-async-buffer-ownership":(
"systems-programming","async-io","design",
"""Design buffer ownership for an asynchronous I/O system where requests can complete
after the function that submitted them has returned. The current implementation
sometimes uses stack buffers.""",
"""Each in-flight operation must own or retain a buffer whose lifetime extends through the
API-defined completion point. Use heap/request objects, a buffer pool, or registered
buffer slots and associate the buffer identity with the request/completion token.

Do not recycle or mutate a buffer while an operation may still read/write it. On
completion, transition ownership back to the application or pool. Cancellation must also
define when the buffer is actually safe to reuse; a cancellation request is not
necessarily completion.

Stack storage from a returning function is unsuitable unless the API has already
completed all access before return.""",
"Must tie buffer lifetime/ownership to asynchronous completion, cover safe reuse/cancellation semantics, and reject returning-function stack storage for outstanding operations.",
["async-io","buffer-lifetime","ownership","completion"]),
"design-priority-ceiling":(
"operating-systems","real-time-scheduling","technical-decision",
"""A hard real-time subsystem has a small fixed set of mutexes shared by tasks with known
priorities. The team wants bounded blocking and protection from unbounded priority
inversion. Explain when a priority-ceiling protocol is attractive compared with an
ordinary mutex.""",
"""With a priority-ceiling protocol, each protected resource is assigned a ceiling based
on the highest-priority task that may lock it. The scheduling/locking rules prevent
certain unsafe lock acquisitions and can bound blocking while preventing the classic
medium-priority interference of unbounded inversion.

It is attractive when the task/resource set and priorities are known enough to configure
ceilings correctly and deterministic blocking analysis matters.

An ordinary mutex without inheritance/ceiling can allow problematic inversion. Priority
inheritance is another useful protocol and may be easier in some systems, but its
blocking behavior and lock interactions differ. The choice should follow the RTOS
semantics and schedulability analysis rather than a generic claim that one protocol is
always faster.""",
"Must explain known resource ceilings/bounded inversion rationale, contrast with ordinary mutex behavior, and frame the choice around deterministic real-time analysis rather than universal performance.",
["priority-ceiling","real-time","mutex","schedulability"]),
}
    domain,sub,task,q,a,details,tags=cases[fid]
    return record(rid,domain,sub,task,difficulty,q,a,"rubric",details,tags)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=10)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="design",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
