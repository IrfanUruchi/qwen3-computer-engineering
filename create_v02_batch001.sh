#!/usr/bin/env bash
set -euo pipefail

cd ~/qwen3-computer-engineering

mkdir -p data/staging/v0.2 configs

python3 - <<'PY'
import json
from pathlib import Path
from textwrap import dedent

OUT = Path("data/staging/v0.2/batch-001.jsonl")
PLAN = Path("configs/dataset-v0.2-batch-001.json")

def s(x):
    return dedent(x).strip()

records = [
{
"id":"ce-systems-epollet-drain-000301",
"version":1,
"split":"train",
"domain":"systems-programming",
"subdomain":"event-driven-io",
"task_type":"failure-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A Linux server uses `epoll` with `EPOLLET` on nonblocking sockets. Its read handler calls
`recv()` once when an event arrives and then returns to the event loop. Under load, some
connections stall even though unread bytes remain in the socket receive buffer.

Explain why this happens and give the correct handling pattern.
""")},
{"role":"assistant","content":s("""
With edge-triggered epoll, readiness is reported when the descriptor changes from not
ready to ready. It is not guaranteed to generate another event merely because unread
data remains after the handler returns.

The socket should be nonblocking, and after a readable event the handler should keep
calling `recv()` until the available input is drained:

- `recv() > 0`: process the bytes and continue reading.
- `recv() == 0`: the peer performed an orderly shutdown.
- `recv() < 0` with `EINTR`: retry.
- `recv() < 0` with `EAGAIN` or `EWOULDBLOCK`: stop; the socket has been drained for
  the current readiness edge.
- Other errors: handle the connection failure.

Returning after only one successful `recv()` can leave the descriptor continuously
readable without producing a new edge, which causes the apparent stall.

The same drain-until-EAGAIN principle applies to other edge-triggered readiness
operations. `EPOLLONESHOT` adds a separate requirement to rearm the descriptor after
processing.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain edge-trigger semantics, require a nonblocking drain loop through EAGAIN/EWOULDBLOCK, distinguish EOF and EINTR, and not claim that epoll generates another edge for data that was never drained."
},
"source":{"type":"original"},
"tags":["epoll","EPOLLET","nonblocking-io","linux","event-loop"]
},

{
"id":"ce-os-priority-inversion-000302",
"version":1,
"split":"train",
"domain":"operating-systems",
"subdomain":"real-time-scheduling",
"task_type":"failure-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A high-priority real-time thread blocks on a mutex held by a low-priority thread.
Several medium-priority CPU-bound threads then run for long periods, preventing the
low-priority thread from releasing the mutex.

Identify the scheduling failure and describe a suitable mitigation.
""")},
{"role":"assistant","content":s("""
This is priority inversion.

The high-priority thread cannot run because it needs a mutex owned by the low-priority
thread. The medium-priority threads do not need that mutex, but they can preempt the
low-priority owner. As a result, they indirectly delay the high-priority thread.

A common mitigation is a mutex with priority inheritance. While the high-priority
thread is blocked on the mutex, the scheduler temporarily raises the effective priority
of the mutex owner so it can finish the critical section and release the lock. Its
priority can then return to normal.

Priority-ceiling protocols are another option in systems that support them and can
provide stronger blocking bounds.

The critical section should also be kept bounded and short. Priority inheritance does
not repair deadlocks or make an unbounded critical section safe; it specifically
addresses scheduler-induced inversion involving lock ownership.

A scheduler trace showing the high-priority waiter, boosted lock owner, and mutex
release is a useful way to verify the fix.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify priority inversion, explain the medium-priority interference, describe priority inheritance or an appropriate ceiling protocol, and avoid claiming that priority inheritance solves deadlock."
},
"source":{"type":"original"},
"tags":["priority-inversion","mutex","real-time","scheduler","priority-inheritance"]
},

