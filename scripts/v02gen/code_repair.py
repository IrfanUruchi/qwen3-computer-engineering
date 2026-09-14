from __future__ import annotations
import argparse, random
from .common import record, run_purpose

FAMILIES = [
    {"id":"repair-size-add-overflow","domain":"systems-programming"},
    {"id":"repair-condvar-loop","domain":"operating-systems"},
    {"id":"repair-atomic-publication","domain":"computer-architecture"},
    {"id":"repair-cas-db-version","domain":"software-engineering"},
    {"id":"repair-spsc-ordering","domain":"embedded-systems"},
    {"id":"repair-partial-send","domain":"systems-programming"},
    {"id":"repair-idempotency-key","domain":"software-engineering"},
    {"id":"repair-secure-openat2","domain":"secure-engineering"},
    {"id":"repair-gpu-accum-step","domain":"compute-model-infrastructure"},
    {"id":"repair-systemd-health-watchdog","domain":"linux-infrastructure"},
]

def build(f,rng,rid,difficulty):
    fid=f["id"]
    if fid=="repair-size-add-overflow":
        q="""Repair this C allocation check so `header_len + payload_len` cannot wrap
`size_t` before `malloc()`:

```c
size_t total = header_len + payload_len;
if (total > LIMIT) return -1;
void *p = malloc(total);
```

Assume `LIMIT <= SIZE_MAX`. Explain why checking `total` only after the addition is
insufficient."""
        a="""Check before the addition:

```c
if (payload_len > SIZE_MAX - header_len)
    return -1;

size_t total = header_len + payload_len;

if (total > LIMIT)
    return -1;

void *p = malloc(total);
if (!p)
    return -1;
```

Unsigned `size_t` arithmetic wraps modulo its width. If the addition overflows, `total`
can become a small value and incorrectly pass the later `LIMIT` check. The subtraction
form proves that the addition is representable before it is evaluated.

If the API also imposes semantic limits on `header_len` or `payload_len`, validate those
separately; the overflow guard addresses representability of the sum."""
        return record(rid,f["domain"],"integer-safety","code-repair",difficulty,q,a,"reference-answer",
                      "Must perform a pre-addition overflow check using SIZE_MAX - header_len (or equivalent checked-add primitive), then apply LIMIT and allocation checks.",
                      ["size_t","overflow","malloc","c"])
    if fid=="repair-condvar-loop":
        q="""Repair this pthread consumer:

```c
pthread_mutex_lock(&m);
if (queue_empty())
    pthread_cond_wait(&cv, &m);
item = pop_item();
pthread_mutex_unlock(&m);
```

The queue can have multiple consumers."""
        a="""Recheck the queue predicate in a loop:

```c
pthread_mutex_lock(&m);

while (queue_empty()) {
    pthread_cond_wait(&cv, &m);
}

item = pop_item();

pthread_mutex_unlock(&m);
```

Condition-variable wakeup is not ownership of an item. The wait may return spuriously,
and another consumer can acquire the mutex first and consume the available item before
this thread reacquires it.

The producer must modify the queue state while holding the same mutex and then signal or
broadcast according to the wakeup policy. Correctness comes from the predicate under the
mutex, not from an `if` tied to one notification."""
        return record(rid,f["domain"],"thread-synchronization","code-repair",difficulty,q,a,"reference-answer",
                      "Must replace if with while and explain predicate rechecking because of spurious wakeups and competing consumers.",
                      ["pthread","condition-variable","mutex","predicate"])
    if fid=="repair-atomic-publication":
        q="""Repair the publication ordering:

```cpp
Payload payload;
std::atomic<bool> ready{false};

void producer() {
    payload = make_payload();
    ready.store(true, std::memory_order_relaxed);
}

void consumer() {
    while (!ready.load(std::memory_order_relaxed)) {}
    use(payload);
}
```

The producer does not modify `payload` after publication."""
        a="""Use release publication and acquire observation:

```cpp
void producer() {
    payload = make_payload();
    ready.store(true, std::memory_order_release);
}

void consumer() {
    while (!ready.load(std::memory_order_acquire)) {}
    use(payload);
}
```

When the acquire load observes the value from the release store, operations before the
release happen-before operations after the acquire. That publishes the ordinary
`payload` writes to the consumer.

Relaxed atomic access makes the flag itself atomic but does not establish the ordering
needed to publish the non-atomic payload."""
        return record(rid,f["domain"],"memory-ordering","code-repair",difficulty,q,a,"reference-answer",
                      "Must use release store and acquire load and explain the synchronizes-with/happens-before relationship for publication.",
                      ["atomics","release","acquire","cpp"])
    if fid=="repair-cas-db-version":
        q="""Two API clients can overwrite each other's updates. The table contains
`id`, `value`, and integer `version`. Both clients read version 12. Repair an
unconditional SQL `UPDATE` so one stale writer is detected without a global lock."""
        a="""Make the observed version part of the atomic update predicate:

```sql
UPDATE objects
SET value = :new_value,
    version = version + 1
WHERE id = :id
  AND version = 12;
```

The server must inspect the affected-row count. One changed row means the update won the
version check. Zero means the object changed since the client read it; return a conflict
or reload and perform a defined merge.

Do not first `SELECT version` and then issue an unconditional update, because another
writer can commit between those two statements. The compare and update must be one
database operation (or equivalently protected within a correct transaction)."""
        return record(rid,f["domain"],"optimistic-concurrency","code-repair",difficulty,q,a,"reference-answer",
                      "Must place expected version in the UPDATE predicate, increment version atomically, and treat zero affected rows as conflict.",
                      ["sql","optimistic-concurrency","lost-update","version"])
    if fid=="repair-spsc-ordering":
        q="""An ISR is the only producer of a ring buffer and the main loop is the only
consumer. Producer writes an element then updates `head`; consumer reads `head` then the
element. On a weakly ordered target, the consumer can observe the new head with stale
element bytes. Repair the publication ordering."""
        a="""Publish the index with release ordering and observe it with acquire ordering.

Producer:
1. write the element contents;
2. store the new `head` with release semantics.

Consumer:
1. load `head` with acquire semantics;
2. after observing the published position, read the corresponding element.

The release prevents element writes from moving after publication; the matching acquire
prevents element reads from moving before observation and establishes the required
happens-before relation.

The index must also be accessed atomically at a width supported by the target. If the
platform lacks suitable ISR-safe atomics, use its documented interrupt-safe critical
section/barrier mechanism. `volatile` alone is not a portable synchronization fix."""
        return record(rid,f["domain"],"ring-buffer","code-repair",difficulty,q,a,"rubric",
                      "Must require element write before release publication and acquire observation before element read, with atomic index access or platform-equivalent synchronization.",
                      ["spsc","ring-buffer","isr","memory-ordering"])
    if fid=="repair-partial-send":
        q="""Repair a nonblocking send loop that currently resubmits the original buffer
whenever `send()` writes fewer bytes than requested. The code must avoid both duplicate
bytes and dropped suffixes."""
        a="""Track progress explicitly:

```c
size_t off = 0;

while (off < len) {
    ssize_t n = send(fd, buf + off, len - off, 0);

    if (n > 0) {
        off += (size_t)n;
        continue;
    }

    if (n < 0 && errno == EINTR)
        continue;

    if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        /* preserve off and resume after writable readiness */
        break;
    }

    /* connection/error handling */
    fail_request();
    break;
}
```

A positive return reports only the accepted prefix. Resubmitting from `buf` after a
partial send duplicates bytes; discarding the request loses the remaining suffix. The
buffer must remain valid until all bytes are accounted for or the operation is aborted."""
        return record(rid,f["domain"],"nonblocking-io","code-repair",difficulty,q,a,"reference-answer",
                      "Must advance buffer offset by each positive send result, preserve state across EAGAIN, handle EINTR, and retain buffer lifetime until completion/abort.",
                      ["send","nonblocking","partial-write","socket"])
    if fid=="repair-idempotency-key":
        q="""A payment endpoint creates a new charge on every POST. Clients retry after
timeouts, so the same logical payment can be charged twice. Repair the API protocol using
an idempotency key."""
        a="""Have the client generate one stable idempotency key for a single logical
payment and reuse it on retries.

On the server, atomically associate that key with a fingerprint of the request and the
operation/result. If the key is new, execute the payment and durably record the result.
If the same key arrives again with the same request, return the recorded result without
creating another charge. If the key is reused with different material parameters, reject
it.

The record must live for a defined retry window. The idempotency boundary must include
the side effect being protected; simply caching an HTTP response after the charge is not
enough if a crash can occur between the charge and the cache write."""
        return record(rid,f["domain"],"api-reliability","code-repair",difficulty,q,a,"rubric",
                      "Must use one stable key per logical operation, atomically bind it to request/result around the protected side effect, replay duplicates, and reject conflicting reuse.",
                      ["idempotency-key","retry","payments","api"])
    if fid=="repair-secure-openat2":
        q="""A privileged helper calls `stat(user_path)` to validate a file, then later
calls `open(user_path)`. Repair the design so an attacker cannot swap a symlink or path
component between check and use."""
        a="""Do not validate a pathname and then resolve it again. Open relative to a
trusted directory descriptor with constrained resolution, for example Linux `openat2()`
using policy-appropriate `RESOLVE_*` restrictions such as staying beneath the trusted
tree and disallowing symlink traversal where required.

Then inspect the already-open file descriptor with `fstat()` if type/owner/mode checks are
needed, and operate on that descriptor.

On systems without `openat2()`, walk components relative to trusted directory file
descriptors with no-follow rules appropriate to the policy. Prior `realpath()` or
`stat()` does not make a later pathname `open()` atomic."""
        return record(rid,f["domain"],"filesystem-races","code-repair",difficulty,q,a,"rubric",
                      "Must eliminate stat-then-open pathname re-resolution, use descriptor-relative constrained resolution/opening, and validate the opened descriptor rather than a prior path.",
                      ["toctou","openat2","symlink","filesystem-security"])
    if fid=="repair-gpu-accum-step":
        q="""A training loop accumulates gradients over four microbatches but calls
`optimizer.step()` and `zero_grad()` after every microbatch. Repair the control flow so
the effective batch is four microbatches."""
        a="""Accumulate gradients across all four microbatches and update once:

```python
optimizer.zero_grad(set_to_none=True)

for i, batch in enumerate(microbatches):
    loss = model_loss(batch) / 4
    loss.backward()

optimizer.step()
```

Dividing each loss by four keeps the accumulated gradient on the same scale as the mean
loss over the combined effective batch (assuming the loss reduction semantics match).

If clipping is used, clip after accumulation and before the optimizer step. Learning-rate
schedules and optimizer step counters should normally advance per optimizer update, not
per microbatch. Mixed-precision overflow handling must likewise match the chosen
accumulation policy."""
        return record(rid,f["domain"],"gradient-accumulation","code-repair",difficulty,q,a,"rubric",
                      "Must accumulate four backward passes before one optimizer step/zeroing, scale the loss/gradient correctly, and keep step-based operations aligned with optimizer updates.",
                      ["gradient-accumulation","optimizer","training","gpu"])
    if fid=="repair-systemd-health-watchdog":
        q="""A systemd service sends `WATCHDOG=1` from a dedicated timer thread even when
the worker pool is deadlocked. systemd therefore believes the service is healthy.
Repair the watchdog design."""
        a="""The heartbeat must represent useful service health, not merely timer-thread
liveness.

Keep `WatchdogSec=` configured, but send `WATCHDOG=1` only after checking meaningful
progress conditions—for example worker-loop progress counters, event-loop advancement,
or completion of a bounded internal health transaction. If those conditions stop
advancing, deliberately stop notifying systemd so the watchdog can fail/restart the
service.

The health check itself must be bounded and should not depend on the same deadlocked
resource it is trying to diagnose in a way that blocks the watchdog thread forever.

A watchdog that is independent of application progress detects only that the heartbeat
thread is alive."""
        return record(rid,f["domain"],"service-supervision","code-repair",difficulty,q,a,"rubric",
                      "Must tie watchdog notification to real application progress/health and stop notifying on deadlock, rather than sending unconditional timer-thread heartbeats.",
                      ["systemd","watchdog","deadlock","health-check"])
    raise KeyError(fid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--records",type=int,default=10)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()
    run_purpose(purpose="code-repair",families=FAMILIES,build=build,
                records_requested=args.records,seed=args.seed)

if __name__=="__main__":
    main()
