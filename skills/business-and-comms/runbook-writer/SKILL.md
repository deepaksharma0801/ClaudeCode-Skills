---
name: runbook-writer
description: Writes an operational runbook for an alert or routine task with triage steps, exact commands, decision points, rollback, and escalation. Use when asked for a runbook, playbook, or on-call doc.
---

# Detailed Instructions

Write for the person paged at 3 a.m. who has never seen this system: every step is a command
they can copy, a result they can check, and a decision with a clear next step. A runbook is
tested by whether someone unfamiliar can follow it under stress without asking anyone — so no
"check the logs", no implied knowledge, and every risky step says how to undo it.

## When to Use

- "Write a runbook for the `HighQueueLatency` alert"
- Documenting a routine operation: rotating certificates, failing over a database, restoring a
  backup, scaling a service
- Turning an incident's fix into a repeatable procedure (often an action item from
  `incident-postmortem`)
- Reviewing an existing runbook for gaps

**Don't use when:** the incident is happening now and there's no runbook (use `log-triage` /
`root-cause-debugging` to work the problem, then write the runbook), or the document explains
architecture rather than steps (use `design-doc-writer` or `codebase-onboarding`).

## Overview

Bad runbooks say what to think about ("investigate the database"), not what to do. They go stale,
assume access the reader doesn't have, and stop at the happy path. This skill writes a runbook
with a fixed shape: what the alert means and its user impact, prerequisites, a fast triage that
branches on what the reader sees, exact remediation commands with expected output and rollback,
verification, and escalation — then marks anything it had to assume so a human can confirm it.

## Workflow Rules

1. **Gather facts** from the user, the alert definition, dashboards, past incidents, scripts, and
   the repo (deploy commands, service names, namespaces). Never invent hostnames, commands, or
   dashboard links — leave `<TODO: confirm>` where a fact is missing.
2. **Header:** what this covers, the alert's exact name and condition, **user impact** if
   ignored, severity, owner team, and last-tested date.
3. **Prerequisites:** access and tools needed (VPN, kubectl context, AWS role, dashboard), with how
   to get them. The middle of an incident is no time to request access.
4. **Triage first (≤ 5 minutes):** 2–4 checks that tell the reader which situation they're in.
   Each check is a command or link, the expected healthy result, and "if X → go to section N".
5. **Remediation per situation:** numbered steps. Each step has the exact command, what output
   to expect, and how long it takes. Mark **[RISKY]** steps (restarts, failovers, data
   changes) with their **rollback** right below them.
6. **Verify:** how to confirm it's fixed (metric back under threshold, alert resolved, a user-level
   check).
7. **Escalate:** when (time limit, or a condition such as "data loss suspected"), to whom (team, rotation,
   channel), and what to include in the message.
8. **After:** what to record (incident ticket, timeline) and when to update this runbook.
9. Keep it **scannable:** headings for each situation, code blocks for commands, no paragraphs
   longer than three lines.

## Output shape

```markdown
# Runbook: <alert or task>
Alert/condition · Impact · Severity · Owner · Last tested
## Prerequisites
## Triage (≤ 5 min)        check → expected → if not, go to …
## Situation A: <cause>    steps with commands, expected output, [RISKY] + rollback
## Situation B: <cause>
## Verify
## Escalate                when · who · what to include
## After the incident
```

## Checklist

```text
- [ ] Alert name, condition, user impact, owner stated
- [ ] Prerequisites list access and how to get it
- [ ] Triage branches to situations in ≤ 5 minutes
- [ ] Every step is a copyable command with expected output
- [ ] Risky steps marked with rollback
- [ ] Verification is observable
- [ ] Escalation has a time limit, a contact, and what to send
- [ ] Unknown facts marked <TODO: confirm>, not invented
- [ ] Last-tested date; owner to keep it current
```

## Anti-Patterns (What NOT to do)

* **"Check the logs" / "investigate"** — say which logs, the query, and what you're looking for.
* **Invented commands, hosts, or links** — a wrong command at 3 a.m. causes the next incident.
* **Restarts and failovers without rollback** — the reader needs a way back if it gets worse.
* **Only the happy path** — triage must cover the 2–3 common causes and "none of the above → escalate".
* **Secrets pasted into the runbook** — reference the secret manager path instead.
* **No owner or test date** — untested runbooks rot quietly.