{
"id":"ce-architecture-release-acquire-000303",
"version":1,
"split":"train",
"domain":"computer-architecture",
"subdomain":"memory-ordering",
"task_type":"code-repair",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A C++ producer fills a non-atomic `Payload payload` and then publishes readiness through
an atomic flag. Repair the synchronization so that a consumer that observes the flag
can safely read the completed payload.

Current sketch:

```cpp
Payload payload;
std::atomic<bool> ready{false};

void producer() {
    payload = build_payload();
    ready.store(true, std::memory_order_relaxed);
}

void consumer() {
    while (!ready.load(std::memory_order_relaxed)) {}
    use(payload);
}
```

Explain why the repaired ordering works.
""")},
{"role":"assistant","content":s("""
Use release publication and acquire observation:

```cpp
Payload payload;
std::atomic<bool> ready{false};

void producer() {
    payload = build_payload();
    ready.store(true, std::memory_order_release);
}

void consumer() {
    while (!ready.load(std::memory_order_acquire)) {
    }
    use(payload);
}
```

If the acquire load observes the value written by the release store, the two operations
form a synchronizes-with relationship. The writes performed by the producer before the
release, including construction of `payload`, happen-before the consumer operations
after the acquire.

That makes publication of the non-atomic payload well defined as long as the producer
does not concurrently modify it afterward.

Using `memory_order_relaxed` for both operations gives atomicity for `ready` but does
not by itself establish the ordering needed to publish the ordinary payload data.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must use release on publication and acquire on observation, explain synchronizes-with/happens-before, and distinguish atomicity of the flag from publication ordering of the non-atomic payload."
},
"source":{"type":"original"},
"tags":["memory-ordering","acquire-release","atomics","cpp","publication"]
},

{
"id":"ce-linux-cgroup-memory-high-000304",
"version":1,
"split":"train",
"domain":"linux-infrastructure",
"subdomain":"cgroup-v2",
"task_type":"troubleshooting",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A service in a cgroup v2 container develops severe latency spikes as memory use grows,
but it is not being OOM-killed. `memory.current` often approaches the configured
`memory.high`.

Explain what `memory.high` does, how it differs from `memory.max`, and what evidence you
would inspect before changing the limits.
""")},
{"role":"assistant","content":s("""
`memory.high` is a reclaim and throttling boundary rather than the cgroup's absolute
memory ceiling. When usage exceeds it, tasks in the cgroup can be forced into direct
reclaim and throttled, so latency can rise sharply even though no process is killed.

`memory.max` is the hard cgroup memory limit. If the cgroup cannot keep usage below
that limit through reclaim, allocation can reach the cgroup OOM path.

Before changing either value, inspect:

- `memory.current` and the configured `memory.high` / `memory.max`;
- `memory.events`, especially the `high`, `max`, `oom`, and `oom_kill` counters;
- memory pressure information such as PSI;
- anonymous memory, page cache, and swap behavior;
- the application's working-set growth and allocation pattern.

If the `high` counter and memory pressure rise with the latency spikes while OOM
counters remain unchanged, reclaim/throttling is a strong explanation. The fix may be
better memory sizing or lower working-set pressure rather than blindly increasing the
hard limit.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must distinguish memory.high throttling/reclaim from the hard memory.max limit and require evidence such as memory.events, current usage and memory pressure before changing configuration."
},
"source":{"type":"original"},
"tags":["cgroup-v2","memory-high","memory-max","psi","linux"]
},

{
"id":"ce-networking-tcp-half-close-000305",
"version":1,
"split":"train",
"domain":"networking",
"subdomain":"tcp-connection-lifecycle",
"task_type":"architecture-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A client sends a complete request over TCP and then calls `shutdown(fd, SHUT_WR)` to
signal that no more request bytes will be sent. The client still expects a potentially
large response.

A developer claims the shutdown means the TCP connection is closed and the client can
stop reading. Explain the mistake and the correct protocol behavior.
""")},
{"role":"assistant","content":s("""
TCP is full duplex. `shutdown(fd, SHUT_WR)` closes only the caller's sending direction.

After queued request bytes are sent, the local TCP endpoint sends a FIN. The peer can
observe end-of-stream for the request direction, but the opposite direction remains
usable. The peer may continue sending the response, and the client must continue
reading it.

The client should therefore:

1. send the complete request;
2. call `shutdown(..., SHUT_WR)` if the protocol uses EOF to delimit the request;
3. continue receiving until the application protocol says the response is complete or
   `recv()` returns zero after the peer's FIN;
4. close the descriptor when both directions are no longer needed.

A FIN is not equivalent to an RST and does not mean that both byte streams have been
discarded.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain TCP half-close semantics, distinguish SHUT_WR/FIN from full close or reset, and state that the client may continue receiving the response."
},
"source":{"type":"original"},
"tags":["tcp","half-close","fin","shutdown","sockets"]
},

