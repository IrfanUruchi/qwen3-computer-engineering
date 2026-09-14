#!/usr/bin/env bash
set -euo pipefail

cd ~/qwen3-computer-engineering

mkdir -p data/staging/v0.2 configs

python3 - <<'PY'
import json
from pathlib import Path
from textwrap import dedent

OUT = Path("data/staging/v0.2/batch-004.jsonl")
PLAN = Path("configs/dataset-v0.2-batch-004.json")

def s(x):
    return dedent(x).strip()

records = [
{
"id":"ce-software-db-write-skew-000331",
"version":1,
"split":"train",
"domain":"software-engineering",
"subdomain":"database-concurrency",
"task_type":"failure-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A hospital scheduling service stores whether each of two doctors is on call. The rule is
that at least one doctor must remain on call.

Two concurrent transactions each read both rows, see that the other doctor is on call,
and set their own row to off call. Both transactions commit under snapshot isolation,
leaving nobody on call.

Explain the anomaly and give two ways to enforce the invariant safely.
""")},
{"role":"assistant","content":s("""
This is write skew. The transactions update different rows, so ordinary write-write
conflict detection does not force one of them to abort. Under snapshot isolation, both
can make decisions from snapshots that were individually valid but jointly produce a
state that violates the cross-row invariant.

Two standard fixes are:

1. use a serializable isolation level that detects the dangerous dependency pattern and
   aborts one transaction; or
2. explicitly lock a common piece of state that represents the invariant, for example
   selecting the relevant rows with an appropriate locking read so the two decisions
   cannot proceed independently.

Another design is to model the invariant so competing updates touch a common row or
constraint that the database can protect atomically.

The important point is that checking the invariant in application code before two
independent writes is not enough. The check and the state transition must be protected
by a concurrency-control mechanism that covers the invariant as a whole.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify write skew under snapshot isolation, explain why different-row writes can both commit, and propose serializable isolation or locking/modeling that protects the cross-row invariant."
},
"source":{"type":"original"},
"tags":["write-skew","snapshot-isolation","serializable","database","concurrency"]
},

{
"id":"ce-systems-cloexec-race-000332",
"version":1,
"split":"train",
"domain":"systems-programming",
"subdomain":"file-descriptor-lifecycle",
"task_type":"code-repair",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A multithreaded Unix process creates a file descriptor with `open()`, then immediately
calls `fcntl(fd, F_SETFD, FD_CLOEXEC)`. Another thread can call `fork()` and `exec()`
between those two operations.

Explain the race and repair the descriptor-creation pattern.
""")},
{"role":"assistant","content":s("""
The close-on-exec flag is being installed in a separate operation from descriptor
creation. If another thread forks after `open()` returns but before `fcntl()` sets
`FD_CLOEXEC`, the child can inherit the descriptor and then carry it across `exec()`.

That can leak files, sockets, pipes, credentials, or other capabilities into a program
that was never supposed to receive them.

The repair is to request close-on-exec atomically when the descriptor is created. For
`open()`, use:

```c
int fd = open(path, flags | O_CLOEXEC, mode);
```

Use the equivalent atomic close-on-exec option for other descriptor-producing APIs,
such as `pipe2(..., O_CLOEXEC)`, `accept4(..., SOCK_CLOEXEC)`, or duplication operations
that support `O_CLOEXEC`/`F_DUPFD_CLOEXEC`.

Setting `FD_CLOEXEC` later with `fcntl()` is acceptable only when the program can prove
there is no concurrent fork/exec window. In a general multithreaded process, atomic
creation is the robust pattern.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must identify the open-then-fcntl race with concurrent fork/exec and require atomic close-on-exec creation such as O_CLOEXEC, SOCK_CLOEXEC, pipe2, or equivalent."
},
"source":{"type":"original"},
"tags":["O_CLOEXEC","fork","exec","file-descriptor","race-condition"]
},

