---
name: pr-description-writer
description: Writes a pull request title and description from the actual branch diff, covering what changed, why, risk, and testing. Use when opening a PR or summarizing a branch for review.
---

# Detailed Instructions

Write for a reviewer who hasn't seen the code: what the change does, why it's needed, what could
break, and how it was tested. Every claim must trace to something in the diff or the commits, and
the testing section states exactly what was run — "Not tested" is an acceptable answer; an implied
test that never happened is not.

## When to Use

- "Open a PR", "write the PR description", "summarize this branch"
- Updating a PR description after the branch changed substantially
- Splitting a large branch into reviewable PRs (propose the split, then describe each)

**Don't use when:** the user wants a single commit message (use `commit-message-writer`) or
user-facing release notes (use `release-notes-writer`).

## Overview

A good PR description saves the reviewer from reverse-engineering intent from code and points them
at the risky parts first. PR descriptions go wrong by listing files instead of purposes, hiding
breaking changes in the middle, claiming testing that didn't happen, and running long. This skill
reads the full diff and commits, groups changes by purpose, and fills a fixed shape: title,
summary, changes, risk, testing, and links.

## Workflow Rules

### 1. Gather

1. **Find the base branch:** the repo default (`git remote show origin | sed -n 's/.*HEAD branch: //p'`)
   or what the user names.
2. **Read everything on the branch:**
   - `git log --oneline <base>..HEAD` — the story in commits
   - `git diff --stat <base>...HEAD` — size and spread
   - `git diff <base>...HEAD` — the actual changes (read it; don't summarize from file names)
3. **Check for a PR template** (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`).
   If one exists, fill its sections instead of the default shape.
4. **Find linked issues** in commit messages and the branch name (`fix/412-webhook-retries` → #412).

### 2. Judge the size

5. **If the diff is large** (roughly > 400 changed lines of non-generated code, or several
   unrelated purposes), say so and propose a split into stacked or independent PRs. Reviewers
   catch far fewer problems in very large diffs.

### 3. Write it (this shape)

```markdown
**Title:** imperative, ≤ 70 chars, names the user-visible effect

## Summary
1–3 sentences: what changes and why (the problem, with evidence if any).

## Changes
- Bullets grouped by purpose, not by file. Mention a file only to direct attention.

## Risk
- What could break, who is affected, and whether it's reversible.
- Always call out: migrations, config/env changes, new dependencies, public API or schema changes,
  permission/security changes, performance-sensitive paths.

## Testing
- Exact commands run and results. Manual steps performed. Or: "Not tested."

## Links
Fixes #123 · design doc · related PRs
```

6. **Title** names the effect: `Retry failed webhook deliveries with backoff`, not
   `Webhook changes` or the branch name.
7. **Breaking changes go first in Risk, in bold,** with what consumers must do.
8. **Screenshots or recordings** for UI changes — say where they should go if you can't capture them.
9. **Keep it under ~250 words** unless the change is genuinely large; link a design doc for depth.
10. **Point reviewers at the risky part:** "Most attention needed: `retry_worker.py` backoff logic."

## Checklist

```text
- [ ] Read the full diff and commit log against the right base
- [ ] Used the repo's PR template if it exists
- [ ] Proposed a split if the diff is too large or mixed
- [ ] Title: imperative, effect-naming, ≤ 70 chars
- [ ] Summary explains why
- [ ] Changes grouped by purpose
- [ ] Risk lists migrations, config, deps, API/schema, security changes
- [ ] Testing lists exact commands, or says "Not tested"
- [ ] Linked issues included
```

## Anti-Patterns (What NOT to do)

* **Describing changes not in the diff, or intentions the code doesn't implement** — reviewers trust the description.
* **A file-by-file changelog** — reviewers need purposes; the file list is already in the PR.
* **"Tested locally" with no commands** — unverifiable and often untrue.
* **Burying breaking changes in a bullet list** — they belong at the top of Risk, in bold.
* **Filler ("This PR aims to…", "Various improvements")** — every sentence should inform.
* **Pasting the diff or long code blocks into the description** — link to the lines instead.

## Examples

### Example 1: a focused feature PR

**User:** "Write the PR for this branch."

**Expected output:**

```markdown
**Title:** Retry failed webhook deliveries with exponential backoff

## Summary
Webhook deliveries that fail with a 5xx or time out are now retried up to 5 times instead of being
dropped. Customers reported missed `order.paid` events during receiver outages (#412).

## Changes
- Add a `delivery_attempts` table and a background worker that retries pending deliveries
  (backoff 30s → 16m, 5 attempts).
- Treat 4xx responses as permanent failures; only 5xx and timeouts are retried.
- Show attempt count and last error on the webhook log page.

## Risk
- **Migration:** adds one table; no changes to existing tables. Safe to roll back.
- Receivers may now see duplicate events if they return 5xx after processing. Events already carry
  an `id` for de-duplication; docs updated to say so.
- Most attention needed: backoff and cutoff logic in `webhooks/retry_worker.py`.

## Testing
- `pytest tests/webhooks` → 41 passed (9 new).
- Pointed a delivery at a server returning 503: saw 5 attempts at the expected intervals, then `failed`.

## Links
Fixes #412
```

### Example 2: a branch that should be split

**User:** "Open a PR for my branch." *(diff: 2,300 lines across a new billing feature, an ORM upgrade, and a lint config change)*

**Expected output:**

```text
This branch mixes three independent changes (2,300 changed lines). Reviewing them together will
be slow and the ORM upgrade could hide regressions in the billing code. Suggested split:

1. "Upgrade SQLAlchemy 1.4 → 2.0" — commits a1b2c3..d4e5f6 (680 lines), merge first
2. "Tighten ruff config and fix lint" — commit 0f9e8d (410 lines, mechanical)
3. "Add usage-based billing" — remaining commits (1,210 lines), rebased on 1 and 2

I can create the three branches with `git switch -c <name> <base>` + `git cherry-pick <commits>`
and draft each description. Proceed?
```

## Quick Reference

| Situation | Do |
|---|---|
| Repo has a PR template | Fill its sections |
| Diff > ~400 lines or mixed purposes | Propose a split |
| Breaking change | Bold, first in Risk, with migration steps |
| UI change | Ask for or note where screenshots go |
| Nothing was run | Write "Not tested" |
| Risky area | Name the file reviewers should focus on |
