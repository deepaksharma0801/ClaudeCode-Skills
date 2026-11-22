---
name: ab-test-readout
description: Analyzes A/B test results with sanity checks, effect size, confidence intervals, and a plain-English call. Use when a user shares experiment data or asks whether a variant won.
compatibility: Requires Python 3.8+ with scipy 1.9+ for the statistical tests.
---

# Detailed Instructions

Validate the experiment before reading the result. Report the effect with its uncertainty, and
make a call a non-statistician can act on.

## Overview

Experiment readouts usually go wrong before any statistics happen: a broken split, a metric that
moved because of a logging change, or a team peeking until p < 0.05. This skill runs the sanity
checks first, then computes lift and intervals, and ends with one of three calls: ship, don't
ship, or keep running.

## Workflow Rules

1. Identify per variant: units (users, sessions), conversions or metric values, and the planned
   split and run dates. Ask for anything missing that the checks below need.
2. **Sample ratio mismatch (SRM):** chi-square test of observed counts vs the planned split. If
   p < 0.001, stop: report SRM and do not interpret the metric.
3. **Duration:** flag runs shorter than one full week (day-of-week effects) and note if the test was
   stopped early because it "looked significant".
4. **Primary metric:**
   - Proportions: conversion per variant, absolute and relative lift, two-proportion z-test, and a
     95% confidence interval on the absolute difference.
   - Means: Welch's t-test and 95% CI; note heavy skew (revenue) and suggest a bootstrap or
     winsorizing if present.
5. **Multiple comparisons:** with more than 2 variants or several primary metrics, apply a
   Bonferroni or Holm correction and say so.
6. **Guardrails:** report any guardrail metrics the user gives (latency, refunds, churn) with the
   same treatment.
7. **Practical significance:** compare the CI to the minimum effect worth shipping, if known.
8. **Call:** `SHIP`, `DON'T SHIP`, or `KEEP RUNNING / INCONCLUSIVE`, with a one-sentence reason.
   For inconclusive, estimate the extra sample needed for the observed effect at 80% power.

## Anti-Patterns (What NOT to do)

* Do not report a p-value without the effect size and confidence interval.
* Do not say "no effect" when the result is inconclusive; say the test could not detect one.
* Do not interpret results when SRM fails.
* Do not slice into segments until something is significant, or present post-hoc segments as findings.
* Do not round away the uncertainty ("a 4% lift") when the interval spans zero.

## Examples

**User:** "Checkout test, 50/50 split, ran 14 days. Control: 48,210 users, 2,893 orders.
Variant: 48,544 users, 3,107 orders. Did it win?"

**Expected output:**

```text
## Sanity checks
- SRM: 48,210 vs 48,544 on a 50/50 plan → χ² p = 0.28. Split is healthy.
- Duration: 14 days (2 full weeks). OK.

## Primary metric: order conversion
| Variant | Users  | Orders | Conversion |
|---------|--------|--------|------------|
| Control | 48,210 | 2,893  | 6.00%      |
| Variant | 48,544 | 3,107  | 6.40%      |

Absolute lift: +0.40 pp (95% CI +0.10 to +0.70 pp)
Relative lift: +6.7%
z-test p = 0.010

## Call: SHIP
The variant raises conversion by about 0.4 points, and the whole interval is above zero.
At the low end (+0.10 pp) the gain is small, so confirm no guardrail (refunds, support tickets)
moved before rolling out.
```
