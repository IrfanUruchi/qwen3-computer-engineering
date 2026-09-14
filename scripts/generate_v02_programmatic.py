#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "dataset-v0.2-programmatic.json"
STAGING = ROOT / "data" / "staging" / "v0.2"
RAW_V01 = ROOT / "data" / "raw" / "v0.1"

def rec(rid, domain, subdomain, task_type, difficulty, q, a, method, details, tags):
    return {
        "id": rid,
        "version": 1,
        "split": "train",
        "domain": domain,
        "subdomain": subdomain,
        "task_type": task_type,
        "difficulty": difficulty,
        "messages": [
            {"role": "user", "content": q.strip()},
            {"role": "assistant", "content": a.strip()},
        ],
        "verification": {
            "method": method,
            "status": "verified",
            "details": details.strip(),
        },
        "source": {"type": "original"},
        "tags": tags,
    }

def load_jsonl(path: Path):
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out

def scan_existing():
    rows = []
    for base in (RAW_V01, STAGING):
        if not base.exists():
            continue
        for p in sorted(base.glob("*.jsonl")):
            if p.name.startswith("."):
                continue
            rows.extend(load_jsonl(p))
    return rows

def next_id_num(rows):
    nums = []
    for r in rows:
        m = re.search(r"-(\d{6})$", r.get("id", ""))
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=300) + 1

