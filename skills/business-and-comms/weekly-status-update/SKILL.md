---
name: weekly-status-update
description: Turns git history, notes, or a task list into a short weekly status update for a manager or team. Use when asked for a status update, weekly report, standup summary, or "what did I do this week".
---

# Detailed Instructions

Lead with outcomes, not activity. Every line should answer "so what?" for a reader who has
30 seconds.
Status updates are read in seconds and skimmed for three things: what's done, what's stuck, and
what the reader must do. Anything else is cost to the reader.

## When to Use

- "Write my weekly update / status report / standup summary"
- "What did I (or the team) do this week?" from git, tickets, or notes
- Monthly or sprint summaries for a manager or stakeholders

**Don't use when:** the audience is non-technical leadership and the topic is one incident or
decision (use `explain-for-stakeholders`), or it's release notes for users (use
`release-notes-writer`).

## Overview

Status updates fail in two ways: a raw list of commits nobody can parse, or vague prose ("made
good progress on auth"). This skill gathers what actually happened, rewrites it as outcomes, and
surfaces blockers and decisions the reader needs to act on.

## Workflow Rules

1. Gather sources the user points to. In a repo, default to
   `git log --since="7 days ago" --author="$(git config user.name)" --oneline --no-merges`
   plus merged PRs if `gh` is available. Otherwise use the notes or tasks the user provides.
2. Group work into 2–5 **themes** (a feature, a project, an incident), not by day or by commit.
3. For each theme write one line: what is now true + the evidence (PR, metric, demo link).
4. List **Blockers / Risks** with what is needed and from whom. If there are none, write "None".
5. List **Next week**: 2–4 concrete commitments.
6. Add **Decisions needed** only if something is waiting on the reader.
7. Keep the whole update under ~150 words. Match the tone the user asks for (Slack, email, doc).
8. If the sources are thin, say what is missing and ask, rather than padding.

## Output shape

```text
**Week of <date>**
**Shipped**            outcome + evidence (PR, metric, demo)
**In progress**        what + how far + next milestone
**Blockers / Risks**   what's needed, from whom, by when — or "None"
**Next week**          2–4 commitments
**Decisions needed**   only if something waits on the reader
```

## Checklist

```text
- [ ] Sources gathered (git log, merged PRs, tickets, notes)
- [ ] Work grouped into 2–5 themes, not by day or commit
- [ ] Each line states an outcome with evidence
- [ ] Blockers name what's needed and from whom
- [ ] Under ~150 words; tone matches the channel
- [ ] No invented metrics; no private data
```

## Anti-Patterns (What NOT to do)

* Do not paste commit messages verbatim or list every commit.
* Do not use activity words with no outcome ("worked on", "looked into", "continued").
* Do not invent metrics, dates, or completion percentages that are not in the sources.
* Do not bury a blocker at the bottom of a paragraph. Blockers get their own section.
* Do not include private or customer data from commit messages or notes in an update meant for a
  wider audience.

## Examples

### Example 1: from a repo

**User:** "Write my weekly update for my manager from this repo."

**Expected output:**

```markdown
**Week of Nov 17**

**Shipped**
- Webhook retries are live — failed deliveries now retry 5x with backoff (#412). Missed-event
  tickets dropped from 9 last week to 0.
- Checkout no longer crashes on products imported after the supplier CSV change (#418).

**In progress**
- Usage-based billing: pricing engine done and tested; invoice rendering 50% (#420).

**Blockers / Risks**
- Need Stripe production keys from Finance to test metered billing end to end.

**Next week**
- Finish invoice rendering and open the billing PR.
- Run dependency audit before the Dec 1 launch.
```

### Example 2: a week with little to show

**User:** "Bad week — mostly debugging a flaky deploy and interviews. Write my update anyway."

**Expected output:**

```markdown
**Week of Nov 17**

**Shipped**
- Found the cause of the intermittent deploy failures: a race between the migration job and app
  start (#431). Fix in review; deploys have failed 6 times this month because of it.

**In progress**
- Fix for #431 — needs one more review, then a week of watching deploys.

**Other**
- 4 candidate interviews for the backend role (feedback submitted).

**Blockers / Risks**
- Usage-based billing slips ~1 week because of the deploy work. New target: Dec 5.

**Next week**
- Merge #431, then back to invoice rendering for billing.
```

Honest about the slip, with the reason and new date — that's what a manager needs.

## Quick Reference

| Do | Instead of |
|---|---|
| "Webhook retries live — missed events 9 → 0" | "Worked on webhooks" |
| Group by theme | List commits by day |
| Blocker + who + by when | "Some blockers" |
| New date when something slips | Silence about the slip |
| ≤ 150 words | A full changelog |
