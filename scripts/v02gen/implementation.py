from __future__ import annotations
import argparse
from .common import record, run_purpose

FAMILIES = [
    {"id":"impl-software-bounded-worker-queue","domain":"software-engineering"},
    {"id":"impl-systems-length-prefixed-parser","domain":"systems-programming"},
    {"id":"impl-os-generation-counter-wakeup","domain":"operating-systems"},
    {"id":"impl-networking-reconnect-backoff","domain":"networking"},
]

DIFFICULTY = {
    "impl-software-bounded-worker-queue":"intermediate",
    "impl-systems-length-prefixed-parser":"advanced",
    "impl-os-generation-counter-wakeup":"expert",
    "impl-networking-reconnect-backoff":"advanced",
}

def build(f,rng,rid,_difficulty):
    fid=f["id"]
    d=DIFFICULTY[fid]

    if fid=="impl-software-bounded-worker-queue":
        q="""Implement the admission rule for a service with a fixed worker pool and a
bounded pending-work queue. New work must not be accepted indefinitely when all workers
and queue slots are occupied. Describe the state transitions and what happens when the
queue is full."""
        a="""Keep two explicit capacity bounds: active workers and pending queue slots.

When a request arrives:
1. if a worker slot is free, start the request immediately;
2. otherwise, if the pending queue has space, enqueue it;
3. otherwise, reject or shed the request according to the API contract.

When a worker finishes, remove one queued request and transfer it directly into the freed
worker slot. Cancellation or timeout of queued work must remove that entry so it does not
consume capacity after it has lost value.

The implementation must update queue/worker accounting under the same synchronization
boundary so concurrent arrivals cannot over-admit. The important property is that the
number of admitted requests is bounded by worker_count + queue_capacity; overload becomes
an explicit admission decision instead of unbounded memory and latency growth."""
        return record(rid,f["domain"],"backpressure","implementation",d,q,a,"rubric",
                      "Must implement bounded worker plus queue admission, reject/shed when both are full, preserve synchronized accounting, and remove cancelled/expired queued work.",
                      ["backpressure","bounded-queue","worker-pool","admission-control"])

    if fid=="impl-systems-length-prefixed-parser":
        q="""Implement the core validation logic for a binary message whose first four
bytes are an unsigned big-endian payload length followed by that many payload bytes.
The parser receives `buf` and `buf_len` and must reject truncated or oversized messages
without out-of-bounds reads. Assume `MAX_PAYLOAD` is defined."""
        a="""A safe parser validates each boundary before using it:

```c
if (buf_len < 4)
    return PARSE_TRUNCATED;

uint32_t n =
    ((uint32_t)buf[0] << 24) |
    ((uint32_t)buf[1] << 16) |
    ((uint32_t)buf[2] << 8)  |
    (uint32_t)buf[3];

if (n > MAX_PAYLOAD)
    return PARSE_TOO_LARGE;

size_t payload_len = (size_t)n;

if (payload_len > buf_len - 4)
    return PARSE_TRUNCATED;

/* payload is buf + 4, length payload_len */
```

The subtraction form avoids computing `4 + payload_len` before proving it fits within
the available buffer. The parser should return a defined status for trailing bytes
according to the framing protocol rather than silently assuming one policy."""
        return record(rid,f["domain"],"binary-parsing","implementation",d,q,a,"reference-answer",
                      "Must check the 4-byte header before reading, decode big-endian length without unaligned casts, enforce MAX_PAYLOAD, and bounds-check payload against buf_len without overflow.",
                      ["binary-protocol","bounds-check","endianness","parser"])

    if fid=="impl-os-generation-counter-wakeup":
        q="""Design an implementation for waiting until a shared subsystem has changed
state, without losing a wakeup that occurs between a caller checking the state and going
to sleep. Use a monotonic generation counter plus a wait primitive. Explain the required
ordering."""
        a="""Maintain an atomic or lock-protected generation number that increments on every
state change relevant to waiters.

A waiter:
1. reads the current generation while checking the state predicate;
2. if the predicate is already satisfied, returns;
3. otherwise registers/waits on the same synchronization domain using the observed
   generation;
4. after wakeup, rechecks both the predicate and generation in a loop.

An updater changes the protected state, increments the generation, then wakes waiters
while obeying the synchronization rules of the chosen primitive.

The key is that the waiter cannot perform an unprotected "check, then sleep" sequence.
Its transition into the waiting state must be atomic with respect to observing updates,
or the primitive must compare the expected generation before sleeping. Wakeups are hints;
the predicate remains authoritative."""
        return record(rid,f["domain"],"wait-wakeup-protocols","implementation",d,q,a,"rubric",
                      "Must eliminate check-then-sleep lost wakeups using an observed generation integrated with the wait primitive, recheck the predicate in a loop, and require updater generation increment plus wake.",
                      ["lost-wakeup","generation-counter","wait","synchronization"])

    if fid=="impl-networking-reconnect-backoff":
        q="""Implement a reconnect policy for 10,000 clients that may all lose connection
to the same service at once. The policy must avoid a synchronized reconnect storm while
still retrying automatically."""
        a="""Use exponential backoff with randomized jitter and an upper bound.

For example, after failure number k:

```text
base = min(max_delay, initial_delay * 2^k)
delay = random_uniform(0, base)      # full jitter
```

Reset the failure counter only after a connection has remained healthy according to a
defined policy, not merely after a TCP handshake that immediately fails again.

Cap attempts by application deadline or lifecycle where appropriate, and make retries
cancellable. Server-provided retry guidance can override the local schedule if the
protocol defines it safely.

The random component is essential at fleet scale: deterministic exponential delays still
cause clients that failed together to retry together. Jitter spreads load over time and
reduces the thundering-herd effect."""
        return record(rid,f["domain"],"reconnection","implementation",d,q,a,"reference-answer",
                      "Must use capped exponential backoff with randomized jitter, explain why deterministic backoff remains synchronized, and define reset/cancellation behavior.",
                      ["reconnect","backoff","jitter","thundering-herd"])

    raise KeyError(fid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=4)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="implementation",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
