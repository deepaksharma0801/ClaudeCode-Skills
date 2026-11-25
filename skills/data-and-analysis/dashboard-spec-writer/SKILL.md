---
name: dashboard-spec-writer
description: Writes a dashboard spec from the decisions it supports, with defined metrics, chart choices, filters, layout, and alerts. Use when designing a new dashboard or cleaning up a cluttered one.
---

# Detailed Instructions

Start from the decisions, not the data: who opens this dashboard, how often, and what they will
do differently based on what they see. Every tile must answer a question that leads to an
action, use a defined metric, and show its comparison (target, last period, or normal range).
A dashboard that answers no specific question gets opened once and then ignored, and one with
40 tiles hides the one number that matters.

## When to Use

- "Design a dashboard for X" / "what should our ops / sales / product dashboard show?"
- Writing a spec for an analyst or BI developer to build in Looker, Tableau, Metabase, Grafana,
  or similar
- Cleaning up a dashboard nobody uses or everyone argues about
- Deciding which metrics deserve alerts instead of a chart

**Don't use when:** critiquing one existing chart's design (use `chart-critique`), defining a
single metric precisely (use `metric-definition-writer`, then reference it here), or building a
one-off analysis (a notebook or memo is better than a dashboard).

## Overview

Most dashboards are built bottom-up: every available field becomes a chart. This skill works
top-down — audience and decisions, then the few questions those decisions need, then one tile
per question with a defined metric, a chart type chosen for the comparison, filters,
and a layout that puts the most important number top-left. It ends with alert thresholds for
anything that needs attention faster than someone would look.

## Workflow Rules

### 1. Audience and decisions

1. Write down the **audience**, **cadence** (live ops screen, daily check, weekly review), and
   **2–4 decisions** the dashboard supports ("Do we need to add support staff this week?").
   If there's no decision, question whether a dashboard is the right output.

### 2. Questions → metrics

2. For each decision, list the questions it needs answered, then the metric for each. Every
   metric gets a definition: formula, filters, grain, source table, owner — or a link to its
   `metric-definition-writer` entry.
3. Give every number a **comparison**: target, same period last week/year, or normal range. A
   number with no comparison can't tell the reader whether to act.

### 3. Tiles

4. Pick the chart from the comparison:

| Comparison | Chart |
|---|---|
| One number vs. target or last period | Big number with delta and sparkline |
| Trend over time | Line chart (bars for few periods) |
| Parts of a whole, ≤ 5 parts | Stacked bar; avoid pie for more than 3 |
| Ranking | Horizontal bar, sorted |
| Two metrics' relationship | Scatter |
| Exact lookups | Table, limited rows, sorted by importance |

5. Label each tile with the question it answers ("Are tickets waiting too long?") and the time
   window and timezone.

### 4. Layout and filters

6. **Layout top to bottom:** headline numbers (the 3–5 that answer "is everything OK?"), then
   trends, then breakdowns for diagnosis. Top-left is the most important tile.
7. **Filters:** only the ones the audience actually uses (date range, region, plan). Default to
   the time window that matches the cadence. Note which tiles ignore a filter.
8. Aim for ≤ 12 tiles on the first screen. More belongs on a drill-down page.

### 5. Alerts and ownership

9. Anything that needs action faster than the dashboard is checked becomes an **alert** with a
   threshold, a duration, and a recipient — not just a red tile.
10. Name an owner and a data freshness expectation ("updates hourly; stale after 3h") and show
    the last-refreshed time on the dashboard.

## Output shape

```markdown
# Dashboard: <name>
Audience · Cadence · Owner · Freshness
## Decisions it supports
## Tiles            # | question | metric (definition link) | chart | comparison
## Layout           rows top to bottom
## Filters          name, default, tiles affected
## Alerts           metric | threshold | duration | who
## Out of scope
```

## Checklist

