---
name: technical-blog-post
description: Writes an engineering blog post that leads with a concrete problem, shows real numbers and runnable code, and covers trade-offs. Use for engineering blogs or how-we-built-it posts.
---

# Detailed Instructions

A technical post earns attention with a specific problem and evidence, not adjectives. Every
claim is backed by a number, a code sample that runs, or a clearly stated opinion.
Engineers share posts that teach them something they can use — with numbers they can trust and code
they can run. Marketing language and hidden trade-offs make readers stop trusting the rest.

## When to Use

- Engineering blog posts, "how we built/fixed X", launch write-ups for developers
- Turning a postmortem, design doc, or benchmark into a public post
- Conference talk abstracts or dev newsletters

**Don't use when:** the audience is customers who need to know what changed (use
`release-notes-writer`), or it's internal documentation (use `design-doc-writer`).

## Overview

Engineering posts fail when they read like press releases ("we're excited to announce a
blazing-fast…"), when the code doesn't run, or when they hide what didn't work. This skill
structures a post around a real problem, the approach, the evidence, and the trade-offs, written
for a reader who will copy the code and check the numbers.

## Workflow Rules

1. **Pin down the audience and takeaway:** who reads it (engineers using the same stack, the
   general dev community, customers) and the one thing they should learn or be able to do.
2. **Gather material:** the problem with measurements (latency, cost, error rates, time), what was
   tried, the final design, code or config, and results. Mark anything unverified as a gap.
3. **Structure:**
   - **Title** that names the specific thing ("How we cut Postgres query time 18x with partial
     indexes"), not a pun.
   - **Opening** (2–4 sentences): the problem and why the reader should care, with a number.
   - **Context:** just enough about the system for the solution to make sense.
   - **What we tried**, including what didn't work and why — this is often the most useful part.
   - **The solution** with code or config the reader can run, and a diagram if there are more
     than two moving parts.
   - **Results** with before/after numbers and how they were measured.
   - **Trade-offs and limits:** what this costs and when not to use it.
   - **Takeaways:** 2–4 bullets.
4. **Code samples:** minimal, complete enough to run, with versions noted; no secrets, internal
   hostnames, or customer data.
5. **Style:** plain, active sentences; define jargon once; short paragraphs; headings a skimmer can
   follow. Target 1,000–2,000 words unless the topic needs more.
6. **Review checklist before publishing:** numbers match sources, code runs, no confidential data,
   claims about other tools are fair and sourced, links work.

## Checklist

```text
- [ ] Audience and single takeaway defined
- [ ] Specific title (names the thing and result)
- [ ] Opening states the problem with a number
- [ ] What didn't work included
- [ ] Code runnable, minimal, versions noted; no secrets or internal hosts
- [ ] Results: before/after with how measured
- [ ] Trade-offs and limits
- [ ] No marketing adjectives; numbers match sources
- [ ] Confidential details (customers, hostnames, unreleased plans) removed
```

## Anti-Patterns (What NOT to do)

* Do not use marketing language ("revolutionary", "blazing fast", "seamless") in place of evidence.
* Do not publish code samples you have not run.
* Do not omit the approaches that failed or the costs of the one that worked.
* Do not include internal hostnames, credentials, customer names, or unreleased plans.
* Do not invent benchmarks or round numbers to make results look better.
* Do not open with company history; open with the problem.

## Examples

### Example 1: a slow dashboard

**User:** "Write a blog post about how we fixed our slow dashboard. Postgres 16, orders table 310M rows,
2% open. p95 was 9.1s on page 1 and page 20 timed out at 30s. A composite index (19 GB) only got
page 1 to 1.1s. A partial index on open orders (410 MB) plus keyset pagination got page 1 to 0.48s
and page 20 to 0.51s, measured over 7 days in prod. We dropped page numbers for Next/Previous."

**Expected output:**

````markdown
# How we cut our dashboard's load time from 9 seconds to 0.5 with two Postgres changes

Our customers' main dashboard took 9 seconds to load at the 95th percentile. Customers with large
accounts saw timeouts. The fix wasn't caching or a bigger database — it was two changes to how we
query Postgres 16: partial indexes and keyset pagination.

## The query
The dashboard lists a customer's open orders, newest first, 50 per page:

```sql
SELECT id, total_cents, created_at FROM orders
WHERE account_id = $1 AND status = 'open'
ORDER BY created_at DESC
LIMIT 50 OFFSET $2;
```

`orders` has 310M rows; only 2% are open.

## What didn't work
- **A composite index on (account_id, status, created_at):** helped page 1 (1.1s) but it was
  large (19 GB) and deep pages were still slow, because OFFSET reads and discards every skipped row.
- **Caching the first page:** hid the problem for page 1 only, and added invalidation bugs.

## Fix 1: a partial index for open orders
```sql
CREATE INDEX CONCURRENTLY orders_open_account_created_idx
  ON orders (account_id, created_at DESC)
  WHERE status = 'open';
```
It indexes only the 2% of rows that are open: 410 MB instead of 19 GB.

## Fix 2: keyset pagination instead of OFFSET
```sql
SELECT id, total_cents, created_at FROM orders
WHERE account_id = $1 AND status = 'open'
  AND (created_at, id) < ($2, $3)        -- last row of the previous page
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

## Results (p95, measured over 7 days in production)
| | Before | After |
|---|---|---|
| Page 1 | 9.1 s | 0.48 s |
| Page 20 | timeout (30 s) | 0.51 s |

## Trade-offs
- Keyset pagination can't jump to "page 37"; we replaced page numbers with Next/Previous.
- The partial index only helps queries that include `status = 'open'`.

## Takeaways
- If most queries touch a small subset of rows, a partial index can be dramatically smaller and faster.
- OFFSET gets slower with every page; keyset pagination stays flat.
- Measure p95 per page depth, not just page 1.
````

### Example 2: turning a postmortem into a public post

**User:** "Turn our internal Redis outage postmortem into a public engineering blog post."

**Expected output:**

````markdown
# What a full Redis memory taught us about our job queue

On November 4, background jobs — emails, exports, webhooks — stopped for 47 minutes. Nothing was
lost, but customers waited for receipts and exports. The cause was a single queue growing until
Redis ran out of memory, and the fix was mostly about limits we hadn't set.

## What happened
A retry bug re-enqueued failed webhook jobs without a cap. Over three days that queue grew to
11 million jobs and filled Redis' 25 GB. With `maxmemory-policy noeviction`, Redis started
rejecting all writes, so no new jobs could be queued.

## What we changed
- Capped retries (10, with exponential backoff) and moved exhausted jobs to a dead-letter queue.
- Alerts on queue length and Redis memory at 70%.
- Separate Redis instances for queues and caching, so a runaway queue can't take caching down.

## What you can take from it
- `noeviction` is the right policy for queues — but only with alerts before memory fills.
- Every retry loop needs a ceiling.
````

Removed from the internal version: hostnames, the customer who reported it first, individual
names, and internal ticket links.

## Quick Reference

| Part | Rule |
|---|---|
| Title | Specific thing + result |
| Opening | Problem + a number, in 2–4 sentences |
| Middle | Context → what failed → solution with runnable code |
| Results | Before/after, how measured |
| Ending | Trade-offs + 2–4 takeaways |
| Never | Invented benchmarks, marketing adjectives, internal names |
