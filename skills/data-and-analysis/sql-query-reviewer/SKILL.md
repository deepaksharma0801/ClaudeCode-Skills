---
name: sql-query-reviewer
description: Reviews a SQL query for wrong results (join fan-out, NULLs, filters) and performance problems. Use when a user shares a SQL query to check, debug, or speed up, or asks why its numbers look off.
---

# Detailed Instructions

Check correctness before performance. A fast query that double-counts is worse than a slow one
that is right.

## Overview

Most SQL bugs return plausible numbers instead of errors: a join that multiplies rows, a
`LEFT JOIN` silently turned into an inner join by a `WHERE` clause, `NOT IN` against a column with
NULLs. This skill walks a fixed checklist, explains each issue with the row-level reason, and
returns a corrected query.

## Workflow Rules

1. Identify the dialect (Postgres, MySQL, BigQuery, Snowflake, SQLite, SQL Server) from syntax or
   ask once if it matters for the fix.
2. Restate in one sentence what the query is meant to return, and the grain of one output row.
3. **Correctness checklist** — check each, report only what applies:
   - Join fan-out: a one-to-many join before `SUM`/`COUNT` inflates totals.
   - `LEFT JOIN` followed by a `WHERE` on the right table (turns it into an inner join).
   - `NOT IN (subquery)` where the subquery can return NULL (returns zero rows).
   - `= NULL` / `<> NULL` instead of `IS NULL`; NULLs dropped by `COUNT(col)` vs `COUNT(*)`.
   - `GROUP BY` missing a selected non-aggregated column (or relying on MySQL's loose mode).
   - `COUNT(DISTINCT …)` hiding a fan-out instead of fixing it.
   - Date filters: timezone, inclusive/exclusive end (`<= '2026-11-30'` misses that day's times),
     `BETWEEN` on timestamps.
   - Integer division (`1/2 = 0`), and `AVG` over a fanned-out set.
   - Window functions without a deterministic `ORDER BY`.
4. **Performance checklist:** functions on indexed columns in `WHERE` (`DATE(created_at) = …`),
   leading-wildcard `LIKE '%x'`, `SELECT *` on wide tables, correlated subqueries that could be a
   join, `OR` across different columns, missing filter on partitioned tables. Suggest indexes only
   with the exact columns and order.
5. If the user can run queries, give a one-line check that proves each correctness issue
   (e.g. `SELECT order_id, COUNT(*) … HAVING COUNT(*) > 1`).
6. Return the corrected query in full, with a comment on each changed line.

## Anti-Patterns (What NOT to do)

* Do not rewrite the whole query in a different style when a two-line fix is enough.
* Do not "fix" fan-out by adding `DISTINCT` to the outer select.
* Do not recommend an index without naming its columns, or claim a speedup you have not measured.
* Do not assume a column is unique or non-null without saying it is an assumption.
* Do not run `UPDATE`, `DELETE`, or DDL to test a theory.

## Examples

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
Intent: total order amount per customer, excluding gift-card items. Grain: one row per customer.

## Correctness
1. Fan-out (main cause of the inflated numbers): joining order_items repeats each order once per
   item, so an order with 3 items has its amount summed 3 times.
   Check: SELECT o.id, COUNT(*) FROM orders o JOIN order_items i ON i.order_id = o.id GROUP BY 1 HAVING COUNT(*) > 1;
2. WHERE i.sku <> 'GIFT' turns both LEFT JOINs into inner joins: customers with no orders vanish,
   and items with NULL sku are dropped (NULL <> 'GIFT' is not true).

## Fixed query
SELECT c.id, COALESCE(SUM(o.amount), 0) AS revenue     -- keep customers with no orders
FROM customers c
LEFT JOIN orders o
  ON o.customer_id = c.id
 AND NOT EXISTS (                                      -- filter at order grain, no fan-out
       SELECT 1 FROM order_items i
       WHERE i.order_id = o.id AND i.sku = 'GIFT')
GROUP BY c.id;

Assumption: an order containing any gift-card item should be excluded entirely. If only the
gift-card line should be excluded, sum order_items.amount instead of orders.amount.
```
