---
name: log-triage
description: Triages application or server logs by grouping lines into patterns, ranking them by count and onset, and pointing to the likely cause. Use when a user shares logs or asks why something is failing.
compatibility: Bundled script requires Python 3.8+ (standard library only).
---

# Detailed Instructions

Group first, read second. Collapse log lines into templates, count them, and find **when each one
started** — then read the few lines that matter. The loudest error is usually a consequence; the
pattern that started first, shortly after something changed, is usually the cause. And logs carry
secrets and personal data, so the analysis never repeats them.

## When to Use

- A pasted log excerpt or a log file, "why is this failing?"
- An incident: errors spiked at a known time
- `kubectl logs`, `journalctl`, CloudWatch/Datadog/Loki exports, nginx/access logs
- Comparing a bad period with a good one

**Don't use when:** the question is adding or improving logging (use
`observability-instrumentation`), or you already know the failing request and need to trace the
code (use `root-cause-debugging`).

## Overview

Large log dumps hide the signal: one new error repeated 40,000 times next to long-standing warnings
that always fire. Reading top to bottom finds the noise. This skill runs
`scripts/log_patterns.py` to normalize variable parts (IDs, numbers, IPs, emails, tokens) into
templates, ranks them by count, separates patterns present from the start of the window
(background) from ones that **start during it**, lines the onsets up against deploys and config
changes, follows one failing request end to end, and reports the top issues with a hypothesis and
the next check.

## Workflow Rules

### 1. Scope

1. **Record the source, time range, and line count.** If the incident time is known, take a window
   that starts well before it (e.g. 30 minutes) so "what changed" is visible. For big files never
   read everything — use the script, `grep`, `awk`, or `sort | uniq -c`.

### 2. Group and rank

2. **Run the grouping script:**
   `python3 scripts/log_patterns.py app.log --level ERROR,WARN --top 20`
   (`-` reads stdin, e.g. `kubectl logs deploy/api --since=2h | python3 scripts/log_patterns.py -`;
   for JSON logs add `--json-field message`). It prints templates with counts and first/last seen,
   then lists patterns that **start** during the window separately from background ones.
3. **If you can, run the same window from a healthy period** (`--after/--before`) and compare:
   a pattern with similar counts in both periods is background.

### 3. Find the onset and the cause

4. **Line up onsets with changes:** deploys, config or feature-flag changes, restarts, traffic
   spikes, dependency incidents. A new pattern minutes after a deploy is a strong lead.
5. **Read the earliest new WARN/ERROR first.** Cascades run forward in time: slow queries →
   connection pool exhaustion → timeouts → 500s. The first link is the cause.
6. **Follow one failing request** by request or trace ID across lines and services
   (`grep <request-id> *.log`) to see the full sequence.
7. **Pull 1–2 raw examples** per important pattern — with secrets and personal data redacted.

### 4. Report

8. For the top 3–5 patterns: template, count, first/last seen, a redacted example, likely cause
   with the evidence (timing, request trace), and the next check (a query, a config, a metric, a
   rollback).

## Checklist

```text
- [ ] Source, time range, and line count recorded; window starts before the incident
- [ ] Ran scripts/log_patterns.py (or equivalent grouping)
- [ ] Background patterns separated from ones that start during the window
- [ ] Onsets lined up with deploys / config changes / traffic
- [ ] Earliest new WARN/ERROR read first
- [ ] One failing request followed end to end
- [ ] Examples redacted
- [ ] Top patterns reported with cause, evidence, and next check
```

## Red Flags

- "The most frequent error must be the cause."
- "Let me scroll through the log from the top."
- "That warning is always there, so it can't matter." (Has its rate changed?)
- Pasting raw log lines with emails, tokens, or IPs into the answer.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The top error by count is the problem." | Count measures volume, not causality. Downstream timeouts usually outnumber the upstream cause. |
| "I'll skim the file." | A 300k-line file can't be skimmed; one-off errors hide between thousands of repeats. Group first. |
| "It's just noise." | Prove it: compare with a healthy period. Noise has the same rate before and after. |

