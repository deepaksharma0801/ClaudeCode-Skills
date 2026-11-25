---
name: metric-definition-writer
description: Turns a vague metric like "active users" or "churn" into a precise definition with formula, grain, filters, edge cases, and reference SQL. Use when defining a KPI or when two reports disagree.
---

# Detailed Instructions

A metric isn't defined until two people computing it independently get the same number. Pin down
every choice that changes the result — what counts, over what window, in which time zone, with
which exclusions — write each one down, and ship a reference query that implements exactly that.
Start from the decision the metric informs; most ambiguous choices resolve themselves once the
purpose is clear.

## When to Use

- Defining a KPI for a dashboard, OKR, board deck, or experiment
- "Our dashboard says 41k MAU and the product team says 38k — which is right?"
- Renaming or changing an existing metric
- Documenting metrics for a catalog or semantic layer (dbt metrics, LookML, Cube)

**Don't use when:** the definition is already settled and the question is a wrong number from a
query (use `sql-query-reviewer`), or the question is an experiment result (use `ab-test-readout`).

## Overview

"Active user", "churn", "revenue", and "conversion" each hide a dozen decisions: which events
qualify, calendar vs rolling windows, UTC vs local time, refunds, trials, internal accounts,
deleted users, late-arriving data. Teams that never write these down argue about numbers
instead of decisions. This skill surfaces each decision, records a choice (asking where the
purpose doesn't settle it), lists edge cases, writes reference SQL, and produces a versioned
definition card.

## Workflow Rules

### 1. Purpose and formula

1. **State the purpose:** which decision or review the metric serves, and who reads it.
   "Track whether customers get ongoing value, for the weekly product review."
2. **Write the formula in words** as numerator / denominator, or a single aggregate:
   "distinct users with ≥ 1 qualifying event in the calendar month".

### 2. Pin every choice

3. **Work through this list** and record a decision for each (ask the user when purpose doesn't
   decide it):

   | Choice | Typical options |
   |---|---|
   | Entity and grain | user, account, workspace, order; one value per day/week/month |
   | Qualifying event | any event? key action (created, edited, purchased)? exclude logins, emails opened, background syncs |
   | Window | calendar period vs rolling N days; how partial periods are shown |
   | Time zone | UTC vs company or customer time zone |
   | Exclusions | internal/test accounts, bots, free tier, trials, refunds, chargebacks, deleted users |
   | Money | gross vs net of refunds/discounts/tax; currency conversion rate and date |
   | Dedup and identity | users with several accounts; anonymous → logged-in merges |
   | Late data | when a period is final (e.g. 3 days after it ends) |
   | Denominator (ratios) | who is eligible: all signups? only those who reached step 1? |

4. **Prefer definitions that resist gaming and drift:** a key action over "logged in"; a fixed
   eligibility rule for denominators.

### 3. Edge cases and SQL

5. **List edge cases with the chosen behavior** — e.g. a user active only via API token, an event
   at 23:30 local that's the next day in UTC, a refund issued the following month, an account
   merged mid-period.
6. **Write reference SQL** that implements the definition, with a comment on each line that
   encodes a choice. If the schema is unknown, write against clearly named placeholders and say so.
7. **Sanity-check the number** if you can run it: compare with the existing dashboard and explain
   the difference by listing which choices differ.

### 4. Publish

8. **Produce a definition card** (below), with a version (`mau_v1`). Changing a definition later
   means a new version and a note on when it changed — never silently.

```text
## Metric: <name> — v<n>
Purpose:      <decision it informs, audience>
Formula:      <words>
Choices:      <table of choice → decision>
Edge cases:   <case → behavior>
Reference SQL <query>
Owner / changed: <team>, <date and what changed>
```

## Checklist

```text
- [ ] Purpose and audience stated
- [ ] Formula in words (numerator / denominator)
- [ ] Every choice in the table decided (or asked)
- [ ] Time zone and window explicit
- [ ] Exclusions listed
- [ ] Edge cases with behavior
- [ ] Reference SQL with a comment per choice
- [ ] Compared with existing numbers; differences explained
- [ ] Versioned definition card
```

## Red Flags

- "Active user" with no definition of active.
- No time zone stated.
- Test, internal, and bot accounts not mentioned.
- A definition with no reference query.
- Changing a published definition without a version bump.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Everyone knows what DAU means." | Ask three teams; you'll get three numbers. |
| "Edge cases are rare." | Refunds, merges, and timezone boundaries move the number every month. |
| "The SQL is the definition." | SQL without written intent can't be reviewed or reimplemented. |
| "We'll just update it in place." | Silent changes break trend lines; version and note the change. |

## Anti-Patterns (What NOT to do)

* **Leaving time zone, window, or exclusions implied** — they're the usual source of disagreements.
* **Picking the definition that flatters the number without saying it's a choice.**
* **Mixing grains** — accounts in the numerator, users in the denominator.
* **Silently changing an existing metric** — version it and note the change date.
* **Inventing table or column names** — use the schema or labeled placeholders.

## Examples

### Example 1: defining MAU

**User:** "Define monthly active users for our dashboard."

**Expected output:**

```text
## Metric: Monthly Active Users (MAU) — v1

Purpose: whether customers get ongoing value; weekly product review.
Formula: distinct users with ≥ 1 qualifying event in the calendar month.

| Choice            | Decision                                                            |
|-------------------|---------------------------------------------------------------------|
| Entity / grain    | user_id; one value per calendar month                               |
| Qualifying event  | project_opened, document_edited, comment_created (not login, not email opens) |
| Window / zone     | calendar month in UTC; current month shown as "month to date"       |
| Exclusions        | internal users, test accounts, emails @ourcompany.com, events after a user's deletion |
| Dedup             | distinct user_id; a user in two workspaces counts once              |
| Final             | 3 days after month end (late mobile events)                         |

Edge cases
- Active only via API token → counts (events carry user_id).
- User deleted mid-month → counted for that month if active before deletion.

Reference SQL
SELECT date_trunc('month', e.occurred_at AT TIME ZONE 'UTC') AS month,
       COUNT(DISTINCT e.user_id) AS mau
FROM events e
JOIN users u ON u.id = e.user_id
WHERE e.event_name IN ('project_opened', 'document_edited', 'comment_created')  -- qualifying
  AND NOT u.is_internal AND NOT u.is_test                                       -- exclusions
  AND u.email NOT LIKE '%@ourcompany.com'
  AND (u.deleted_at IS NULL OR e.occurred_at < u.deleted_at)                    -- before deletion
GROUP BY 1
ORDER BY 1;
```

### Example 2: two reports disagree

**User:** "Dashboard says 41,200 MAU for October; the product team's notebook says 37,900. Which is right?"

**Expected output:**

```text
Both are "right" for different definitions. Differences found by reading both queries:

| Choice        | Dashboard                  | Notebook                         | Effect on Oct |
|---------------|----------------------------|----------------------------------|---------------|
| Qualifying    | any event incl. login      | key actions only                 | −2,450        |
| Time zone     | UTC                        | America/Los_Angeles              | −310          |
| Exclusions    | none                       | internal + test users            | −540          |
| Total         | 41,200                     | 37,900                           | −3,300        |

(Effects measured by changing one choice at a time on the dashboard query.)

Recommendation: adopt the notebook's key-action definition as mau_v2 (logins overstate value),
keep UTC for company-wide reporting, apply the exclusions. Publish the card, re-point the
dashboard, and annotate the chart at the switch date.
```

## Quick Reference

| Question | Default unless purpose says otherwise |
|---|---|
| Active means | A key action, not login |
| Window | Calendar period; partial period labeled |
| Time zone | UTC for company metrics; state it |
| Exclusions | Internal, test, bots |
| Revenue | Net of refunds; state tax and currency handling |
| Changing a metric | New version + change date annotation |
| Disagreement | Diff the choices, measure each one's effect |