def next_batch_num():
    nums = []
    for p in STAGING.glob("batch-*.jsonl"):
        m = re.fullmatch(r"batch-(\d+)\.jsonl", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1

def domain_counts_v02():
    c = Counter()
    for p in sorted(STAGING.glob("batch-*.jsonl")):
        for r in load_jsonl(p):
            c[r["domain"]] += 1
    return c

def fmt(x, digits=2):
    s = f"{x:.{digits}f}"
    return s.rstrip("0").rstrip(".")

# ---------------------------------------------------------------------
# Domain generators. Pure Python: parameters -> exact answer.
# No external model/API is used.
# ---------------------------------------------------------------------

def gen_software(rng, rid, i):
    fam = i % 3
    if fam == 0:
        workers = rng.choice([8, 12, 16, 24])
        rate = rng.choice([35, 40, 50, 60])
        service_ms = rng.choice([120, 150, 180, 200])
        capacity = workers * (1000.0 / service_ms)
        util = rate / capacity
        q = f"""
A service has a fixed worker pool of {workers} threads. Each request occupies one worker
for an average of {service_ms} ms while waiting on a downstream dependency. Incoming
traffic is {rate} requests/s. The input queue is currently unbounded.

Estimate worker capacity and utilization, then explain why an unbounded queue is a poor
failure mode when the downstream service slows further. Propose a bounded-backpressure
design.
"""
        a = f"""
Ignoring other overhead, one worker can complete about 1000/{service_ms} =
{fmt(1000/service_ms)} requests/s, so {workers} workers provide roughly
{fmt(capacity)} requests/s.

At {rate} requests/s, nominal utilization is approximately
{rate}/{fmt(capacity)} = {fmt(util*100,1)}%.

Even if this load is currently below nominal capacity, an unbounded queue is dangerous:
when the downstream dependency slows, worker service time increases, capacity drops, and
queued requests can grow without a useful upper bound. That converts a dependency
slowdown into rising memory use and very long tail latency.

A safer design bounds both concurrency and queued work. When the queue is full, reject,
shed, or push back according to the API contract rather than accepting unlimited work.
Requests should also carry deadlines/cancellation so stale queued work is not processed
after it has lost value.

The exact queue size should come from latency and burst requirements, not from the
average-rate calculation alone.
"""
        return rec(rid,"software-engineering","backpressure","performance-analysis","advanced",
                   q,a,"reference-answer",
                   "Capacity must be workers*(1000/service_ms); utilization must be arrival_rate/capacity. Answer must explain slowdown-induced queue growth and use bounded admission/backpressure rather than an unbounded queue.",
                   ["backpressure","worker-pool","queue","capacity","latency"])
    if fam == 1:
        refill = rng.choice([20, 25, 40])
        burst = rng.choice([50, 80, 100])
        request_burst = rng.choice([120, 150, 180])
        time_to_refill = max(0, (request_burst-burst)/refill)
        q = f"""
An API uses a token-bucket limiter with a refill rate of {refill} tokens/s and a bucket
capacity of {burst} tokens. The bucket is initially full. A client sends a burst of
{request_burst} requests at once and each request costs one token.

How many requests can pass immediately, and how long would it take to accumulate enough
new tokens for the remaining requests if no other traffic arrives? Explain what the
bucket capacity controls versus what the refill rate controls.
"""
        a = f"""
The initially full bucket contains {burst} tokens, so {burst} requests can pass
immediately.

The remaining request count is:

{request_burst} - {burst} = {request_burst-burst}.

At {refill} tokens/s, accumulating that many replacement tokens takes:

({request_burst-burst}) / {refill} = {fmt(time_to_refill)} s.

So the immediate burst allowance is {burst} requests, while the sustained long-run rate
is controlled by the {refill}-token/s refill rate.

Bucket capacity controls how much short-term burstiness can be absorbed. The refill rate
controls how quickly permission is regenerated and therefore the sustainable average
rate. A production limiter also needs a defined policy for excess requests, clock
handling, and distributed coordination if multiple independent limiters share one
logical quota.
"""
        return rec(rid,"software-engineering","rate-limiting","performance-analysis","advanced",
                   q,a,"reference-answer",
                   "Must compute immediate allowance as bucket capacity, remaining requests as burst minus capacity, refill time as remaining/refill_rate, and distinguish burst capacity from sustained rate.",
                   ["token-bucket","rate-limit","burst","capacity","api"])
    pool = rng.choice([20, 30, 40])
    active = rng.choice([16, 24, 32])
    if active >= pool:
        active = pool - 4
    reserve = pool-active
    q = f"""
A web service has a database connection pool of {pool} connections. During normal load,
{active} are already in use. A new feature performs fan-out work and can start 12
additional database operations concurrently per request.

Explain why simply allowing every request to launch all 12 operations can create a
self-inflicted outage. State the current connection headroom and propose a safer
concurrency design.
"""
    a = f"""
The pool currently has:

{pool} - {active} = {reserve}

unused connections.

A single request that tries to start 12 database operations concurrently can consume
more than that headroom, and several such requests can quickly make every connection
busy. Other requests then wait for the pool, hold application resources while waiting,
and can trigger a positive feedback loop of timeouts and retries.

The safer design is to bound database concurrency independently of request fan-out.
Use a semaphore, work queue, or bulkhead sized from measured database capacity and leave
headroom for unrelated traffic. Fan-out can still be expressed logically, but only a
bounded number of database operations should be active at once.

Pool size is not itself a throughput target: increasing it blindly can move the
bottleneck into the database and make contention worse. Measure query latency,
connection wait time, database CPU/I/O saturation, and timeout behavior when selecting
the bound.
"""
    return rec(rid,"software-engineering","connection-pools","architecture-analysis","advanced",
               q,a,"reference-answer",
               f"Must compute connection headroom as {reserve}, explain pool exhaustion from unbounded fan-out, and propose a separate concurrency bound/bulkhead rather than blindly increasing the pool.",
               ["connection-pool","bulkhead","database","fan-out","concurrency"])

def gen_systems(rng, rid, i):
    fam = i % 3
    if fam == 0:
        total = rng.choice([65536, 131072, 262144])
        first = rng.choice([8192, 16384, 32768])
        remain = total-first
        q = f"""
A nonblocking socket must send a {total}-byte application frame. The first `send()`
returns {first}. The current code treats any positive return as if the whole frame was
sent and reuses the buffer.

Explain the bug and give the correct progress-tracking rule for the remaining data.
"""
        a = f"""
A positive return from `send()` reports the number of bytes accepted from this call, not
completion of the entire application frame.

After the first call, progress is {first} bytes and the unsent suffix is:

{total} - {first} = {remain} bytes.

The application must retain the buffer, advance an offset by each positive return, and
retry only the unsent suffix. On a nonblocking socket, `EAGAIN`/`EWOULDBLOCK` means stop
for now and wait for writable readiness. `EINTR` should be handled according to the
operation's retry policy, while other errors terminate or fail the connection.

The buffer cannot be reused or freed until the application has accounted for all
{total} bytes or abandoned the frame.

Reissuing the original pointer/length after a partial send can duplicate bytes; assuming
the first positive return completed the frame can drop the unsent suffix.
"""
        return rec(rid,"systems-programming","nonblocking-io","code-repair","advanced",
                   q,a,"reference-answer",
                   f"Must compute {remain} bytes remaining, advance pointer/offset after partial sends, retain buffer ownership, and handle EAGAIN without resending already accepted bytes.",
                   ["send","partial-write","nonblocking","socket","buffer-lifetime"])
    if fam == 1:
        offset = rng.choice([4096, 8192, 16384])
        readn = rng.choice([512,1024,2048])
        q = f"""
A process opens a file and then calls `dup()` to create a second descriptor. It seeks the
first descriptor to byte offset {offset}. Another thread reads {readn} bytes through the
duplicated descriptor and is surprised that the first descriptor's current offset also
moves.

Explain the behavior and give a design for independent offsets.
"""
        a = f"""
`dup()` creates another file descriptor referring to the same open file description.
The descriptors therefore share state stored in that open file description, including
the current file offset.

After the seek sets the shared offset to {offset}, a successful {readn}-byte read through
the duplicate advances the shared offset to approximately {offset + readn}, so subsequent
offset-relative I/O through either descriptor observes that progress.

If independent offsets are required, open the file separately so each `open()` creates
its own open file description, or use positional I/O such as `pread()`/`pwrite()` when
the operation should specify an explicit offset without changing the shared file
position.

Duplicating the descriptor number is not equivalent to independently reopening the
file.
"""
        return rec(rid,"systems-programming","file-descriptors","explanation","advanced",
                   q,a,"reference-answer",
                   f"Must state that dup shares the open file description/current offset and that the read advances it to about {offset+readn}; independent open descriptions or positional I/O are valid fixes.",
                   ["dup","file-offset","open-file-description","pread","file-descriptor"])
    width = rng.choice([16,32,64])
    value = rng.choice([0x1234,0x12345678,0x01020304])
    nbytes = width//8
    q = f"""
A binary protocol stores an unsigned {width}-bit integer in network byte order. A parser
currently casts a pointer into the receive buffer to `uint{width}_t*` and dereferences
it directly.

Explain two portability/correctness problems with that approach and describe a safe
decode strategy for a {nbytes}-byte field.
"""
    a = f"""
Directly casting the byte-buffer address to `uint{width}_t*` is unsafe for at least two
reasons.

First, the field may not be naturally aligned for a {width}-bit load on the target.
Second, the host's native byte order may differ from the protocol's network byte order.
Depending on the language/compiler rules, pointer aliasing can be another concern.

A safe parser first verifies that at least {nbytes} bytes remain in the message, then
decodes the field without assuming alignment. For example it can copy the bytes into a
properly aligned integer object and apply the appropriate network-to-host conversion, or
assemble the value byte-by-byte with shifts.

The bounds check must happen before reading the field. The parser should advance its
cursor only after the field has been decoded successfully.

Protocol layout is defined by bytes, not by the host C struct layout or the alignment
properties of the receive buffer.
"""
    return rec(rid,"systems-programming","binary-parsing","code-repair","advanced",
               q,a,"rubric",
               "Must identify alignment and endianness problems, require a length check before access, and recommend memcpy plus byte-order conversion or explicit byte assembly rather than unaligned pointer dereference.",
               ["binary-protocol","endianness","alignment","parsing","network-byte-order"])

def gen_os(rng, rid, i):
    fam = i % 3
    if fam == 0:
        entries = rng.choice([64,128,256])
        page_kib = rng.choice([4,16,64])
        coverage_mib = entries*page_kib/1024
        q = f"""
A CPU has a TLB that can hold {entries} translations for a process. Assume the workload
uses {page_kib} KiB pages and ignore multiple page sizes or associativity effects.

What is the maximum memory coverage represented by those TLB entries at one time? Why
can a sequential scan much larger than that still suffer frequent TLB misses even when
the data cache behaves reasonably?
"""
        a = f"""
Each entry covers one {page_kib} KiB page, so total TLB coverage is:

{entries} × {page_kib} KiB = {entries*page_kib} KiB = {fmt(coverage_mib)} MiB.

A sequential working set substantially larger than that translation footprint can
continually evict older translations. The data itself may stream efficiently through
the cache hierarchy, but address translation is a separate resource: each newly touched
page can require a TLB fill and potentially a page-table walk.

This is one reason huge pages can help some large-memory workloads: each translation
covers more bytes. Whether they help overall still requires measurement because page
size also affects fragmentation, allocation behavior, NUMA placement, and other memory
management costs.
"""
        return rec(rid,"operating-systems","virtual-memory","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"TLB coverage must be {entries*page_kib} KiB = {fmt(coverage_mib)} MiB and the explanation must separate translation locality from data-cache locality.",
                   ["tlb","page-size","virtual-memory","page-walk","working-set"])
    if fam == 1:
        ram_gib = rng.choice([16,32,64])
        parent_gib = rng.choice([4,8,12])
        dirty_pct = rng.choice([10,25,40])
        copied = parent_gib*dirty_pct/100
        q = f"""
A process has {parent_gib} GiB of private anonymous memory in use and then calls `fork()`.
Soon afterward, the child writes to {dirty_pct}% of those pages while the parent keeps
its original contents.

Ignoring page tables and allocator overhead, approximately how much additional physical
memory is created by copy-on-write? Explain why `fork()` does not immediately duplicate
all {parent_gib} GiB.
"""
        a = f"""
Immediately after `fork()`, parent and child can share the same physical pages while
their page-table mappings are marked for copy-on-write.

The child modifies {dirty_pct}% of {parent_gib} GiB:

{parent_gib} GiB × {dirty_pct/100:.2f} = {fmt(copied)} GiB.

So, under the stated assumptions, approximately {fmt(copied)} GiB of additional physical
page data is created for the modified subset.

`fork()` does not need to eagerly copy all {parent_gib} GiB because unmodified pages can
remain shared. A private copy is allocated when a process first writes a shared
copy-on-write page.

Real memory usage also includes page tables, allocator behavior, pages changed by both
processes, shared mappings, kernel metadata, and possible reclaim, so the calculation is
an intentionally simplified estimate.
"""
        return rec(rid,"operating-systems","copy-on-write","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Additional data memory must be approximately {fmt(copied)} GiB, derived from {parent_gib} GiB × {dirty_pct}%, and answer must explain lazy COW copying on write.",
                   ["fork","copy-on-write","memory","page-fault","process"])
    fault_us = rng.choice([80,120,250])
    faults = rng.choice([2000,5000,10000])
    seconds = fault_us*faults/1_000_000
    q = f"""
A workload triggers {faults} major page faults during a short phase. Storage and kernel
measurements show an average service cost of about {fault_us} microseconds per major
fault.

Ignoring overlap, estimate the direct stall time attributable to those faults. Why is
the estimate only a first-order bound for real wall-clock impact?
"""
    a = f"""
The first-order serialized stall estimate is:

{faults} × {fault_us} microseconds = {faults*fault_us:,} microseconds
= {fmt(seconds,3)} seconds.

So the direct fault-service time is about {fmt(seconds,3)} s if those stalls do not
overlap with useful execution.

Real wall-clock impact can differ because I/O may overlap, multiple threads can run,
storage service times have a distribution rather than one fixed value, readahead can
change future faults, scheduler delays can add cost, and page reclaim may create
additional work.

The calculation is therefore useful for checking order of magnitude, while profiler and
fault-latency distributions are needed to explain the actual end-to-end slowdown.
"""
    return rec(rid,"operating-systems","page-faults","performance-analysis","advanced",
               q,a,"reference-answer",
               f"Serialized estimate must be {fmt(seconds,3)} seconds from fault_count × average_fault_latency, with caveats about overlap, scheduling and latency distribution.",
               ["major-page-fault","latency","virtual-memory","profiling","io"])

def gen_arch(rng, rid, i):
    fam = i % 3
    if fam == 0:
        hit = rng.choice([1,2,3])
        miss_rate = rng.choice([0.02,0.05,0.08])
        penalty = rng.choice([60,80,120])
        amat = hit + miss_rate*penalty
        q = f"""
A cache has a {hit}-cycle hit time, a {miss_rate*100:.0f}% miss rate, and an additional
{penalty}-cycle miss penalty. Using the simple one-level AMAT model, compute average
memory-access time. Which term would you try to reduce first if profiling shows the miss
penalty is dominated by off-chip memory latency?
"""
        a = f"""
For the simple model:

AMAT = hit time + miss rate × miss penalty

= {hit} + {miss_rate:.2f} × {penalty}
= {fmt(amat)} cycles.

So the estimated average access time is {fmt(amat)} cycles.

If off-chip latency dominates the miss penalty, reducing miss frequency can be highly
valuable because every avoided miss removes exposure to that large penalty. Possible
work depends on the workload: improve locality, data layout, blocking, or cache
utilization before assuming a larger cache alone is the answer.

The model is deliberately simplified. Real systems can overlap misses, have multiple
cache levels, prefetching, memory-level parallelism, and variable latency, so hardware
counter/profiler evidence should guide the optimization.
"""
        return rec(rid,"computer-architecture","cache-performance","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"AMAT must equal {fmt(amat)} cycles using hit + miss_rate*penalty, and the answer should connect a large miss penalty to reducing misses/locality while noting the model's simplifications.",
                   ["cache","amat","miss-rate","memory-latency","performance"])
    if fam == 1:
        base_cpi = rng.choice([0.8,1.0,1.2])
        branch_frac = rng.choice([0.15,0.20,0.25])
        mispred = rng.choice([0.03,0.05,0.08])
        penalty = rng.choice([12,15,18])
        extra = branch_frac*mispred*penalty
        total = base_cpi+extra
        q = f"""
A core has a base CPI of {base_cpi}. Branches are {branch_frac*100:.0f}% of
instructions, {mispred*100:.0f}% of those branches are mispredicted, and each
misprediction costs {penalty} cycles. Using a simple additive model, estimate the CPI
contribution from mispredictions and the resulting CPI.
"""
        a = f"""
The number of mispredictions per instruction is:

{branch_frac:.2f} × {mispred:.2f} = {fmt(branch_frac*mispred,4)}.

Multiplying by the {penalty}-cycle penalty gives an added CPI of:

{fmt(branch_frac*mispred,4)} × {penalty} = {fmt(extra,3)}.

The resulting simplified CPI is:

{base_cpi} + {fmt(extra,3)} = {fmt(total,3)}.

This is an order-of-magnitude model. Real out-of-order cores can overlap some work and
branch behavior can interact with front-end bandwidth, speculation depth, and predictor
state, so measured branch-miss counters and cycles should be used to validate the model.
"""
        return rec(rid,"computer-architecture","branch-prediction","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Added CPI must be branch_fraction*mispredict_rate*penalty = {fmt(extra,3)} and total CPI {fmt(total,3)}.",
                   ["branch-prediction","cpi","misprediction","pipeline","performance"])
    bandwidth = rng.choice([50,80,120])
    bytes_per_item = rng.choice([32,64,96])
    max_items = bandwidth*1e9/bytes_per_item
    q = f"""
A streaming kernel moves {bytes_per_item} bytes from/to memory per processed item and
performs very little computation. Sustained memory bandwidth is measured at
{bandwidth} GB/s.

Ignoring other bottlenecks, what memory-bandwidth ceiling does this imply for item
throughput? Explain why adding more arithmetic units would not raise throughput if this
ceiling is already reached.
"""
    a = f"""
The bandwidth ceiling is:

{bandwidth}×10^9 bytes/s ÷ {bytes_per_item} bytes/item
= {max_items:,.0f} items/s.

That is approximately {fmt(max_items/1e9,3)} billion items/s.

If profiling shows the kernel already consumes the available memory bandwidth, extra
arithmetic throughput does not supply more bytes to the execution units. The kernel is
memory-bandwidth bound, so optimization should reduce bytes moved per item, improve
locality/reuse, compress representation where appropriate, or increase effective memory
bandwidth.

The calculation assumes the measured {bandwidth} GB/s is sustainable for this access
pattern; irregular accesses, protocol overhead, NUMA placement, and cache behavior can
lower the actual ceiling.
"""
    return rec(rid,"computer-architecture","memory-bandwidth","performance-analysis","advanced",
               q,a,"reference-answer",
               f"Throughput ceiling must be {max_items:,.0f} items/s from bandwidth/bytes_per_item and answer must identify the memory-bandwidth bottleneck.",
               ["memory-bandwidth","roofline","throughput","streaming","bottleneck"])

def gen_linux(rng, rid, i):
    fam = i % 3
    if fam == 0:
        quota_us = rng.choice([50000,100000,150000])
        period_us = rng.choice([100000,200000])
        cores = quota_us/period_us
        q = f"""
A cgroup v2 has `cpu.max` configured as `{quota_us} {period_us}`. Ignoring burst effects
and other scheduling constraints, what average CPU capacity does that quota represent in
CPU-core equivalents? What symptom would you expect if a latency-sensitive service
needs more CPU than that for sustained periods?
"""
        a = f"""
The average CPU allowance is the quota divided by the period:

{quota_us} / {period_us} = {fmt(cores)} CPU-core equivalents.

For example, {fmt(cores)} means the group can consume that fraction/multiple of one CPU
on average across each quota period, even if its threads could otherwise run on more
cores.

If sustained demand exceeds the allowance, the cgroup can be throttled after exhausting
its quota for the current period. A latency-sensitive service may therefore show bursts
of runnable work followed by throttling and elevated tail latency.

Verification should inspect cgroup CPU statistics, including throttling counters/time,
alongside scheduler and application latency measurements. CPU affinity and CPU quota are
different controls: affinity chooses where work may run; quota limits how much CPU time
the cgroup may consume.
"""
        return rec(rid,"linux-infrastructure","cgroup-v2","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"CPU capacity must be quota/period = {fmt(cores)} core equivalents, with throttling identified as a likely symptom when sustained demand exceeds quota.",
                   ["cgroup-v2","cpu.max","throttling","cpu-quota","latency"])
    if fam == 1:
        limit = rng.choice([1024,4096,8192])
        baseline = rng.choice([300,700,1200])
        per_client = rng.choice([2,3,4])
        clients = max(1,(limit-baseline)//per_client)
        q = f"""
A Linux service has an effective file-descriptor limit of {limit}. It normally consumes
about {baseline} descriptors before accepting clients, and each connected client uses
approximately {per_client} descriptors across sockets/files/pipes.

Ignoring safety margin, roughly how many such clients fit before descriptor exhaustion?
Why should production admission stop below that arithmetic maximum?
"""
        a = f"""
Descriptor headroom is:

{limit} - {baseline} = {limit-baseline} descriptors.

At about {per_client} descriptors per client, the arithmetic ceiling is:

floor(({limit} - {baseline}) / {per_client}) = {clients} clients.

Production admission should stop below that number because descriptor use is not
perfectly constant. Logging, DNS, temporary files, monitoring, accepted-but-not-yet-
accounted sockets, and transient operations also consume descriptors. Hitting the hard
limit can prevent the service from opening resources needed to report or recover from
the failure.

Measure actual descriptor usage and reserve operational headroom rather than treating
{clients} as a safe configured capacity.
"""
        return rec(rid,"linux-infrastructure","resource-limits","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Arithmetic ceiling must be floor(({limit}-{baseline})/{per_client}) = {clients}, with explicit operational headroom below RLIMIT_NOFILE.",
                   ["rlimit","file-descriptor","capacity","linux","resource-exhaustion"])
    inode_total = rng.choice([100000,250000,500000])
    inode_used = rng.choice([90000,225000,450000])
    free = inode_total-inode_used
    q = f"""
A filesystem reports plenty of free bytes, but it has {inode_total:,} total inodes and
{inode_used:,} are already in use. A workload creates many tiny files and starts failing
with `ENOSPC`.

How many inodes remain, and why can `ENOSPC` occur even when byte capacity is available?
What should operations monitor?
"""
    a = f"""
Remaining inode capacity is:

{inode_total:,} - {inode_used:,} = {free:,} inodes.

A traditional filesystem needs both data blocks and an inode (or equivalent metadata
object) for each file. A workload with huge numbers of tiny files can exhaust available
inodes before exhausting byte storage. Once the filesystem cannot allocate metadata for
another file, file creation can fail with `ENOSPC` even though `df` still shows free
bytes.

Operations should monitor both byte usage and inode usage, plus the file-count growth
pattern. Remediation may require deleting/compacting tiny files, redesigning storage
layout, or creating/reformatting a filesystem with metadata sizing appropriate to the
workload.

Free bytes and free file metadata are separate capacity dimensions.
"""
    return rec(rid,"linux-infrastructure","filesystem-capacity","troubleshooting","advanced",
               q,a,"reference-answer",
               f"Remaining inodes must be {free:,}; answer must explain inode exhaustion as independent from byte-space exhaustion and recommend monitoring both.",
               ["inode","ENOSPC","filesystem","capacity","tiny-files"])

def gen_embedded(rng, rid, i):
    fam = i % 3
    if fam == 0:
        bits = rng.choice([12,14,16])
        vref = rng.choice([3.3,2.5,1.8])
        lsb = vref/(2**bits-1)
        q = f"""
An ideal {bits}-bit ADC uses a {vref} V reference and returns unsigned codes from 0 to
{2**bits-1}. Approximately what input-voltage step corresponds to one LSB? Why is that
number not the same as guaranteed measurement accuracy on real hardware?
"""
        a = f"""
The ideal code step is approximately:

{vref} V / ({2**bits} - 1) = {lsb:.8f} V

which is about {lsb*1000:.4f} mV per LSB.

That is quantization resolution, not guaranteed absolute accuracy. Real measurements can
also include reference tolerance/noise, ADC offset and gain error, integral/differential
nonlinearity, input source impedance effects, PCB noise, temperature drift, and sampling
settling error.

So one LSB describes the ideal spacing between adjacent codes. Accuracy must be taken
from the ADC/reference specifications and validated in the actual analog design.
"""
        return rec(rid,"embedded-systems","adc","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Ideal LSB must be Vref/(2^bits-1) = {lsb:.8f} V and answer must distinguish resolution from real measurement accuracy.",
                   ["adc","quantization","lsb","vref","embedded"])
    if fam == 1:
        freq = rng.choice([48_000_000,72_000_000,80_000_000])
        desired = rng.choice([115200,230400,460800])
        oversample = 16
        div = round(freq/(oversample*desired))
        actual = freq/(oversample*div)
        err = (actual-desired)/desired*100
        q = f"""
A UART peripheral derives baud rate as `clock / (16 * divisor)`. The peripheral clock is
{freq/1e6:.0f} MHz and the desired baud rate is {desired} bit/s. Using the nearest
integer divisor, compute the divisor, actual baud rate, and percentage error.
"""
        a = f"""
The ideal divisor is:

{freq} / (16 × {desired}) = {freq/(16*desired):.4f}.

The nearest integer divisor is {div}.

Actual baud rate:

{freq} / (16 × {div}) = {actual:.2f} bit/s.

Percentage error relative to {desired} bit/s is:

({actual:.2f} - {desired}) / {desired} × 100 = {err:.3f}%.

Whether that error is acceptable depends on the UARTs at both ends, oscillator tolerance,
sampling design, and accumulated timing margin. The arithmetic establishes the local
baud error but does not by itself prove reliable communication.
"""
        return rec(rid,"embedded-systems","uart","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Nearest divisor must be {div}, actual baud about {actual:.2f}, error about {err:.3f}%.",
                   ["uart","baud-rate","clock-divider","serial","embedded"])
    writes_per_day = rng.choice([100,500,1000])
    endurance = rng.choice([10000,100000])
    slots = rng.choice([16,32,64])
    days_single = endurance/writes_per_day
    days_wl = endurance*slots/writes_per_day
    q = f"""
A flash page is rated for {endurance:,} erase/program cycles. Firmware updates one
persistent counter about {writes_per_day} times per day.

Estimate lifetime if every update rewrites the same erase unit. Then estimate the ideal
upper bound if wear is perfectly distributed across {slots} equivalent slots. Why is the
second number only an upper bound?
"""
    a = f"""
Without wear leveling, the simple lifetime estimate is:

{endurance:,} / {writes_per_day} = {fmt(days_single,1)} days.

If wear were distributed perfectly across {slots} equivalent slots, the idealized cycle
budget becomes {endurance:,} × {slots}, giving:

({endurance:,} × {slots}) / {writes_per_day}
= {fmt(days_wl,1)} days.

That second result is only an upper bound. Real designs need metadata, valid-record
selection, power-loss-safe updates, erase-block granularity, uneven access, bad blocks,
temperature effects, and safety margin. A robust implementation commonly uses a
journal/ring of versioned records with integrity checks rather than repeatedly rewriting
one location.
"""
    return rec(rid,"embedded-systems","flash-endurance","architecture-analysis","advanced",
               q,a,"reference-answer",
               f"Single-location estimate must be {fmt(days_single,1)} days; perfect {slots}-slot distribution gives ideal {fmt(days_wl,1)} days, with real wear-leveling/power-loss caveats.",
               ["flash","wear-leveling","endurance","persistent-state","embedded"])

def gen_network(rng, rid, i):
    fam = i % 3
    if fam == 0:
        bandwidth_mbps = rng.choice([100,500,1000])
        rtt_ms = rng.choice([20,50,80])
        bdp_bytes = bandwidth_mbps*1e6*(rtt_ms/1000)/8
        q = f"""
A TCP path has {bandwidth_mbps} Mbit/s available bandwidth and {rtt_ms} ms round-trip
time. Ignoring protocol overhead and loss, compute the bandwidth-delay product in bytes
and MiB. Why can a sender with a much smaller effective window fail to fill the link?
"""
        a = f"""
Bandwidth-delay product is bandwidth multiplied by round-trip time:

{bandwidth_mbps}×10^6 bit/s × {rtt_ms/1000:.3f} s
= {bandwidth_mbps*1e6*(rtt_ms/1000):,.0f} bits.

Dividing by 8 gives {bdp_bytes:,.0f} bytes, or approximately
{fmt(bdp_bytes/(1024**2),3)} MiB.

That is roughly the amount of data that must be in flight to keep the path fully
occupied under the simplified assumptions. If the congestion/receive window limits
in-flight data to much less than this, the sender can become window-limited and wait
for acknowledgements before enough data is outstanding to use the path's full bandwidth.

Actual TCP throughput also depends on congestion control, loss, ACK behavior, kernel
buffering, and application delivery, so the BDP is a sizing guide rather than a
guarantee.
"""
        return rec(rid,"networking","tcp-performance","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"BDP must be {bdp_bytes:,.0f} bytes = {fmt(bdp_bytes/(1024**2),3)} MiB and explanation must connect insufficient in-flight window to underutilization.",
                   ["tcp","bdp","window","rtt","bandwidth"])
    if fam == 1:
        outer_mtu = rng.choice([1500,9000])
        overhead = rng.choice([50,74,98])
        inner = outer_mtu-overhead
        q = f"""
A tunnel runs over a link with MTU {outer_mtu} bytes. Encapsulation adds {overhead} bytes
per packet before the packet is placed on that link.

Ignoring optional headers, what maximum inner-packet size avoids exceeding the outer MTU?
Why must TCP MSS or interface MTU account for this overhead?
"""
        a = f"""
The maximum inner packet size under the stated assumptions is:

{outer_mtu} - {overhead} = {inner} bytes.

If an inner endpoint emits packets sized to the full {outer_mtu}-byte physical MTU, the
tunnel adds another {overhead} bytes and creates an outer packet that is too large for
the link. Depending on protocol and path behavior this can require fragmentation or
trigger packet-too-big handling; if feedback is broken it can contribute to an MTU
black hole.

The tunnel interface MTU or TCP MSS should therefore reflect the encapsulation overhead
so ordinary traffic is sized to fit after the outer headers are added.
"""
        return rec(rid,"networking","tunneling","configuration","advanced",
                   q,a,"reference-answer",
                   f"Maximum inner size must be {inner} bytes from outer_mtu-overhead and answer must connect tunnel overhead to interface MTU/MSS sizing.",
                   ["mtu","tunnel","mss","encapsulation","networking"])
    ports = rng.choice([20000,30000,50000])
    dests = rng.choice([1,2,4])
    conns = ports*dests
    q = f"""
A NAT gateway has approximately {ports:,} usable translated source ports per public
address for connections to one fixed destination tuple. Traffic is evenly spread across
{dests} distinct destination IP/port tuples.

Ignoring timeouts and implementation reservations, what rough concurrent-connection
tuple capacity does that provide per public source address? Why is this only a rough
planning number?
"""
    a = f"""
Under the simplified assumptions, each destination tuple can use roughly {ports:,}
translated source-port values independently.

Across {dests} destination tuples, the rough tuple capacity is:

{ports:,} × {dests} = {conns:,} concurrent mappings per public source address.

It is only a planning number because real NAT implementations reserve ports, apply
mapping policies, retain state after flows close, handle multiple protocols, may hash
or partition port ranges, and can have memory/CPU limits before the theoretical tuple
space is exhausted.

Measure actual NAT state usage and allocation failures rather than operating exactly at
the arithmetic ceiling.
"""
    return rec(rid,"networking","nat","performance-analysis","advanced",
               q,a,"reference-answer",
               f"Rough capacity must be {conns:,} mappings from usable_ports × destination_tuples, with caveats about state retention/reservations/implementation limits.",
               ["nat","ports","connection-tracking","capacity","networking"])

def gen_distributed(rng, rid, i):
    fam = i % 2
    if fam == 0:
        replicas = rng.choice([3,5,7])
        p = rng.choice([0.98,0.99,0.995])
        majority = replicas//2+1
        # Binomial probability at least majority available
        avail = sum(math.comb(replicas,k)*(p**k)*((1-p)**(replicas-k)) for k in range(majority,replicas+1))
        q = f"""
A replicated service has {replicas} independent replicas. Assume each replica is
available with probability {p:.3f} at a randomly chosen instant and the service needs a
majority ({majority} replicas) to make progress.

Under the independence assumption, compute the probability that a majority is available.
Why should this not be presented as the real production availability without qualification?
"""
        a = f"""
The probability of at least {majority} available replicas is the binomial sum:

sum from k={majority} to {replicas} of
C({replicas}, k) * {p:.3f}^k * (1-{p:.3f})^({replicas}-k).

Evaluating that gives approximately {avail:.8f}, or {avail*100:.5f}%.

This is only an idealized estimate because replica failures are rarely fully independent.
Replicas can share power, network paths, software bugs, configuration, deployment events,
control-plane dependencies, and upstream services. Correlated failures can dominate the
tail risk.

The calculation is useful for understanding quorum redundancy, but production
availability should use measured failure modes and fault-domain correlations.
"""
        return rec(rid,"distributed-systems","replication","performance-analysis","expert",
                   q,a,"reference-answer",
                   f"Must compute the binomial probability of at least {majority} available replicas as approximately {avail:.8f} and explicitly qualify the independence assumption.",
                   ["replication","quorum","availability","probability","fault-domain"])
    nodes = rng.choice([4,5,8,10])
    moved = 1/(nodes+1)
    q = f"""
A consistent-hashing system has {nodes} equally loaded storage nodes with many virtual
nodes. One equally capable node is added.

Under the ideal uniform-hashing approximation, what fraction of keys should move to the
new node? Contrast this with a simple modulo-based `hash(key) % N` scheme.
"""
    a = f"""
With ideal consistent hashing and balanced virtual nodes, the new cluster has
{nodes+1} equal shares. The newly added node should therefore acquire approximately:

1 / {nodes+1} = {fmt(moved*100,2)}%

of the keyspace, so roughly that fraction of keys move.

With simple modulo hashing, changing N from {nodes} to {nodes+1} changes the modulus for
most hash values, so a large fraction of keys can map to different nodes.

The exact movement in a real consistent-hash ring depends on token placement, virtual
node count, weighting, and replication policy, but the key property is that membership
changes affect a limited portion of the keyspace rather than remapping nearly everything.
"""
    return rec(rid,"distributed-systems","consistent-hashing","comparison","advanced",
               q,a,"reference-answer",
               f"Ideal moved fraction must be 1/{nodes+1} = {fmt(moved*100,2)}%, with contrast to broad modulo remapping.",
               ["consistent-hashing","sharding","rebalance","virtual-nodes","distributed"])

def gen_compute(rng, rid, i):
    fam = i % 2
    if fam == 0:
        layers = rng.choice([24,32,40])
        heads = rng.choice([16,24,32])
        head_dim = rng.choice([64,128])
        seq = rng.choice([2048,4096,8192])
        bytes_per = 2
        # K + V
        kv = layers*2*heads*head_dim*seq*bytes_per
        q = f"""
For a transformer inference estimate, assume {layers} layers, {heads} KV heads per layer,
head dimension {head_dim}, sequence length {seq}, batch size 1, and FP16/BF16 KV-cache
elements at 2 bytes each.

Ignoring allocator overhead and cache layout optimizations, estimate total KV-cache
memory for keys plus values.
"""
        a = f"""
Each token stores both a key and a value for every layer and KV head.

Element count:

{layers} layers × 2 (K and V) × {heads} heads × {head_dim} values/head × {seq} tokens
= {layers*2*heads*head_dim*seq:,} elements.

At 2 bytes per element:

{layers*2*heads*head_dim*seq:,} × 2
= {kv:,} bytes
= {fmt(kv/(1024**3),3)} GiB.

So the simplified batch-1 KV-cache estimate is about {fmt(kv/(1024**3),3)} GiB.

Real implementations can differ through grouped-query attention, cache quantization,
padding/alignment, paged cache metadata, batching, and framework-specific layout, so
the estimate should be checked against runtime memory measurements.
"""
        return rec(rid,"compute-model-infrastructure","kv-cache","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"KV cache must be layers*2*heads*head_dim*seq*2 bytes = {kv:,} bytes = {fmt(kv/(1024**3),3)} GiB.",
                   ["kv-cache","transformer","inference","vram","memory"])
    stages = rng.choice([2,4,8])
    micro = rng.choice([4,8,16])
    # simple GPipe efficiency m/(m+s-1)
    eff = micro/(micro+stages-1)
    q = f"""
Use the simple GPipe-style bubble model for a pipeline with {stages} stages and
{micro} microbatches, assuming balanced stage times and ignoring communication.
The idealized pipeline utilization is `m / (m + s - 1)`.

Compute utilization and bubble fraction. What does the model suggest about increasing
microbatch count?
"""
    a = f"""
Using m={micro} microbatches and s={stages} stages:

utilization = m / (m + s - 1)
= {micro} / ({micro} + {stages} - 1)
= {fmt(eff*100,2)}%.

The corresponding bubble fraction is approximately:

1 - {eff:.6f} = {fmt((1-eff)*100,2)}%.

Increasing the number of microbatches reduces the fixed fill/drain bubble fraction in
this simplified model because the useful steady-state portion becomes larger relative to
pipeline startup and drain.

It is not free: more microbatches can change activation memory, scheduling overhead,
kernel efficiency, and communication behavior. Real stage imbalance also reduces
utilization beyond this idealized formula.
"""
    return rec(rid,"compute-model-infrastructure","pipeline-parallelism","performance-analysis","advanced",
               q,a,"reference-answer",
               f"Utilization must be {fmt(eff*100,2)}% and bubble fraction {fmt((1-eff)*100,2)}% using m/(m+s-1).",
               ["pipeline-parallelism","microbatch","bubble","gpu","training"])

def gen_security(rng, rid, i):
    fam = i % 2
    if fam == 0:
        bits = rng.choice([96,128,160])
        guesses = rng.choice([1e9,1e12])
        years = (2**bits/2)/guesses/(60*60*24*365.25)
        q = f"""
A service issues uniformly random {bits}-bit bearer tokens. Assume an attacker can make
{guesses:.0e} online guesses per second with no rate limiting, and use half the keyspace
as the expected brute-force work.

Estimate the expected brute-force time in years. Then explain why token entropy does not
remove the need for rate limiting, secure transport, and careful token storage.
"""
        a = f"""
Expected guesses are approximately 2^({bits}-1).

At {guesses:.0e} guesses/s, the expected time is:

2^({bits}-1) / {guesses:.0e}
≈ {years:.3e} years.

That demonstrates that a uniformly generated {bits}-bit token has an enormous brute-force
search space under the stated assumptions.

Entropy addresses guessing resistance, but bearer-token security also depends on
preventing theft and misuse. Tokens still need TLS in transit, protection from logs and
client-side leakage, appropriate storage, expiry/revocation policy, and rate limiting to
reduce abuse and operational load.

A strong random token that is leaked can usually be used immediately; brute-force
strength does not compensate for exposure.
"""
        return rec(rid,"secure-engineering","token-security","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Expected brute-force time must be approximately {years:.3e} years from 2^(bits-1)/guess_rate, with operational controls still required.",
                   ["token","entropy","brute-force","rate-limit","security"])
    attempts = rng.choice([5,10,20])
    window_min = rng.choice([1,5,15])
    accounts = rng.choice([1000,5000])
    max_guesses = attempts*accounts
    rate = max_guesses/(window_min*60)
    q = f"""
An authentication service permits at most {attempts} failed attempts per account in each
{window_min}-minute window. An attacker targets {accounts:,} distinct accounts.

Ignoring IP/device limits, what aggregate guess rate can the attacker still generate
while staying within the per-account rule? What does this show about relying on only one
rate-limit dimension?
"""
    a = f"""
Across {accounts:,} accounts, the attacker can make:

{attempts} × {accounts:,} = {max_guesses:,}

attempts per {window_min}-minute window.

That is an aggregate rate of:

{max_guesses:,} / ({window_min} × 60)
= {fmt(rate,2)} guesses/s.

So a per-account limit can protect each individual account while still allowing a large
distributed attack across many accounts.

A robust design usually combines dimensions such as account, source/network reputation,
device/session signals, global capacity protection, and adaptive controls. The exact
policy must avoid turning rate limiting into an easy denial-of-service primitive against
legitimate users.
"""
    return rec(rid,"secure-engineering","rate-limiting","architecture-analysis","advanced",
               q,a,"reference-answer",
               f"Aggregate rate must be {fmt(rate,2)} guesses/s from attempts*accounts/window_seconds, and answer must explain multi-dimensional rate limiting.",
               ["authentication","rate-limit","brute-force","account-security","abuse"])

def gen_reasoning(rng, rid, i):
    fam = i % 2
    if fam == 0:
        raw_gb = rng.choice([500,800,1200])
        ratio = rng.choice([2.0,2.5,4.0])
        comp_gb = raw_gb/ratio
        raw_bw = rng.choice([100,200,400])
        comp_bw = rng.choice([100,200,400])
        raw_time = raw_gb*8/raw_bw
        comp_time = comp_gb*8/comp_bw
        q = f"""
A dataset is {raw_gb} GB uncompressed. A compression method reduces size by a factor of
{ratio}x. The uncompressed transfer path sustains {raw_bw} Gbit/s; the compressed path
also sustains {comp_bw} Gbit/s, and compression/decompression CPU cost is negligible for
this estimate.

Compare transfer times and state the time saved.
"""
        a = f"""
Compressed size is:

{raw_gb} GB / {ratio} = {fmt(comp_gb)} GB.

Using 8 bits per byte, uncompressed transfer time is:

{raw_gb} × 8 / {raw_bw} = {fmt(raw_time)} s.

Compressed transfer time is:

{fmt(comp_gb)} × 8 / {comp_bw} = {fmt(comp_time)} s.

The estimated time saved is:

{fmt(raw_time)} - {fmt(comp_time)} = {fmt(raw_time-comp_time)} s.

This comparison deliberately ignores compression CPU time and assumes both paths sustain
their stated rates. In a real system, compression is worthwhile only if reduced transfer
time exceeds added compute/latency and does not create a new bottleneck.
"""
        return rec(rid,"engineering-reasoning","transfer-analysis","performance-analysis","advanced",
                   q,a,"reference-answer",
                   f"Compressed size must be {fmt(comp_gb)} GB; times {fmt(raw_time)} s and {fmt(comp_time)} s; saved time {fmt(raw_time-comp_time)} s.",
                   ["compression","bandwidth","transfer-time","bottleneck","engineering"])
    power = rng.choice([180,250,320])
    throughput = rng.choice([900,1200,1600])
    better_power = rng.choice([150,200,260])
    better_tp = rng.choice([850,1100,1500])
    e1 = power/throughput
    e2 = better_power/better_tp
    improvement = (e1-e2)/e1*100
    q = f"""
System A consumes {power} W while processing {throughput} tasks/s. System B consumes
{better_power} W while processing {better_tp} tasks/s.

Compute energy per task for both systems in joules/task and identify which is more
energy-efficient. If B is better, give the percentage reduction in energy per task.
"""
    a = f"""
Energy per task is power divided by task rate because one watt is one joule per second.

System A:

{power} J/s / {throughput} tasks/s = {fmt(e1,4)} J/task.

System B:

{better_power} J/s / {better_tp} tasks/s = {fmt(e2,4)} J/task.

{"System B" if e2 < e1 else "System A"} is more energy-efficient under these measurements.

The energy-per-task reduction from A to B is:

({fmt(e1,4)} - {fmt(e2,4)}) / {fmt(e1,4)} × 100
≈ {fmt(improvement,2)}%.

This metric combines performance and power more meaningfully than comparing watts alone,
provided both measurements represent equivalent completed work and comparable quality.
"""
    return rec(rid,"engineering-reasoning","energy-efficiency","performance-analysis","advanced",
               q,a,"reference-answer",
               f"Energy/task must be {fmt(e1,4)} J for A and {fmt(e2,4)} J for B, with reduction about {fmt(improvement,2)}%.",
               ["energy-efficiency","power","throughput","joules-per-task","engineering"])

GENERATORS = {
    "software-engineering": gen_software,
    "systems-programming": gen_systems,
    "operating-systems": gen_os,
    "computer-architecture": gen_arch,
    "linux-infrastructure": gen_linux,
    "embedded-systems": gen_embedded,
    "networking": gen_network,
    "distributed-systems": gen_distributed,
    "compute-model-infrastructure": gen_compute,
    "secure-engineering": gen_security,
    "engineering-reasoning": gen_reasoning,
}

def validate_batch(path: Path):
    p = subprocess.run(
        [sys.executable, "scripts/validate_dataset.py", str(path)],
        cwd=ROOT,
    )
    if p.returncode:
        raise SystemExit(f"Validator failed for {path}")

def normalized_question(r):
    q = r["messages"][0]["content"].lower()
    q = re.sub(r"\d+(?:\.\d+)?", "<n>", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-total", type=int, default=None)
    ap.add_argument(
        "--records",
        type=int,
        default=None,
        help="Generate only this many additional records in this run.",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    target_total = args.target_total or int(cfg["target_total"])
    if target_total != 100:
        raise SystemExit(
            "This first programmatic generator library is intentionally scoped to the "
            "v0.2-A 100-record quality gate. Expand generator families before scaling beyond 100."
        )

    STAGING.mkdir(parents=True, exist_ok=True)

    existing = scan_existing()
    counts = domain_counts_v02()
    targets = cfg["domain_targets"]

    needs = {d: max(0, targets[d] - counts[d]) for d in targets}
    needed_total = sum(needs.values())

    if args.records is None:
        run_goal = needed_total
    else:
        if args.records < 1:
            raise SystemExit("--records must be >= 1")
        run_goal = min(args.records, needed_total)

    print("=" * 78)
    print("Qwen3 CE v0.2 PROGRAMMATIC generator — no API, no external AI")
    print("=" * 78)
    print("Current v0.2 records:", sum(counts.values()))
    print("Target:", target_total)
    print("Need to target:", needed_total)
    print("Generate this run:", run_goal)
    print()
    for d in targets:
        print(f"{d:30s} current={counts[d]:2d} target={targets[d]:2d} add={needs[d]:2d}")

    if args.dry_run or run_goal == 0:
        return

    # Build a deterministic partial-run schedule that keeps the dataset moving
    # toward the configured domain proportions instead of exhausting one domain first.
    remaining = dict(needs)
    scheduled_domains = []
    domain_order = {d: i for i, d in enumerate(targets)}

    while len(scheduled_domains) < run_goal:
        candidates = [d for d in targets if remaining[d] > 0]
        if not candidates:
            break

        # Highest fractional deficit first; then absolute deficit; then config order.
        d = max(
            candidates,
            key=lambda x: (
                remaining[x] / targets[x],
                remaining[x],
                -domain_order[x],
            ),
        )
        scheduled_domains.append(d)
        remaining[d] -= 1

    if sum(targets.values()) != target_total:
        raise SystemExit("Config domain targets do not sum to target_total.")

    rng = random.Random(int(cfg["seed"]))
    nid = next_id_num(existing)
    batch_no = next_batch_num()
    batch_size = int(cfg["batch_size"])

    existing_ids = {r["id"] for r in existing}
    seen_q = {normalized_question(r) for r in existing if r.get("messages")}

    generated = []

    # Start family rotation from current per-domain count so a later partial run
    # does not restart every domain from family 0.
    per_domain_index = Counter(counts)

    for domain in scheduled_domains:
        idx = per_domain_index[domain]

        # Try parameter/family variations until the normalized question is new.
        for attempt in range(100):
            slug = domain.replace("-", "")
            rid = f"ce-{slug}-programmatic-{nid:06d}"
            r = GENERATORS[domain](rng, rid, idx + attempt)
            nq = normalized_question(r)
            if r["id"] not in existing_ids and nq not in seen_q:
                break
        else:
            raise SystemExit(f"Could not generate a unique record for {domain}")

        generated.append(r)
        existing_ids.add(r["id"])
        seen_q.add(nq)
        per_domain_index[domain] += 1
        nid += 1

    assert len(generated) == run_goal

    # Write in stable batches.
    for start in range(0, len(generated), batch_size):
        batch = generated[start:start+batch_size]
        data_path = STAGING / f"batch-{batch_no:03d}.jsonl"
        plan_path = ROOT / "configs" / f"dataset-v0.2-batch-{batch_no:03d}.json"

        with data_path.open("w", encoding="utf-8") as f:
            for r in batch:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        plan = {
            "batch": f"{batch_no:03d}",
            "dataset_version": "0.2",
            "stage": "v0.2-A-programmatic",
            "split": "train",
            "generator": "scripts/generate_v02_programmatic.py",
            "seed": cfg["seed"],
            "records": [
                {
                    "id": r["id"],
                    "domain": r["domain"],
                    "subdomain": r["subdomain"],
                    "task_type": r["task_type"],
                    "difficulty": r["difficulty"],
                    "verification": r["verification"]["method"],
                }
                for r in batch
            ],
        }
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

        validate_batch(data_path)

        manifest = {
            "batch": f"{batch_no:03d}",
            "records": len(batch),
            "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
            "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        }
        manifest_path = STAGING / f"batch-{batch_no:03d}.sha256.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        print(
            f"FROZEN batch-{batch_no:03d}: {len(batch)} records | "
            f"{manifest['data_sha256']}"
        )
        batch_no += 1

    final_counts = domain_counts_v02()
    print()
    print("=" * 78)
    print("v0.2-A COUNTS AFTER THIS RUN")
    print("=" * 78)
    total = 0
    for d in targets:
        n = final_counts[d]
        total += n
        print(f"{d:30s} {n:3d} / {targets[d]:3d}")
        if n > targets[d]:
            raise SystemExit(f"Quota exceeded for {d}: {n} > {targets[d]}")

    print("TOTAL:", total)
    print("Generated this run:", len(generated))
    print("Remaining to 100:", max(0, target_total - total))

    print()
    if total == target_total:
        for d in targets:
            if final_counts[d] != targets[d]:
                raise SystemExit(
                    f"Final quota mismatch for {d}: "
                    f"{final_counts[d]} != {targets[d]}"
                )
        print("SUCCESS: v0.2-A 100-record quality gate complete.")
    else:
        print("SUCCESS: partial programmatic batch complete.")

    print("No external AI/API was used.")

if __name__ == "__main__":
    main()