```text
- [ ] Audience, cadence, 2–4 decisions written
- [ ] Each tile answers a question tied to a decision
- [ ] Every metric defined (formula, filters, grain, source)
- [ ] Every number has a comparison
- [ ] Chart type matches the comparison
- [ ] Headline numbers top-left; ≤ 12 tiles on first screen
- [ ] Filters minimal with sensible defaults
- [ ] Urgent conditions are alerts, not just colors
- [ ] Owner, freshness, and last-refreshed shown
```

## Anti-Patterns (What NOT to do)

* **A tile for every field** — volume hides signal; cut what supports no decision.
* **Numbers without comparisons** — "4,210" means nothing without a target or last week.
* **Undefined metrics** — two dashboards with different "active users" start arguments.
* **Pie charts with 9 slices, dual axes, 3D** — hard to read accurately.
* **Using red tiles as alerting** — nobody is watching at 2 a.m.; send an alert.
* **Vanity metrics** (cumulative signups since launch) — they only go up and drive no action.

## Examples

### Example 1: a support operations dashboard

**User:** "Design a dashboard for our support team leads. We use Zendesk data in Snowflake."

**Expected output:**

```markdown
# Dashboard: Support Operations
**Audience:** support team leads · **Cadence:** checked each morning + glanced during the day
**Owner:** Support Ops analyst · **Freshness:** hourly; flagged stale after 3h

## Decisions it supports
1. Do we need to move agents between queues today?
2. Do we need to add weekend coverage next week?
3. Which topics should we escalate to Product?

## Tiles
| # | Question | Metric | Chart | Comparison |
|---|---|---|---|---|
| 1 | Are customers waiting too long now? | Median first-response time, open tickets, last 24h | Big number + sparkline | SLA 4h |
| 2 | Is the backlog growing? | Open tickets (created − solved, cumulative) | Line, 14 days | Same weekday last week |
| 3 | Which queue is behind? | Open tickets > SLA by queue | Horizontal bar, sorted | SLA |
| 4 | Is quality holding? | CSAT, 7-day rolling | Big number + sparkline | Target 90% |
| 5 | When does volume arrive? | Tickets created by hour × weekday, last 4 weeks | Heatmap | — |
| 6 | What are customers contacting us about? | Tickets by tag, top 10, this week | Horizontal bar | Last week |

Metric definitions: first-response time excludes auto-replies and counts business hours only
(see metrics/support.md#frt). Tickets merged as duplicates are excluded everywhere.

## Layout
Row 1: tiles 1, 4 (headline). Row 2: tiles 2, 3. Row 3: tiles 5, 6.

## Filters
Date range (default: last 14 days; tile 1 always last 24h), queue, channel.

## Alerts
| Metric | Threshold | Duration | Who |
|---|---|---|---|
| Tickets breaching SLA | > 25 | 30 min | #support-leads |
| Data freshness | > 3h stale | — | Support Ops analyst |

## Out of scope
Per-agent performance (separate page with restricted access).
```

### Example 2: cleaning up a 38-tile dashboard

**User:** "Our growth dashboard has 38 charts and nobody trusts it."

**Expected output:**

```text
Start by finding what it's for:
1. Ask the 3–4 people who should use it which decisions they make weekly. Pull view logs too:
   tiles nobody has opened in 90 days are candidates to cut.
2. Map each of the 38 tiles to a decision. Expect most to map to none — archive those.
3. "Nobody trusts it" usually means competing definitions: list every metric, and where two
   tiles show "signups" with different numbers, pick one definition and document it.
4. Rebuild as ≤ 12 tiles: headline numbers with comparisons on top, trends, then breakdowns.
   Keep the old dashboard read-only for a month in case something was needed.
```

## Quick Reference

| Step | Output |
|---|---|
| Audience & decisions | Who, how often, 2–4 decisions |
| Questions → metrics | Defined metric per question |
| Comparison | Target, last period, or normal range on every number |
| Chart | Chosen by the comparison |
| Layout | Headlines top-left, ≤ 12 tiles first screen |
| Alerts | Threshold + duration + who |
| Trust | Owner, freshness, last-refreshed time |
