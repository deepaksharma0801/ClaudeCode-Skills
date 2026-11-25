---
name: dbt-model-review
description: Reviews dbt models for grain, join fan-out, incremental logic, tests, naming, and documentation before merge. Use when reviewing a dbt PR or writing a new staging, intermediate, or mart model.
compatibility: Assumes dbt Core or dbt Cloud 1.5+. Commands use the dbt CLI.
---

# Detailed Instructions

Every model must have a stated **grain** (one row per what), a test that enforces it, and joins
that can't change it by accident. Check incremental models with extra care, because a bad
`is_incremental()` filter quietly drops or duplicates rows in production for weeks. Review the
layer structure next (sources → staging → intermediate → marts), since putting logic in the
wrong layer is what makes dbt projects hard to change later.

## When to Use

- Reviewing a dbt PR or a new model
- "Why does this mart have duplicates / missing rows?"
- Converting a model to incremental
- Setting up tests and docs for an existing project

**Don't use when:** reviewing one ad-hoc SQL query (use `sql-query-reviewer`), designing pipeline
checks across tools (use `data-quality-checks`), or defining a business metric (use
`metric-definition-writer`).

## Overview

dbt makes SQL modular, but modules still fan out, drift from their grain, and miss late-arriving
data. This skill reads the model and its `schema.yml`, confirms the grain and primary-key tests,
checks each join's cardinality, reviews incremental and snapshot logic, checks layer
conventions and `ref`/`source` use, and runs the model and its tests on a dev target to confirm.

## Workflow Rules

### 1. Grain and keys

1. State the grain from the model's SQL and docs, then require `unique` + `not_null` tests on the
   primary key (or `dbt_utils.unique_combination_of_columns` for composite keys).
2. For each join, note its cardinality (1:1, many:1, 1:many). A 1:many join in a model whose
   grain is the "one" side causes fan-out; aggregate the many side first in a CTE or an
   intermediate model.

### 2. Layers and references

3. **Staging (`stg_`)**: one model per source table — rename, cast, light cleaning only; no joins
   or business logic. **Intermediate (`int_`)**: joins and reusable logic. **Marts (`fct_`,
   `dim_`)**: business-facing, documented.
4. Every table reference uses `{{ ref() }}` or `{{ source() }}` — never hard-coded schema names,
   which break lineage and environments.
5. Sources have `freshness` checks where timeliness matters.

### 3. Incremental models

6. Check the `is_incremental()` filter handles **late-arriving data**: use a lookback
   (`where updated_at > (select max(updated_at) from {{ this }}) - interval '3 days'`) rather than
   a strict `>` on event time.
7. Set `unique_key` so reprocessed rows merge instead of duplicating, and confirm the
   `incremental_strategy` (merge, delete+insert, insert_overwrite) suits the warehouse.
8. Know how to rebuild: `dbt run --full-refresh -s model` and how long that takes.
9. Schema changes: set `on_schema_change` deliberately (`append_new_columns` or `fail`).

### 4. Tests and docs

10. Beyond keys: `relationships` for foreign keys, `accepted_values` for status columns, and a
    row-count or recency test for critical marts. Use `severity: warn` for soft checks.
11. Document the model and every column that a business user would read; add the grain to the
    model description.

### 5. Verify

12. Run on a dev target: `dbt build -s +model_name` (builds the model, its parents, and their
    tests), and compare row counts with the previous version
    (`select count(*), count(distinct pk)`).

## Checklist

```text
- [ ] Grain stated; PK unique + not_null tests
- [ ] Every join's cardinality known; no fan-out
- [ ] Layer conventions: stg rename/cast only, logic in int/marts
- [ ] Only ref()/source(); source freshness where needed
- [ ] Incremental: lookback for late data, unique_key, strategy, full-refresh plan
- [ ] on_schema_change set deliberately
- [ ] relationships / accepted_values / recency tests
- [ ] Model and key columns documented
- [ ] dbt build -s +model passes; row counts compared
```

## Red Flags

- A mart with no `unique` test on its key.
- `select distinct` at the end of a model.
- `where event_at > (select max(event_at) from {{ this }})` with no lookback.
- `from analytics.raw_orders` instead of `source()`.
- Joins and business logic in a `stg_` model.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The key is obviously unique." | Upstream changes make it not unique; a test catches it on the next run. |
| "DISTINCT cleans up the duplicates." | It hides a fan-out and costs a sort on every run. |
| "Late data is rare." | Mobile events, retries, and backfills arrive late every day. |
| "Docs can come later." | Undocumented marts get misused and re-derived differently. |

## Anti-Patterns (What NOT to do)

* **Business logic in staging** — every downstream model inherits it and it can't be reused cleanly.
* **Incremental without `unique_key`** — reruns duplicate rows.
* **Hard-coded schemas** — breaks dev/prod environments and lineage.
* **Huge single models with 15 CTEs** — split reusable steps into intermediate models.
* **Tests only on staging** — marts need their own grain tests after joins.

## Examples

### Example 1: an incremental order fact

**User:** "Review this model."

```sql
{{ config(materialized='incremental') }}
select o.order_id, o.created_at, o.customer_id, p.amount
from analytics.raw_orders o
join {{ ref('stg_payments') }} p on p.order_id = o.order_id
{% if is_incremental() %}
where o.created_at > (select max(created_at) from {{ this }})
{% endif %}
```

**Expected output:**

```markdown
1. **Fan-out — High.** An order can have several payments (partial captures, retries), so the
   grain becomes one row per payment while the name `fct_orders` promises one per order.
   Aggregate first:
       payments as (select order_id, sum(amount) as amount_paid
                    from {{ ref('stg_payments') }} group by 1)
2. **No unique_key — High.** Reruns append duplicates. Add `unique_key='order_id'`.
3. **Late data dropped — High.** Strict `>` on `created_at` misses orders whose payment lands
   later, and never revisits updated orders. Filter on `updated_at` with a lookback:
       where o.updated_at > (select max(updated_at) from {{ this }}) - interval '3 days'
4. **Hard-coded source — Medium.** Use `{{ ref('stg_orders') }}` (or `source()`).
5. **Tests missing — Medium.** Add to schema.yml: `order_id: [unique, not_null]`,
   `relationships` to `dim_customers`.
Verify: `dbt build -s +fct_orders`, then compare `count(*)` vs `count(distinct order_id)`.
```

### Example 2: duplicates in a dimension

**User:** "`dim_customers` started failing its unique test today."

**Expected output:**

```text
Find the duplicated keys and what differs between their rows:
  select customer_id, count(*) from {{ ref('dim_customers') }} group by 1 having count(*) > 1 limit 10;
Then diff two rows for one id. Usual causes: a new join to a 1:many table (addresses, plans),
or the source started sending multiple rows per customer (check stg_customers' own unique test).
Fix at the source of the fan-out — pick one row (latest by updated_at with row_number()) or
aggregate — and don't remove the unique test.
```

## Quick Reference

| Check | How |
|---|---|
| Grain | Stated in docs + `unique`/`not_null` on PK |
| Fan-out | Aggregate the many side before joining |
| Layers | stg = rename/cast, int = joins, marts = business |
| References | `ref()` / `source()` only |
| Incremental | Lookback filter, `unique_key`, full-refresh plan |
| Tests | relationships, accepted_values, recency |
| Verify | `dbt build -s +model`; count vs distinct PK |
