---
name: ab-test-readout
description: Analyzes A/B test results with sample-ratio and duration checks, lift, confidence intervals, power, and a plain-English ship call. Use when a user shares experiment data or asks whether a variant won.
compatibility: Bundled calculator requires Python 3.8+ (standard library only). For mean metrics, scipy is optional.
---

# Detailed Instructions

Validate the experiment before reading the result, report the effect with its uncertainty, and end
with a call a non-statistician can act on. A p-value without an effect size and interval is not a
readout, and a result from a broken split is not a result at all — so the sample-ratio check comes
first and can stop the analysis.

## When to Use

- "Did the variant win?", "is this significant?", "can we ship B?"
- Experiment dashboards or raw counts per variant
- Deciding whether to keep running a test, or how long it needs to run
- Reviewing someone else's experiment conclusion

**Don't use when:** there was no randomized control (before/after comparisons, opt-in features —
say the result can't be read causally and suggest a proper test), or the question is retention over
time (use `cohort-retention-analysis` on each arm).

## Overview

Experiment readouts usually go wrong before any statistics happen: a broken assignment (sample
ratio mismatch), a test stopped the day it first looked significant, a metric that moved because
of a logging change, or five variants compared with no correction. This skill checks validity,
computes lift and intervals with `scripts/ab_test.py`, handles multiple comparisons and guardrails,
compares the interval with the smallest effect worth shipping, and makes one of three calls.

## Workflow Rules

### 1. Gather

1. **Per variant:** users (the randomization unit), conversions or metric values, the planned
   split, start and end dates, and the primary metric chosen *before* the test. Ask for what's
   missing.

### 2. Validate (stop here if it fails)

2. **Sample ratio mismatch (SRM):** observed counts vs the planned split. `ab_test.py` runs a
   chi-square test; p < 0.001 means the split is broken (assignment bug, bot filtering in one arm,
   redirect losses, logging). Report SRM and do **not** interpret the metric.
3. **Duration:** at least one full week to cover day-of-week effects; flag tests stopped early
   "because it looked significant" (peeking inflates false positives) and tests that overlapped a
   holiday, outage, or tracking change.
4. **Unit consistency:** randomized by user but measured per session? Say so; it understates
   variance.

### 3. Measure

5. **Conversion metrics:**
   `python3 scripts/ab_test.py --group control:USERS:CONV --group variant:USERS:CONV [--split 50:50]`
   It reports rates, absolute and relative lift, the confidence interval for the difference,
   the p-value, and — when not significant — the sample size needed to detect the observed effect.
6. **Mean metrics** (revenue per user, time on page): Welch's t-test and a CI; revenue is heavily
   skewed, so also report a bootstrap CI or a winsorized mean and say which you used.
7. **More than two arms or several primary metrics:** correct for multiple comparisons —
   `ab_test.py` applies Bonferroni automatically when you pass more than one variant.
8. **Guardrails** (refunds, latency, support contacts, unsubscribes) with the same treatment. A
   win on the primary metric with a significant guardrail regression is not a ship.

### 4. Decide

9. **Compare the interval with the minimum effect worth shipping** (ask, or use the effect the test
   was powered for). A significant +0.05% lift may not be worth the complexity.
10. **Make the call:**
    - `SHIP` — the interval excludes zero on the good side, guardrails OK, effect worth it
    - `DON'T SHIP` — the interval excludes zero on the bad side, or a guardrail regressed
    - `KEEP RUNNING / INCONCLUSIVE` — the interval includes zero; give the sample still needed
11. **Write it up** in this shape: validity checks → result table → lift with CI and p →
    guardrails → call with one-sentence reason → caveats.

## Checklist

