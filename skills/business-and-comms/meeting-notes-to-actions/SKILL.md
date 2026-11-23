---
name: meeting-notes-to-actions
description: Turns a meeting transcript or notes into decisions, action items with owners and dates, and open questions. Use when a user shares meeting notes or a transcript and wants a summary or follow-ups.
---

# Detailed Instructions

Extract what was decided and who does what. A recap of the conversation is not the deliverable;
the action list is.
People skim meeting notes for one question: what do I have to do, and by when? Notes that bury the
action items in a chronological recap get no follow-through.

## When to Use

- A meeting transcript (Zoom, Meet, Teams, Otter) or rough notes
- "What were the action items?", "send a recap", "who's doing what?"
- Turning a long Slack thread into decisions and owners

**Don't use when:** the meeting was an incident review (use `incident-postmortem`), or the user
wants a verbatim transcript cleaned up.

## Overview

Meeting summaries fail by retelling the discussion in order, while the decisions and commitments
stay buried. This skill pulls out decisions, action items (owner, task, due date), and unresolved
questions, quoting the source when something is ambiguous.

## Workflow Rules

1. Read the whole transcript or notes before writing anything.
2. **Decisions:** statements where the group agreed on something ("let's go with", "agreed",
   "we'll ship X"). One line each, with who made or approved it if stated.
3. **Action items:** each needs an owner, a concrete task starting with a verb, and a due date.
   - Owner: use the name as written. If no one took it, write `Owner: unassigned`.
   - Due date: use what was said ("by Friday" → the actual date, relative to the meeting date if
     known). If none was said, write `Due: not set`.
4. **Open questions:** topics raised but not resolved, with who is expected to answer.
5. **Summary:** at most 3 sentences on purpose and outcome, written last.
6. Flag contradictions (two people assigned the same task, a decision later reversed) instead of
   picking one silently.
7. Output in the format the user asks for (Slack message, email, doc); default to Markdown with
   the action items as a checklist.

## Output shape

```markdown
**<Meeting> — <date>**
**Summary**         ≤ 3 sentences: purpose and outcome
**Decisions**       one line each, with who decided
**Action items**    - [ ] **Owner** — verb-first task — due date (or "not set")
**Open questions**  topic — who answers
```

## Checklist

```text
- [ ] Read the whole transcript first
- [ ] Decisions captured with who made them
- [ ] Every action has owner, verb-first task, due date (or marked unassigned / not set)
- [ ] Relative dates converted to real dates
- [ ] Contradictions flagged (two owners, reversed decisions)
- [ ] Open questions with who should answer
- [ ] Sensitive remarks left out of shareable notes
```

## Anti-Patterns (What NOT to do)

* Do not summarize the meeting chronologically ("First, Ana talked about…").
* Do not invent owners or deadlines. "Someone should look at this" is unassigned.
* Do not turn every topic mentioned into an action item.
* Do not include side conversations, personal remarks, or sensitive comments (performance, health,
  compensation) in a summary meant to be shared.
* Do not drop disagreements; list them as open questions.

## Examples

### Example 1: a launch-planning call

**User:** *(pastes a 40-minute transcript of a launch-planning call held Tue Nov 18)*
"Give me the follow-ups."

**Expected output:**

```markdown
**Launch planning — Nov 18**

**Summary**
Agreed to launch the billing beta on Dec 1 to 20 design-partner accounts. Pricing page copy and
the Stripe production setup are the remaining blockers.

**Decisions**
- Beta launches Dec 1, limited to 20 accounts (approved by Priya).
- Annual plans are out of scope for the beta.

**Action items**
- [ ] **Marco** — Get Stripe production keys from Finance — due Fri Nov 21
- [ ] **Ana** — Final pricing page copy for review — due Mon Nov 24
- [ ] **Priya** — Send beta invite list to Support — due Wed Nov 26
- [ ] **Unassigned** — Write the rollback runbook — due not set

**Open questions**
- Do beta accounts get a discount after the beta ends? (Priya to confirm with Sales)
- Marco and Ana both said they'd draft the launch email — needs one owner.
```

### Example 2: a meeting with no clear decisions

**User:** *(pastes notes from a 1-hour architecture discussion)* "Action items?"

**Expected output:**

```markdown
**Architecture sync — Nov 20**

**Summary**
Discussed moving search from Postgres full-text to OpenSearch. No decision was made; two concerns
(operating cost and team experience) need data first.

**Decisions**
- None. (Ravi suggested deciding "next week", but nothing was agreed.)

**Action items**
- [ ] **Ravi** — Estimate monthly OpenSearch cost for current index size — due: not set
- [ ] **Unassigned** — Benchmark Postgres full-text on the 10 slowest production queries — due: not set

**Open questions**
- Who operates OpenSearch on-call? (Engineering manager to answer)
- Is search latency actually a customer complaint, or an engineering preference? (Product)

Suggest: assign the benchmark and set dates before the next sync, or this repeats.
```

## Quick Reference

| Phrase in transcript | Becomes |
|---|---|
| "Let's go with X" / "agreed" | Decision |
| "I'll do X by Friday" | Action, owner, real date |
| "Someone should…" | Action, Owner: unassigned |
| "We need to figure out…" | Open question |
| Two people claim it | Flag the contradiction |
| Personal / HR remarks | Leave out |
