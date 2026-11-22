---
name: incident-postmortem
description: Writes a blameless incident postmortem with impact, timeline, root cause, and tracked action items. Use after an outage, incident, or production bug when the user shares notes, logs, or a chat thread.
---

# Detailed Instructions

Describe what happened to the system, not who made a mistake. Every claim comes from the material
provided; every action item has an owner and makes this class of incident less likely or less bad.

## Overview

Postmortems turn a bad day into durable fixes, but only if they are accurate, blameless, and end in
action items someone actually owns. This skill assembles the timeline from the raw material,
quantifies impact, separates trigger from root cause and contributing factors, and produces a
document in a standard shape.

## Workflow Rules

1. Gather inputs: incident channel export, alerts, logs, deploy history, status page updates, notes.
2. **Summary:** 2–3 sentences: what broke, for whom, for how long, and how it was fixed.
3. **Impact:** duration (start → mitigated → resolved), affected users or requests (numbers if
   available), revenue or SLA impact, data loss (yes/no).
4. **Timeline** in one time zone (state it), from first cause to resolution, including detection
   and each key decision. Mark detection time and mitigation time.
5. **Root cause and contributing factors:** the trigger (what changed), the underlying cause (why
   that change could break things), and factors that made it worse or slower to fix (missing alert,
   unclear runbook). Use "5 whys" to go past the first answer.
6. **What went well / what was hard:** honest, specific, short.
7. **Action items:** each is concrete, has an owner, a priority, and a due date or ticket, and is
   tagged prevent / detect / mitigate. Mark owner "TBD" if not assigned in the source.
8. Flag gaps in the source material as open questions instead of filling them in.

## Anti-Patterns (What NOT to do)

* Do not name individuals as the cause ("Sam pushed a bad config"). Describe the system: "a config change was deployed without validation".
* Do not stop at the trigger; ask why the system allowed it.
* Do not write action items like "be more careful" or "improve monitoring". Make them specific and checkable.
* Do not invent timestamps, numbers, or owners that are not in the material.
* Do not include customer personal data from logs or tickets.

## Examples

**User:** *(pastes the incident Slack thread and deploy log)* "Write the postmortem for yesterday's checkout outage."

**Expected output:**

```markdown
# Postmortem: Checkout unavailable for 47 minutes (Nov 20)

**Status:** Draft · **Severity:** SEV-1 · **Times:** UTC

## Summary
A config change set the payment provider timeout to 100ms instead of 10s. Most payment requests
timed out and checkout returned errors from 14:06 to 14:53. Rolling back the config resolved it.

## Impact
- 47 minutes of failed checkout (14:06–14:53); 2,318 failed payment attempts.
- About 61% of checkout attempts failed during the window. No data loss; no double charges.

## Timeline
- 14:04 Config change deployed (timeout_ms: 10000 → 100)
- 14:06 Payment error rate rises above 50%
- 14:19 **Detected** — customer support reports failures (no alert fired)
- 14:31 On-call links errors to the config deploy
- 14:49 Config rolled back
- 14:53 **Mitigated** — error rate back to baseline

## Root cause
The timeout value was entered in milliseconds where the reviewer expected seconds. Config changes
skip CI and staging, so no test exercised the new value before production.

Contributing factors
- No alert on payment error rate; detection took 13 minutes and came from customers.
- The rollback command for config was not in the runbook (18 minutes from diagnosis to rollback).

## What went well
- Diagnosis was quick once the deploy log was checked.

## Action items
| Action | Type | Owner | Priority | Due |
|---|---|---|---|---|
| Validate timeout config against allowed ranges in CI | prevent | Payments team | P1 | Nov 28 |
| Route config changes through staging | prevent | Platform | P1 | Dec 5 |
| Alert when payment error rate > 5% for 2 min | detect | On-call lead | P1 | Nov 25 |
| Add config rollback to the checkout runbook | mitigate | TBD | P2 | Nov 27 |

## Open questions
- Were any orders left in "pending payment" that need manual follow-up?
```
