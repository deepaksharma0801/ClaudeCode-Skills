---
name: funnel-analysis
description: Builds conversion funnels with ordered steps, conversion windows, and per-step drop-off, then finds where and for whom users drop. Use for signup, checkout, or onboarding drop-off.
---

# Detailed Instructions

A funnel number is meaningless without its definition: which events, in what order, within what
time window, counted per user or per session. Define those first, then find the step that loses
the most users and the segment where it is worst.
Counting events independently of order produces "funnels" where later steps exceed earlier
ones, and unbounded windows count users who converted months later. Both look plausible and both
are wrong.

## When to Use

- "Where are we losing users in signup / checkout / onboarding?"
- Comparing conversion across devices, channels, or countries
- Validating that a funnel dashboard is computed correctly
- Before designing an experiment on a step

**Don't use when:** the question is whether users return over time (use
`cohort-retention-analysis`), or whether a change caused an improvement (use `ab-test-readout`).

## Overview

Funnel analysis goes wrong in quiet ways: counting step events regardless of order, letting a user
convert six months later, mixing users and sessions, or comparing a funnel across a period where
tracking changed. This skill pins the definition, writes the query (SQL with ordered steps and a
window), computes step and overall conversion, and breaks drop-off down by segment.

## Workflow Rules

1. **Define the funnel:**
   - **Steps:** 3–6 events in order, with exact event names (`viewed_pricing` → `started_checkout`
     → `entered_payment` → `purchased`).
   - **Unit:** users (default) or sessions.
   - **Window:** maximum time from step 1 to the last step (e.g. 7 days), and the entry period
     (users who entered step 1 in a date range).
   - **Ordering:** strict (each step after the previous one) — the default.
2. **Write the query** with each step's timestamp required to follow the previous step's, within
   the window from step 1. Use the first step-1 event in the entry period per user. Prefer
   `MIN(timestamp)` per step joined in order, or the warehouse's funnel function if one exists
   (e.g. `windowFunnel` in ClickHouse).
3. **Report for each step:** users reaching it, conversion from the previous step, conversion
   from step 1, and the median time from the previous step.
4. **Find the biggest leak:** the step with the largest absolute loss of users, not just the
   lowest percentage.
5. **Segment that step** by 2–4 dimensions likely to matter (device, traffic source, country,
   plan, new vs returning). Show only segments with enough users to compare (say n ≥ 100 at the
   step). Flag differences that are large and not explained by sample size.
6. **Check tracking** before concluding: an event that fires twice, was renamed, or is missing on
   one platform can fake a drop-off. Compare event counts over time around the step.
7. **Report:** definition, funnel table, biggest leak, segment finding, tracking caveats, and one
   or two hypotheses to test — not conclusions about why users leave.

## Checklist

```text
- [ ] Steps (exact event names), unit, window, entry period, and ordering defined
- [ ] Query enforces order and window; counts distinct units
- [ ] Per-step and overall conversion, plus time between steps
- [ ] Biggest absolute leak identified
- [ ] Leak segmented by 2–4 dimensions with n ≥ 100
- [ ] Tracking checked around the leak (duplicates, renames, platform gaps)
- [ ] Hypotheses to test, not causes asserted
```

## Red Flags

- A later step has more users than an earlier one.
- "Conversion is 3% — must be the form." (No segment or tracking check.)
- Window "all time".
- Mixing sessions and users in one table.

## Anti-Patterns (What NOT to do)

* Do not count step events independently of order (a "funnel" where step 3 exceeds step 2).
* Do not leave the conversion window unbounded.
* Do not mix user-level and session-level counts in one funnel.
* Do not present a cause ("the form is confusing") as a finding; funnels show where, not why.
* Do not compare funnels across a tracking change without saying so.

## Examples

### Example 1: a checkout funnel

**User:** "Where are we losing people in checkout?" *(Postgres table `events(user_id, event, occurred_at, device)`)*

**Expected output:**

```text
Definition: users entering checkout (viewed_cart) Nov 1–14; strict order; 7-day window from
viewed_cart; first entry per user.

WITH s1 AS (
  SELECT user_id, MIN(occurred_at) AS t1
  FROM events WHERE event = 'viewed_cart' AND occurred_at >= '2026-11-01' AND occurred_at < '2026-11-15'
  GROUP BY user_id
), s2 AS (
  SELECT s1.user_id, s1.t1, MIN(e.occurred_at) AS t2
  FROM s1 JOIN events e ON e.user_id = s1.user_id AND e.event = 'started_checkout'
   AND e.occurred_at > s1.t1 AND e.occurred_at <= s1.t1 + interval '7 days'
  GROUP BY s1.user_id, s1.t1
), s3 AS (
  SELECT s2.user_id, s2.t1, MIN(e.occurred_at) AS t3
  FROM s2 JOIN events e ON e.user_id = s2.user_id AND e.event = 'entered_payment'
   AND e.occurred_at > s2.t2 AND e.occurred_at <= s2.t1 + interval '7 days'
  GROUP BY s2.user_id, s2.t1
), s4 AS (
  SELECT DISTINCT s3.user_id
  FROM s3 JOIN events e ON e.user_id = s3.user_id AND e.event = 'purchased'
   AND e.occurred_at > s3.t3 AND e.occurred_at <= s3.t1 + interval '7 days'
)
SELECT (SELECT count(*) FROM s1) AS cart, (SELECT count(*) FROM s2) AS checkout,
       (SELECT count(*) FROM s3) AS payment, (SELECT count(*) FROM s4) AS purchased;

| Step             | Users  | From previous | From start |
|------------------|--------|---------------|------------|
| viewed_cart      | 18,400 | —             | 100%       |
| started_checkout | 9,936  | 54.0%         | 54.0%      |
| entered_payment  | 7,452  | 75.0%         | 40.5%      |
| purchased        | 5,589  | 75.0%         | 30.4%      |

Biggest leak: cart → checkout loses 8,464 users (46%).

Segment at that step (cart → checkout):
| Device  | Users at cart | Converted |
|---------|---------------|-----------|
| desktop | 7,900         | 66.1%     |
| mobile  | 10,500        | 44.9%     |

Mobile converts 21 points lower at this step; the gap is far outside sampling noise at these sizes.
Tracking check: started_checkout counts on mobile are stable across the period (no release gap).

Hypotheses to test: the mobile cart's checkout button placement; forced account creation on mobile.
```

### Example 2: a funnel that goes up

**User:** "Our dashboard funnel shows 10,000 cart views → 6,100 checkout starts → 6,400 payment pages. How can step 3 be bigger?"

**Expected output:**

```text
A strict funnel can't grow, so this one counts events independently. Checked:
- payment_page_viewed fires on page load and again on every card-validation error (event counts
  per user: median 1, p90 3) → counted twice for many users.
- Some users reach the payment page from a saved "Buy again" link without starting checkout, so
  they never had step 2.

Recomputed as a strict, per-user, 24-hour funnel from cart view:
cart 10,000 → checkout 6,100 (61.0%) → payment 5,380 (88.2%) → purchased 4,410 (82.0%)

Also fix tracking: fire payment_page_viewed once per page view (dedupe on page_view_id), and
document the "Buy again" path as a separate funnel.
```

## Quick Reference

| Rule | Default |
|---|---|
| Unit | Distinct users |
| Order | Strict: each step after the previous |
| Window | Bounded from step 1 (e.g. 1 or 7 days) |
| Biggest leak | Largest absolute loss, not lowest % |
| Segments | Only with n ≥ 100 at the step |
| Step count grows | Tracking or ordering bug |
