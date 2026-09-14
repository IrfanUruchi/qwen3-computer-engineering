#!/usr/bin/env bash
set -euo pipefail

cd ~/qwen3-computer-engineering

mkdir -p data/staging/v0.2 configs

python3 - <<'PY'
import json
from pathlib import Path
from textwrap import dedent

OUT = Path("data/staging/v0.2/batch-003.jsonl")
PLAN = Path("configs/dataset-v0.2-batch-003.json")

def s(x):
    return dedent(x).strip()

records = [
{
"id":"ce-systems-nonblocking-connect-000321",
"version":1,
"split":"train",
"domain":"systems-programming",
"subdomain":"nonblocking-sockets",
"task_type":"debugging",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A client creates a nonblocking TCP socket and calls `connect()`. The call returns `-1`
with `errno == EINPROGRESS`. The program treats that as a failed connection and closes
the socket.

Explain the bug and give the correct completion check for a nonblocking connect.
""")},
{"role":"assistant","content":s("""
For a nonblocking socket, `EINPROGRESS` normally means the connection attempt has started
but has not completed yet. It is not itself a connection failure.

The program should wait until the socket becomes writable, for example with `poll()`,
`select()`, or `epoll()`, and then query the pending socket error:

```c
int err = 0;
socklen_t len = sizeof(err);

if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &err, &len) < 0) {
    /* getsockopt itself failed */
} else if (err == 0) {
    /* connect succeeded */
} else {
    /* connect failed; err is the connection error */
}
```

Writable readiness alone is not proof of success: a failed asynchronous connect can also
make the descriptor writable. `SO_ERROR` is the decisive completion result.

The application should also enforce its own timeout rather than waiting forever.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must treat EINPROGRESS as an in-progress asynchronous connect, wait for readiness, then check SO_ERROR; writable readiness alone must not be treated as success."
},
"source":{"type":"original"},
"tags":["nonblocking","connect","EINPROGRESS","SO_ERROR","tcp"]
},

{
"id":"ce-os-fork-multithreaded-child-000322",
"version":1,
"split":"train",
"domain":"operating-systems",
"subdomain":"process-creation",
"task_type":"failure-analysis",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A multithreaded Unix process calls `fork()`. In the child, before `exec()`, it calls a
logging function that takes a mutex. The child occasionally deadlocks even though it
has only one thread after the fork.

Explain how this can happen and describe the safe design rule for the child path.
""")},
{"role":"assistant","content":s("""
After `fork()` in a multithreaded process, the child contains a copy of the calling
thread, but the memory image also contains synchronization objects in whatever state
they had at the instant of the fork.

If another thread held the logger mutex at that instant, the child inherits the mutex
state but not the thread that could unlock it. Calling the logger can therefore block
forever.

The safe rule is that, between `fork()` and `exec()` in the child of a multithreaded
process, code should use only operations that are defined as async-signal-safe for this
context, plus minimal direct setup required for the exec path. Complex library code,
memory allocation, stdio, logging, and arbitrary mutex-taking code should be avoided.

Common designs use `posix_spawn()` where suitable, or arrange the child path to perform
only simple descriptor operations and then `exec()` immediately.

`pthread_atfork()` handlers can repair selected library/application locks, but they are
not a general excuse to call arbitrary non-safe code in the child.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must explain inherited locked state without the owning thread, identify the fork-in-multithreaded-process hazard, and require an async-signal-safe/minimal child path before exec."
},
"source":{"type":"original"},
"tags":["fork","multithreading","deadlock","exec","async-signal-safe"]
},

