---
name: data-quality-checks
description: Designs automated data quality tests for a table or pipeline: freshness, volume, uniqueness, nulls, ranges, and referential integrity. Use when building a pipeline or after bad data reached a report.
---

# Detailed Instructions

Test the assumptions downstream users rely on, and make every check fail loudly with a clear
message. Each check states the rule, why it matters, and what happens when it fails.

## Overview

Bad data rarely crashes a pipeline; it flows quietly into dashboards. This skill reads a table's
schema and purpose, proposes a focused set of checks grouped by the classic dimensions, assigns a
severity (block the pipeline vs warn), and writes them in the user's tool — dbt tests, Great
Expectations, Soda, or plain SQL assertions.

## Workflow Rules

1. Identify the table, its **grain** (one row per what), who consumes it, and how it is loaded
   (full refresh, incremental, streaming).
2. Propose checks across these dimensions, only where they apply:
   - **Freshness:** max(loaded_at or event time) within an expected lag.
   - **Volume:** row count for the latest load within a range of recent loads (e.g. ±30% of the
     7-day median), and never zero.
   - **Uniqueness:** the grain's key is unique.
   - **Completeness:** required columns not null; null rate of optional columns below a threshold.
   - **Validity:** accepted values for enums, numeric ranges, date sanity (not in the future,
     not before the company existed), formats (emails, currency codes).
   - **Referential integrity:** foreign keys exist in the parent table.
   - **Consistency:** totals reconcile with the source system or an upstream table within tolerance.
3. Give each check a **severity**: `error` (stop the pipeline / block publishing) or `warn` (alert
   only). Grain and freshness checks are usually `error`.
4. Use thresholds derived from history when possible; if no history is available, say the
   threshold is an initial guess to tune.
5. Write the checks in the user's tool. Default to dbt `schema.yml` tests plus SQL for checks dbt
   lacks; otherwise plain SQL queries that return failing rows.
6. Say where each check runs (after load, before publish) and who is alerted.
7. If investigating a past incident, add a check that would have caught it, and name it after the
   failure mode.

## Anti-Patterns (What NOT to do)

* Do not add `not_null` and `unique` to every column by reflex. Test the assumptions that matter.
* Do not make every check blocking; alert fatigue makes people ignore real failures.
* Do not hard-code exact row counts that will fail on normal growth.
* Do not write checks that silently pass on an empty table.
* Do not invent column names; use the schema provided or say what is assumed.

## Examples

**User:** "Add tests to our `fct_orders` dbt model. Last week a duplicate load doubled revenue on the dashboard."

**Expected output:**

```yaml
# models/marts/schema.yml
models:
  - name: fct_orders
    description: One row per order. Loaded incrementally every hour.
    tests:
      - dbt_utils.recency:              # freshness
          datepart: hour
          field: loaded_at
          interval: 3
          config: { severity: error }
    columns:
      - name: order_id
        tests:
          - unique:                     # grain — would have caught last week's duplicate load
              config: { severity: error }
          - not_null
      - name: customer_id
        tests:
          - not_null
          - relationships:              # referential integrity
              to: ref('dim_customers')
              field: customer_id
              config: { severity: warn }
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'paid', 'refunded', 'cancelled']
      - name: amount_cents
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10000000       # initial guess; tune from history
```

```sql
-- tests/fct_orders_daily_volume.sql  (warn): yesterday's orders within ±30% of the prior 7-day median
with daily as (
  select date(created_at) as d, count(*) as n
  from {{ ref('fct_orders') }}
  where created_at >= current_date - 8
  group by 1
), baseline as (
  select percentile_cont(0.5) within group (order by n) as median_n
  from daily where d < current_date
)
select d, n, median_n
from daily, baseline
where d = current_date - 1
  and (n < 0.7 * median_n or n > 1.3 * median_n)
```

Runs: `dbt build --select fct_orders` after each hourly load; `error` tests block downstream
models, `warn` tests post to #data-alerts.
