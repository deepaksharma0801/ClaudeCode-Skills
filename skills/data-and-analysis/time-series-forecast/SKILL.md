---
name: time-series-forecast
description: Builds simple, honest forecasts with seasonal baselines, backtests against naive methods, and prediction intervals. Use when asked to forecast demand, revenue, traffic, tickets, or capacity.
---

# Detailed Instructions

Start with the simplest forecast that could work — last year's same period, a seasonal naive,
or a moving average — and only use a more complex model if it **beats that baseline in a
backtest**. Always give a range, not just a point. A forecast without a comparison to a naive
method has no evidence behind it, and a point estimate without an interval hides how uncertain
it is.

## When to Use

- "Forecast next quarter's revenue / signups / support tickets / traffic"
- Capacity planning (servers, staff, inventory)
- Setting targets and checking whether they're realistic
- Reviewing someone else's forecast

**Don't use when:** explaining why a metric already moved (use `metric-drop-investigation`), or
estimating the effect of a change (use `experiment-design`).

## Overview

Forecasts usually go wrong by fitting a sophisticated model to too little history, ignoring
seasonality and holidays, never backtesting, and reporting one number. This skill inspects the
series (trend, seasonality, breaks, outliers), builds a naive baseline, tries one or two simple
models, backtests them on held-out periods, picks the best by error, and reports the forecast
with prediction intervals and its assumptions.

## Workflow Rules

### 1. Understand the series

1. Plot it. Note the frequency, length of history, trend, **seasonality** (weekly, yearly),
   holidays, and **structural breaks** (a launch, pricing change, COVID-era data, tracking
   change). Breaks may mean using only data after the break.
2. Rule of thumb: you need at least two full seasonal cycles to estimate seasonality (2 years for
   yearly patterns). With less, say so and widen the interval.
3. Handle outliers deliberately (an outage day, a one-off promo): mark them, and decide whether
   they'll recur.

### 2. Baselines first

4. Build naive baselines:
   - **Seasonal naive:** next period = same period last cycle (last year's same week).
   - **Seasonal naive + growth:** last year's value × recent year-over-year growth.
   - **Moving average** for series without seasonality.

### 3. Try simple models

5. Try one or two: exponential smoothing with trend and seasonality (Holt-Winters /
   `statsmodels.tsa.holtwinters.ExponentialSmoothing`), or Prophet for daily data with
   holidays. Add known future events (planned promos, price changes) as explicit adjustments,
   documented.

### 4. Backtest

6. **Rolling-origin backtest:** for several cutoffs, fit on data before the cutoff, forecast the
   horizon you care about, compare with what happened. Never evaluate on data the model saw.
7. Compare models by **MAPE** (or MAE when values approach zero) and bias (consistently over or
   under). Pick the model that beats seasonal naive; if none does, use seasonal naive.

### 5. Report

8. Give the forecast with an **80% (and/or 95%) prediction interval**, the method, backtest error
   vs. baseline, assumptions (growth rate, known events), and what would invalidate it.
9. Say when to re-forecast (monthly, or when actuals leave the interval).

## Checklist

```text
- [ ] Series plotted; trend, seasonality, holidays, breaks, outliers noted
- [ ] Enough history for the seasonality (or limitation stated)
- [ ] Seasonal-naive baseline built
- [ ] 1–2 simple models tried; known events added explicitly
- [ ] Rolling-origin backtest at the real horizon
- [ ] Model beats baseline on MAPE/MAE, or baseline used
- [ ] Prediction intervals reported
- [ ] Assumptions, invalidating events, re-forecast cadence stated
```

## Red Flags

- A forecast with no baseline comparison.
- A single number, no interval.
- Fitting a yearly seasonal model on 9 months of data.
- Evaluating accuracy on the training data.
- A straight-line trend extrapolated over a launch spike.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "A more complex model is more accurate." | Often not; simple seasonal methods are hard to beat on short business series. |
| "Leadership wants one number." | Give the point and the range; plans should survive the low end. |
| "The fit looks great." | In-sample fit says little; backtest on held-out periods. |
| "Last year was weird, use it anyway." | Adjust or exclude breaks explicitly and say so. |

## Anti-Patterns (What NOT to do)

* **Skipping the naive baseline** — no way to know if the model adds value.
* **Ignoring holidays and calendar effects** — Easter, Black Friday, and month length shift demand.
* **Linear trend on a growth curve that's flattening** — overshoots badly.
* **Silent adjustments** — every manual adjustment needs a reason in the report.
* **Never comparing to actuals** — track forecast error over time.

## Examples

### Example 1: support tickets next quarter

**User:** "Forecast weekly support tickets for Q1. We have 3 years of weekly data."

**Expected output:**

```markdown
**Forecast:** Q1 total ≈ 41,600 tickets (80% interval 38,900–44,500); peak in the first week of January
≈ 4,100 (holiday backlog).

**Method:** Holt-Winters (additive trend, multiplicative yearly seasonality) on weekly data
since 2023 (excluding the Mar 2025 outage week, marked as one-off).

**Backtest** (rolling origin, 13-week horizon, 6 cutoffs):
| Model | MAPE | Bias |
|---|---|---|
| Seasonal naive (same week last year) | 9.8% | −6% (under-forecasts: volume grows) |
| Seasonal naive × YoY growth (+7%) | 6.1% | −1% |
| Holt-Winters | 5.4% | +1% |

Holt-Winters beats both baselines, so it's used; the growth-adjusted naive is a close second
and a useful sanity check (it gives 42,300 for Q1).

**Assumptions:** customer base grows as in the last 12 months; no major release in Q1.
**Would invalidate it:** the planned pricing change (if moved into Q1, add a launch bump —
last pricing change added ~15% tickets for 3 weeks). **Re-forecast** monthly or if a week lands
outside the interval.
```

### Example 2: too little history

**User:** "We launched 5 months ago. Forecast next year's monthly revenue."

**Expected output:**

```text
Five months can't show yearly seasonality or a stable growth rate, so any 12-month forecast will
be mostly assumptions. What I can do honestly:
1. A scenario range instead of a model: low / base / high monthly growth (e.g. 3% / 6% / 10%,
   based on the last 3 months' 4–9% range), shown as three lines.
2. A short-horizon forecast (next 2–3 months) from the recent trend, with a wide interval.
3. Re-forecast monthly; once there are 12+ months, add seasonality.
Which growth assumptions do you want for the scenarios?
```

## Quick Reference

| Step | Rule |
|---|---|
| Inspect | Trend, seasonality, holidays, breaks, outliers |
| History | ≥ 2 seasonal cycles, or say it's thin |
| Baseline | Seasonal naive (± growth) |
| Models | Holt-Winters / Prophet; keep it simple |
| Backtest | Rolling origin at the real horizon; MAPE + bias |
| Choose | Must beat baseline |
| Report | Point + interval, method, error, assumptions |
