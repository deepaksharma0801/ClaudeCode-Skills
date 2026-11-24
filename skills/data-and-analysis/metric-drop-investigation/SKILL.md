---
name: metric-drop-investigation
description: Investigates why a business metric dropped or spiked by ruling out data bugs, checking seasonality, and decomposing by segment and formula. Use when asked why signups, revenue, or conversion changed.
---

# Detailed Instructions

Before explaining a metric move, prove it's real, then prove it's unusual, then find **where** it
happened before guessing **why**. Most "drops" are a broken pipeline, a tracking change, a
holiday, or a mix shift, and confident causal stories about them waste a week of
work.

## When to Use

- "Why did signups / revenue / DAU / conversion drop (or jump) this week?"
- An anomaly alert on a dashboard metric
- A metric moved after a release, campaign, or pricing change
- Preparing an answer for leadership about a KPI change

**Don't use when:** the change was caused by a controlled experiment (use `ab-test-readout`), the
question is about a funnel step specifically (use `funnel-analysis` once the drop is localized),
or the issue is a production outage (use `log-triage` / `incident-postmortem`).

## Overview

The usual failure is jumping from "the chart went down" to a story ("the new onboarding hurt
conversion") without checking the data or the base rate. This skill runs a fixed order: verify the
data, size the change against normal variation, decompose the metric into its formula and
segments to find where the change is concentrated, line it up against a timeline of known events,
and report the finding with a confidence level and the next check.

## Workflow Rules

### 1. Is it real? (data checks first)

1. **Freshness and completeness:** is the latest period partial? Did the pipeline run? Compare row
   counts per day against the prior weeks. A "drop" today is often a day that hasn't finished
   loading.
2. **Definition and tracking changes:** check for recent changes to the metric SQL, event
   names, SDK versions, bot filters, or consent banners. A tracking change shows up as a drop
   concentrated on one platform or app version, starting on a release date.
3. **Cross-check against an independent source** (billing system vs. analytics, backend events vs.
   client events). If only one source moved, suspect the data.

### 2. Is it unusual?

4. Compare against **the same period last week and last year**, and the normal range (e.g. the
   min–max or ±2 standard deviations of the last 8 same-weekdays). Holidays, paydays, month-ends,
   and school terms explain many moves.
5. State the size: absolute and relative change, and whether it is outside normal variation. If
   it isn't, say so and stop.

### 3. Where is it? (decompose)

6. **Break the metric into its formula.** Revenue = users × conversion × orders per buyer ×
   average order value. Signups = visits × signup rate. Find which factor moved.
7. **Segment** by platform, country, channel, new vs. returning, plan, app version. Compute each
   segment's contribution to the total change (segment Δ ÷ total Δ), not just its % change — a
   small segment can drop 50% and not matter.
8. **Check mix shift:** if every segment's rate is flat but the total moved, the share of traffic
   changed (e.g. more low-converting paid traffic). That's a different story from "conversion fell".

### 4. Why? (match to events)

9. Build a short timeline of releases, experiments, campaigns, pricing changes, outages, and
   external events around the onset. Match the **onset time and the segment** to an event: a drop
   on Android only, starting the day v5.2 rolled out, points at v5.2.
10. Treat the cause as a hypothesis until something confirms it: the effect reverses when the
    change reverts, or the mechanism shows up in the data (e.g. error events from the new form).

### 5. Report

11. Lead with the answer and confidence: what moved, by how much, where, the likely cause, how
    sure (confirmed / likely / unknown), and the next check. Include the data caveats.

## Checklist

```text
- [ ] Latest period complete; pipeline ran; row counts normal
- [ ] No metric-definition or tracking changes (or found one)
- [ ] Cross-checked with an independent source
- [ ] Compared to last week, last year, and the normal range
- [ ] Metric decomposed into formula factors
- [ ] Segments ranked by contribution to the change; mix shift checked
- [ ] Onset and segment matched to a timeline of events
- [ ] Cause labeled confirmed / likely / unknown, with the next check
```

## Red Flags

- Explaining the drop before checking the latest day is complete.
- Quoting "% change by segment" without contribution to the total.
- A cause that matches the timing but not the segment (drop everywhere, change shipped to iOS only).
- "It's probably seasonality" with no year-over-year comparison.
- One day's move treated as a trend.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The release was that day, so it's the release." | Timing alone is weak. Check the release's segment and mechanism. |
| "The data is fine, it's from the dashboard." | Dashboards break silently; partial days and tracking changes are the most common cause. |
| "Every segment dropped a bit, so it's broad." | Check mix shift — flat rates with a changing mix give the same total. |
| "Leadership needs an answer now." | "Likely X, confirming by Y" is an answer. A wrong certain one costs more. |

## Anti-Patterns (What NOT to do)

* **Skipping data checks** — a broken pipeline looks exactly like a business problem.
* **Ranking segments by % change** — rank by contribution to the total change.
* **Comparing to yesterday only** — weekday and seasonal patterns make that comparison noisy.
* **Presenting a hypothesis as confirmed** — label confidence and name the confirming check.
* **Slicing by 30 dimensions until something looks odd** — with enough slices something always does; start from the formula and the timeline.

## Examples

### Example 1: signups down 18%

**User:** "Signups were 4,100 last week vs 5,000 the week before. Why?"

**Expected output:**

```markdown
**Answer:** Signups fell 900 (−18%), outside the normal weekly range (4,700–5,300 over the last
8 weeks). The drop is almost entirely Android app signups, starting Tue Nov 18 — the day app
v5.2 reached 100%. **Likely cause: v5.2's signup form (confidence: likely).**

**Data checks**
- Pipeline complete for all 7 days; web and backend user-created counts agree (4,108 vs 4,100).
- No change to the signup metric definition.

**Decomposition**
- Visits to signup screen: 41,000 → 40,200 (−2%) — not the driver.
- Signup rate: 12.2% → 10.2%.

| Segment | Before | After | Δ | Share of total Δ |
|---|---|---|---|---|
| Android | 1,600 | 820 | −780 | 87% |
| iOS | 1,500 | 1,440 | −60 | 7% |
| Web | 1,900 | 1,840 | −60 | 7% |
| **Total** | 5,000 | 4,100 | −900 | 100% |

(Rounding: 87 + 7 + 7 = 101%.)

**Why v5.2:** Android signups dropped only on v5.2 (v5.1 users unchanged), and `signup_error`
events with code `phone_format` rose from ~30/day to ~410/day on v5.2.

**Next check:** reproduce the phone-number validation on v5.2 with a non-US number; if confirmed,
hotfix and watch Android signups recover.
```

### Example 2: a "drop" that isn't one

**User:** "Revenue today is down 40% vs yesterday! What happened?"

**Expected output:**

```text
Probably nothing yet:
- Today is partial: it's 14:00 UTC and the revenue table is loaded hourly. At this hour on the last
  4 Mondays, revenue was 55–60% of the day's final total, so "−40%" is roughly what a normal
  partial day looks like.
- Yesterday was Sunday's peak; Mondays are typically 10% lower.

Compare like with like: today until 14:00 vs. last Monday until 14:00 is −3%, inside normal range.
Re-check tomorrow with the full day before investigating further.
```

## Quick Reference

| Step | Question | Tool |
|---|---|---|
| Real? | Complete, unchanged definition, matches another source? | Row counts, change log, second source |
| Unusual? | Outside last week / last year / normal range? | Same-weekday comparison |
| Where? | Which factor, which segment, or mix? | Formula decomposition, contribution share |
| Why? | Which event matches onset **and** segment? | Release / campaign timeline |
| Report | What, how much, where, cause, confidence, next check | Answer-first summary |
