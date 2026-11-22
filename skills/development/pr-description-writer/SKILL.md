---
name: pr-description-writer
description: Writes a pull request title and description from the actual branch diff and commits. Use when the user asks to open a PR, draft a PR description, or summarize a branch for review.
---

# Detailed Instructions

Describe what the diff does and why, for a reviewer who has not seen it. Every claim must be
traceable to a change in the diff.

## Overview

A good PR description saves the reviewer from reverse-engineering intent from code. This skill
reads the real changes, groups them by purpose, and produces a short title plus a description
with a summary, the reasoning, the risk, and how it was tested.

## Workflow Rules

1. Find the base branch (`main`, `master`, or what the user names) and collect:
   `git log --oneline <base>..HEAD` and `git diff --stat <base>...HEAD`, then read the full diff.
2. Write the **title**: imperative mood, under 70 characters, names the user-visible effect
   (`Add retry to webhook delivery`, not `webhook changes`).
3. Write **Summary**: 1–3 sentences on what changes and why.
4. Write **Changes**: bullets grouped by purpose, not by file. Mention a file only when a reviewer
   needs to look there.
5. Write **Risk**: what could break, who is affected, and whether it is reversible. Call out
   migrations, config changes, new dependencies, and public API changes explicitly.
6. Write **Testing**: the exact commands run and their result. If nothing was run, say
   "Not tested" — do not imply otherwise.
7. Link any issue numbers found in commit messages or the branch name.
8. Keep it under ~250 words unless the change is genuinely large.

## Anti-Patterns (What NOT to do)

* Do not describe changes that are not in the diff, or intentions the code does not implement.
* Do not list every file. A file-by-file changelog is not a description.
* Do not write "Tested locally" without saying what was run.
* Do not hide breaking changes in the middle of a bullet list. They go under **Risk**.
* Do not use filler ("This PR aims to…", "Various improvements").
* Do not paste the diff or long code blocks into the description.

## Examples

**User:** "Write the PR for this branch."

**Expected output:**

```markdown
**Title:** Retry failed webhook deliveries with exponential backoff

## Summary
Webhook deliveries that fail with a 5xx or timeout are now retried up to 5 times instead of being
dropped. Customers reported missed `order.paid` events during receiver outages (#412).

## Changes
- Add a `delivery_attempts` table and a background worker that retries pending deliveries
  (backoff 30s → 16m).
- Treat 4xx responses as permanent failures; only 5xx and timeouts are retried.
- Expose attempt count and last error on the webhook log page.

## Risk
- **Migration:** adds one table; no changes to existing tables. Safe to roll back.
- Receivers may see duplicate events if they return 5xx after processing. Events already carry an
  `id` for de-duplication; docs updated to say so.

## Testing
- `pytest tests/webhooks` → 41 passed (9 new).
- Manually pointed a delivery at a server returning 503, saw 5 attempts, then `failed`.
```