## Examples

### Example 1: queue latency alert

**User:** "Write a runbook for our `OrdersQueueLagHigh` alert. It fires when the orders SQS queue's
oldest message is > 5 min old. Workers run as the `orders-worker` deployment in the `prod`
namespace on EKS."

**Expected output:**

````markdown
# Runbook: OrdersQueueLagHigh

**Condition:** SQS `orders-prod` ApproximateAgeOfOldestMessage > 300 s for 5 min
**Impact:** orders confirm late; customers don't get confirmation emails; > 30 min risks duplicate
orders from retries. **Severity:** SEV-2 · **Owner:** Orders team · **Last tested:** <TODO: confirm>

## Prerequisites
- VPN + `kubectl` context `prod-eks` (`aws eks update-kubeconfig --name <TODO: cluster> --region <TODO>`)
- AWS role `oncall-readonly` (request in #infra-access ahead of your first shift)

## Triage (≤ 5 min)
1. Are workers running?
   `kubectl -n prod get deploy orders-worker`
   Expected: READY = desired (e.g. 6/6). Not ready → **Situation A**.
2. Are workers erroring?
   `kubectl -n prod logs deploy/orders-worker --since=10m | grep -c ERROR`
   Expected: < 10. Many errors → **Situation B**.
3. Is traffic just high? Dashboard: <TODO: link> "Orders received/min".
   > 2× normal with healthy workers → **Situation C**.
4. None of these → **Escalate**.

## Situation A: workers not running
1. `kubectl -n prod describe deploy orders-worker` → read Events.
2. CrashLoopBackOff after a recent deploy → roll back:
   **[RISKY]** `kubectl -n prod rollout undo deploy/orders-worker`
   Rollback of the rollback: `kubectl -n prod rollout undo deploy/orders-worker` again
   (returns to the newer revision).
   Expected: `kubectl -n prod rollout status deploy/orders-worker` → "successfully rolled out" in ~2 min.

## Situation B: workers erroring
1. `kubectl -n prod logs deploy/orders-worker --since=10m | grep ERROR | sort | uniq -c | sort -rn | head`
2. `payments-api timeout` dominant → payments is degraded: check #payments-status; escalate to
   Payments on-call. Don't restart workers (retries will add load).
3. Unknown error → escalate with the top 5 lines.

## Situation C: traffic spike
**[RISKY]** Scale workers: `kubectl -n prod scale deploy/orders-worker --replicas=12`
Rollback: `kubectl -n prod scale deploy/orders-worker --replicas=6`
Max 12 — the database connection pool limits beyond that <TODO: confirm limit>.

## Verify
Queue age < 60 s on the dashboard and the alert resolves within 10 min.

## Escalate
After 20 min without improvement, or if any orders may be lost: page Orders secondary via
<TODO: paging tool>; post in #incidents with alert time, triage results, and what you've tried.

## After the incident
Open an incident ticket with the timeline. If a step here was wrong or missing, fix this runbook
in the same week.
````

### Example 2: reviewing a vague runbook

**User:** "Is this runbook OK? 'If the DB is slow, check the dashboards and restart if needed.'"

**Expected output:**

```text
Not yet — an unfamiliar on-call couldn't act on it:
1. "DB is slow" → which alert and threshold? (e.g. p95 query time > 500 ms for 5 min)
2. "check the dashboards" → which dashboard, which panel, what's normal?
3. "restart if needed" → restart what, with which command, when is it needed, and what's the
   risk? Restarting a primary database drops every connection — that needs a [RISKY] marker and a rollback or
   failover plan, or it shouldn't be in the runbook at all.
4. Missing: triage branches (long-running query? lock contention? CPU?), verification, escalation.

Send me the alert definition and the usual causes from past incidents, and I'll rewrite it in the
standard shape.
```

## Quick Reference

| Section | Must contain |
|---|---|
| Header | Alert condition, user impact, severity, owner, last tested |
| Prerequisites | Access + how to get it |
| Triage | Check → expected → which section next |
| Remediation | Exact commands, expected output, [RISKY] + rollback |
| Verify | Observable signal it's fixed |
| Escalate | Time limit, who, what to send |
| Unknowns | `<TODO: confirm>`, never invented |
