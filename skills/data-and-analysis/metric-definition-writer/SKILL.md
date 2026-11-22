---
name: metric-definition-writer
description: Turns a vague metric like "active users" or "churn" into a precise definition with formula, grain, filters, edge cases, and SQL. Use when defining a KPI or when two reports disagree on a number.
---

# Detailed Instructions

A metric is not defined until two people computing it independently get the same number. Pin
down every choice that changes the result, and write it down.

## Overview

Teams argue about numbers because "active user" or "monthly revenue" hides a dozen decisions:
which events count, which time zone, whether refunds or test accounts are excluded. This skill
surfaces each decision, records a choice (or asks), and produces a definition card plus a
reference query.

## Workflow Rules

1. Restate the metric's **purpose**: what decision it informs. This settles most ambiguous choices.
2. Define the **formula** as numerator / denominator (or a single aggregate), in words.
3. Pin down each of these explicitly:
   - **Entity and grain:** user, account, order; one row per what per when.
   - **Qualifying event:** which actions count (login? any API call? a purchase?).
   - **Time window and zone:** calendar month vs rolling 30 days; UTC vs business time zone; how
     partial periods are shown.
   - **Exclusions:** internal and test accounts, bots, refunds, chargebacks, free tiers, deleted users.
   - **Dedup and attribution:** how repeat events and multi-account users are handled.
   - **Late data:** when a period is considered final.
4. List **edge cases** with the chosen behavior (user active on the 31st in one zone and the 1st in
   another; refund issued next month).
5. Write a **reference SQL** query that implements the definition, with each choice commented.
6. If two existing reports disagree, list which of the choices above differs between them.
7. Output a definition card the team can paste into a metrics catalog.

## Anti-Patterns (What NOT to do)

* Do not leave the time zone, window, or exclusions implied.
* Do not pick a definition that flatters the number without saying it is a choice.
* Do not mix grains (counting accounts in the numerator and users in the denominator).
* Do not silently change an existing metric's definition; version it (`active_users_v2`).
* Do not invent table or column names. If the schema is unknown, write the SQL against named placeholders and say so.

## Examples

**User:** "Define monthly active users for our dashboard."

**Expected output:**

```text
## Metric: Monthly Active Users (MAU) — v1

Purpose: track whether customers are getting ongoing value, for the weekly product review.

Formula: count of distinct users with >= 1 qualifying event in the calendar month.

| Choice            | Decision                                                       |
|-------------------|----------------------------------------------------------------|
| Entity / grain    | user_id; one value per calendar month                          |
| Qualifying event  | any of: project_opened, document_edited, comment_created (not login, not email opens) |
| Window / zone     | calendar month in UTC; current month shown as "month to date"  |
| Exclusions        | is_internal = true, email ending @ourcompany.com, accounts flagged as test, events after a user's deletion |
| Dedup             | distinct user_id; a user in two workspaces counts once         |
| Final             | month is final 3 days after it ends (late mobile events)       |

Edge cases
- User acts only via API token → counts (events carry user_id).
- User deleted later in the month → excluded from all months after deletion, kept before.

Reference SQL
SELECT date_trunc('month', e.occurred_at AT TIME ZONE 'UTC') AS month,
       COUNT(DISTINCT e.user_id) AS mau
FROM events e
JOIN users u ON u.id = e.user_id
WHERE e.event_name IN ('project_opened', 'document_edited', 'comment_created')  -- qualifying
  AND NOT u.is_internal AND NOT u.is_test                                       -- exclusions
  AND u.email NOT LIKE '%@ourcompany.com'
  AND (u.deleted_at IS NULL OR e.occurred_at < u.deleted_at)                  -- drop events after deletion
GROUP BY 1
ORDER BY 1;
```
