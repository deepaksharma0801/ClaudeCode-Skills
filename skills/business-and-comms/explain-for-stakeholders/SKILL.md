---
name: explain-for-stakeholders
description: Rewrites technical updates, incidents, or trade-offs for executives, customers, or non-engineers, with the bottom line first and a clear ask. Use for any non-technical audience.
---

# Detailed Instructions

Answer the reader's real question first — what happened, what it means for them, and what you
need from them — in words they already use. Accuracy stays; jargon goes.

## Overview

Engineers write updates in the order they experienced the work: the investigation, then the
mechanism, then (finally) the impact. Executives and customers read in the opposite order and stop
early. This skill restructures the same facts for the audience: bottom line, impact, what is being
done, what is needed, and only as much mechanism as builds trust.

## Workflow Rules

1. **Identify the audience** and what they decide or worry about:
   executives (risk, money, dates, decisions), customers (am I affected, is my data safe, what do I
   do), sales/support (what to tell customers), non-technical teammates (how it changes their work).
2. **Bottom line first:** one or two sentences that stand on their own. If the reader stops here,
   they still know what matters.
3. **Impact in their units:** customers affected, revenue, hours, dates, risk — not services,
   error rates, or ticket numbers. Quantify when the source has numbers; say "we don't know yet"
   when it doesn't.
4. **What we are doing** and when the next update comes.
5. **The ask:** a decision, approval, budget, or action, with a deadline. If there is none, say
   "No action needed."
6. **Mechanism, briefly:** at most two sentences, plain words. Use an analogy only if it is
   accurate; drop it otherwise.
7. **Translate jargon** or remove it: "database migration" → "a change to how we store orders";
   "p95 latency" → "the slowest 1 in 20 page loads". Keep a term only if the reader needs it later.
8. **Match length to channel:** a Slack message is 3–5 lines; an email is a short page; a status
   page is a few sentences per update.
9. **Check honesty:** no minimizing ("brief blip" for a 3-hour outage), no unearned certainty, and
   no blame on individuals or vendors without the facts.

## Anti-Patterns (What NOT to do)

* Do not start with the investigation story or the technical cause.
* Do not leave jargon, acronyms, or internal system names the reader won't know.
* Do not soften or hide impact; trust is lost when the reader finds out later.
* Do not promise dates or root causes that are not confirmed.
* Do not bury the ask in the last paragraph.
* Do not condescend; plain language is not simplified facts.

## Examples

**User:** "Turn this into an update for the CEO." *(engineering note: "p95 on /checkout regressed from 400ms to 3.2s after Tuesday's deploy due to an N+1 in the pricing service; rollback blocked by schema migration; hotfix ETA Thursday; ~6% of sessions hit timeouts; conversion down 11% WoW on mobile.")*

**Expected output:**

```text
Subject: Checkout slowdown — fix lands Thursday, no action needed

Bottom line: Since Tuesday's release, checkout has been slow for some customers, and mobile
sales are down 11% compared with last week. A fix is scheduled for Thursday.

Impact
- About 6 in 100 checkout visits time out instead of completing.
- Mobile conversion is down 11% week over week; desktop is not noticeably affected.

What we're doing
- A fix is in testing and planned to ship Thursday. We can't simply undo Tuesday's release
  because it included a change to how orders are stored that can't be safely reversed.
- I'll send an update Thursday afternoon with results.

Why it happened (short version): the new release made checkout look up prices one item at a time
instead of all at once, which is much slower for large carts.

Ask: none right now. If Thursday's fix slips, I'll ask whether to temporarily turn off the new
pricing feature to restore speed.
```
