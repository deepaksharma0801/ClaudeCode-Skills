---
name: code-review-comments
description: Writes clear, kind, actionable code review comments labeled by intent (blocking issue, suggestion, nitpick, question). Use when reviewing a PR or softening harsh review feedback.
---

# Detailed Instructions

Every comment says what you noticed, why it matters, and what would resolve it — and whether it
blocks the merge. The author should never have to guess how serious a comment is.

## Overview

Review comments fail in two ways: vague ("this seems off") or harsh ("why would you do this?").
Both slow merges and wear people down, and unlabeled nitpicks get treated as blockers. This skill
writes comments using the [Conventional Comments](https://conventionalcomments.org/) labels so
intent is explicit, anchors each one to code, and suggests a concrete change.

## Workflow Rules

1. **Read the whole diff first** and the PR description, so comments address the change's intent,
   not just lines.
2. **Prioritize:** correctness, security, and data-loss risks first; then design and
   maintainability; style last. Leave style to linters and formatters where possible.
3. **Label every comment** with a Conventional Comments label and, when useful, a decoration:
   - `issue (blocking):` a problem that must be fixed before merge
   - `suggestion:` / `suggestion (non-blocking):` a better way, with the proposed change
   - `question:` you genuinely don't know; ask instead of asserting
   - `nitpick (non-blocking):` trivial preference
   - `praise:` something done well (specific, not filler)
   - `thought:` / `note:` context with no action needed
4. **Write each comment as:** observation → why it matters (impact or risk) → concrete fix, ideally
   as a code suggestion block.
5. **Talk about the code, not the person:** "this query runs per item" — not "you wrote an N+1".
   Use "we" or neutral phrasing; ask "what do you think about…" for judgment calls.
6. **Be specific:** cite the line, the input that breaks it, or the doc that supports the point.
7. **Batch the small stuff:** group repeated nitpicks into one comment instead of ten.
8. **Summarize** at the top of the review: the overall verdict (approve, approve with suggestions,
   request changes), the blocking items, and one line of genuine praise if earned.

## Anti-Patterns (What NOT to do)

* Do not leave unlabeled comments; the author can't tell a blocker from a preference.
* Do not ask rhetorical questions ("Why would you do it like this?") — state the concern.
* Do not block a merge on personal style preferences.
* Do not write "LGTM" on a change you didn't actually read, or bury a blocking issue under nits.
* Do not leave a comment without a proposed resolution unless it is a genuine question.
* Do not use sarcasm, "just", "obviously", or "simply".

## Examples

**User:** "Help me word my review. Draft notes: 'n+1 in get_orders. why no tests?? also var names bad. retry loop has no limit'"

**Expected output:**

````markdown
**Summary:** Requesting changes — two blocking items (unbounded retry, N+1 query). The new
pagination helper is a nice cleanup.

---

**issue (blocking):** `orders/service.py:58` — the retry loop has no maximum, so a persistent
failure (e.g. the payment API returning 500) retries forever and holds the worker.
Suggest capping attempts with backoff:
```python
for attempt in range(MAX_ATTEMPTS):  # MAX_ATTEMPTS = 5
    try:
        return client.charge(order)
    except TransientError:
        time.sleep(min(2 ** attempt, 30))
raise ChargeFailed(order.id)
```

**issue (blocking):** `orders/service.py:31` — `get_orders` loads each order's customer inside the
loop, which is one query per order (51 queries for a page of 50). Could we use
`select_related("customer")` here?

**question:** I don't see tests for the new retry path. Is that covered somewhere I missed? If not,
a test with a client that always raises `TransientError` would pin the new limit.

**nitpick (non-blocking):** a few names (`d`, `tmp2`, `res`) in `build_summary` are hard to follow;
`due_date`, `line_totals`, `summary` would read more easily.

**praise:** `paginate()` is a clear, reusable helper — nice to see the three copies of that logic go.
````
