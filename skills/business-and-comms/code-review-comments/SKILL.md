---
name: code-review-comments
description: Writes clear, kind, actionable code review comments labeled by intent (blocking issue, suggestion, nitpick, question). Use when reviewing a PR or softening harsh review feedback.
---

# Detailed Instructions

Every comment says what you noticed, why it matters, and what would resolve it — and whether it
blocks the merge. The author should never have to guess how serious a comment is.
The author reads each comment asking "do I have to change this, and how?" Labels answer the
first question and a concrete suggestion answers the second; tone decides whether they ask
follow-up questions or get defensive.

## When to Use

- Writing or polishing review comments on a pull request
- Turning rough review notes into clear feedback
- Softening comments without losing the point
- Writing the overall review summary (approve / request changes)

**Don't use when:** the task is finding bugs in the code (review it first — e.g. with
`auth-code-review`, `sql-query-reviewer`, or `api-design-review` — then use this to word the
findings), or writing the PR description (use `pr-description-writer`).

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

## Output shape

```text
Summary: verdict (approve / approve with suggestions / request changes) + blocking items + one
genuine praise if earned.

<label> (<decoration>): <file:line> — <observation>. <why it matters>. <concrete fix or question>
```

## Checklist

```text
- [ ] Whole diff and PR description read first
- [ ] Correctness/security before design before style
- [ ] Every comment labeled (issue/suggestion/question/nitpick/praise/thought)
- [ ] Blocking vs non-blocking explicit
- [ ] Each comment: observation → why → concrete fix
- [ ] About the code, not the person; no sarcasm or rhetorical questions
- [ ] Repeated nits batched into one comment
- [ ] Summary with verdict at the top
```

## Anti-Patterns (What NOT to do)

* Do not leave unlabeled comments; the author can't tell a blocker from a preference.
* Do not ask rhetorical questions ("Why would you do it like this?") — state the concern.
* Do not block a merge on personal style preferences.
* Do not write "LGTM" on a change you didn't actually read, or bury a blocking issue under nits.
* Do not leave a comment without a proposed resolution unless it is a genuine question.
* Do not use sarcasm, "just", "obviously", or "simply".

## Examples

### Example 1: rough notes into comments

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

### Example 2: a large PR with only style issues

**User:** "This 600-line PR looks fine logically, I just have a bunch of naming and formatting nits. How should I review it?"

**Expected output:**

```markdown
**Summary:** Approve. Logic and tests look good; a few non-blocking naming suggestions below.
Formatting differences should be handled by the formatter, not review.

**suggestion (non-blocking):** Could we run `ruff format` in pre-commit so quote style and line
length stop showing up in reviews? Happy to add it in a follow-up.

**nitpick (non-blocking):** A few names are hard to scan — `tmp2` (export.py:41), `d` (export.py:88),
`res2` (export.py:120). Maybe `filtered_rows`, `due_date`, `csv_rows`?

**praise:** The streaming writer keeps memory flat for large exports — nice.
```

One batched nitpick instead of fifteen separate comments, and nothing blocking that a tool should own.

## Quick Reference

| Label | Use for | Blocks merge? |
|---|---|---|
| `issue (blocking):` | Bugs, security, data loss, broken contracts | Yes |
| `suggestion:` | A better approach, with the change | No (unless marked) |
| `question:` | You genuinely don't know | Usually no |
| `nitpick (non-blocking):` | Preference, naming | No |
| `praise:` | Specific good work | — |
| Style/formatting | Formatter or linter | Shouldn't need review |