{
"id":"ce-architecture-branch-predictor-aliasing-000323",
"version":1,
"split":"train",
"domain":"computer-architecture",
"subdomain":"branch-prediction",
"task_type":"performance-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
Two hot branches in different functions each behave predictably in isolation, but when
both functions are active their misprediction rates rise sharply. The instruction mix
and input data for each function have not changed.

Give a microarchitectural explanation for this behavior and describe how you would
verify the hypothesis.
""")},
{"role":"assistant","content":s("""
A plausible cause is branch-predictor aliasing or interference.

Predictor structures have finite tables indexed by some combination of branch address
and history. Two unrelated branches can map to overlapping predictor entries or history
patterns, so training from one branch can disturb the state used to predict the other.
Each branch can therefore look stable when measured alone but become less predictable
when both execute.

To verify the hypothesis:

- measure per-branch mispredictions with hardware performance counters or a profiler;
- compare each function alone versus the combined workload;
- change code layout, alignment, or function placement without changing semantics and
  see whether the interference pattern moves or disappears;
- repeat enough times to distinguish layout-sensitive predictor effects from ordinary
  data-dependent unpredictability.

The exact indexing function is processor-specific, so the diagnosis should be based on
measurement rather than assuming a particular predictor design.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must identify predictor-table/history aliasing as a plausible cause, emphasize finite shared predictor state, and propose counter/profiler plus layout-sensitivity experiments without inventing undocumented indexing details."
},
"source":{"type":"original"},
"tags":["branch-prediction","aliasing","misprediction","microarchitecture","profiling"]
},

{
"id":"ce-linux-systemd-watchdog-000324",
"version":1,
"split":"train",
"domain":"linux-infrastructure",
"subdomain":"service-supervision",
"task_type":"configuration",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A long-running service can become stuck while the process remains alive. The operator
currently uses `Restart=on-failure`, but systemd never restarts the hung process because
it has not exited.

Design a systemd watchdog-based configuration and explain the corresponding application
behavior.
""")},
{"role":"assistant","content":s("""
`Restart=on-failure` reacts after a process fails; it does not detect a process that is
alive but no longer making progress.

A watchdog design can use a unit configuration such as:

```ini
[Service]
Type=notify
WatchdogSec=20s
Restart=on-failure
```

The application must participate in the protocol. After startup it should notify systemd
that it is ready and, while healthy, send watchdog keepalive notifications at an
interval comfortably shorter than `WatchdogSec`—commonly around half the configured
period.

The keepalive must represent actual service health, not merely a timer thread that keeps
running while the useful work is deadlocked. The application should only send the
watchdog notification after checking the progress conditions that matter.

If systemd stops receiving the expected watchdog messages, it treats the service as
failed and can restart it according to the restart policy.

The exact notification API may use `sd_notify()` or an equivalent implementation of
the systemd notification protocol.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must distinguish process exit detection from hang detection, use WatchdogSec with a notify-capable service, require periodic health-backed watchdog notifications, and avoid a blind heartbeat that can survive a real deadlock."
},
"source":{"type":"original"},
"tags":["systemd","watchdog","sd_notify","service-supervision","restart"]
},

{
"id":"ce-embedded-watchdog-reset-loop-000325",
"version":1,
"split":"train",
"domain":"embedded-systems",
"subdomain":"fault-recovery",
"task_type":"design",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
An embedded device uses a hardware watchdog. A firmware bug causes the device to reboot,
hit the same bug during startup, and reboot again forever.

Design a recovery strategy that keeps the watchdog useful while avoiding an endless
reset loop.
""")},
{"role":"assistant","content":s("""
The watchdog should remain enabled, but the boot path needs persistent awareness of
repeated watchdog resets.

A typical strategy is:

1. read and preserve the hardware reset-cause register very early during boot;
2. maintain a small persistent boot-failure counter in storage suitable for the
   platform;
3. increment the counter when startup follows a watchdog reset and clear or decay it
   only after the system reaches a known-good milestone;
4. after a threshold of repeated failures, enter a recovery mode instead of starting
   the normal application path again.

Recovery mode might boot a known-good firmware slot, disable the failing optional
feature, expose a maintenance interface, or wait for an update.

Persistent state itself must be updated safely for the storage technology—for example,
using bounded writes, checksums/versioning, or redundant slots where power loss can
interrupt updates.

The watchdog is still valuable because it recovers from hangs. The added policy prevents
the exact same crash from causing unlimited unattended reboot cycles.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must preserve watchdog protection, track repeated watchdog-caused boots across resets, clear the count only after a known-good milestone, and enter a bounded recovery path after a threshold."
},
"source":{"type":"original"},
"tags":["watchdog","reset-loop","recovery-mode","embedded","boot"]
},