{
"id":"ce-embedded-dma-cache-coherency-000306",
"version":1,
"split":"train",
"domain":"embedded-systems",
"subdomain":"dma-cache-coherency",
"task_type":"failure-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
An MCU has a data cache that is not hardware-coherent with a DMA engine. DMA receives
network frames into a RAM buffer. The DMA status says a frame completed, but the CPU
occasionally reads old bytes from that buffer.

Explain the failure and design a safe buffer-ownership/cache-maintenance strategy.
""")},
{"role":"assistant","content":s("""
The CPU can retain cache lines containing an older copy of the DMA buffer. Because the
DMA writes RAM directly and the cache is not coherent with it, DMA completion alone
does not force those cached lines to be refreshed.

For a DMA-to-CPU receive buffer, ownership should transfer explicitly:

1. while DMA owns the buffer, CPU code must not read or modify it;
2. wait for the DMA completion indication using the platform's required synchronization;
3. invalidate the relevant data-cache lines before the CPU consumes the bytes;
4. only then transfer ownership to CPU code.

For CPU-to-DMA transfers, dirty CPU cache lines generally need to be cleaned to memory
before DMA reads the buffer.

Cache maintenance must operate on the architecture's required cache-line boundaries.
Buffers should be aligned and isolated so invalidating one DMA buffer does not discard
dirty unrelated data sharing the same cache line. Memory barriers required by the MCU
or DMA API should also be used at ownership transitions.

An alternative is to place DMA buffers in a correctly configured non-cacheable region
when the platform and performance requirements permit it.

The exact clean/invalidate primitives are platform-specific, but the essential rule is
that software must explicitly maintain coherency and buffer ownership when the hardware
does not.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify stale CPU cache lines, distinguish invalidate for DMA-to-CPU from clean for CPU-to-DMA, require ownership discipline and cache-line-safe maintenance, and avoid assuming hardware coherency."
},
"source":{"type":"original"},
"tags":["dma","cache-coherency","embedded","cache-maintenance","buffer-ownership"]
},

{
"id":"ce-distributed-transactional-outbox-000307",
"version":1,
"split":"train",
"domain":"distributed-systems",
"subdomain":"transactional-messaging",
"task_type":"architecture-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
An order service commits an order to a relational database and then publishes an
`OrderCreated` event to a message broker. A crash after the database commit but before
the publish leaves a committed order with no event. Publishing first creates the
opposite failure mode.

Design a safer architecture without assuming a distributed transaction between the
database and broker.
""")},
{"role":"assistant","content":s("""
Use a transactional outbox.

In the same local database transaction that creates the order, insert an outbox row
describing the `OrderCreated` event. The order update and the intent to publish then
commit atomically in one database.

A separate relay reads committed outbox rows and publishes them to the broker. If the
relay crashes, it can retry because the event remains durably recorded.

The relay and broker boundary is normally at-least-once rather than magically
exactly-once. A crash can occur after the broker accepts an event but before the relay
records that fact. Therefore events should have stable identifiers and consumers should
be idempotent or deduplicate processed event IDs.

Outbox cleanup should occur only after the system's delivery policy considers the row
safe to retire.

This removes the dangerous gap between the order transaction and recording the intent
to publish, while explicitly handling duplicates at the remaining failure boundary.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must atomically write domain state and outbox state in one database transaction, use a relay with retry, acknowledge possible duplicate publication, and require idempotency/deduplication rather than claiming exactly-once delivery."
},
"source":{"type":"original"},
"tags":["transactional-outbox","messaging","idempotency","distributed-systems","retries"]
},

{
"id":"ce-software-optimistic-concurrency-000308",
"version":1,
"split":"train",
"domain":"software-engineering",
"subdomain":"concurrency-control",
"task_type":"code-repair",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
Two API clients read the same database object at version 7. Each edits a different
field and sends an update. The current implementation performs an unconditional
`UPDATE`, so the second request silently overwrites data written by the first.

Repair the update protocol without serializing all clients through one global lock.
""")},
{"role":"assistant","content":s("""
Use optimistic concurrency control with the version observed by the client.

For example, if the client read version 7:

```sql
UPDATE objects
SET field_a = ?, field_b = ?, version = version + 1
WHERE id = ? AND version = 7;
```

The update succeeds only if the database row is still at the version the client read.
The server must inspect the affected-row count.

- One affected row means the update won the compare-and-swap style check.
- Zero affected rows means another writer changed the object first. Return a conflict
  response or reload and perform an application-defined merge rather than silently
  overwriting the newer state.

For an HTTP API, the same idea can be exposed through an ETag and `If-Match`.

The version check and increment must occur atomically in the database operation.
Reading the current version in one query and then performing an unconditional update
in another simply recreates the race.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must use an atomic version predicate/CAS-style update, detect zero affected rows as conflict, increment the version on success, and avoid a separate check followed by an unconditional write."
},
"source":{"type":"original"},
"tags":["optimistic-concurrency","lost-update","etag","compare-and-swap","database"]
},

