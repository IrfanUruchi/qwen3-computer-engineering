from __future__ import annotations
import argparse
from .common import record, run_purpose

FAMILIES = [
    {"id":"test-software-idempotency-crash-window","domain":"software-engineering"},
    {"id":"test-arch-false-sharing-ab","domain":"computer-architecture"},
    {"id":"test-linux-service-restart-contract","domain":"linux-infrastructure"},
]

DIFFICULTY = {
    "test-software-idempotency-crash-window":"intermediate",
    "test-arch-false-sharing-ab":"advanced",
    "test-linux-service-restart-contract":"advanced",
}

def build(f,rng,rid,_difficulty):
    fid=f["id"]; d=DIFFICULTY[fid]

    if fid=="test-software-idempotency-crash-window":
        q="""Design a test for a payment endpoint that claims to be idempotent by request
key. The important failure window is a process crash after the external charge succeeds
but before the HTTP response reaches the client."""
        a="""Use a fake or isolated payment backend that records charge attempts by a stable
logical payment identifier.

Test sequence:
1. send a request with idempotency key K;
2. arrange for the charge side effect to succeed;
3. inject a process crash before the client receives a successful response;
4. restart the service;
5. retry the identical request with K;
6. assert that the backend still contains exactly one charge and that the service returns
   the durable result of the original logical operation.

Also test that reusing K with materially different request parameters is rejected.

This specifically exercises the crash boundary that simple duplicate-POST tests miss.
A response cache written only after the charge would fail this test because the crash can
occur between side effect and cache persistence."""
        return record(rid,f["domain"],"idempotency","testing",d,q,a,"rubric",
                      "Must inject failure after side effect but before response, retry the same key after restart, assert exactly one charge, and test conflicting key reuse.",
                      ["idempotency","crash-testing","payments","retry"])

    if fid=="test-arch-false-sharing-ab":
        q="""Design an A/B microbenchmark to prove that two hot per-thread counters are
suffering from false sharing rather than ordinary lock contention. The counters are
currently adjacent in one structure."""
        a="""Create two otherwise identical variants.

Variant A places the independently updated counters in the original adjacent layout.
Variant B aligns/pads them so the hot counters occupy different cache lines. Run the same
thread count, affinity, work per thread, and compiler settings for both.

Measure throughput/cycles and, where the platform exposes them, coherence/HITM or cache-
line ownership traffic. No locks should be added between variants.

Evidence for false sharing is a substantial improvement in B together with reduced
coherence traffic when only the physical layout changes. Repeat across core placements,
especially same-core/same-cluster versus different-core/socket placement, because the
coherence cost can vary with topology."""
        return record(rid,f["domain"],"cache-coherence","testing",d,q,a,"rubric",
                      "Must change only cache-line layout between A/B variants, hold workload/affinity constant, avoid adding locks, and use throughput plus coherence evidence to support false sharing.",
                      ["false-sharing","microbenchmark","cache-line","coherence"])

    if fid=="test-linux-service-restart-contract":
        q="""A systemd-managed daemon is supposed to recover from a crash without leaving a
stale Unix-domain socket pathname that prevents restart. Design an automated integration
test for that restart contract."""
        a="""Run the service in an isolated test environment with the same systemd unit and
runtime-directory configuration used in production.

1. start the service and verify the socket accepts a request;
2. terminate the daemon abruptly rather than performing its graceful cleanup path;
3. let systemd restart it according to the unit policy;
4. assert that the restarted instance becomes active within the expected bound;
5. verify the socket accepts a fresh request and that only the intended listener owns it.

Capture journal output and service state so the test fails if restart loops on
`EADDRINUSE`, stale PID/socket state, or permission errors.

If systemd socket activation owns the listener, adapt the assertion accordingly: the
socket unit should remain valid while the service process is replaced."""
        return record(rid,f["domain"],"service-supervision","testing",d,q,a,"rubric",
                      "Must use abrupt termination, verify automatic restart and endpoint usability, detect stale-socket/EADDRINUSE failure, and account for socket-activation ownership if used.",
                      ["systemd","integration-test","restart","unix-socket"])

    raise KeyError(fid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=3)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="testing",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
