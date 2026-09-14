from __future__ import annotations
import argparse, random
from .common import record, run_purpose

FAMILIES = [
    {"id":"dbg-epoll-et-starvation","domain":"systems-programming"},
    {"id":"dbg-dns-negative-cache","domain":"networking"},
    {"id":"dbg-cgroup-cpu-throttle","domain":"linux-infrastructure"},
    {"id":"dbg-numa-remote-memory","domain":"computer-architecture"},
    {"id":"dbg-dma-stale-buffer","domain":"embedded-systems"},
    {"id":"dbg-replica-read-staleness","domain":"distributed-systems"},
    {"id":"dbg-gpu-sync-timeline","domain":"compute-model-infrastructure"},
    {"id":"dbg-db-pool-starvation","domain":"software-engineering"},
    {"id":"dbg-priority-inversion","domain":"operating-systems"},
    {"id":"dbg-tls-clock-failure","domain":"secure-engineering"},
]

def build(f, rng, rid, difficulty):
    fid=f["id"]
    if fid=="dbg-epoll-et-starvation":
        q="""A Linux server uses edge-triggered epoll. Under high request rates, a few
connections stop making progress even though `ss` shows unread receive data. The read
handler performs one successful `recv()` per readiness notification and returns to the
event loop. Diagnose the stall and state exactly what you would change and observe to
verify the repair."""
        a="""With edge-triggered epoll, the handler must drain a nonblocking socket until
`recv()` returns `EAGAIN`/`EWOULDBLOCK`. One successful read does not guarantee a new
edge for bytes that were already present. Returning early can therefore leave unread
data without another notification.

Change the handler to loop on `recv()`: process positive byte counts, treat zero as peer
EOF, retry/handle `EINTR`, and stop only on `EAGAIN`/`EWOULDBLOCK` or a real error.

Verify with a trace or counters that each readable callback drains multiple chunks when
needed, that the socket reaches `EAGAIN`, and that stalled connections disappear. Do not
"fix" this by adding polling or assuming another EPOLLIN edge is guaranteed."""
        return record(rid,f["domain"],"event-driven-io","debugging",difficulty,q,a,"rubric",
                      "Must diagnose incomplete draining under EPOLLET, require a loop through EAGAIN/EWOULDBLOCK, distinguish EOF/errors, and propose runtime verification.",
                      ["epoll","EPOLLET","recv","debugging"])
    if fid=="dbg-dns-negative-cache":
        q="""A service discovery client briefly queried a hostname before its DNS record
was created. The name now resolves correctly from `dig`, but one long-running process
continues reporting "name not found" for several minutes while other processes recover.
Give a debugging plan that distinguishes authoritative DNS failure from local negative
caching."""
        a="""First compare the authoritative/current DNS answer with the failing process's
resolver path. `dig` proving that the record now exists does not prove the process has
discarded an earlier negative result.

Inspect the process/runtime resolver cache, local caching daemon, container DNS layer,
and the SOA negative-caching TTL if applicable. Compare queries from the same network
namespace and resolver configuration as the process. Restarting the process can be a
diagnostic experiment, but not the primary fix.

If the process recovers when its negative-cache entry expires or is flushed while fresh
lookups succeed elsewhere, negative caching is the likely cause. Fix TTL/cache behavior
or discovery sequencing rather than repeatedly changing the authoritative record."""
        return record(rid,f["domain"],"dns","debugging",difficulty,q,a,"rubric",
                      "Must separate authoritative current state from cached negative results, inspect the same resolver path/namespace, and use TTL/cache expiry as evidence.",
                      ["dns","negative-cache","ttl","service-discovery"])
    if fid=="dbg-cgroup-cpu-throttle":
        q="""A containerized API shows periodic latency spikes. Host CPU utilization is
only 45%, yet application traces contain gaps where runnable threads make no progress.
The service has a cgroup v2 CPU quota. What measurements would confirm or reject quota
throttling as the cause?"""
        a="""Host-wide idle CPU does not rule out a cgroup quota bottleneck. Inspect the
service's `cpu.max` and `cpu.stat`, especially throttling event counts and throttled
time, and correlate them with the latency spikes. Also inspect runnable-thread counts,
per-cgroup CPU usage, and scheduler traces around the gaps.

If the cgroup repeatedly exhausts its quota and throttling counters/time rise exactly
when the application stalls, quota throttling is strong evidence. If those counters stay
flat, look elsewhere.

The fix should follow measured demand: adjust quota/period or reduce CPU demand. CPU
affinity is not a substitute for quota because it controls placement, not allowed CPU
time."""
        return record(rid,f["domain"],"cgroup-v2","debugging",difficulty,q,a,"reference-answer",
                      "Must inspect cpu.max and cpu.stat throttling data, correlate with latency, distinguish host CPU utilization from cgroup entitlement, and avoid confusing affinity with quota.",
                      ["cgroup-v2","cpu-throttling","latency","debugging"])
    if fid=="dbg-numa-remote-memory":
        q="""A two-socket server runs faster when all worker threads are pinned to socket
0 than when half are pinned to socket 1. CPU utilization is high in both cases. The main
thread allocates and initializes the entire working set before workers start. Diagnose
the likely NUMA problem and give a measurement experiment."""
        a="""The main thread likely first-touches most pages on socket 0, so workers on
socket 1 perform remote-memory accesses across the inter-socket fabric. Moving compute
without moving memory can therefore reduce bandwidth and increase latency.

Confirm with NUMA placement tools/counters and local-versus-remote memory traffic. Then
repeat after parallel first-touch initialization: pin workers to the sockets that will
own each partition and have each worker initialize its own pages.

If page placement becomes balanced and socket-1 bandwidth/latency improves, the
diagnosis is supported. CPU pinning alone does not relocate existing physical pages."""
        return record(rid,f["domain"],"numa","debugging",difficulty,q,a,"rubric",
                      "Must connect single-thread first touch to socket-0 page placement, require NUMA/local-remote measurement, and use parallel first touch or explicit placement as the experiment.",
                      ["numa","first-touch","remote-memory","profiling"])
    if fid=="dbg-dma-stale-buffer":
        q="""An MCU receives frames by DMA into cacheable RAM. A logic analyzer proves the
peripheral transferred the correct bytes, but firmware occasionally parses data from the
previous frame. The DMA engine is not cache coherent with the CPU. Diagnose the failure
and state what instrumentation or experiment would confirm it."""
        a="""The CPU can keep stale cache lines for the DMA buffer. DMA updates RAM
directly, but completion does not invalidate those CPU cache lines.

After DMA-to-memory completion and before CPU consumption, transfer ownership to the CPU
using the platform's required barriers and invalidate the affected cache lines. Align
and isolate buffers so cache maintenance does not discard unrelated dirty data.

A strong experiment is to place the receive buffer in a correctly configured
non-cacheable region, or add the required invalidate operation, and see whether the
stale-frame failures disappear. For the opposite CPU-to-DMA direction, dirty lines need
cleaning before DMA reads them."""
        return record(rid,f["domain"],"dma-cache-coherency","debugging",difficulty,q,a,"rubric",
                      "Must diagnose stale CPU cache lines, use invalidate for DMA-to-CPU after completion, mention ownership/barriers, and give a confirmatory cacheability/maintenance experiment.",
                      ["dma","cache","coherency","debugging"])
    if fid=="dbg-replica-read-staleness":
        q="""A replicated service acknowledges a write, then an immediate read routed to a
different replica returns the old value. Minutes later everything converges. There is no
evidence of data loss. Give a debugging plan that distinguishes replication lag from a
broken write path."""
        a="""First identify which replica accepted the write, what acknowledgement rule
made it successful, and which replica served the stale read. Measure replication/apply
lag and the replica's version/log position rather than only comparing values.

If the primary/leader has the committed value while the read replica is behind and later
applies the missing entry, the symptom is replication lag plus a read-consistency policy
that permits stale replicas.

Then decide whether the API requires read-after-write consistency. Possible fixes are
session/leader reads, waiting for a minimum version, or a stronger quorum/read policy.
Do not classify eventual convergence as proof of write loss."""
        return record(rid,f["domain"],"replication","debugging",difficulty,q,a,"rubric",
                      "Must compare write/ack location to read replica, inspect replication/apply position, distinguish lag from data loss, and connect remediation to the required read consistency.",
                      ["replication","stale-read","lag","consistency"])
    if fid=="dbg-gpu-sync-timeline":
        q="""GPU utilization falls to near zero every iteration although kernels themselves
are fast. A profiler shows a device-to-host scalar copy followed by CPU code before the
next kernel launch. Explain the likely synchronization point and give a minimal
experiment to prove it."""
        a="""A host read of a value produced on the GPU often requires the producing work
to finish before the CPU can consume the value. The device-to-host scalar copy can
therefore create a synchronization boundary that drains queued GPU work each iteration.

Confirm on the timeline that the copy/host read waits for prior kernels and that future
kernel submission does not resume until the CPU finishes using the value. Then remove
the per-iteration host dependency—for example keep the decision on device, batch the
reads, or read asynchronously at a coarser cadence—and compare overlap and throughput.

The diagnosis should come from the timeline, not from GPU-utilization percentage alone."""
        return record(rid,f["domain"],"gpu-synchronization","debugging",difficulty,q,a,"reference-answer",
                      "Must identify the device-to-host value dependency as a synchronization boundary, use timeline evidence, and propose an experiment that removes or batches the host dependency.",
                      ["gpu","synchronization","profiler","device-to-host"])
    if fid=="dbg-db-pool-starvation":
        q="""An API has a 40-connection database pool. During an incident, database CPU is
only moderate, but requests spend most of their time waiting to acquire a connection.
Several endpoints start nested fan-out queries. Give a debugging plan before increasing
the pool size."""
        a="""Measure pool occupancy, connection-acquire wait time, per-endpoint concurrent
query count, query duration, and transaction hold time. Trace whether fan-out requests
reserve multiple connections concurrently or hold connections while waiting on other
work.

If the pool remains saturated while database execution itself is not saturated, the
bottleneck is application-side connection ownership/concurrency rather than raw database
CPU. Bound fan-out concurrency, shorten transaction/connection hold time, and leave
headroom for unrelated requests.

Increasing pool size without understanding the ownership pattern can simply move
contention into the database and worsen overload."""
        return record(rid,f["domain"],"connection-pools","debugging",difficulty,q,a,"rubric",
                      "Must inspect pool wait/occupancy and connection hold patterns, connect nested fan-out to pool starvation, and avoid blindly increasing pool size.",
                      ["database","connection-pool","starvation","fan-out"])
    if fid=="dbg-priority-inversion":
        q="""A high-priority real-time thread blocks on a mutex. Tracing shows the mutex is
owned by a low-priority thread, while medium-priority CPU-bound threads repeatedly
preempt that owner. The high-priority thread misses its deadline. Diagnose the scheduler
interaction and state what trace change would confirm a priority-inheritance fix."""
        a="""This is priority inversion. The high-priority thread waits for a resource held
by the low-priority thread, while unrelated medium-priority work prevents the owner from
running long enough to release it.

Use a mutex/protocol that supports priority inheritance or an appropriate priority
ceiling. With priority inheritance, the low-priority owner should temporarily execute at
the inherited higher effective priority while it blocks the high-priority waiter.

A confirming trace should show the owner being boosted, preempting the medium-priority
threads, releasing the mutex sooner, and then returning to its normal priority. This does
not fix deadlocks or unbounded critical sections."""
        return record(rid,f["domain"],"real-time-scheduling","debugging",difficulty,q,a,"reference-answer",
                      "Must identify priority inversion, explain medium-priority interference, and specify the observable priority boost/earlier lock release expected from priority inheritance.",
                      ["priority-inversion","mutex","real-time","scheduler"])
    if fid=="dbg-tls-clock-failure":
        q="""After a VM snapshot is restored, outbound TLS connections fail with certificate
'not yet valid' errors. The certificates are known-good and other machines connect
normally. What should be checked before rotating certificates or changing trust stores?"""
        a="""Check the VM's system clock and time synchronization first. Certificate
validity is evaluated against local time, so a restored snapshot with a clock behind the
certificate's `notBefore` time can make a valid certificate appear not yet valid.

Compare UTC time, synchronization state, hypervisor/guest time settings, and the
certificate validity interval. Correct the clock through the normal time-sync mechanism
and retry.

If the connection succeeds once local time is correct, there is no reason to rotate the
certificate or modify trust anchors. Trust-chain failures and validity-window failures
are different classes of TLS error."""
        return record(rid,f["domain"],"tls","debugging",difficulty,q,a,"reference-answer",
                      "Must check local clock/time synchronization against certificate validity before changing certificates or trust stores, and distinguish validity-window failure from trust-chain failure.",
                      ["tls","certificate","clock","vm","debugging"])
    raise KeyError(fid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=10)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="debugging",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
