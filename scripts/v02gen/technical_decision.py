from __future__ import annotations
import argparse
from .common import record, run_purpose

FAMILIES = [
    {"id":"decision-distributed-rw-quorum","domain":"distributed-systems"},
    {"id":"decision-reasoning-scaleup-vs-scaleout","domain":"engineering-reasoning"},
    {"id":"decision-reasoning-latency-headroom","domain":"engineering-reasoning"},
]

DIFFICULTY = {
    "decision-distributed-rw-quorum":"expert",
    "decision-reasoning-scaleup-vs-scaleout":"advanced",
    "decision-reasoning-latency-headroom":"advanced",
}

def build(f,rng,rid,_difficulty):
    fid=f["id"]; d=DIFFICULTY[fid]

    if fid=="decision-distributed-rw-quorum":
        q="""A replicated key-value store has N=5 replicas. The team proposes W=2 and R=2
because both are majorities of the currently healthy subset during normal operation.
Decide whether those values guarantee read/write quorum intersection over all five
replicas, and give one simple intersecting choice."""
        a="""They do not guarantee read/write intersection over N=5 because the standard
intersection condition is:

R + W > N.

Here, 2 + 2 = 4, which is not greater than 5. A write could be accepted by one pair of
replicas while a later read consults a disjoint pair.

A simple intersecting choice is R=3 and W=3, since 3+3=6>5. Other combinations such as
R=2, W=4 can also satisfy intersection, with different latency/availability tradeoffs.

This arithmetic is necessary but not a complete consistency proof. The protocol still
needs well-defined versioning, conflict handling, failure assumptions, and rules for what
constitutes an acknowledged operation."""
        return record(rid,f["domain"],"quorums","technical-decision",d,q,a,"reference-answer",
                      "Must reject R=2,W=2 for N=5 because R+W=4 is not >5, provide an intersecting choice such as 3/3, and note quorum arithmetic alone is not a full consistency proof.",
                      ["quorum","replication","read-write","intersection"])

    if fid=="decision-reasoning-scaleup-vs-scaleout":
        q="""A service is CPU-bound on one 16-core server. Profiling shows the workload
parallelizes well inside one process, has little shared state, and network overhead
between requests is small. The team can either replace the server with a 32-core machine
or run two 16-core replicas behind a load balancer. What factors should drive the
decision instead of assuming both choices are equivalent?"""
        a="""Both options roughly double nominal core capacity, but they change failure and
scaling properties differently.

A 32-core scale-up preserves one process/address space and can be simpler when work
benefits from shared caches or low-latency communication, but it increases dependence on
one machine and may hit memory-bandwidth/NUMA limits.

Two 16-core replicas provide fault isolation, rolling-upgrade flexibility, and horizontal
capacity growth, but require request distribution, duplicated memory footprint, external
or partitioned state, and may introduce load-balancer/network effects.

Measure per-core scaling, memory bandwidth/NUMA behavior, per-replica memory cost,
failure/restart objectives, deployment needs, and price/performance. The correct decision
is about bottleneck shape and operational requirements, not simply "32 cores equals two
times 16 cores." """
        return record(rid,f["domain"],"capacity-planning","technical-decision",d,q,a,"rubric",
                      "Must compare scale-up and scale-out across bottlenecks, failure isolation, state/load balancing, memory/NUMA effects, operations, and cost rather than equating core counts.",
                      ["scale-up","scale-out","capacity","reliability"])

    if fid=="decision-reasoning-latency-headroom":
        q="""A service can sustain 1,000 requests/s in a benchmark, but p99 latency rises
sharply above 750 requests/s. Normal traffic is 650 requests/s and can burst to 850.
Decide whether 1,000 requests/s should be treated as safe production capacity and explain
the headroom policy you would use."""
        a="""Do not treat the absolute throughput ceiling as safe production capacity.
The latency objective is already degrading around 750 requests/s, so the service's useful
capacity is constrained by its SLO before it reaches the benchmark maximum.

Normal load at 650 leaves only 100 requests/s of margin before the observed p99 knee, and
the stated 850-request/s burst exceeds that region.

Choose an operating target below the latency knee with enough reserve for bursts,
measurement error, uneven request cost, failover, and recovery. Then use admission
control/autoscaling/load shedding appropriate to the system so excursions do not turn
into runaway queueing.

The exact safe target needs production-like tests, but 1,000 requests/s is clearly a
saturation number, not a capacity promise."""
        return record(rid,f["domain"],"capacity-headroom","technical-decision",d,q,a,"rubric",
                      "Must reject 1000 rps as safe capacity because the p99 knee occurs near 750, explicitly reason about only 100 rps normal headroom and 850-rps bursts, and recommend operating reserve/admission policy.",
                      ["latency","headroom","capacity","slo"])

    raise KeyError(fid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=3)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="technical-decision",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
