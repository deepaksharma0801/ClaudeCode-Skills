---
name: performance-investigation
description: Finds why code or an endpoint is slow by measuring first, profiling the hot path, and proving each fix with numbers. Use when something is slow, times out, or uses too much CPU or memory.
---

# Detailed Instructions

Measure before you change anything, change one thing at a time, and measure again. A performance
fix without a before/after number is a guess.

## Overview

Performance work goes wrong when people optimize what looks slow instead of what is slow: caching
a function that takes 2 ms while an N+1 query takes 900 ms. This skill sets a baseline, uses a
profiler or tracing to find where time actually goes, fixes the biggest contributor, and reports
measured results.

## Workflow Rules

1. **Define the problem** as a number: "`GET /orders` p95 is 2.4 s, target < 300 ms", or "the
   import of 100k rows takes 11 min".
2. **Reproduce and baseline** with a repeatable command: a benchmark, a load test (`hey`, `k6`,
   `wrk`), or a script with realistic data volume. Run it several times; report median and spread.
3. **Profile, don't guess.** Use the right tool:

   | Stack | Tools |
   |---|---|
   | Python | `py-spy record`, `cProfile` + `snakeviz`, `scalene` (memory) |
   | Node | `node --cpu-prof`, `clinic flame`, Chrome DevTools |
   | Go | `pprof` (CPU, heap, block) |
   | JVM | async-profiler, JFR |
   | SQL | `EXPLAIN (ANALYZE, BUFFERS)`, slow query log, query counts per request |
   | Frontend | Lighthouse, Performance panel, bundle analyzer |

4. **Rank where time goes:** top 3–5 contributors with their share of total time.
5. **Check the usual suspects** in the hot path: N+1 queries, missing indexes, work inside loops
   that could be batched, repeated serialization, synchronous I/O on a hot path, unbounded result
   sets, oversized payloads, lock contention, memory churn.
6. **Fix the biggest contributor first**, one change at a time; rerun the benchmark after each.
7. **Report** before/after numbers per change, and check correctness (tests still pass, same output).
8. Stop when the target is met; list remaining opportunities instead of continuing.

## Anti-Patterns (What NOT to do)

* Do not optimize before profiling, or based on how code looks.
* Do not add caching as the first fix; it hides the cause and adds invalidation bugs.
* Do not benchmark with toy data when the problem appears at production volume.
* Do not report a single run as a result; variance matters.
* Do not trade correctness for speed without saying so.

## Examples

**User:** "The /orders page takes about 2 seconds to load."

**Expected output:**

```text
## Problem
GET /orders?limit=50 — p50 1.9 s, p95 2.4 s (k6, 20 virtual users, 60 s, staging data: 80k orders).
Target: p95 < 300 ms.

## Where the time goes (py-spy + SQL logging, one request)
| Share | What                                                         |
|-------|--------------------------------------------------------------|
| 71%   | 51 SQL queries — 1 for orders + 50 for customer (N+1)       |
| 18%   | ORDER BY created_at on orders without an index (seq scan)   |
| 6%    | Pydantic serialization                                      |

## Changes (measured after each)
1. Eager-load customers (selectinload) — 51 → 2 queries      p95 2.4 s → 640 ms
2. Index on orders(created_at DESC)                          p95 640 ms → 210 ms

Target met. Tests: 212 passed. Response body identical (diffed 50 orders before/after).

## Not done (not needed for target)
- Serialization (~12 ms) could drop with response_model_exclude_unset.
```
