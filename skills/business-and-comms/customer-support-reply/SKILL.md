---
name: customer-support-reply
description: Drafts customer support replies that answer the actual question, give clear next steps, and follow policy without overpromising. Use for tickets, complaints, refunds, or angry customers.
---

# Detailed Instructions

Answer the question the customer asked, in the first lines, with steps they can follow. Be warm
without padding, honest about what you don't know, and never promise what policy or the product
can't deliver.

## Overview

Support replies go wrong by opening with three sentences of apology, answering a different
question, burying the steps, or promising a fix date nobody committed to. This skill reads the
ticket for the real need and emotion, checks the facts and policy available, and drafts a reply
that resolves it or sets an honest expectation.

## Workflow Rules

1. **Read the whole thread** and identify: the customer's actual question or goal, what they
   already tried, their emotional state, and their plan or account details if relevant.
2. **Check facts** against what you have: help docs, policy (refunds, SLAs), account data, known
   incidents. If a fact isn't available, mark it `[CHECK: …]` for the agent instead of guessing.
3. **Structure the reply:**
   - One line of acknowledgment that is specific to their situation (not generic "sorry for any
     inconvenience").
   - The answer or resolution, up front.
   - Numbered steps if they need to do something; exact button and menu names.
   - What happens next and when, only with commitments that are real ("I've escalated this to our
     billing team; they reply within 1 business day" if that is the SLA).
   - A short close; offer one specific follow-up.
4. **Tone:** match formality to the customer; calm and direct with angry customers; no blame on
   the customer or other teams; no internal jargon or ticket codes.
5. **Policy limits:** if the answer is "no", say so clearly, explain why briefly, and offer the
   best available alternative.
6. **Length:** as short as solves it. Most replies fit in 60–150 words.
7. **Flag for the agent** anything risky: legal threats, security or data concerns, chargebacks,
   requests outside policy that need approval.

## Anti-Patterns (What NOT to do)

* Do not promise refunds, credits, fix dates, or features that are not confirmed.
* Do not open with paragraphs of apology before the answer.
* Do not paste the knowledge-base article instead of answering their specific case.
* Do not blame the customer ("as clearly stated in our docs") or other teams.
* Do not invent account details, order status, or policy; mark them for checking.
* Do not ask for information they already gave in the thread.

## Examples

**User:** "Draft a reply." *(ticket: "This is the THIRD time I'm writing. I was charged twice for my annual plan on Nov 3 ($240 each). Nobody has answered. I want my money back or I'm disputing it with my bank.")*

**Expected output:**

```text
Hi Maria,

You're right — you were charged twice for your annual plan on November 3, and you should have
heard back from us long before a third message. I'm sorry about that.

I've refunded the duplicate $240 charge today. Refunds take 5–10 business days to appear on
your statement, depending on your bank [CHECK: refund processed in Stripe]. Your annual plan stays
active through November 3, 2027 — nothing changes there.

You don't need to contact your bank; if you've already opened a dispute, reply here and I'll
make sure the two don't overlap.

I'll check back on November 18 to confirm the refund has landed.

Best,
Sam
```

```text
Agent notes: customer mentioned a bank dispute → if a chargeback is already open, a refund can
double-credit; check in Stripe before sending. Earlier two tickets (#48121, #48233) were unassigned
— worth a look for the queue.
```