{
"id":"ce-compute-transfer-overlap-000309",
"version":1,
"split":"train",
"domain":"compute-model-infrastructure",
"subdomain":"gpu-data-transfer",
"task_type":"performance-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A GPU inference pipeline was changed to call `cudaMemcpyAsync()` in one stream and run
kernels in another, but a profiler still shows host-to-device copies serialized with
compute.

Give a debugging plan for determining why useful transfer/compute overlap is not
occurring.
""")},
{"role":"assistant","content":s("""
First verify that the prerequisites for asynchronous overlap actually exist rather than
assuming the API name guarantees concurrency.

Check the profiler timeline for the copy, kernel, stream and synchronization boundaries.
Then verify:

- the host source buffers are page-locked/pinned where required for truly asynchronous
  host-to-device transfer;
- copies and kernels are issued to streams that can execute independently rather than
  being serialized by the same stream or legacy default-stream behavior;
- there is no host call, event dependency, device synchronization, or framework
  operation forcing one stream to wait for the other;
- the GPU reports the copy-engine/concurrent-copy-and-execute capability needed by the
  intended schedule;
- transfers are large enough and kernels long enough for overlap to be visible.

A common pipeline is double buffering: while buffer A is consumed by compute, buffer B
is filled asynchronously, with events expressing only the dependencies that are
actually required.

Pinned memory and multiple streams are enabling conditions, not proof of overlap. The
final evidence should come from the GPU timeline and measured end-to-end throughput,
because hardware and workload constraints can still serialize execution.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must inspect a profiler timeline, cover pinned host memory, independent streams/dependencies, hardware copy/compute capability and workload granularity, and avoid claiming cudaMemcpyAsync alone guarantees overlap."
},
"source":{"type":"original"},
"tags":["cuda","async-copy","pinned-memory","streams","profiling"]
},

{
"id":"ce-security-toctou-path-000310",
"version":1,
"split":"train",
"domain":"secure-engineering",
"subdomain":"filesystem-races",
"task_type":"code-repair",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A privileged Linux helper receives a relative filename inside a trusted directory. It
first calls `stat()` to verify the path is a regular file and then later calls `open()`
on the same pathname.

Explain the security flaw and describe a safer file-opening design.
""")},
{"role":"assistant","content":s("""
The check and the use operate on the pathname at different times. An attacker who can
modify part of the path can replace a component, for example with a symlink, after the
`stat()` check but before `open()`. The object that gets opened may therefore be
different from the object that was validated. This is a TOCTOU filesystem race.

The safer design is to make resolution and opening part of the trusted operation
instead of validating a pathname and reopening it later.

On Linux, a strong approach is to open the trusted parent directory and resolve the
user-supplied relative path beneath that directory with an interface such as `openat2`
using appropriate resolution restrictions, for example preventing escape from the
trusted directory and disallowing symlink traversal when the policy requires it.

Operate on the returned file descriptor. If file type, owner or mode must be checked,
inspect the already-open descriptor with `fstat()` rather than performing a pathname
check followed by another pathname open.

On systems without `openat2`, carefully walking path components relative to trusted
directory file descriptors with suitable no-follow rules can provide the same design
principle.

Canonicalizing or checking the pathname first does not by itself remove the race if the
path is later resolved again.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify the stat/open TOCTOU race, recommend descriptor-relative constrained resolution/opening, validate the opened descriptor when needed, and avoid treating prior pathname canonicalization as an atomic security check."
},
"source":{"type":"original"},
"tags":["toctou","openat2","filesystem-security","symlink","race-condition"]
}
]

assert len(records) == 10
assert len({r["id"] for r in records}) == 10

existing_ids = set()

for p in Path("data/raw/v0.1").glob("*.jsonl"):
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            existing_ids.add(json.loads(line)["id"])

collisions = sorted({r["id"] for r in records} & existing_ids)
if collisions:
    raise SystemExit(f"ID collisions with v0.1: {collisions}")

with OUT.open("w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

plan = {
    "batch": "001",
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

python3 -m json.tool configs/dataset-v0.2-batch-001.json >/dev/null \
  && echo "Batch plan: VALID JSON"

python3 scripts/validate_dataset.py \
  data/staging/v0.2/batch-001.jsonl
