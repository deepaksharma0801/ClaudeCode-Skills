---
name: implementation-plan-writer
description: Turns a feature request, spec, or ticket into an ordered implementation plan of small, testable tasks with files, verification, and risks. Use before starting multi-step coding work.
---

# Detailed Instructions

Read the code before planning, then break the work into tasks small enough to finish, test, and
commit one at a time — each leaves the system working. A plan built from the real codebase
catches the hard part (the migration, the shared module, the missing test harness) before it
derails the work; a plan built from the ticket alone just restates it.

## When to Use

- "Plan this feature / ticket / spec before we start"
- A change that touches more than ~3 files, several layers, or needs a migration or rollout
- Splitting work across people, PRs, or sessions
- Estimating, or deciding what can ship first

**Don't use when:** the change is a one-file fix (just do it), the design itself is still open
(use `design-doc-writer` to choose an approach first), or the task is a refactor with no behavior
change (use `safe-refactor`).

## Overview

Without a plan, multi-step work drifts: the risky part is found last, tasks are too large to
review, and nothing works until everything does. This skill explores the codebase, pins down
what "done" means, finds the riskiest unknown and schedules it first, and writes an ordered list
of tasks — each with files, the test that proves it, and a commit point.

## Workflow Rules

### 1. Understand the goal

