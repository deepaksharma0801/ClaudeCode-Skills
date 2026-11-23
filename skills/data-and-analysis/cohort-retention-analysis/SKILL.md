---
name: cohort-retention-analysis
description: Builds and interprets cohort retention tables from event or order data, without fake drop-offs from incomplete periods. Use for retention, churn, stickiness, or "are users coming back" questions.
compatibility: Bundled script requires Python 3.8+ (standard library only).
---

# Detailed Instructions

Pick the retention definition before computing anything, and never compare a cohort's unfinished
period with older cohorts' finished ones. Most "retention is collapsing" charts are incomplete
recent periods.
The definition (what counts as active, which period, cohort by signup or first activity) changes
the numbers more than any product change will, so it is fixed and written down before the table
is built.

## When to Use

- "Are users coming back?", "what's our retention / churn / stickiness?"
- Judging whether a product or onboarding change improved retention
- Repeat-purchase behavior from orders data
- Investigating a retention chart that "suddenly dropped"

**Don't use when:** the question is a single conversion step (use `funnel-analysis`) or an
experiment between two arms (use `ab-test-readout`, then this skill per arm if needed).

## Overview

Retention answers "of the people who started in period X, how many were still active N periods
later?" The answer depends on choices people rarely state: what counts as active, weekly vs
monthly periods, cohort by signup or by first activity, classic (active in period N) vs rolling
(active in N or later). This skill fixes those choices, builds the table with
`scripts/retention.py`, and reads it correctly.

## Workflow Rules

1. **Define it** in one line each, and confirm with the user if unclear:
   - **Cohort:** signup date, or first qualifying event.
   - **Active:** which event counts (purchase, session, key action) — "logged in" overstates value.
   - **Period:** week for products used weekly or more, month for monthly or less (billing, purchases).
   - **Type:** classic N-period retention (default) or rolling/unbounded (active in N *or later*).
2. **Prepare the data** as a CSV of qualifying events with at least a user ID and a timestamp
   (one row per event). Exclude internal and test users first. In SQL, export only the columns needed.
3. **Build the table:**
   `python3 scripts/retention.py events.csv --user-col user_id --time-col occurred_at --period week --max-periods 8`
   Add `--cohort-col signed_up_at` to cohort by signup instead of first event.
   Periods that have not fully elapsed are left blank on purpose.
4. **Read it in three directions:**
   - Along a row: the cohort's retention curve. Does it **flatten** (a retained core) or keep
     decaying toward zero?
   - Down a column: is W1 or M1 improving for newer cohorts? That is the signal that product
     changes work.
   - The weighted average row: the overall curve, weighted by cohort size.
5. **Check before concluding:** small cohorts (< ~100 users) are noisy — say so; seasonal cohorts
   (holiday signups) behave differently; a change in what counts as "active" breaks comparisons.
6. **Report:** the definition, the table (or the first 8 periods), 3–5 findings tied to numbers,
   and caveats. For a chart, plot one line per cohort (or the average) with periods on the x-axis.

## Checklist

```text
- [ ] Cohort, active event, period, and classic vs rolling decided and written down
- [ ] Internal/test users excluded
- [ ] Ran scripts/retention.py; incomplete periods left blank
- [ ] Read rows (curve shape), columns (newer vs older cohorts), and the weighted average
- [ ] Small cohorts and seasonal cohorts flagged
- [ ] Findings tied to numbers, with caveats
```

## Red Flags

- "The latest cohort's month 1 is way down — retention is collapsing."
- "Active = logged in."
- "Average the cohort percentages."
- "W1 went from 44% to 47% — the redesign worked." (with 70-user cohorts)

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Partial periods are close enough." | A period that's half over shows roughly half the activity. Blank it. |
| "Logins are a fine proxy." | Logins include auto-logins and bounces; they overstate retained value. |
| "Simple average is fine." | It weights a 13-user cohort the same as a 900-user one. Weight by size. |

## Anti-Patterns (What NOT to do)

* Do not compute retention for periods that have not ended; the latest cohorts will look like they churned.
* Do not use "any login" as active without saying it overstates engagement.
* Do not average cohort percentages without weighting by cohort size.
* Do not mix classic and rolling retention between charts or teams.
* Do not call a 2–3 point change between small cohorts a trend.

## Examples

### Example 1: did the redesign help?

**User:** "Here's our events export. Is retention getting better since the October onboarding redesign?" *(events.csv: user_id, occurred_at, event)*

**Expected output:**

```text
Definition: cohort = first qualifying event week (Mon–Sun, data time zone); active = any
"project_edited" event; classic weekly retention. Internal users excluded (31 removed).

$ python3 scripts/retention.py edits.csv --user-col user_id --time-col occurred_at --max-periods 6

| cohort     | users | W0     | W1    | W2    | W3    | W4    | W5    | W6    |
|------------|-------|--------|-------|-------|-------|-------|-------|-------|
| 2026-09-07 | 79    | 100.0% | 44.3% | 48.1% | 36.7% | 39.2% | 30.4% | 12.7% |
| 2026-09-14 | 65    | 100.0% | 56.9% | 41.5% | 50.8% | 38.5% | 29.2% | 26.2% |
| ...        |       |        |       |       |       |       |       |       |
| 2026-10-26 | 82    | 100.0% | 41.5% | 42.7% |       |       |       |       |
| weighted   | 600   | 100.0% | 46.2% | 45.8% | 37.5% | 36.9% | 31.0% | 21.2% |

Findings
1. W1 retention has not improved since the redesign: 48.4% for the 4 September cohorts (312 users)
   vs 43.8% for the 4 October cohorts (288 users), weighted. The 4.6-point gap is within noise
   at these sizes (95% CI roughly ±8 points), so: no detectable change.
2. Curves have not flattened by W6 (21.2%) — users are still leaving; there is no stable core yet.
3. Cohorts are 65–90 users, so week-to-week swings of ±8 points are within noise.

Caveats: the newest cohorts have only 2–3 complete weeks (blank cells are not drop-off).
Next step: compare W1 for users who completed the new onboarding vs those who skipped it.
```

### Example 2: "why are cells blank?"

**User:** "Monthly retention by first purchase month please. Why are some cells empty?" *(data through 2026-11-20)*

**Expected output:**

```text
$ python3 scripts/retention.py orders.csv --user-col customer_id --time-col ordered_at --period month --max-periods 2 --format csv
cohort,users,M0,M1,M2
2026-09-01,254,100.0%,83.1%,
2026-10-01,333,100.0%,,
2026-11-01,13,,,
weighted avg,600,100.0%,83.1%,

Blank cells are periods that haven't finished yet, not churn:
- October's M1 is November, which runs to Nov 30; data ends Nov 20.
- November's M0 is still in progress, so even it is blank.
Only September has a complete M1 (83.1% of 254 customers ordered again in October).
Re-run after Dec 1 for October's M1. Until then, don't compare cohorts on M1.
```

## Quick Reference

| Choice | Default |
|---|---|
| Period | Week for weekly-use products; month for purchases/billing |
| Active | A key action, not login |
| Type | Classic (active in period N) unless stated |
| Incomplete periods | Blank, never zero |
| Averages | Weighted by cohort size |
| Small cohorts | < ~100 users → call it noisy |