```text
- [ ] Planned split, dates, randomization unit, and primary metric known
- [ ] SRM checked (stop if p < 0.001)
- [ ] Ran at least a full week; no early stop on peeking; no overlapping incidents
- [ ] Lift reported as absolute and relative, with CI and p
- [ ] Multiple comparisons corrected
- [ ] Guardrails checked
- [ ] Interval compared with the minimum worthwhile effect
- [ ] Call: SHIP / DON'T SHIP / KEEP RUNNING, with the reason
```

## Red Flags

- "It hit p < 0.05 on day 3, let's call it."
- "The overall result is flat, but mobile users in Canada loved it."
- "SRM is just a small imbalance, the result still holds."
- "p = 0.08 is basically significant."
- "We tested 6 variants and one is significant at 0.05."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The split is only slightly off." | With large samples, a "slight" imbalance is statistically impossible by chance — something filtered users unevenly, and that something likely affects the metric. |
| "We stopped once it was significant to save time." | Checking repeatedly and stopping at the first p < 0.05 makes false positives far more likely than 5%. |
| "No significant difference means no effect." | It means the test couldn't detect one at this size. Report the interval and the sample needed. |
| "This segment is clearly significant." | Segments found after the fact are hypotheses for the next test, not results. |

## Anti-Patterns (What NOT to do)

* **A p-value without effect size and CI** — the reader can't judge whether it matters.
* **"No effect" for an inconclusive result** — say the test couldn't detect one.
* **Interpreting results despite SRM** — the comparison isn't valid.
* **Slicing into segments until something is significant** — that's how false wins ship.
* **Rounding away uncertainty** ("a 4% lift") when the interval spans zero.

## Examples

### Example 1: a clean win

**User:** "Checkout test, 50/50 split, ran 14 days. Control: 48,210 users, 2,893 orders.
Variant: 48,544 users, 3,107 orders. Did it win?"

**Expected output:**

```text
$ python3 scripts/ab_test.py --group control:48210:2893 --group variant:48544:3107
## Sample ratio check
  control 48,210 / variant 48,544 vs planned 1:1 -> chi2 = 1.15, p = 0.283
  OK: no sample ratio mismatch.
## Conversion (alpha 0.05)
  control  48,210  2,893  6.00%
  variant  48,544  3,107  6.40%
  variant vs control: +0.40 pts (+6.7% relative) 95.0% CI [+0.10, +0.70] pts, p = 0.00998 -> significant

Duration: 14 days (two full weeks). No incidents reported.

## Call: SHIP
Conversion rises by about 0.4 points (6.0% → 6.4%), and the whole interval is above zero. The low
end (+0.10 pts) is small, so confirm refunds and support contacts didn't rise before rolling out.
```

### Example 2: a broken split

**User:** "Variant looks better: control 50,000 users / 2,500 conversions, variant 46,000 / 2,400. 50/50 test."

**Expected output:**

```text
$ python3 scripts/ab_test.py --group control:50000:2500 --group variant:46000:2400
## Sample ratio check
  control 50,000 / variant 46,000 vs planned 1:1 -> chi2 = 166.67, p = 3.96e-38
  SRM DETECTED (p < 0.001): the split is broken. Do not interpret the results below.

## Call: CAN'T READ — fix the experiment first
4,000 users are missing from the variant. That can't happen by chance with a 50/50 split; something
drops or misroutes variant users (a redirect that loses some sessions, bot filtering applied to one
arm, a crash before the exposure is logged). Those missing users are probably not typical, so the
variant's 5.22% vs 5.00% can't be trusted in either direction.

Check: exposure logging by browser/platform per arm, redirect error rates, and whether filtering
runs before or after assignment. Then rerun.
```

## Quick Reference

| Check | Rule |
|---|---|
| SRM | chi-square p < 0.001 → stop, investigate |
| Duration | ≥ 1 full week; no peeking-based stop |
| Report | Absolute + relative lift, CI, p |
| Multiple arms | Bonferroni (automatic in `ab_test.py`) |
| Not significant | "Inconclusive" + sample needed, never "no effect" |
| Ship | CI excludes zero, guardrails OK, effect worth it |
