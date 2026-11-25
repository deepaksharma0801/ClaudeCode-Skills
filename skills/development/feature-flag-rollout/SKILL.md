---
name: feature-flag-rollout
description: Plans and implements a feature-flagged rollout with staged exposure, success and kill criteria, monitoring, and flag cleanup. Use when shipping a risky change gradually or adding a feature flag.
---

# Detailed Instructions

Separate deploy from release: ship the code dark behind a flag, then widen exposure in stages
with written criteria for going forward and for turning it off. Each stage is a small, reversible
bet, and the flag's off switch is only useful if someone checked it works and knows when to use it.
Every flag also needs a removal date, because flags left behind become permanent branches in the code.

## When to Use

- Shipping a risky change: new checkout, a rewritten service path, a pricing change, a migration
  read path
- "Add a feature flag for X" / "how should we roll this out?"
- A change that must be enabled per customer, region, or plan
- Cleaning up old flags

**Don't use when:** the question is whether the change *improves* a metric (use
`experiment-design` — an A/B test needs randomization and a power calculation, a rollout
doesn't), or the change is a database schema change (use `db-migration-safety`; flags don't
make schema changes reversible).

## Overview

Flags go wrong in predictable ways: the flag is checked in some code paths but not others, nobody
defined what "healthy" means before ramping, the kill switch was never tested, and the flag
lives forever. This skill puts the flag check at one boundary, defines stages with numeric
go/no-go criteria, wires the metrics to watch, tests both flag states, and schedules cleanup.

## Workflow Rules

### 1. Design the flag

1. **One flag, one decision.** Name it for the behavior (`checkout_v2_enabled`), not the ticket.
   Record an owner and an expiry date where flags are defined.
2. **Evaluate it once, at the boundary** (request handler, job entry), and pass the result down.
   Scattered checks drift apart and leave half-on states.
3. **Safe default:** if the flag service is unreachable, the flag evaluates to the old behavior.
4. **Sticky targeting:** bucket by a stable key (user or account id), so a user doesn't flip
   between versions on each request. For B2B, bucket by account.

### 2. Make both paths correct

5. Test both states in CI (parameterize tests over the flag). Make sure data written by the new
   path can be read by the old one — turning the flag off mustn't break users who already used the
   new version.
6. Log or tag telemetry with the flag variant so metrics can be split by it.

### 3. Plan the stages

7. Write the stages and criteria **before** starting:

| Stage | Exposure | Hold for | Go if | Kill if |
|---|---|---|---|---|
| 0 | Internal users | 1–2 days | No new errors | Any P1 bug |
| 1 | 1% | ≥ 1 day incl. peak | Error rate and p95 within +10% of control | Errors > 2× control, any data issue |
| 2 | 10% | 2–3 days | Same + business metric not down | Same |
| 3 | 50% | 2–3 days | Same | Same |
| 4 | 100% | 1 week | — | — |

   Adjust the numbers to the system, but always compare the flagged cohort against the unflagged
   one at the same time, not against last week.
8. **Kill switch:** who can turn it off, how (dashboard or CLI), how fast it takes effect, and
   confirm it works in staging before stage 1.

### 4. Ramp and watch

9. At each stage, check the dashboards split by variant against the criteria, and record the
   decision (go, hold, or kill) with the numbers.
10. Avoid ramping on Fridays or before holidays unless someone is watching.

### 5. Clean up

11. At 100% with the hold passed, remove the flag: delete the old path, the flag checks, the tests
    for the off state, and the flag definition. Open the cleanup ticket on day one with the
    expiry date.

## Checklist

```text
- [ ] Flag named for behavior; owner and expiry recorded
- [ ] Evaluated once at the boundary; safe default = old behavior
- [ ] Sticky bucketing by user/account
- [ ] Both states tested; old path can read new data
- [ ] Telemetry tagged with variant
- [ ] Stages with numeric go/kill criteria written up front
- [ ] Kill switch tested; who and how documented
- [ ] Decision recorded at each stage
- [ ] Cleanup ticket with date; flag removed after 100%
```

## Red Flags

- "We'll figure out what to watch once it's at 10%."
- The flag checked in five files.
- Turning the flag off would break users who already used the new path.
- Comparing the flagged cohort to last week instead of the unflagged cohort now.
- A flag older than six months with no owner.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "It's behind a flag, so it's safe." | Only if off actually restores the old behavior and someone knows when to flip it. |
| "1% is too small to matter." | 1% is what catches the crash before 100% does. |
| "We'll remove the flag later." | Without a date and a ticket, later is never. |
| "Flags work like A/B tests." | Without randomization and a power calculation, a ramp can't prove a lift. |

## Anti-Patterns (What NOT to do)

* **Flagging schema changes** — the flag can't un-drop a column; use expand/contract migrations.
* **Random per-request bucketing** — users see flip-flopping behavior.
* **Defaulting to the new path when the flag service fails** — an outage turns into a full release.
* **Nested flags that depend on each other** — combinations become untestable.
* **Never-removed flags** — dead code paths and surprise behavior years later.

## Examples

### Example 1: rolling out a new checkout

**User:** "We rewrote checkout. Plan the rollout. We use LaunchDarkly."

**Expected output:**

```markdown
**Flag:** `checkout_v2_enabled` (boolean) — owner: Payments, expires 2027-01-31.
Evaluated in `CheckoutController#show`, passed down to the service; default `false` on
LaunchDarkly errors. Targeting by `user.key` (sticky).

**Both paths:** CI runs checkout specs with the flag on and off. v2 writes orders in the same
schema as v1, so turning it off is safe for users mid-checkout. Metrics and logs are tagged
`checkout_variant=v1|v2`.

**Stages**
| Stage | Exposure | Hold | Go | Kill |
|---|---|---|---|---|
| 0 | Employees | 2 days | No P1 bugs | Any payment error |
| 1 | 1% | 24h incl. evening peak | v2 payment errors ≤ v1 + 0.2pp; p95 ≤ v1 + 10% | Errors > 2× v1, any double charge |
| 2 | 10% | 3 days | Same + v2 conversion not below v1 by > 1pp | Same |
| 3 | 50% | 3 days | Same | Same |
| 4 | 100% | 1 week | — | — |

**Kill switch:** on-call can toggle in LaunchDarkly (takes effect in < 5 s); tested in staging.
**Cleanup:** PAY-812 opened — delete v1 checkout and the flag after the 100% week.
Note: the 1pp conversion check is a safety guardrail, not proof v2 is better — run an A/B
test if you need that claim.
```

### Example 2: flag debt

**User:** "We have 140 feature flags. Help."

**Expected output:**

```text
Triage them by state, from the flag service's last-evaluated data:
1. 100% on everywhere for > 30 days → remove the flag and the old path (most flags land here).
2. 0% / never evaluated for > 30 days → confirm with the owner, delete the flag and new path.
3. Long-lived on purpose (per-customer entitlements, ops kill switches) → rename to make
   that clear (`entitlement_*`, `ops_*`) and exempt from expiry.
4. Mid-rollout → make sure it has an owner and expiry.
Then add a rule: every new flag needs an owner and an expiry, and CI warns on expired flags.
```

## Quick Reference

| Rule | Why |
|---|---|
| Evaluate once at the boundary | No half-on states |
| Safe default = old path | Flag outage ≠ release |
| Sticky by user/account | Consistent experience |
| Test both states | Off must really work |
| Criteria before stage 1 | No moving goalposts |
| Compare to unflagged cohort now | Removes seasonality |
| Owner + expiry + cleanup ticket | Flags don't become permanent |
