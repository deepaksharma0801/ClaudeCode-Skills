---
name: sql-query-reviewer
description: Reviews a SQL query for wrong results (join fan-out, NULL traps, filters, dates) and slowness, then returns a corrected query. Use when SQL numbers look off, or to check or speed up a query.
---

# Detailed Instructions

Check correctness before performance — a fast query that double-counts is worse than a slow one
that's right, because nobody notices it's wrong. Most SQL bugs return plausible numbers instead of
errors, so read every join and filter against the intended grain of the result, and prove each
suspected bug with a one-line check query before changing anything.

## When to Use

- "These numbers look too high / too low", "doesn't match the dashboard / Stripe / finance"
- Reviewing a query before it goes into a report, dbt model, or dashboard
- A slow query or one that times out
- Translating a query between dialects

**Don't use when:** the question is about schema changes or locks (use `db-migration-safety`), or
defining what a metric should mean (use `metric-definition-writer` first, then review the SQL).

## Overview

The classic silent bugs: a one-to-many join before `SUM` multiplies totals; a `WHERE` on the right
table of a `LEFT JOIN` silently drops the unmatched rows; `NOT IN` against a subquery containing a
NULL returns nothing; a date filter `<= '2026-11-30'` misses the whole last day. This skill states
the intended grain, walks a fixed correctness checklist, proves each issue with a check query, then
reviews performance, and returns a corrected query with every change commented.

## Workflow Rules

### 1. Understand intent

1. **Identify the dialect** (Postgres, MySQL, BigQuery, Snowflake, Redshift, SQLite, SQL Server,
   DuckDB) from syntax; ask once if it changes the fix.