{
"id":"ce-networking-quic-connection-id-000326",
"version":1,
"split":"train",
"domain":"networking",
"subdomain":"quic",
"task_type":"architecture-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A mobile client using QUIC switches from Wi-Fi to cellular, changing its source IP
address and UDP port. A developer assumes the connection must be recreated because the
network 4-tuple changed.

Explain why QUIC can preserve the logical connection across this change and what
protocol mechanism makes that possible.
""")},
{"role":"assistant","content":s("""
QUIC does not identify a connection solely by the IP/UDP 4-tuple. It uses connection IDs
that let endpoints associate packets with an existing QUIC connection even when the
underlying network path changes.

When a client moves to a new address or port, packets carrying a valid connection ID can
still be mapped to the existing connection state. QUIC then performs path validation
before fully trusting the new path.

This allows connection migration without redoing the entire application connection
solely because the client's network address changed.

The mechanism does not mean every path change is automatically safe or accepted.
Implementations still apply validation, anti-amplification rules, congestion-control
state transitions, and policy restrictions as required by the protocol and deployment.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must explain that QUIC connection identity is not bound only to the 4-tuple, identify connection IDs and path validation, and avoid claiming that arbitrary path changes are accepted without validation."
},
"source":{"type":"original"},
"tags":["quic","connection-id","migration","udp","path-validation"]
},

{
"id":"ce-distributed-quorum-intersection-000327",
"version":1,
"split":"train",
"domain":"distributed-systems",
"subdomain":"replication",
"task_type":"technical-decision",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A replicated key-value store has N=5 replicas. A designer proposes write quorum W=2 and
read quorum R=2 and claims that every read is guaranteed to overlap the latest successful
write quorum.

Evaluate the claim and give a quorum choice that guarantees read/write intersection.
""")},
{"role":"assistant","content":s("""
The claim is false.

For guaranteed read/write quorum intersection, the usual condition is:

`R + W > N`.

With N=5, R=2 and W=2 gives:

`2 + 2 = 4`, which is not greater than 5.

The two quorums can therefore be disjoint.

A choice such as R=3 and W=3 satisfies:

`3 + 3 = 6 > 5`,

so every read quorum must overlap every write quorum by at least one replica.

Depending on the consistency model, systems may require additional conditions such as
`W > N/2` to prevent multiple disjoint successful write quorums, and real implementations
must also handle version ordering, failures, and stale replicas. Quorum intersection is
a necessary combinatorial property, not a complete consistency protocol by itself.
""")}
],
"verification":{
"method":"reference-answer",
"status":"verified",
"details":"Must reject R=2/W=2 for N=5, apply R+W>N for guaranteed read/write intersection, provide a valid choice such as 3/3, and avoid presenting quorum arithmetic as a complete consistency protocol."
},
"source":{"type":"original"},
"tags":["quorum","replication","read-quorum","write-quorum","consistency"]
},

{
"id":"ce-software-idempotency-key-000328",
"version":1,
"split":"train",
"domain":"software-engineering",
"subdomain":"api-reliability",
"task_type":"design",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A payment API client times out after sending a charge request. It cannot tell whether the
server committed the charge, so retrying may create a duplicate payment.

Design an idempotency-key protocol that lets the client safely retry the logical request.
""")},
{"role":"assistant","content":s("""
The client should assign a stable idempotency key to one logical payment attempt and
reuse that same key for retries of the same request.

On the server, processing should be tied atomically to durable idempotency state:

- if the key has never been seen, record it together with a fingerprint of the request
  and execute/commit the payment under the server's transactional rules;
- if the same key is received again with the same logical request, return the previously
  stored result instead of creating another payment;
- if the same key is reused for materially different parameters, reject it rather than
  silently treating the new request as the old one.

The key record must survive the retry window and should have a defined expiration policy.

The design protects against duplicate effects caused by ambiguous client retries. It does
not make every downstream side effect automatically idempotent; the server must place the
idempotency boundary around the operation whose duplication it is preventing.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must require one stable key per logical request, durable server-side deduplication/result replay, request-parameter binding, and explicit handling of retries without claiming all downstream effects become idempotent automatically."
},
"source":{"type":"original"},
"tags":["idempotency-key","payments","retry","api","deduplication"]
},

{
"id":"ce-compute-gradient-accumulation-000329",
"version":1,
"split":"train",
"domain":"compute-model-infrastructure",
"subdomain":"training-memory",
"task_type":"performance-analysis",
"difficulty":"advanced",
"messages":[
{"role":"user","content":s("""
A model does not fit the desired global batch size in GPU memory. An engineer proposes
using gradient accumulation over four microbatches and claims this is always identical
to training with one batch four times larger.

Explain when the approximation is valid and name important reasons the two runs can
still differ.
""")},
{"role":"assistant","content":s("""
Gradient accumulation can reproduce the same accumulated gradient as a larger batch when
the per-example computation is otherwise equivalent and gradients are scaled correctly.
A common pattern is to divide each microbatch loss by the accumulation count, accumulate
gradients, then perform one optimizer step after all microbatches.

However, the training runs are not guaranteed to be identical.

Differences can come from:

- layers whose behavior depends on microbatch statistics, such as ordinary BatchNorm;
- dropout and other random-number consumption changing with execution order;
- optimizer schedules or counters being advanced per microbatch instead of per optimizer
  step;
- gradient clipping being applied at the wrong time;
- mixed-precision overflow/loss-scaling behavior;
- numerical roundoff from a different accumulation order;
- data-order or distributed-synchronization differences.

So accumulation is primarily a memory technique for approximating a larger effective
batch. Correct implementation requires defining what happens per microbatch versus per
optimizer step.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must explain loss/gradient scaling and one optimizer step after accumulation, while noting non-equivalence sources such as batch-dependent layers, RNG, schedule/step semantics, clipping, mixed precision, or floating-point order."
},
"source":{"type":"original"},
"tags":["gradient-accumulation","batch-size","training","gpu-memory","optimizer"]
},