{
"id":"ce-systems-mmap-truncate-sigbus-000333",
"version":1,
"split":"train",
"domain":"systems-programming",
"subdomain":"memory-mapped-files",
"task_type":"failure-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A process memory-maps a 1 GiB file and later reads near the end of the mapping. Another
process truncates the file to 100 MiB while the mapping remains active. The reader then
crashes with `SIGBUS`.

Explain why the mapping can still exist yet an access fails, and give a safer design for
concurrent file replacement.
""")},
{"role":"assistant","content":s("""
The virtual mapping and the file's current backing extent are related but not identical.
Truncating the file does not automatically remove the other process's virtual mapping.
However, pages in the mapping beyond the new end of the file no longer have valid file
backing. Accessing such a page can therefore raise `SIGBUS`.

A safer update design avoids truncating a file that other processes may still have
mapped. A common pattern is:

1. write the new contents to a separate temporary file;
2. finish and validate that file;
3. atomically rename the new file over the published pathname.

Existing mappings continue to refer to the old inode, while new openers see the new
file. The old inode can be reclaimed after the old mappings/file descriptors are gone.

If in-place resizing is unavoidable, readers and writers need an explicit coordination
protocol that prevents readers from accessing regions whose backing may disappear.

A pathname replacement is different from truncating the inode currently backing an
existing mapping.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain SIGBUS from accessing a file-backed mapping beyond the file's new EOF, distinguish mapping lifetime from valid backing pages, and recommend replacement-by-new-file/rename or explicit coordination."
},
"source":{"type":"original"},
"tags":["mmap","truncate","SIGBUS","rename","file-lifetime"]
},

{
"id":"ce-os-condition-variable-predicate-000334",
"version":1,
"split":"train",
"domain":"operating-systems",
"subdomain":"thread-synchronization",
"task_type":"code-repair",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A worker waits for a queue item using a condition variable:

```c
pthread_mutex_lock(&m);
if (queue_empty())
    pthread_cond_wait(&cv, &m);
item = pop_item();
pthread_mutex_unlock(&m);
```

Occasionally `pop_item()` runs when the queue is empty.

Repair the pattern and explain why an `if` check is insufficient.
""")},
{"role":"assistant","content":s("""
The condition variable is only a notification mechanism; the queue state is the real
predicate. The predicate must be rechecked after every return from the wait.

Use a loop:

```c
pthread_mutex_lock(&m);

while (queue_empty()) {
    pthread_cond_wait(&cv, &m);
}

item = pop_item();

pthread_mutex_unlock(&m);
```

`pthread_cond_wait()` atomically releases the mutex while sleeping and reacquires it
before returning, but returning does not guarantee that this particular thread may
consume an item.

Reasons include spurious wakeups and competition from other consumers: another thread
can acquire the mutex first and consume the item before this worker gets the lock back.

The producer must modify the queue state while holding the same mutex and signal or
broadcast according to the program's wakeup policy. Correctness comes from protecting
and rechecking the predicate under the mutex, not from treating a wakeup as ownership
of the condition.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must replace if with while, explain predicate rechecking under the mutex, cover spurious wakeups and competing consumers, and not treat condition-variable notification as ownership of the resource."
},
"source":{"type":"original"},
"tags":["condition-variable","pthread","predicate","spurious-wakeup","mutex"]
},

{
"id":"ce-architecture-huge-pages-tlb-000335",
"version":1,
"split":"train",
"domain":"computer-architecture",
"subdomain":"memory-translation",
"task_type":"performance-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A memory-intensive analytics process walks a 120 GiB in-memory dataset with poor TLB
locality. An engineer proposes using huge pages and claims they will always improve
performance.

Explain why huge pages can help, why they are not universally beneficial, and what you
would measure before enabling them broadly.
""")},
{"role":"assistant","content":s("""
Huge pages map more memory with each TLB entry, so they can increase TLB reach and reduce
page-walk overhead for workloads that touch large memory regions with poor translation
locality.

They are not automatically better. Tradeoffs can include:

- internal fragmentation and wasted memory;
- allocation/compaction difficulty under memory pressure;
- longer or more disruptive allocation behavior depending on the mechanism used;
- coarser-grained copy-on-write or memory-management operations;
- interactions with NUMA placement and workload lifetime;
- little benefit when TLB misses are not an important bottleneck.

Before enabling them broadly, compare representative runs using hardware counters and
profiling: TLB misses, page walks, CPU cycles, memory bandwidth, latency, RSS/allocated
memory, NUMA locality, and end-to-end throughput.

Also distinguish explicitly reserved huge pages from transparent huge pages because
their allocation and operational behavior differ.

The decision should be driven by measured translation pressure and whole-system cost,
not by page size alone.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must explain increased TLB reach/reduced page walks, include meaningful downsides such as fragmentation/allocation/NUMA effects, and require measurement rather than claiming universal improvement."
},
"source":{"type":"original"},
"tags":["huge-pages","tlb","page-walk","memory","performance"]
},

