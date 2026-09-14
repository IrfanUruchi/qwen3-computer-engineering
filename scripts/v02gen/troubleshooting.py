from __future__ import annotations
import argparse
from .common import record, run_purpose

FAMILIES = [
    {"id":"trouble-os-dirty-writeback-stall","domain":"operating-systems"},
    {"id":"trouble-arch-memory-bandwidth-wall","domain":"computer-architecture"},
    {"id":"trouble-networking-backlog-overflow","domain":"networking"},
]

DIFFICULTY = {
    "trouble-os-dirty-writeback-stall":"advanced",
    "trouble-arch-memory-bandwidth-wall":"expert",
    "trouble-networking-backlog-overflow":"advanced",
}

def build(f,rng,rid,_difficulty):
    fid=f["id"]; d=DIFFICULTY[fid]

    if fid=="trouble-os-dirty-writeback-stall":
        q="""A Linux process that normally writes quickly to buffered files develops
multi-second write latency spikes during sustained output. Storage utilization is high,
dirty memory grows before each spike, and CPU is not saturated. Give a troubleshooting
sequence that distinguishes page-cache buffering from writeback pressure."""
        a="""Track dirty-page and writeback metrics over time together with application write
latency and block-device latency/queue depth. Buffered writes can initially complete by
copying data into the page cache, so early application throughput may exceed what the
device can sustain.

If dirty memory rises until kernel thresholds/background writeback can no longer absorb
the excess and application writes then stall while storage drains, the workload is
writeback-limited rather than CPU-limited.

Confirm the device's sustainable throughput with a representative test, inspect mount/
filesystem behavior, and compare the application's long-run write rate with that limit.
The fix can involve reducing write rate, batching differently, improving storage, or
tuning only after measurement. Increasing dirty limits merely allows a larger backlog
and can make eventual stalls longer."""
        return record(rid,f["domain"],"writeback","troubleshooting",d,q,a,"rubric",
                      "Must correlate dirty/writeback growth with application stalls and device saturation, explain buffered-write burst illusion, and reject blindly increasing dirty limits as a root fix.",
                      ["page-cache","writeback","dirty-pages","storage"])

    if fid=="trouble-arch-memory-bandwidth-wall":
        q="""A parallel array-processing kernel scales almost linearly from 1 to 8 cores,
then throughput barely improves from 8 to 32 cores. CPU utilization continues to rise.
Hardware counters show LLC misses and memory-controller traffic increasing. Give a
troubleshooting plan for a memory-bandwidth wall."""
        a="""Measure sustained memory bandwidth as thread count increases and compare it with
the platform's achievable bandwidth for a similar access pattern. Also track bytes moved
per unit of useful work, LLC miss behavior, NUMA placement, and per-socket traffic.

If throughput stops scaling at the same point that aggregate DRAM bandwidth plateaus,
additional cores are competing for a saturated memory subsystem rather than adding useful
throughput.

Then test optimizations that reduce memory traffic: improve locality/blocking, reuse data
in cache, change representation, fuse passes, or improve NUMA placement. Moving threads
between cores without reducing bytes transferred will not remove a bandwidth ceiling.

The conclusion should come from the bandwidth plateau plus workload counters, not from
high CPU utilization alone."""
        return record(rid,f["domain"],"memory-bandwidth","troubleshooting",d,q,a,"rubric",
                      "Must correlate scaling plateau with saturated DRAM bandwidth, inspect bytes/work and NUMA/locality, and target memory traffic rather than assuming more cores help.",
                      ["memory-bandwidth","scaling","numa","profiling"])

    if fid=="trouble-networking-backlog-overflow":
        q="""A TCP server remains reachable, but during traffic bursts some clients time
out during connection establishment. Established connections are healthy. CPU is
moderate and packet capture shows bursts of new SYNs. Give a troubleshooting plan focused
on listen/backlog pressure."""
        a="""Inspect the listener's configured backlog, kernel listen/SYN queue statistics,
accept rate, and drops/overflows during the burst. Compare arrival rate of new
connections with the rate at which the application calls `accept()` and begins servicing
them.

If queue occupancy/drops rise while established traffic remains healthy, the bottleneck
is in connection admission rather than established-flow processing.

Check whether the application event loop is delaying `accept()`, whether worker handoff
blocks the accept path, and whether kernel backlog/SYN-cookie behavior matches the load.
Increase backlog only if the application and memory budget can support it; also reduce
connection churn or improve accept-loop responsiveness.

The evidence should distinguish queue overflow from packet loss elsewhere on the path."""
        return record(rid,f["domain"],"tcp-listener","troubleshooting",d,q,a,"rubric",
                      "Must inspect listen/SYN queue occupancy/drops and accept rate, distinguish admission-path failure from established-flow health, and avoid treating backlog increase as the only fix.",
                      ["tcp","listen-backlog","accept","syn"])

    raise KeyError(fid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=3)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="troubleshooting",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
