---
name: design-doc-writer
description: Writes a technical design doc with context, goals, non-goals, design, alternatives, risks, and a rollout plan. Use when the user asks for a design doc, RFC, tech spec, or proposal for a change.
---

# Detailed Instructions

A design doc exists to get the right decision made before code is written. Make the problem and
the trade-offs clear enough that a reviewer can disagree specifically.

## Overview

Weak design docs describe a solution without the problem, skip the alternatives, or hide the risky
parts. This skill structures a doc so reviewers can check the reasoning: why now, what success
looks like, what is explicitly out of scope, what was considered and rejected, and how the change
ships safely.

## Workflow Rules

1. Gather inputs: the problem, constraints, existing system (read the relevant code if available),
   and the audience (team, architecture review, leadership).
2. Use this structure, scaling depth to the size of the change:
   - **Context:** the current state and the problem, with evidence (metrics, incidents, requests).
   - **Goals:** measurable outcomes. **Non-goals:** things a reader might expect that are out of scope.
   - **Proposed design:** components, data model changes, APIs, and a diagram (Mermaid) for
     anything with more than two moving parts. Cover failure modes.
   - **Alternatives considered:** at least two, including "do nothing", each with why it was not
     chosen.
   - **Risks and open questions:** what could go wrong, and what still needs a decision.
   - **Rollout:** migration steps, feature flags, backfill, monitoring, and rollback.
   - **Cost and effort:** rough estimate and any new infrastructure.
3. Put the recommendation and the decisions needed from reviewers at the top in a short summary.
4. Mark assumptions explicitly; do not present them as facts.
5. Keep it as short as the change allows. A two-week change needs two pages, not ten.

## Anti-Patterns (What NOT to do)

* Do not start with the solution before explaining the problem.
* Do not include straw-man alternatives designed to lose.
* Do not leave out the rollout and rollback plan for anything touching production data.
* Do not invent metrics, current-system details, or estimates; ask or mark them as assumptions.
* Do not pad with generic sections that have nothing specific to say.

## Examples

**User:** "Write a design doc for moving our PDF invoice generation from the web request to a background job. Requests time out on large invoices."

**Expected output:**

```markdown
# Design: Async invoice PDF generation

**Status:** Draft · **Decision needed by:** Dec 3
**Summary:** Move PDF rendering out of the request into a queued job; the API returns immediately and the
PDF link arrives by webhook and email. Reviewers: please confirm the webhook contract (section 4).

## 1. Context
POST /invoices renders the PDF synchronously. Invoices over ~400 lines exceed the 30 s gateway
timeout (212 failures last month; 3 enterprise customers affected).

## 2. Goals / Non-goals
Goals: no invoice creation fails due to PDF time; p95 POST /invoices < 500 ms; PDF ready < 2 min.
Non-goals: changing the PDF template; supporting other document types.

## 3. Proposed design
POST /invoices → save invoice (pdf_status = pending) → enqueue render_pdf(invoice_id) → 201
Worker → render → upload to storage → pdf_status = ready → webhook invoice.pdf_ready + email
Failures: 3 retries with backoff, then pdf_status = failed and an alert.

## 4. API changes
- POST /invoices returns 201 with pdf_status: "pending" (was: pdf_url).  **Breaking** for clients
  reading pdf_url immediately → keep pdf_url for invoices under 100 lines for 90 days.
- New webhook: invoice.pdf_ready { invoice_id, pdf_url }.

## 5. Alternatives considered
- Raise the gateway timeout to 120 s — rejected: ties up workers and still fails for the largest invoices.
- Faster renderer — reduces time ~40% (benchmark), not enough for 1,000-line invoices.
- Do nothing — enterprise customers keep failing.

## 6. Risks / open questions
- Clients relying on synchronous pdf_url (mitigated by compatibility window).
- Queue backlog at month end: ~9k invoices on the 1st — size workers accordingly (assumption, to verify).

## 7. Rollout
Feature flag per account → internal accounts → 10% → 100% over 2 weeks. Dashboards: queue depth,
render duration, failure count. Rollback: disable the flag; synchronous path stays until Q2.
```
