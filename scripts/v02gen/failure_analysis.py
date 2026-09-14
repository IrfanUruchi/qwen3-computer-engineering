from __future__ import annotations
import argparse
from .common import record, run_purpose

FAMILIES=[
 {"id":"fail-mmap-truncate","domain":"systems-programming"},
 {"id":"fail-tlb-shootdown","domain":"operating-systems"},
 {"id":"fail-false-sharing","domain":"computer-architecture"},
 {"id":"fail-inotify-overflow","domain":"linux-infrastructure"},
 {"id":"fail-watchdog-reset-loop","domain":"embedded-systems"},
 {"id":"fail-pmtud-blackhole","domain":"networking"},
 {"id":"fail-stale-lease-writer","domain":"distributed-systems"},
 {"id":"fail-hidden-host-sync","domain":"compute-model-infrastructure"},
 {"id":"fail-db-write-skew","domain":"software-engineering"},
 {"id":"fail-scm-rights-leak","domain":"secure-engineering"},
]

def build(f,rng,rid,difficulty):
    fid=f["id"]
    cases={
"fail-mmap-truncate":(
"systems-programming","memory-mapped-files",
"""A process keeps a 1 GiB file mapping while another process truncates the underlying
file to 100 MiB. The mapping still appears in `/proc/<pid>/maps`, but touching a page
near the old end raises `SIGBUS`. Explain the failure boundary and a safer replacement
protocol.""",
"""The virtual mapping can remain present even though the file no longer backs pages
beyond its new EOF. Touching one of those invalid file-backed pages can therefore raise
`SIGBUS`.

Avoid truncating an inode that other processes may still map. Publish replacements by
writing a new file completely, validating/durably finishing it as required, then
atomically renaming it over the pathname. Existing mappings continue to reference the
old inode; new openers see the new inode.

If in-place resizing is unavoidable, readers and writers need an explicit coordination
protocol that prevents access to ranges whose backing can disappear.""",
"Must explain that mapping lifetime can outlive valid file backing after truncate, connect access beyond new EOF to SIGBUS, and recommend new-file-plus-rename or explicit coordination.",
["mmap","truncate","SIGBUS","file-lifetime"]),
"fail-tlb-shootdown":(
"operating-systems","virtual-memory",
"""A many-core process repeatedly changes page protections in a shared mapping. Kernel
CPU time and cross-CPU interrupts rise with thread count even though the process does
little I/O. Explain how this can become a TLB-shootdown scaling failure.""",
"""Changing mappings or permissions can invalidate translations cached by other CPUs.
The kernel must coordinate invalidation with CPUs that may hold stale TLB entries. As
more cores actively use the same address space, frequent changes can trigger repeated
cross-CPU synchronization/interrupt work.

Evidence should include page-table/TLB invalidation paths in profiles, rising
shootdown/IPI counters where available, and a strong relationship between protection
change frequency and core count.

Reduce unnecessary `mprotect`/unmap/remap operations, batch changes, or redesign the
hot path to reuse mappings. An ordinary TLB miss is not itself a shootdown; coordinated
stale-translation invalidation is the key mechanism.""",
"Must connect mapping changes to cross-CPU TLB invalidation, explain scaling with participating CPUs, distinguish misses from shootdowns, and propose measurable evidence.",
["tlb","shootdown","mprotect","scalability"]),
"fail-false-sharing":(
"computer-architecture","cache-coherence",
"""Two threads update different counters and never read each other's counter. Throughput
collapses only when the threads run on different cores. The counters occupy the same
cache line. Explain the failure and the layout change that should fix it.""",
"""This is false sharing. Coherence operates at cache-line granularity, not variable
granularity. Even though the threads touch different counters, each write requests
ownership of the shared line, so the line repeatedly moves or invalidates between cores.

Place independently hot writable counters on different cache lines using padding,
alignment, or a per-thread structure layout, then aggregate later if needed.

Verify with cache-coherence/HITM-style counters where available and by comparing the
same workload before and after line separation. A mutex is not required to explain the
slowdown; the issue is cache-line ownership traffic.""",
"Must identify cache-line-granularity coherence/false sharing, propose separating hot writable fields onto different lines, and suggest measurement or A/B verification.",
["false-sharing","cache-line","coherence","performance"]),
"fail-inotify-overflow":(
"linux-infrastructure","filesystem-monitoring",
"""A daemon treats its inotify event stream as authoritative. During a burst it receives
`IN_Q_OVERFLOW`, logs a warning, clears an internal flag, and continues processing new
events. Explain why its state can remain permanently wrong.""",
"""`IN_Q_OVERFLOW` means events were dropped. The daemon no longer knows which filesystem
changes occurred during the lost interval, so continuing from the surviving stream
cannot reconstruct authoritative state.

After overflow, treat the local event-derived state as suspect. Rescan the authoritative
filesystem state, rebuild/reconcile the in-memory model, then resume incremental event
processing using a race-aware handoff strategy appropriate to the application.

There is no valid generic operation that recreates the dropped event sequence from the
overflowed queue. The recovery boundary is authoritative resynchronization, not merely
clearing a warning flag.""",
"Must explain that dropped events destroy event-stream completeness and require authoritative rescan/reconciliation rather than queue clearing or pretending future events repair the gap.",
["inotify","overflow","rescan","linux"]),
"fail-watchdog-reset-loop":(
"embedded-systems","fault-recovery",
"""A hardware watchdog correctly resets a hung device, but a deterministic startup bug
causes every reboot to hit the same hang. The product now resets forever in the field.
Explain the recovery design missing from the boot process.""",
"""The watchdog handles a single hang but the boot policy lacks bounded recovery across
resets.

Capture reset cause very early and persist a small failure/boot-attempt counter in a
power-loss-tolerant form. Clear or decay it only after the device reaches a known-good
milestone. If repeated watchdog resets exceed a threshold, enter recovery instead of
restarting the same failing path: boot a known-good slot, disable an optional feature,
wait for maintenance, or accept an update.

Keep the watchdog enabled. The fix is adding cross-reset policy so the same deterministic
failure cannot create an infinite reboot loop.""",
"Must keep watchdog protection, persist repeated-failure knowledge across resets, define a known-good milestone, and enter bounded recovery after a threshold.",
["watchdog","reset-loop","recovery","boot"]),
"fail-pmtud-blackhole":(
"networking","path-mtu-discovery",
"""TCP handshakes and small messages succeed, but bulk transfers repeatedly retransmit
larger packets and stall. A tunnel on the path lowers effective MTU and relevant ICMP
packet-too-big feedback is filtered. Explain the failure.""",
"""This is a path-MTU-discovery black hole. Packets small enough for every link succeed,
but larger packets that exceed the reduced path MTU cannot pass. If fragmentation is
not available/allowed and the required ICMP feedback is filtered, the sender may keep
retransmitting a size the path cannot carry.

Confirm with packet capture, size-controlled probes, tunnel/interface MTU inspection,
and checks for missing ICMP packet-too-big/fragmentation-needed messages.

Fix the path by permitting required feedback or setting correct tunnel/interface MTUs.
Deliberate MSS clamping can be a practical edge mitigation when it accurately reflects
the tunnel's path constraint.""",
"Must connect large-packet stall to reduced path MTU plus missing ICMP feedback, explain why small traffic works, and give packet/MTU evidence and appropriate fixes.",
["pmtud","mtu","icmp","tcp"]),
"fail-stale-lease-writer":(
"distributed-systems","leases-and-locks",
"""Worker A holds a distributed lease, pauses for longer than the lease duration, and
loses ownership. Worker B obtains the lease and updates shared storage. A later resumes
and overwrites B's data. Explain why the lease did not protect the resource.""",
"""Lease expiry changes who is authorized according to the lock service, but it cannot
physically stop an old paused process from resuming and issuing writes.

Use fencing tokens: each new ownership grant receives a monotonically increasing token.
Every protected write carries that token, and the storage/resource layer remembers the
highest accepted token and rejects older ones. Once token 42 is accepted, a resumed
holder with token 41 is fenced out.

The enforcement must occur at the protected resource. A token generated only by the
lock service provides no protection if storage ignores it.""",
"Must explain that lease expiry cannot stop stale actors, require monotonically increasing fencing tokens, and require resource-side rejection of old tokens.",
["lease","fencing-token","stale-writer","distributed"]),
"fail-hidden-host-sync":(
"compute-model-infrastructure","gpu-synchronization",
"""A GPU training loop has fast kernels but poor utilization. Each iteration computes a
loss on the GPU, copies one scalar to the CPU for logging, then launches the next
iteration. Explain how the logging path can serialize execution.""",
"""Reading a GPU-produced scalar on the host creates a data dependency: the CPU cannot
consume the value until the producing GPU work has completed. If this happens every
iteration, the device-to-host copy/read can drain the asynchronous queue and prevent
useful overlap with the next iteration.

A profiler timeline should show the host waiting around the scalar transfer and future
kernel submission delayed until the read completes.

Log less frequently, batch/asynchronously stage metrics, or keep decisions on-device
when possible. Confirm improvement in the timeline and end-to-end throughput rather
than relying only on average utilization.""",
"Must identify the host scalar read as a synchronization boundary, require timeline evidence, and propose batching/removing the per-iteration host dependency.",
["gpu","host-sync","logging","profiling"]),
"fail-db-write-skew":(
"software-engineering","database-concurrency",
"""Two transactions each verify that a cross-row safety invariant currently holds, then
update different rows. Under snapshot isolation they both commit and the invariant is
false afterward. Explain why ordinary write-write conflict detection missed the failure.""",
"""This is write skew. Each transaction reads a snapshot in which the invariant holds and
writes a different row, so there may be no direct write-write conflict to force an
abort. The two individually valid decisions combine into an invalid final state.

Protect the invariant with serializable isolation, a locking read/common lock covering
the relevant state, or a schema/model that makes competing updates touch a common
database constraint/state.

Checking the invariant in application code and then writing independently is not enough;
the concurrency-control mechanism must cover the invariant as a whole.""",
"Must identify write skew under snapshot isolation, explain the absence of direct write-write conflict, and propose serializable/locking/modeling that protects the cross-row invariant.",
["write-skew","snapshot-isolation","database","invariant"]),
"fail-scm-rights-leak":(
"secure-engineering","unix-domain-sockets",
"""A privileged daemon accepts arbitrary file descriptors sent over a Unix-domain socket
with `SCM_RIGHTS`. When validation fails, several error paths forget to close the received
descriptor. Explain both the resource and authority failure.""",
"""A received descriptor is a live kernel-object reference. If rejected descriptors are
not closed, an attacker can exhaust the daemon's descriptor table and keep underlying
objects alive. If the daemon blindly trusts them, the sender can also hand it authority
over an unexpected file, socket, device, or directory.

Treat each received descriptor as owned immediately by the receive path: set
close-on-exec, validate the object itself with descriptor-based checks such as `fstat()`
or type-specific queries, enforce policy, and close on every rejection/error path.
Bound how many descriptors a client may submit.

`SCM_RIGHTS` passes capabilities, not merely integer metadata.""",
"Must cover descriptor/resource leaks and authority risk, require close-on-exec, descriptor-based validation, bounded input, and cleanup on every rejected/error path.",
["SCM_RIGHTS","file-descriptor","resource-leak","capability-security"]),
}
    domain,sub,q,a,details,tags=cases[fid]
    return record(rid,domain,sub,"failure-analysis",difficulty,q,a,"rubric",details,tags)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=10)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="failure-analysis",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