2. **State what the query should return** and the **grain of one output row** ("one row per
   customer per month"). Every join and aggregation is checked against this.
3. **Note key assumptions** you can't verify: uniqueness of join keys, nullability, time zone of
   timestamps. Mark them as assumptions in the output.

### 2. Correctness checklist (report only what applies)

4. **Join fan-out:** a one-to-many join before `SUM`/`COUNT`/`AVG` repeats parent rows. Aggregate
   the child to the parent's grain first, or use `EXISTS` for filtering.
5. **LEFT JOIN undone by WHERE:** a condition on the right table in `WHERE` turns the outer join
   into an inner join. Move it into the `ON` clause, or handle `NULL` explicitly.
6. **NULL traps:** `NOT IN (subquery)` returns no rows if the subquery yields any NULL (use
   `NOT EXISTS`); `= NULL` / `<> NULL` are never true (use `IS [NOT] NULL`); `col <> 'x'` drops
   NULL rows; `COUNT(col)` skips NULLs while `COUNT(*)` doesn't; `SUM` of no rows is NULL
   (wrap in `COALESCE`).
7. **Grouping:** every selected non-aggregated column is in `GROUP BY` (MySQL's loose mode hides
   this and returns arbitrary values); `COUNT(DISTINCT …)` masking a fan-out instead of fixing it.
8. **Dates and time zones:** inclusive/exclusive bounds (`< '2026-12-01'`, not `<= '2026-11-30'`
   on timestamps); `BETWEEN` on timestamps; which time zone the timestamps are in and which the
   report means; `DATE(ts)` in the server's zone.
9. **Arithmetic:** integer division (`1/2 = 0` in Postgres and SQL Server), averages over a
   fanned-out set, percentages computed before filtering.
10. **Windows and ordering:** window functions need a deterministic `ORDER BY` (add a unique
    tiebreaker); `LIMIT` without `ORDER BY` returns arbitrary rows.
11. **Prove each issue** with a short check query, e.g.
    `SELECT order_id, COUNT(*) FROM … GROUP BY 1 HAVING COUNT(*) > 1 LIMIT 10;` — and say what
    it returned if you can run it.

### 3. Performance checklist

12. **Read the plan** when possible (`EXPLAIN ANALYZE` in Postgres/MySQL 8, query profile in
    BigQuery/Snowflake). Then check: functions on filtered columns (`WHERE DATE(created_at) = …`
    can't use an index — use a range); leading-wildcard `LIKE '%x'`; `SELECT *` on wide tables;
    correlated subqueries that could be joins; `OR` across different columns; missing partition
    or cluster filters in warehouses (scanned bytes = cost).
13. **Suggest indexes with exact columns and order** (equality filters first, then range/sort),
    and say it's a suggestion until measured.

### 4. Return

14. **Corrected query in full**, each change marked with a comment, plus the check queries and the
    list of assumptions.

## Checklist

```text
- [ ] Dialect identified
- [ ] Intended result and output grain stated
- [ ] Joins checked for fan-out against the grain
- [ ] LEFT JOIN conditions in ON, not WHERE
- [ ] NULL handling: NOT EXISTS, IS NULL, COALESCE on SUM
- [ ] GROUP BY complete; no DISTINCT masking fan-out
- [ ] Date bounds exclusive at the end; time zone stated
- [ ] Integer division and averages checked
- [ ] Each issue proven with a check query
- [ ] Performance: plan read; sargable filters; partition filters
- [ ] Corrected query with commented changes and listed assumptions
```

## Red Flags

- "Just add DISTINCT, the duplicates go away."
- "The LEFT JOIN keeps everything, so the counts are complete."
- "Totals are close to finance's, probably timing."
- "It runs fast, so it's fine."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "DISTINCT fixes the duplicates." | It hides the fan-out and silently drops legitimate duplicate values; `SUM(DISTINCT amount)` undercounts equal amounts. |
| "The number is roughly right." | Fan-out errors often look like 5–15% inflation — exactly the range people call "roughly right". |
| "The key is obviously unique." | Check it. Soft-deleted rows, history tables, and multi-currency rows break "obvious" uniqueness. |

## Anti-Patterns (What NOT to do)

* **Rewriting the whole query in a new style** when a two-line fix is enough — reviewers can't see what changed.
* **Fixing fan-out with `DISTINCT` on the outer select** — the aggregate is still wrong.
* **Recommending an index without columns and order, or claiming a speedup you didn't measure.**
* **Assuming uniqueness or non-nullness silently** — list it as an assumption.
* **Running `UPDATE`, `DELETE`, or DDL to test a theory** — use read-only check queries.

## Examples

### Example 1: inflated revenue

**User:** "Revenue per customer from this query is way higher than in Stripe."

```sql
SELECT c.id, SUM(o.amount) AS revenue
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
LEFT JOIN order_items i ON i.order_id = o.id
WHERE i.sku <> 'GIFT'
GROUP BY c.id;
```

**Expected output:**

```text
Intent: total order amount per customer, excluding orders with gift cards. Grain: one row per customer.

## Correctness
1. Fan-out (main cause): joining order_items repeats each order once per item, so an order with
   3 items has its amount summed 3 times.
   Check: SELECT o.id, COUNT(*) FROM orders o JOIN order_items i ON i.order_id = o.id
          GROUP BY o.id HAVING COUNT(*) > 1 LIMIT 10;
2. WHERE i.sku <> 'GIFT' undoes both LEFT JOINs: customers with no orders disappear, and items
   with a NULL sku are dropped (NULL <> 'GIFT' is not true).

## Fixed query
SELECT c.id, COALESCE(SUM(o.amount), 0) AS revenue      -- keep customers with no orders
FROM customers c
LEFT JOIN orders o
  ON o.customer_id = c.id
 AND NOT EXISTS (                                       -- filter at order grain: no fan-out
       SELECT 1 FROM order_items i
       WHERE i.order_id = o.id AND i.sku = 'GIFT')
GROUP BY c.id;

Assumption: an order containing any gift-card item is excluded entirely. If only the gift-card
lines should be excluded, sum order_items amounts instead of orders.amount.
```

### Example 2: a slow, subtly wrong date filter

**User:** "This daily report is slow and November looks a bit low."

```sql
SELECT DATE(created_at) AS day, COUNT(*) AS signups
FROM users
WHERE DATE(created_at) BETWEEN '2026-11-01' AND '2026-11-30'
  AND referrer NOT IN (SELECT domain FROM blocked_domains)
GROUP BY 1;
```

**Expected output:**

```text
## Correctness
1. NOT IN drops users with no referrer: for direct signups referrer IS NULL, and
   NULL NOT IN (...) is unknown, not true — so they vanish from the count.
   Check: SELECT COUNT(*) FROM users WHERE referrer IS NULL
          AND created_at >= '2026-11-01' AND created_at < '2026-12-01';
   (And if blocked_domains ever gains a NULL row, NOT IN returns no rows at all.) Use NOT EXISTS.
2. Time zone: created_at is UTC (timestamptz); DATE() uses the session zone. State which zone
   the report means (the team reports in America/New_York).

## Performance
DATE(created_at) in WHERE prevents using the index on created_at → sequential scan of 41M rows.
Use a half-open range instead.

## Fixed query
SELECT (created_at AT TIME ZONE 'America/New_York')::date AS day, COUNT(*) AS signups
FROM users u
WHERE u.created_at >= TIMESTAMPTZ '2026-11-01 00:00 America/New_York'   -- sargable range
  AND u.created_at <  TIMESTAMPTZ '2026-12-01 00:00 America/New_York'   -- exclusive end
  AND NOT EXISTS (SELECT 1 FROM blocked_domains b WHERE b.domain = u.referrer)  -- NULL-safe
GROUP BY 1
ORDER BY 1;
```

## Quick Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| Totals too high | Join fan-out | Aggregate child first, or `EXISTS` |
| Rows missing after LEFT JOIN | Right-table filter in WHERE | Move it into `ON` |
| `NOT IN` returns nothing / too little | NULL in subquery | `NOT EXISTS` |
| Last day missing | `<=` on a timestamp | `< next_day` |
| Percent = 0 | Integer division | Cast to numeric |
| Slow despite index | Function on the column in WHERE | Range predicate |
