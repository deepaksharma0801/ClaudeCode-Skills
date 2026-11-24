---
name: experiment-design
description: Designs an A/B test before launch with a hypothesis, one primary metric, guardrails, sample size, duration, and a decision rule. Use when planning a test or asking how long to run one.
---

# Detailed Instructions

Decide everything that could be fudged **before** any data arrives: the hypothesis, the single
primary metric, the minimum effect worth detecting, the sample size and duration, the guardrails,
and what result means ship. An experiment designed after peeking at results can be made to
say anything; one designed up front gives a decision everyone accepted in advance.

## When to Use

- "We want to A/B test X — how should we set it up?"
- "How many users / how long do we need?"
- Writing an experiment brief or pre-registration
- Reviewing a test plan before launch

**Don't use when:** the test already ran and needs analyzing (use `ab-test-readout`), the change is
a bug fix or legal requirement that ships regardless (just ship it with monitoring), or traffic is
too low to detect any plausible effect (say so and suggest a non-experimental approach).

## Overview

Most bad experiments are bad at design time: the metric is too noisy, the test is underpowered,
there's no guardrail, or the stopping rule is "when it looks good". This skill writes a one-page
design: the hypothesis tied to a mechanism, one primary metric with its baseline, the minimum
detectable effect (MDE), sample size and runtime from a power calculation, guardrails, the
randomization unit, and the decision rule.

## Workflow Rules

1. **Hypothesis with a mechanism:** "Showing shipping cost on the product page (change) reduces
   checkout abandonment from surprise fees (mechanism), increasing purchase conversion (metric)."
   No mechanism usually means no clear metric.
2. **One primary metric** that the change can move within the test window, with its current
   baseline rate or mean and variance. Secondary metrics explain; they don't decide.
3. **Guardrails:** metrics that must not get worse (revenue per visitor, error rate, latency,
   refunds, unsubscribes), each with a tolerance ("no worse than −1%").
4. **Randomization unit** matches the metric and avoids contamination: user for user-level
   conversion, account/company for B2B or shared features, session only when users can't notice
   the switch. Analyze at the unit you randomize on.
5. **MDE:** the smallest effect worth shipping, from the business (cost of the change, value of a
   lift). Don't pick the MDE to fit available traffic without saying so.
6. **Sample size and duration.** Two-proportion test, α = 0.05 two-sided, 80% power:
   `n per arm ≈ 2 × (1.96 + 0.84)² × p̄(1−p̄) / δ²`, where δ is the absolute difference and
   p̄ the average rate (2 × 2.8² ≈ 15.7). Recompute it rather than estimating by eye. Duration = n × arms ÷ eligible units per day, rounded **up to whole
   weeks** (at least 1, usually 2) to cover weekday cycles.
7. **If the duration is unreasonable,** say so and offer levers: a bigger MDE, a more sensitive
   metric closer to the change, more traffic (wider eligibility), or variance reduction (CUPED
   with pre-period data). Don't quietly run an underpowered test.
8. **Decision rule, written now:** ship if the primary metric's 95% CI excludes zero in the right
   direction and no guardrail breaches; don't ship if it excludes zero the wrong way; otherwise
   "no detectable effect at this MDE" and decide on other grounds. No early stopping unless a
   sequential method is used, apart from a guardrail kill switch.
9. **Pre-launch checks:** an A/A test or at least an SRM check plan, logging verified in staging,
   exclusions (internal users, bots) defined, the exposure point (count users when they actually
   see the change, not at login).

## Output shape

```markdown
# Experiment: <name>
Hypothesis — change → mechanism → metric
Primary metric — definition, baseline, MDE (absolute and relative)
Guardrails — metric, tolerance
Unit & exposure — randomization unit, where exposure is logged, exclusions
Sample size & duration — n per arm, traffic/day, runtime in weeks
Decision rule — ship / don't ship / no detectable effect
Risks — novelty, interference, seasonality, other tests running
```

## Checklist

```text
- [ ] Hypothesis names change, mechanism, metric
- [ ] One primary metric with baseline; secondaries labeled as such
- [ ] Guardrails with tolerances
- [ ] Randomization unit matches the metric; exposure point defined
- [ ] MDE chosen from business value
- [ ] Sample size computed; duration in whole weeks
- [ ] Underpowered? Levers offered instead of running anyway
- [ ] Decision rule and stopping rule written before launch
- [ ] SRM / A/A check and logging verified
```

## Red Flags