{
"id":"ce-linux-systemd-socket-activation-000336",
"version":1,
"split":"train",
"domain":"linux-infrastructure",
"subdomain":"service-supervision",
"task_type":"architecture-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A daemon takes several seconds to initialize, but operators want clients to connect
immediately during boot and also want the listening socket to survive daemon restarts.

Explain how systemd socket activation can provide this behavior and what the daemon must
do differently.
""")},
{"role":"assistant","content":s("""
With socket activation, systemd creates and owns the listening socket before the service
process starts. Incoming connections can be queued by the kernel while the daemon is
being launched.

The service receives the already-open listening descriptor from systemd instead of
blindly creating and binding a second socket at the same address. The daemon must detect
and adopt the passed descriptor using the systemd socket-activation protocol or an
appropriate library helper.

Because the socket belongs to the socket unit, the listening endpoint can remain present
while the service process is restarted. New work can wait in the listen queue until the
replacement daemon is ready, subject to queue limits and timeout behavior.

The application still needs correct handling for accepted/in-flight connections; socket
activation does not preserve arbitrary process memory or active connection state across
a crash.

The architectural change is that listener lifetime is supervised separately from daemon
process lifetime.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain that systemd owns/creates the listener, queues connections before service readiness, passes the descriptor to the daemon, and distinguish listener persistence from preservation of already accepted application state."
},
"source":{"type":"original"},
"tags":["systemd","socket-activation","service-restart","listen-socket","boot"]
},

{
"id":"ce-embedded-spsc-ring-ordering-000337",
"version":1,
"split":"train",
"domain":"embedded-systems",
"subdomain":"lock-free-buffers",
"task_type":"code-repair",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
An ISR is the single producer for a ring buffer and the main loop is the single consumer.
The producer writes an element and then advances `head`. The consumer reads `head` and
then reads the element.

On a weakly ordered MCU, the implementation uses ordinary non-atomic loads/stores and
occasionally the consumer sees the new `head` but stale element data.

Describe the ordering required for safe publication.
""")},
{"role":"assistant","content":s("""
The producer must not publish the new `head` until the element contents are globally
visible to the consumer. The consumer must not read the element before it has observed
that publication with the corresponding ordering.

A standard single-producer/single-consumer pattern is:

- producer writes the element data normally;
- producer stores the new `head` with release semantics;
- consumer loads `head` with acquire semantics;
- after the acquire observes the published position, the consumer reads the element.

The release prevents prior element writes from being reordered after publication. The
matching acquire prevents subsequent element reads from being reordered before the
publication observation and establishes the required happens-before relationship.

The index variables also need atomic access of a width and alignment supported safely by
the target. If the MCU or language environment does not provide suitable atomics between
ISR and main context, use the platform's interrupt-safe critical-section/barrier
primitives instead.

`volatile` alone is not a portable replacement for these ordering guarantees.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must require data write before release publication of head and acquire observation before data read, address atomic index access, and reject volatile as a portable synchronization substitute."
},
"source":{"type":"original"},
"tags":["ring-buffer","spsc","release-acquire","isr","memory-ordering"]
},

{
"id":"ce-networking-time-wait-000338",
"version":1,
"split":"train",
"domain":"networking",
"subdomain":"tcp-connection-lifecycle",
"task_type":"troubleshooting",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A client opens and closes thousands of short TCP connections per second to the same
server. Eventually new `connect()` calls fail because the client runs out of usable
ephemeral port combinations, while many old connections remain in `TIME_WAIT`.

Explain why `TIME_WAIT` exists and give architectural fixes that are safer than simply
trying to disable it.
""")},
{"role":"assistant","content":s("""
`TIME_WAIT` is normally entered by the endpoint that performs the active close. It keeps
the old connection identity unavailable for a period so delayed duplicate TCP segments
from that connection cannot be mistaken for data belonging to a later connection using
the same tuple. It also allows retransmission of the final ACK if necessary.

At very high connection churn, the finite source-address/source-port/destination tuple
space can become a practical limit.

Safer fixes focus on reducing churn or increasing legitimate tuple capacity:

- reuse persistent connections or connection pools;
- multiplex multiple logical requests over one transport where the protocol supports it;
- spread outbound traffic across additional source addresses when appropriate;
- increase the configured ephemeral-port range if it is unnecessarily small;
- measure which side performs the active close and whether the workload design can avoid
  needless reconnects.

Options that aggressively recycle `TIME_WAIT` state can create correctness problems in
the presence of delayed packets and should not be treated as a generic first-line fix.

The real objective is to reduce pressure on connection identities while preserving TCP's
safety assumptions.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must explain delayed-segment protection/final-ACK role of TIME_WAIT, connect churn to tuple/ephemeral-port exhaustion, and prefer pooling/multiplexing/address or port-range capacity over unsafe blanket recycling."
},
"source":{"type":"original"},
"tags":["tcp","TIME_WAIT","ephemeral-ports","connection-pooling","networking"]
},

