---
name: decision-memo
description: Writes a one-page decision memo that frames the choice, compares options on the criteria that matter, and makes a clear recommendation. Use when a user must choose between options or wants buy-in.
---

# Detailed Instructions

Lead with the recommendation, then earn it. A reader should know what you want decided in the
first two lines and be able to see exactly why the other options lost.
Decision-makers read the first lines and the comparison table. If the recommendation is buried
or the criteria are chosen after the fact, the memo informs no one and persuades no one.

## When to Use

- Build vs buy, vendor selection, tool or framework choices
- "Help me make the case for X", "should we do A or B?"
- Any choice that needs sign-off from someone with limited time

**Don't use when:** the decision needs a detailed technical design (use `design-doc-writer`), or
it's a status update with nothing to decide (use `weekly-status-update`).

## Overview

Decisions stall when the options are described but not compared, or when the memo hides its
recommendation. This skill frames the decision, picks criteria before scoring options, compares
them side by side with evidence, states the recommendation and its main risk, and says what would
change the answer.

## Workflow Rules

1. **Frame the decision** in one sentence as a question with a deadline and a decision-maker:
   "Should we build or buy our feature-flag system? Decision by Dec 5, owner: VP Eng."
2. **Recommendation first:** one or two sentences with the choice and the main reason.
3. **Criteria:** 3–5 criteria that actually matter for this decision (cost, time to ship, risk,
   reversibility, strategic fit), defined *before* comparing options. Weight them if they are not equal.
4. **Options:** 2–4 real options, including the status quo. For each: a one-line description, and
   how it scores on each criterion with evidence (numbers, quotes, benchmarks).
5. **Comparison table** of options × criteria.
6. **Risks of the recommendation** and how they will be mitigated.
7. **What would change our mind:** the facts that would make another option better.
8. **Next steps** if approved: owner, first milestone, date.
9. Fit on one page. Supporting detail goes in an appendix or links.

## Output shape

```markdown
# Decision: <question>
**Decision needed:** <date> · **Decider:** <who>
**Recommendation:** <choice + main reason, ≤ 2 sentences>
## Criteria (weighted)       defined before scoring
## Options                   table: options × criteria, with evidence
## Risks of recommendation   + mitigations
## What would change our mind
## Next steps                owner, first milestone, date
```

## Checklist

```text
- [ ] Decision framed as a question with deadline and decider
- [ ] Recommendation in the first two lines
- [ ] 3–5 criteria, weighted, chosen before comparing
- [ ] 2–4 real options including status quo
- [ ] Evidence (numbers, quotes); estimates marked
- [ ] Risks + mitigations; what would change the answer
- [ ] Next steps with owner and date
- [ ] Fits on one page
```

## Anti-Patterns (What NOT to do)

* Do not bury the recommendation at the end, or avoid making one.
* Do not choose criteria after the fact to fit the preferred option.
* Do not present options that nobody would seriously pick just to make the recommendation look good.
* Do not invent costs, quotes, or numbers; mark estimates as estimates.
* Do not write "it depends" without saying on what.

## Examples

### Example 1: build vs buy feature flags

**User:** "Help me write up whether we should build our own feature-flag service or buy one. We have 3 backend engineers."

**Expected output:**

```markdown
# Decision: Build vs buy feature flags

**Decision needed:** by Dec 5 · **Decider:** Head of Engineering

**Recommendation:** Buy a hosted feature-flag service. It ships this week instead of in ~6 weeks
and costs less than one engineer-month per year, with low lock-in if we use the OpenFeature SDK.

## Criteria (weighted)
1. Time to first use (30%)  2. Total yearly cost incl. engineering time (30%)
3. Reliability on the request path (25%)  4. Lock-in / reversibility (15%)

## Options
| | Buy (hosted) | Build in-house | Status quo (env vars) |
|---|---|---|---|
| Time to first use | ~1 week | ~6 weeks (estimate, 1 engineer) | now |
| Yearly cost | ~$6k license (quote) | ~$25k eng. time + upkeep (estimate) | $0 |
| Reliability | vendor SLA 99.99%; local cache if API down | depends on us; new on-call surface | high, but every change needs a deploy |
| Lock-in | low with OpenFeature SDK | none | none |

## Risks of recommendation
- Vendor outage: SDK serves last-known flags from cache; default values defined in code.
- Cost growth with seats: renegotiate at 50 seats; build becomes attractive above ~$20k/year.

## What would change our mind
- A requirement to evaluate flags fully offline or on-prem.
- License quote above $20k/year.

## Next steps
Trial for 2 weeks (owner: Priya, starting Dec 8); migrate the 3 riskiest env-var toggles first.
```

### Example 2: when the honest answer is "not yet"

**User:** "Write a memo recommending we move from Heroku to Kubernetes."

**Expected output:**

```markdown
# Decision: Move from Heroku to Kubernetes?

**Decision needed:** Q1 planning · **Decider:** CTO
**Recommendation:** Not now. Stay on Heroku for 2026 and fix the two problems driving this
(cost of the largest dynos, and slow builds) directly; revisit if spend passes $15k/month.

## Criteria
1. Monthly cost (35%)  2. Engineering time to migrate and operate (35%)
3. Reliability (20%)  4. Flexibility for future needs (10%)

## Options
| | Stay on Heroku + fixes | Managed Kubernetes (EKS) | Simpler PaaS (e.g. Render/Fly) |
|---|---|---|---|
| Monthly cost | $8.2k → ~$6.5k after dyno right-sizing (estimate) | ~$5k infra + ops time | ~$5.5k (quote) |
| Eng time | 1 week | ~3 months migration + ongoing on-call (estimate) | ~3 weeks |
| Reliability | known, 99.95% last year | depends on our ops maturity | similar to Heroku |
| Flexibility | limited | high | medium |

## What would change our mind
Spend above $15k/month, a compliance requirement Heroku can't meet, or workloads (GPUs,
long-running jobs) Heroku doesn't support.
```

The memo argued against the requested conclusion because the numbers did; say so plainly to the
requester before circulating it.

## Quick Reference

| Part | Rule |
|---|---|
| Opening | Recommendation in ≤ 2 sentences |
| Criteria | Chosen and weighted before scoring |
| Options | Real alternatives + status quo |
| Numbers | Evidence or marked estimates |
| Risks | With mitigations |
| Changing mind | Name the facts that would flip it |
| Length | One page; detail in links |
