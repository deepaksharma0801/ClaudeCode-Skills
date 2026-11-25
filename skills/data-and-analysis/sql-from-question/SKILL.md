---
name: sql-from-question
description: Writes correct SQL from a plain-English question by checking schema, grain, and join keys first, then validating the result. Use when asked to pull numbers or answer a data question.
---

# Detailed Instructions

Before writing SQL, pin down three things: the exact definition of each number asked for, the
**grain** (one row per what?) of every table you'll touch, and the keys you'll join on. Then
build the query in small steps and sanity-check the result against a number you already
trust. Most wrong answers come from SQL that runs fine — duplicated rows from a join, a filter
that drops NULLs, a timezone shift — not from syntax errors.

## When to Use

- "How many / what's the average / which top 10 … ?" against a database or warehouse
- "Write me a query for X" given a schema, dbt models, or table names
- Turning a stakeholder request into SQL for a report or dashboard tile
- Translating a question into the dialect in use (Postgres, BigQuery, Snowflake, Redshift,
  DuckDB)

**Don't use when:** reviewing a query someone already wrote (use `sql-query-reviewer`), defining a
company KPI for reuse (use `metric-definition-writer`), or the question is "why did it change?"
(use `metric-drop-investigation`).

## Overview

A plausible-looking query with a quietly wrong number is worse than no answer. This skill
restates the question as a precise definition, inspects the schema and sample rows to learn
each table's grain and keys, writes the query as readable CTEs that each do one thing, checks
row counts at every join, and validates the final number with a cross-check before reporting it
with its assumptions.

## Workflow Rules

### 1. Make the question precise

1. Restate it with every ambiguity resolved: which time range and timezone, what counts as a
   "customer" or an "order" (test accounts? refunds? cancelled?), and the unit of the answer.
   If an ambiguity would change the number a lot, ask; otherwise choose and state the
   assumption.

### 2. Learn the data

2. Inspect the schema: `information_schema.columns`, dbt `schema.yml`, or `DESCRIBE`. Prefer
   modeled/curated tables (`fct_`, `dim_`, marts) over raw ones.
3. Find each table's **grain** and confirm it:
   `SELECT id, COUNT(*) FROM t GROUP BY id HAVING COUNT(*) > 1 LIMIT 5;` — no rows means `id` is
   unique.
4. Look at 5–10 sample rows and the distinct values of status/type columns before filtering on
   them (`SELECT status, COUNT(*) FROM orders GROUP BY 1`). Check how deleted, test, and refunded
   rows are marked.
5. Check timestamp types and timezones (`timestamp` vs `timestamptz`, UTC vs local).

### 3. Build in steps

6. Write one CTE per step: filter the base table, aggregate to the needed grain, **then** join.
   Aggregating before joining avoids fan-out.
7. After each join, compare the row count with the count before it. A rise you didn't expect means
   a one-to-many join is duplicating rows.
8. Handle NULLs explicitly: `COUNT(col)` skips NULLs, `NOT IN` with a NULL in the subquery
   returns nothing (use `NOT EXISTS`), and `WHERE col <> 'x'` drops NULL rows.
9. Use half-open date ranges: `created_at >= '2026-10-01' AND created_at < '2026-11-01'`, not
   `BETWEEN` with a date that ends at midnight.
10. Divide safely: `x / NULLIF(y, 0)`, and cast to a decimal before dividing integers (Postgres
    `1/3 = 0`).

### 4. Validate and report

11. Cross-check the result: total against a known dashboard number, a sum of segments
    against the total, or one hand-checked entity end to end.
12. Report the answer first, then the query, the assumptions, and the cross-check result.

## Checklist

```text
- [ ] Question restated with time range, timezone, inclusions/exclusions
- [ ] Curated tables preferred; grain of each table confirmed
- [ ] Status/type values and deleted/test rows inspected
- [ ] Aggregated before joining; row counts checked after joins
- [ ] NULL handling explicit; NOT EXISTS over NOT IN
- [ ] Half-open date ranges; timezone stated
- [ ] Safe division with decimals
- [ ] Result cross-checked; assumptions listed
```