{
"id":"ce-security-seccomp-pathname-limit-000330",
"version":1,
"split":"train",
"domain":"secure-engineering",
"subdomain":"sandboxing",
"task_type":"technical-decision",
"difficulty":"expert",
"messages":[
{"role":"user","content":s("""
A Linux sandbox designer wants a seccomp filter that allows `openat()` only when the
pathname begins with `/srv/app/data/` and denies other paths.

Can classic seccomp-BPF enforce this pathname policy directly? Explain the limitation
and propose a safer architecture.
""")},
{"role":"assistant","content":s("""
Classic seccomp-BPF can filter system-call numbers and scalar argument values, but it
cannot safely dereference an arbitrary user-space pointer to inspect the pathname string
passed to `openat()`.

The filter can see the pointer value, not reliably interpret the pointed-to path as a
string policy input. Even a hypothetical separate pathname check would face races and
filesystem-resolution issues if the path were later resolved differently.

A safer design combines seccomp with mechanisms that constrain filesystem authority
itself, for example:

- place the process in a mount namespace exposing only the files it should access;
- pass already-open directory/file descriptors as capabilities;
- use descriptor-relative APIs and constrained resolution such as `openat2()` with
  suitable `RESOLVE_*` restrictions in a trusted broker;
- move pathname-sensitive policy into a broker process that performs the actual open and
  returns approved descriptors.

Then seccomp can restrict which syscalls and descriptor operations the sandboxed process
may perform, while pathname/filesystem policy is enforced by mechanisms designed to
control resolution and object access.
""")}
],
"verification":{
"method":"rubric",
"status":"verified",
"details":"Must state that seccomp-BPF cannot safely dereference pathname pointers for string-prefix policy, explain the pointer/path-resolution limitation, and propose authority-based filesystem restriction or a trusted broker rather than pathname inspection in seccomp."
},
"source":{"type":"original"},
"tags":["seccomp","sandbox","openat","path-resolution","linux-security"]
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
    "batch": "003",
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

python3 -m json.tool configs/dataset-v0.2-batch-003.json >/dev/null \
  && echo "Batch plan: VALID JSON"

python3 scripts/validate_dataset.py \
  data/staging/v0.2/batch-003.jsonl
