---
name: performance-investigation
description: Finds why code, a page, or an endpoint is slow by measuring first, profiling the hot path, and proving each fix with numbers. Use when something is slow, times out, or uses too much CPU or memory.
---

# Detailed Instructions

Measure before changing anything, change one thing at a time, and measure again. Optimize what the
profiler says is slow, not what looks slow. A performance claim without a before/after number from
the same benchmark is a guess, and a fix that changes the output is a bug.

## When to Use

- "This endpoint / page / job is slow", "it times out", "p95 went up after the deploy"
- High CPU, memory growth, or out-of-memory kills
- A batch job that no longer finishes in its window
- Cost spikes from compute or database load

**Don't use when:** the slowness is in the build pipeline's configuration (use
`ci-failure-debugger` or `dockerfile-optimizer`), or a schema change is locking tables (use
`db-migration-safety`).

## Overview

Performance work goes wrong when people optimize code that looks inefficient instead of code that
is actually on the hot path — caching a 2 ms function while an N+1 query costs 900 ms. This skill
turns the complaint into a target number, builds a repeatable benchmark with realistic data,
profiles to rank where time goes, fixes the biggest contributor first, verifies correctness and
the new number after each change, and stops when the target is met.

## Workflow Rules

### 1. Define and measure

1. **State the problem as a number and a target:** "`GET /orders` p95 is 2.4 s; target < 300 ms",
   "nightly import of 100k rows takes 11 min; must finish in 5". Without a target you can't know
   when to stop.
2. **Build a repeatable benchmark** with production-like data volume — performance problems often
   appear only at scale (N+1 queries, missing indexes, quadratic loops). Use a load tool for
   services (`k6`, `hey`, `wrk`, `ab`), a timing script or `hyperfine` for commands, or
   `pytest-benchmark` / `benchmark.js` for functions.
3. **Run it several times** and record median and p95 (or min/median/max). Note the environment
   (machine, data size, warm vs cold cache). Single runs lie.

### 2. Profile — find where time actually goes

4. **Pick the right tool:**

   | Stack | CPU / wall time | Memory |
   |---|---|---|
   | Python | `py-spy record -o profile.svg -- python app.py`, `cProfile` + `snakeviz` | `scalene`, `memray`, `tracemalloc` |
   | Node | `node --cpu-prof`, `clinic flame`, Chrome DevTools | `--heap-prof`, heap snapshots |
   | Go | `pprof` (`net/http/pprof`, `go test -cpuprofile`) | `pprof` heap / allocs |
   | JVM | async-profiler, JFR | JFR, heap dumps (Eclipse MAT) |
   | Database | `EXPLAIN (ANALYZE, BUFFERS)`, slow query log, `pg_stat_statements` | — |
   | Frontend | Lighthouse, DevTools Performance panel | bundle analyzer, Memory panel |
   | Distributed | Traces (OpenTelemetry / APM) to see which service and span is slow | — |

5. **Count queries and external calls per request** — log or trace them. Fifty queries for a page
   of fifty rows is the signature of an N+1.
6. **Rank the top 3–5 contributors** by share of total time. The biggest one is usually much
   bigger than the rest.

### 3. Fix the biggest contributor first

7. **Check the usual suspects on the hot path:**
   - N+1 queries → eager loading / batching (`select_related`, `selectinload`, `include`, DataLoader)
   - Missing or unused index → read the plan; add the index that matches the filter and sort
   - Work inside loops that could be done once or in bulk (bulk inserts, batched API calls)
   - Unbounded result sets → pagination, limits, streaming
   - Repeated serialization or parsing of the same data
   - Synchronous I/O on a request path → move to a background job
   - Oversized payloads → select only needed columns/fields, compress
   - Lock contention, connection-pool exhaustion → check pool waits and lock stats
   - Memory: accidental retention (global caches, closures), loading whole files instead of streaming
8. **One change at a time.** Re-run the benchmark after each and record the new number.
9. **Check correctness after each change:** tests pass and the output is identical (diff a sample
   response or result set before and after).
10. **Cache last, not first.** Caching hides the cause and adds invalidation bugs; reach for it
    only when the work is inherently expensive and the data tolerates staleness.

### 4. Stop and report

11. **Stop when the target is met.** List remaining opportunities instead of continuing to tune.
12. **Report:** problem and target, benchmark setup, profile ranking, each change with before/after
    numbers, correctness check, and what's left.