## Anti-Patterns (What NOT to do)

* **Pasting large raw log sections back to the user** — summarize with templates.
* **Treating the loudest message as the root cause** — check onset order.
* **Ignoring the first error in a cascade** because a later one is louder.
* **Repeating tokens, passwords, emails, or customer data from logs.**
* **Stating a cause without a log line, timing, or trace that supports it.**

## Examples

### Example 1: 500s after a deploy

**User:** "API started returning 500s around 14:00. Here's an hour of logs." *(20,000 lines; deploy v2.41 finished 14:00:30)*

**Expected output:**

```text
$ python3 scripts/log_patterns.py api.log --level ERROR,WARN
Lines read: 20,000. By level: INFO 12,089, WARN 6,469, ERROR 1,442

| # | level | count | first seen          | template                                                   |
|---|-------|-------|---------------------|------------------------------------------------------------|
| 1 | WARN  | 5,905 | 2026-11-20T13:30:00 | WARN cache miss ratio <N>% key=user:<N>                    |
| 2 | ERROR | 811   | 2026-11-20T14:02:13 | ERROR db pool timeout after <N> (pool size <N>) req=<UUID> |
| 3 | ERROR | 631   | 2026-11-20T14:02:12 | ERROR GET /orders/<N>?<QUERY> <N> upstream=orders-db ...   |
| 4 | WARN  | 564   | 2026-11-20T14:01:51 | WARN slow query <N>: SELECT * FROM orders WHERE status=$<N> |

Start during the window (earliest first):
- 14:01:51 WARN slow query on orders.status
- 14:02:12 ERROR GET /orders 500 upstream=orders-db
- 14:02:13 ERROR db pool timeout
Background: cache miss warnings, present from 13:30 at a steady rate — not related.

## Timeline
14:00:30 deploy v2.41 finished
14:01:51 first slow query on orders.status (new query in v2.41)
14:02:11 pool timeouts begin; 500s follow on the same request IDs

## Likely cause
v2.41 added a query filtering orders by status without a supporting index. Slow queries hold
connections, the pool (size 20) runs out, and requests time out with 500s.
Request trace (req 8f2c…, redacted): slow query 9.8 s → pool timeout → 500.

## Next checks
- EXPLAIN the orders.status query; check for an index on orders(status, created_at).
- Immediate relief: roll back to v2.40.
```

### Example 2: a pattern that isn't new

**User:** "We see thousands of 'connection reset by peer' errors. Is that why checkout is down?"

**Expected output:**

```text
Compared today 09:00–10:00 (incident) with yesterday 09:00–10:00 (healthy):

| template                                    | yesterday | today  |
|---------------------------------------------|-----------|--------|
| WARN connection reset by peer <IP>          | 3,912     | 4,087  |  ← same rate: background
| ERROR stripe charge failed: card_declined   | 210       | 198    |  ← normal
| ERROR stripe charge failed: api_key_expired | 0         | 2,341  |  ← NEW, starts 09:14:02

"Connection reset" is background (clients disconnecting; same rate both days).
The new pattern is api_key_expired from 09:14:02 — the Stripe restricted key used by checkout
expired. Next: rotate the key in the secret store and redeploy checkout; add an expiry alert.
```

## Quick Reference

| Step | Command / rule |
|---|---|
| Group | `python3 scripts/log_patterns.py FILE --level ERROR,WARN` |
| Stream | `… | python3 scripts/log_patterns.py -` |
| JSON logs | `--json-field message` |
| Compare periods | `--after T1 --before T2` for incident vs healthy windows |
| Cause | Earliest *new* pattern near a change, not the loudest |
| Confirm | Follow one request ID end to end |
| Output | Templates + counts; redacted examples only |