## Red Flags

- Joining two fact tables (orders and payments) directly and then summing.
- `SELECT DISTINCT` added to "fix" duplicates.
- Filtering on a status value you haven't seen in the data.
- Reporting a number with no cross-check.
- A query that silently assumes UTC is local time.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The query ran, so it's right." | Fan-out and NULL traps run fine and return wrong numbers. |
| "DISTINCT fixes the duplicates." | It hides the bad join and can drop real duplicate values. |
| "I know this schema." | Status values and soft-delete flags change; 30 seconds of checking is cheap. |
| "Close enough to the dashboard." | Unexplained differences are where the bug lives — explain them. |

## Anti-Patterns (What NOT to do)

* **Writing SQL before knowing the grain** — the main cause of double counting.
* **Summing after a one-to-many join** — aggregate each side first, then join.
* **`BETWEEN '2026-10-01' AND '2026-10-31'` on timestamps** — misses most of the last day.
* **One 200-line query with nested subqueries** — CTEs are checkable step by step.
* **Inventing table or column names** — inspect the schema; ask if access is missing.

## Examples

### Example 1: revenue per customer

**User:** "What was average revenue per paying customer in October? Postgres. Tables: `orders`
(id, customer_id, created_at, status, total_cents) and `order_items` (order_id, sku, qty,
price_cents)."

**Expected output:**

````markdown
**Answer:** $84.12 average revenue per paying customer in October 2026 (UTC), across 12,480
customers. *(Numbers from the run; cross-check below.)*

**Assumptions:** "paying" = at least one order with status `paid` or `shipped`
(`refunded`/`cancelled` excluded); October = 2026-10-01 to 2026-11-01 UTC; revenue =
`orders.total_cents` (includes tax and shipping — say if you want item revenue instead).

```sql
WITH oct_orders AS (
  SELECT customer_id, total_cents
  FROM orders
  WHERE created_at >= '2026-10-01' AND created_at < '2026-11-01'
    AND status IN ('paid', 'shipped')
),
per_customer AS (
  SELECT customer_id, SUM(total_cents) AS revenue_cents
  FROM oct_orders
  GROUP BY customer_id
)
SELECT COUNT(*) AS paying_customers,
       ROUND(AVG(revenue_cents) / 100.0, 2) AS avg_revenue_usd
FROM per_customer;
```

**Why not join order_items?** It's one row per line item; joining it to orders and summing
`total_cents` would count each order once per item.

**Checks:** `orders.id` is unique (0 duplicates); status values seen: paid, shipped, refunded,
cancelled, pending. Total revenue $1,049,818 matches the finance dashboard's October gross
($1.05M).
````

### Example 2: a NOT IN trap

**User:** "Customers who never ordered: `SELECT id FROM customers WHERE id NOT IN (SELECT
customer_id FROM orders)` returns 0 rows, but I know there are some."

**Expected output:**

```text
`orders.customer_id` contains at least one NULL (guest checkouts). `x NOT IN (…, NULL)` is never
true, so every row is filtered out. Use NOT EXISTS, which ignores NULLs:

SELECT c.id
FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

Check: SELECT COUNT(*) FROM orders WHERE customer_id IS NULL; confirms the NULLs.
```

## Quick Reference

| Trap | Fix |
|---|---|
| Unknown grain | `GROUP BY key HAVING COUNT(*) > 1` |
| Join fan-out | Aggregate each side, then join; compare row counts |
| `NOT IN` with NULLs | `NOT EXISTS` |
| Timestamp ranges | `>= start AND < next_start` |
| Integer division | `x * 1.0 / NULLIF(y, 0)` |
| Unseen status values | `SELECT status, COUNT(*) … GROUP BY 1` first |
| Trusting the result | Cross-check against a known number |