## Checklist

```text
- [ ] Problem and target stated as numbers
- [ ] Benchmark is repeatable and uses realistic data volume
- [ ] Baseline: several runs, median and p95
- [ ] Profiled with the right tool; top contributors ranked by share
- [ ] Queries/external calls per request counted
- [ ] Biggest contributor fixed first, one change at a time
- [ ] Benchmark re-run after each change
- [ ] Tests pass and output is identical
- [ ] Stopped at target; remaining opportunities listed
```

## Red Flags

- "This loop looks slow, let me optimize it." (Has the profiler shown it?)
- "Let's just add Redis."
- "It's faster on my machine with my 20 test rows."
- "I changed four things and it's faster now."
- "The benchmark varied a lot, but the best run looks great."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I can see what's slow by reading the code." | Intuition about hot paths is wrong often enough that profiling is cheaper than guessing. |
| "Caching will fix it." | Caching hides the slow path, adds staleness and invalidation bugs, and the first request is still slow. |
| "Small test data is fine for benchmarking." | N+1 queries and missing indexes are invisible at 20 rows and dominant at 2 million. |
| "Micro-optimizations add up." | Not compared with one query that takes 70% of the time. Fix the biggest contributor first. |

## Anti-Patterns (What NOT to do)

* **Optimizing before profiling** — effort goes to code that doesn't matter.
* **Benchmarking with toy data** — the problem doesn't appear.
* **Reporting a single run** — variance can be larger than the improvement.
* **Several changes between measurements** — you can't attribute the gain or the regression.
* **Trading correctness for speed silently** — say so if results change (approximation, staleness).
* **Continuing to tune past the target** — complexity has a cost too.

## Examples

### Example 1: a slow endpoint

**User:** "The /orders page takes about 2 seconds to load."

**Expected output:**

```text
## Problem
GET /orders?limit=50 — p50 1.9 s, p95 2.4 s (k6, 20 virtual users, 60 s, staging with 80k orders).
Target: p95 < 300 ms.

## Where the time goes (py-spy + SQL logging, one request)
| Share | What                                                       |
|-------|------------------------------------------------------------|
| 71%   | 51 SQL queries — 1 for orders + 50 for customers (N+1)     |
| 18%   | ORDER BY created_at without an index (sequential scan)     |
| 6%    | Pydantic serialization                                     |

## Changes (measured after each)
1. Eager-load customers (selectinload): 51 → 2 queries      p95 2.4 s → 640 ms
2. Index on orders(created_at DESC)                        p95 640 ms → 210 ms

Target met. Tests: 212 passed. Response bodies identical (diffed 50 orders before/after).

## Not done (not needed for target)
Serialization (~12 ms) could drop with response_model_exclude_unset.
```

### Example 2: memory growth

**User:** "Our worker's memory climbs from 300 MB to 4 GB over a day and gets OOM-killed."

**Expected output:**

```text
## Reproduce
Replayed 2 hours of production jobs locally at 10x speed with memray attached:
memray run -o worker.bin worker.py --replay jobs.jsonl
RSS: 310 MB → 1.9 GB over the replay; still climbing.

## Profile (memray flamegraph, allocations still alive at the end)
| Retained | Where                                                        |
|----------|--------------------------------------------------------------|
| 1.4 GB   | pricing.py:22 `_rate_cache = {}` — module-level dict, never evicted |
| 120 MB   | normal working set                                           |

Cause: _rate_cache is keyed by (customer_id, sku, date); a new date every day means entries are
never reused or removed.

## Fix
Replace the dict with functools.lru_cache(maxsize=50_000) on get_rate().
Replay again: RSS plateaus at 380 MB after 20 minutes and stays flat. Cache hit rate 92%
(was 94%), so lookup speed is unchanged within noise. Tests: 318 passed.
```

## Quick Reference

| Symptom | First thing to check |
|---|---|
| Slow endpoint | Queries per request; `EXPLAIN ANALYZE` on the slowest |
| Slow at scale only | Benchmark with production-size data |
| p95 much worse than p50 | Lock waits, pool exhaustion, GC pauses, cold caches |
| CPU pegged | CPU profiler flame graph |
| Memory climbs | Allocation profiler; look for unbounded caches and globals |
| Slow page in browser | Lighthouse + Performance panel; bundle size |
| Many services | Traces to find the slow span |