- "We'll look at a bunch of metrics and see what moves."
- "Run it until it's significant."
- Duration of 3 days, or "until we hit 1,000 users", without a power calculation.
- Randomizing by session for a metric measured per user.
- The MDE quietly set to whatever the traffic allows.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "We'll pick the metric after we see the data." | With 20 metrics, one will be "significant" by chance (~64% chance at α=0.05). |
| "We'll stop as soon as it's significant." | Repeated peeking inflates false positives far above 5%. Use a fixed horizon or a sequential test. |
| "One week is enough." | If the power calc says 3 weeks, one week mostly measures noise. |
| "Guardrails slow us down." | They're what stops a "win" on clicks that loses revenue. |

## Anti-Patterns (What NOT to do)

* **Multiple primary metrics** — inflates false positives; pick one, label the rest secondary.
* **Counting users who never saw the change** — dilutes the effect and wastes power.
* **Running partial weeks** — weekday mix differs between days and biases results.
* **Designing for an MDE nobody would act on** — a 0.1% lift that costs a quarter of work isn't worth testing for.
* **Launching without an SRM check plan** — broken assignment invalidates everything downstream.

## Examples

### Example 1: shipping cost on the product page

**User:** "We want to test showing shipping cost on product pages. Checkout conversion is 3.0%.
About 40,000 product-page visitors a day. How long?"

**Expected output:**

```markdown
# Experiment: Shipping cost on product page

**Hypothesis:** Showing shipping cost on the product page → fewer surprise-fee abandonments at
checkout → higher purchase conversion.

**Primary metric:** purchase conversion per product-page visitor, 7-day window.
Baseline 3.0%. **MDE: +0.3pp absolute (+10% relative)** — the smallest lift that pays for the
engineering and ongoing shipping-API cost.

**Guardrails:** revenue per visitor (no worse than −1%), product-page latency p95 (no worse than
+100ms), add-to-cart rate (watch: could fall if shipping looks expensive).

**Unit & exposure:** user (logged-in id, else first-party cookie). Exposure logged when the
shipping line renders. Exclude employees and known bots.

**Sample size:** p̄ = 3.15%, δ = 0.003
n ≈ 2 × 2.8² × 0.0315 × 0.9685 / 0.003² ≈ 53,000 per arm → 106,000 total.
At 40,000 visitors/day that's ~2.7 days of new users, but returning visitors don't add new units
— assume ~25,000 new eligible users/day → ~4.2 days. **Run 2 full weeks** (covers weekday cycles
and the 7-day conversion window for early users).

**Decision rule:** ship if the 95% CI for conversion lift excludes 0 on the positive side and no
guardrail breaches. If CI includes 0: no detectable effect ≥ 0.3pp; decide on UX grounds.
No early stopping except a guardrail kill switch (latency or revenue −5%).

**Risks:** a running checkout test may interact — check overlap; holiday traffic starts in 3 weeks.
```

### Example 2: an underpowered request

**User:** "Our B2B app has 300 new trials a week, trial-to-paid is 12%. Test a new onboarding
for a week?"

**Expected output:**

```text
A week won't work. To detect a +3pp lift (12% → 15%, a 25% relative lift):
n ≈ 2 × 2.8² × 0.135 × 0.865 / 0.03² ≈ 2,030 trials per arm → ~4,060 trials → ~13.5 weeks.

Options:
1. Use a faster, closer metric — "completed setup in 3 days" (baseline 40%): detecting +6pp
   needs about 2.8² × 2 × 0.43 × 0.57 / 0.06² ≈ 1,070 per arm → ~7 weeks.
2. Accept a larger MDE (+6pp on paid conversion, ~555 per arm → ~4 weeks), knowing smaller wins will be missed.
3. Skip the experiment: ship to all, watch trial-to-paid over the next 2 months, and interview 10
   trial users. Lower rigor, honest about it.

I'd do option 1 with paid conversion as a secondary metric.
```

## Quick Reference

| Item | Rule of thumb |
|---|---|
| Primary metric | One, moveable within the window, with a baseline |
| Sample size (80% power, α 0.05) | n/arm ≈ 15.7 × p̄(1−p̄) / δ² |
| Duration | Whole weeks, ≥ 1, usually 2 |
| Unit | Same as the metric's unit; account for B2B |
| Exposure | Log when the change is actually seen |
| Stopping | Fixed horizon, or a proper sequential method |
| Too little traffic | Bigger MDE, closer metric, CUPED, or don't experiment |