1. Restate the goal as **acceptance criteria**: observable behaviors ("Admins can export invoices
   as CSV from /billing; the file has one row per invoice line"). If the request is ambiguous on
   something that changes the plan, ask — one round, at most 3 questions.
2. List **non-goals** to stop scope creep ("No PDF export; no scheduling").

### 2. Read the code

3. Find where the change lands: entry points, the module that owns the data, similar existing
   features to copy (`grep -r "export" src/`), test layout, and how migrations and feature flags
   are done. Cite real paths in the plan; never invent file names.
4. Note **constraints** found: shared code with other callers, public APIs, data volume,
   permissions, missing tests around the area.

### 3. Order the work

5. **Riskiest unknown first.** If something might make the approach fail (a library limit, a slow
   query, an API that may not exist), make task 1 a spike that answers it.
6. **Thin vertical slice early:** get one path working end to end (even ugly) before broadening.
   That surfaces integration problems on day 1, not day 5.
7. **Each task:** ≤ ~half a day, one reviewable commit or PR, the system still builds and passes
   tests after it. Expand-then-contract for anything breaking (add new → migrate callers → remove
   old).
8. Put **tests inside each task**, not in a "write tests" task at the end.

### 4. Write the plan

9. Use the output shape below. Each task names files, the change, and **how to verify** (a test,
   a command, a manual check). Mark tasks that can run in parallel.
10. End with **risks and open questions**, and a **rollout** line if users are affected (flag,
    migration order, backfill).

## Output shape

```markdown
# Plan: <feature>
**Goal / acceptance criteria** — bullet list of observable behaviors
**Non-goals**
**Context found** — key files, patterns to follow, constraints
## Tasks
1. <task> — files: … — verify: … — (parallel with 2?)
2. …
**Risks & open questions**
**Rollout**
```

## Checklist

```text
- [ ] Acceptance criteria and non-goals written
- [ ] Codebase read; real paths, patterns, and constraints cited
- [ ] Riskiest unknown scheduled first (spike if needed)
- [ ] Thin end-to-end slice early
- [ ] Every task small, verifiable, leaves the build green
- [ ] Tests inside tasks, not at the end
- [ ] Breaking changes split expand → migrate → contract
- [ ] Risks, open questions, rollout listed
```

## Red Flags

- A task called "implement backend" or "write tests".
- A plan with no file paths — it wasn't built from the code.
- The migration, permissions, or perf question sitting at task 7.
- Nothing works end to end until the last task.
- Starting to code before acceptance criteria exist.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "It's obvious, no plan needed." | If it touches 5+ files, the order matters and the risky bit hides. |
| "Tests at the end are faster." | Bugs found late cost more, and "tests" is the task that gets cut. |
| "We'll figure out the migration later." | The migration often decides the whole approach. Do it first. |
| "One big PR is easier." | Big PRs get shallow reviews and are hard to revert. |

## Anti-Patterns (What NOT to do)

* **Planning from the ticket alone** — invented paths and patterns make the plan wrong on contact.
* **Horizontal layers (all DB, then all API, then all UI)** — nothing is testable until the end.
* **Tasks without verification** — "done" becomes an opinion.
* **Over-detailed plans for uncertain work** — plan the spike, then plan the rest with its answer.
* **Silent scope growth** — anything not in the criteria goes to non-goals or a follow-up.

## Examples

### Example 1: invoice CSV export

**User:** "Plan adding CSV export to the invoices page. Django + React."

**Expected output:**

```markdown
# Plan: CSV export for invoices

**Acceptance criteria**
- Admins see "Export CSV" on /billing/invoices; non-admins don't.
- Export respects the current filters (date range, status).
- One row per invoice line; columns match docs/billing-fields.md.
- Works for the largest tenant (~180k lines) without timing out.

**Non-goals:** PDF export, scheduled exports, email delivery.

**Context found**
- Invoice list API: billing/views.py `InvoiceListView` (filters in billing/filters.py).
- Existing streaming export to copy: reports/views.py `UsageExportView` (StreamingHttpResponse).
- Permission: `billing.view_all_invoices` used by `IsBillingAdmin` in billing/permissions.py.
- Frontend: web/src/pages/Invoices.tsx; no existing download helper.

## Tasks
1. **Spike (risk):** time `InvoiceLine` query for the largest tenant with
   `.iterator(chunk_size=2000)`. Verify: < 30s locally on a prod-size snapshot. If not, switch to
   an async job (replan tasks 3–5).
2. **Endpoint, one column:** `GET /api/invoices/export.csv` streaming id + total, reusing
   `InvoiceFilter` and `IsBillingAdmin`. Files: billing/views.py, billing/urls.py.
   Verify: test for 200 as admin, 403 as member, filter applied.
3. **All columns + formatting** per docs/billing-fields.md (money as decimal strings, ISO dates,
   CSV-injection escaping for cells starting with = + - @). Verify: snapshot test of a 3-line file.
4. **Frontend button** (parallel with 3): add to Invoices.tsx, pass current filters as query
   params, hidden without permission. Verify: component test + manual download.
5. **Large-tenant check:** run against the staging snapshot. Verify: completes, memory flat.

**Risks & open questions**
- If task 1 fails, export becomes an async job with an emailed link (bigger change).
- Do finance want tax lines as separate rows? (Asked in ticket; affects task 3.)

**Rollout:** behind `invoice_csv_export` flag; enable for internal tenant, then all.
```

### Example 2: when the right answer is "design first"

**User:** "Plan migrating our auth from sessions to JWTs."

**Expected output:**

```text
Before a task list, there's an open design choice that changes every task: where tokens live
(httpOnly cookie vs. Authorization header), how revocation works (short-lived access + refresh
with a denylist?), and whether mobile clients need it too. Those are design-doc questions, not
plan questions.

Suggest: write a short design doc (design-doc-writer) choosing the approach — or tell me the
decisions and I'll plan it. If you want to start now, the safe first task is the same either way:
add tests that pin current login, logout, and session-expiry behavior (auth/tests/), so the
migration has a safety net.
```

## Quick Reference

| Principle | In practice |
|---|---|
| Criteria first | Observable behaviors + non-goals |
| Read before planning | Real paths, patterns to copy, constraints |
| Risk first | Spike the unknown as task 1 |
| Vertical slice | One path working end to end early |
| Small tasks | ≤ half a day, green build after each |
| Verify each | Test or command per task |
| Breaking changes | Expand → migrate → contract |
