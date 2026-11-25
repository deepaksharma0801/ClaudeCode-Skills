---
name: design-doc-writer
description: Writes a technical design doc with context, goals, non-goals, design, alternatives, risks, and a rollout plan. Use when the user asks for a design doc, RFC, tech spec, or proposal for a change.
---

# Detailed Instructions

A design doc exists to get the right decision made before code is written. Make the problem and
the trade-offs clear enough that a reviewer can disagree specifically.
A design doc is cheapest when it changes the plan: reviewers can only push back on what's written
down. Hiding the alternatives or the risky parts turns the review into a rubber stamp.

## When to Use

- "Write a design doc / RFC / tech spec / proposal" for a change
- A change that touches several teams, production data, public APIs, or costs real money
- Writing down a decision already made, so others understand why

**Don't use when:** the question is a single choice between options for a decision-maker (use
`decision-memo`), or the change is small enough that a PR description covers it
(use `pr-description-writer`).

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

## Output shape

```markdown
# <Title> — design doc
Status · Author · Reviewers · Decision needed by
## Summary              recommendation + decisions needed from reviewers
## Context              current state, the problem, evidence
## Goals / Non-goals
## Proposed design      components, data, APIs, diagram, failure modes
## Alternatives         ≥ 2 incl. "do nothing", why not chosen
## Risks & open questions
## Rollout              steps, flags, backfill, monitoring, rollback
## Cost & effort
```

## Checklist

```text
- [ ] Problem and evidence stated before the solution
- [ ] Goals measurable; non-goals explicit
- [ ] Design covers components, data, APIs, failure modes (diagram if > 2 parts)
- [ ] ≥ 2 real alternatives incl. "do nothing", each with why not
- [ ] Risks and open questions listed
- [ ] Rollout with flags, migration, monitoring, rollback
- [ ] Cost/effort estimate; assumptions marked
- [ ] Summary with recommendation and decisions needed at the top
- [ ] Length proportional to the change
```

## Anti-Patterns (What NOT to do)

* Do not start with the solution before explaining the problem.
* Do not include straw-man alternatives designed to lose.
* Do not leave out the rollout and rollback plan for anything touching production data.
* Do not invent metrics, current-system details, or estimates; ask or mark them as assumptions.
* Do not pad with generic sections that have nothing specific to say.

## Examples

### Example 1: async PDF generation

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

### Example 2: a one-page doc for a small change

**User:** "Do we need a full design doc for adding rate limiting to our public API?"

**Expected output:**

```markdown
# Design: Rate limiting for the public API (1 page)

**Summary:** Add per-API-key rate limits (600 req/min default) at the gateway, returning 429 with
Retry-After. Decision needed: default limit and whether enterprise keys get higher limits.

**Problem:** Two customers' scripts caused 30-minute slowdowns for everyone in October (incidents #88, #93).

**Design:** Token bucket per API key in Redis (gateway plugin, already supported).
Headers: RateLimit-Limit, RateLimit-Remaining, Retry-After. Per-key overrides in the admin panel.

**Alternatives:** per-IP limits (rejected: customers share NAT IPs); no limit + autoscaling
(rejected: cost, and the DB is the bottleneck).

**Rollout:** log-only mode for 1 week to see who'd be limited → email those customers → enforce.
Rollback: disable the plugin.

**Risk:** a customer's legitimate batch job gets throttled → overrides + the log-only week.
```

A page is enough here: one component, a reversible rollout, and the main decision is a number.

## Quick Reference

| Section | Must contain |
|---|---|
| Summary | Recommendation + decisions needed |
| Context | Problem with evidence |
| Goals / non-goals | Measurable; explicit exclusions |
| Design | Components, data, APIs, failure modes |
| Alternatives | ≥ 2 real ones + do nothing |
| Rollout | Flags, migration, monitoring, rollback |
| Length | Proportional to risk and scope |
