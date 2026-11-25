---
name: okr-writer
description: Writes and reviews OKRs with outcome objectives, measurable key results with baselines and targets, and separate initiatives. Use when planning quarterly goals or reviewing OKR drafts.
---

# Detailed Instructions

An objective says what will be different and why it matters; a key result is a number with a
baseline and a target that shows the objective happened. The work that moves the numbers
(projects, launches) is an initiative, not a key result. Keeping these three apart is what makes
OKRs useful: a team that ships every project and moves no number has learned something, but only
if the OKRs measured the outcome.

## When to Use

- "Help me write OKRs / quarterly goals for my team"
- Reviewing a team's OKR draft before planning
- Turning a strategy doc or roadmap into measurable goals
- Mid-quarter or end-of-quarter scoring

**Don't use when:** the task is a project plan with dates and tasks (use
`implementation-plan-writer`), or defining one metric precisely (use `metric-definition-writer`
and reference it from the KR).

## Overview

Common OKR drafts are task lists in disguise ("Launch the new dashboard"), have no baselines, set
ten key results, or pick numbers the team can't measure. This skill sets 1–3 objectives
tied to a business outcome, 2–4 key results each with baseline, target, data source, and owner,
lists initiatives separately as bets, and checks that every KR is measurable today and
moveable by the team within the quarter.

## Workflow Rules

1. **Start from context:** company or org goals, the team's mission, last quarter's results,
   and known constraints (headcount, dependencies). Ask for these if missing.
2. **Objectives (1–3):** qualitative, outcome-focused, inspiring but concrete: "New customers
   get value on day one" — not "Improve onboarding" or "Ship onboarding v2".
3. **Key results (2–4 per objective):** each is `metric: baseline → target by date`, with a
   data source and owner. Test each: could we hit this without achieving the objective? If yes,
   add a counter-metric (e.g. speed and quality).
4. **Prefer outcome KRs** (activation rate, latency, churn) over output KRs (features shipped).
   Use an output KR only when the outcome can't be measured within the quarter, and say so.
5. **Baselines must exist.** If the metric isn't measured yet, the first KR or initiative is
   to instrument it; don't invent a baseline.
6. **Ambition:** decide with the team whether OKRs are stretch (≈ 70% expected) or
   committed (100% expected) and label them — mixing the two confuses scoring.
7. **Initiatives** go in a separate list under each objective: the bets the team believes will move
   the KRs. They can change mid-quarter; KRs shouldn't.
8. **Check scope:** ≤ 3 objectives, ≤ 4 KRs each, every KR within the team's influence, and
   dependencies on other teams named.
9. **Scoring (when asked):** score each KR 0.0–1.0 as progress from baseline to target, explain
   misses with what was learned, and carry forward deliberately rather than by default.

## Output shape

```markdown
## Objective 1: <outcome, why it matters>   (stretch | committed)
| KR | Baseline | Target | Source | Owner |
Initiatives: bets that should move the KRs
Dependencies / risks
```

## Checklist

```text
- [ ] Context gathered (org goals, last quarter, constraints)
- [ ] ≤ 3 objectives, outcome-focused
- [ ] 2–4 KRs each: metric, baseline → target, date, source, owner
- [ ] Outcome KRs preferred; output KRs justified
- [ ] Counter-metrics where a KR could be gamed
- [ ] No invented baselines; instrumentation first if missing
- [ ] Stretch vs committed labeled
- [ ] Initiatives listed separately
- [ ] Dependencies named
```

## Anti-Patterns (What NOT to do)

* **Tasks as key results** ("Launch v2") — shipping isn't proof of impact.
* **KRs without baselines** — progress can't be scored.
* **Ten KRs per objective** — focus disappears; pick the 2–4 that matter.
* **Metrics the team can't move** (company revenue for a platform team) — choose a leading metric in their control.
* **Gameable KRs with no counter-metric** — "close 50% more tickets" invites closing tickets unsolved.
* **Invented numbers** — leave `<baseline: TODO>` and add instrumentation.

## Examples

### Example 1: rewriting a task-list draft

**User:** "Our onboarding team's draft: O: Improve onboarding. KRs: Launch onboarding checklist;
Redesign welcome email; Add 3 tutorial videos. We know day-1 activation is 34% and 30-day retention
is 41%."

**Expected output:**

```markdown
## Objective: New customers reach their first success on day one   (stretch)

| Key result | Baseline | Target | Source | Owner |
|---|---|---|---|---|
| Day-1 activation (created and shared first report) | 34% | 45% | Product analytics, `activation_d1` | PM Onboarding |
| 30-day retention of new accounts | 41% | 46% | Retention dashboard | PM Onboarding |
| Median time to first report | <TODO: baseline> | <TODO: target> | Instrument `first_report_created` (wk 1) | Eng lead |
| Onboarding support tickets per 100 signups (counter-metric) | <TODO> | No increase | Zendesk, tag `onboarding` | Support lead |

**Initiatives (bets):** onboarding checklist, welcome-email redesign, 3 tutorial videos.
These were your original KRs — they're how you plan to move the numbers, not the numbers
themselves. If the checklist ships and activation doesn't move, that's the signal to try
something else mid-quarter.

**Note:** 30-day retention for signups late in the quarter won't be measurable until after it
ends; score it on signups from the first two months.
```

### Example 2: a KR the team can't move

**User:** "Platform team OKR: KR — increase company revenue 20%."

**Expected output:**

```text
The platform team can't move company revenue directly, so this KR will be scored on things
outside your control. Pick a metric you own that plausibly supports revenue:
- "Checkout API p95 latency: 900 ms → 400 ms" (if checkout speed affects conversion)
- "Deploys per week: 6 → 15" (faster product iteration for revenue teams)
- "Availability of revenue-critical services: 99.5% → 99.9%"
Which of these matters most to the teams you support? I'll write the objective around it.
```

## Quick Reference

| Part | Shape | Test |
|---|---|---|
| Objective | Qualitative outcome + why | Would anyone notice if it happened? |
| Key result | Metric: baseline → target, date | Can we score it today? |
| Counter-metric | Quality/cost guardrail | Can the KR be gamed? |
| Initiative | Project or bet | Separate list; may change |
| Scope | ≤ 3 objectives, ≤ 4 KRs | Fits on one page |
| Scoring | 0.0–1.0 from baseline to target | Lessons, not blame |