{
"id":"ce-distributed-clock-skew-lease-000339",
"version":1,
"split":"train",
"domain":"distributed-systems",
"subdomain":"leases-and-time",
"task_type":"failure-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A distributed lock service grants a 10-second lease. A client records the lease expiry
using its wall clock and continues acting until `now < expiry`. Administrators later
adjust the machine clock backward with time synchronization, causing the client to act
for longer than intended.

Explain the timekeeping bug and design the local expiry check more safely.
""")},
{"role":"assistant","content":s("""
Wall-clock time is not a safe duration clock because it can jump due to synchronization,
manual changes, timezone-independent clock corrections, or virtualization effects. If
the clock moves backward, a client comparing wall-clock timestamps can believe a lease
is valid longer than the duration it was actually granted.

For local duration measurement, record the grant against a monotonic clock and compare
elapsed monotonic time to a conservative local deadline. A monotonic clock is designed
not to step backward when civil time is corrected.

The client should also account for uncertainty: network delay, processing time, and any
documented clock/error bounds may require stopping before the server-side expiry rather
than exactly at it.

Most importantly, a local lease timer cannot by itself prevent a stale client from
acting after ownership changes. For operations that must reject stale holders, combine
leases with server/resource-side enforcement such as fencing tokens.

Use wall-clock timestamps for human/civil time when needed; use monotonic time for local
elapsed-duration decisions.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify wall-clock jumps as unsafe for elapsed lease duration, require a monotonic deadline with safety margin/uncertainty handling, and note that fencing/resource-side enforcement is needed against stale actors."
},
"source":{"type":"original"},
"tags":["lease","monotonic-clock","clock-skew","fencing-token","distributed-systems"]
},

{
"id":"ce-reasoning-queue-utilization-000340",
"version":1,
"split":"train",
"domain":"engineering-reasoning",
"subdomain":"queueing-performance",
"task_type":"performance-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A service can process 100 requests per second on average. Incoming traffic rises from
50 requests/s to 90 requests/s while the service-time distribution is otherwise
unchanged.

An engineer says latency should rise by only about 10% because throughput demand rose
from 50% to 90% of capacity. Explain why queueing delay can increase much more sharply
as utilization approaches 100%, using an M/M/1 model only as an illustrative bound.
""")},
{"role":"assistant","content":s("""
Queueing is nonlinear near saturation.

For an illustrative M/M/1 queue with service rate mu = 100 requests/s and arrival rate
lambda, mean time in the system is:

W = 1 / (mu - lambda).

At 50 requests/s:

W = 1 / (100 - 50) = 0.02 s = 20 ms.

At 90 requests/s:

W = 1 / (100 - 90) = 0.10 s = 100 ms.

So the model predicts a fivefold increase in mean response time even though the offered
load increased by less than a factor of two.

The exact numbers should not be treated as a prediction for an arbitrary real service:
M/M/1 assumes Poisson arrivals, exponential service times, one server, and other idealized
conditions. The engineering lesson is that as utilization approaches capacity, there is
less spare service time to absorb arrival variability, so queues can grow rapidly.

Measure the real arrival distribution, service-time distribution, concurrency, queue
depth, and percentile latency before choosing a production capacity target.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must show nonlinear queueing growth near saturation, correctly compute 20 ms at lambda=50 and 100 ms at lambda=90 for M/M/1 with mu=100, and state that the model assumptions make this illustrative rather than universally predictive."
},
"source":{"type":"original"},
"tags":["queueing","utilization","latency","capacity","performance"]
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
    "batch": "004",
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

python3 -m json.tool configs/dataset-v0.2-batch-004.json >/dev/null \
  && echo "Batch plan: VALID JSON"

python3 scripts/validate_dataset.py \
  data/staging/v0.2/batch-004.jsonl
