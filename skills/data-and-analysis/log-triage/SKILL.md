---
name: log-triage
description: Triages application or server logs by grouping errors into patterns, ranking them by count and onset, and pointing to the likely cause. Use when a user shares logs or asks why something is failing.
---

# Detailed Instructions

Group first, read second. Normalize the noise out of log lines, count the patterns, and find when
each one started — then read the few lines that matter.

## Overview

Large log dumps hide the signal: one new error repeated 40,000 times next to familiar background
warnings. This skill collapses lines into templates, ranks them, lines them up against time and
deploys, and returns the top issues with representative examples and a first hypothesis.

## Workflow Rules

1. **Scope:** note the source, time range, and line count. For large files, work with `grep`,
   `awk`, `sort | uniq -c`, or a short script instead of reading the whole file.
2. **Parse** timestamp, level, and message (JSON logs: use the fields; plain text: infer the format).
3. **Normalize** messages into templates by replacing variable parts — IDs, UUIDs, numbers, IPs,
   emails, paths, durations — with placeholders.
4. **Count** templates by level. Rank errors and warnings by count and by **first seen** time.
5. **Onset:** find templates that start or spike at a specific time. Compare with deploys,
   restarts, config changes, or traffic shifts if the user provides them.
6. **Correlate** using request or trace IDs: follow one failing request across lines and services.
7. For the top 3–5 patterns give: template, count, first/last seen, one raw example (with secrets
   and personal data redacted), and a likely cause with the evidence.
8. Suggest the next check for each (a query, a config to inspect, a metric to graph).

## Anti-Patterns (What NOT to do)

* Do not paste large raw log sections back to the user.
* Do not treat the most frequent message as the root cause; long-standing noise is often harmless.
* Do not ignore the first error in a cascade in favor of the loudest one after it.
* Do not repeat tokens, passwords, emails, or customer data from logs in your output.
* Do not state a cause without a log line or timing that supports it.

## Examples

**User:** "API started returning 500s around 14:00. Here's an hour of logs." *(312,480 lines)*

**Expected output:**

```text
Scope: api-prod, 13:30–14:30 UTC, 312,480 lines (2.1% ERROR, 6.4% WARN)

## Top patterns
| # | Level | Template                                                | Count  | First seen | Note |
|---|-------|---------------------------------------------------------|--------|------------|------|
| 1 | ERROR | db pool timeout after <N>ms (pool size <N>)             | 5,912  | 14:02:11   | new  |
| 2 | ERROR | GET /orders/<ID> 500 upstream=orders-db                 | 5,880  | 14:02:11   | new, follows #1 |
| 3 | WARN  | slow query <N>ms: SELECT ... FROM orders WHERE status=? | 1,204  | 14:01:47   | new  |
| 4 | WARN  | cache miss ratio <N>%                                   | 18,330 | 13:30:00   | present all hour — background |

## Timeline
14:00:30 deploy v2.41 finished (from user)
14:01:47 first slow-query warning on orders.status
14:02:11 pool timeouts begin; 500s follow on the same request IDs

## Likely cause
v2.41 introduced a query filtering orders by status with no supporting index. Slow queries hold
connections, the pool (size 20) is exhausted, and requests time out.
Example (req 8f2c…): slow query 9,840ms → pool timeout → 500.

## Next checks
- EXPLAIN the orders.status query; check for a missing index on orders(status, created_at).
- Compare v2.40 and v2.41 query changes.
- Quick relief: roll back v2.41.
```
