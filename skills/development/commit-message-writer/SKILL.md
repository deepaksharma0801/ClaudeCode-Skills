---
name: commit-message-writer
description: Writes a clear commit message from the staged diff, following the repo's existing style. Use when the user asks to commit, write a commit message, or split staged work into commits.
---

# Detailed Instructions

The subject says what the commit does; the body says why. Match the conventions already in
`git log` rather than imposing a new one.

## Overview

Commit history is documentation that outlives every ticket and chat thread. This skill reads the
staged changes and recent history, then writes a message a future reader can understand from
`git log --oneline` alone — and suggests splitting the commit when it mixes unrelated changes.

## Workflow Rules

1. Read `git diff --cached` (if nothing is staged, say so and show `git status --short`).
2. Read `git log -15 --format=%s` to detect the house style: Conventional Commits
   (`feat:`, `fix(scope):`), ticket prefixes (`ABC-123:`), or plain imperative sentences. Use it.
3. If the staged diff contains two or more unrelated changes (e.g. a bug fix and a dependency bump),
   propose a split with the exact `git restore --staged <path>` / `git add -p` steps before writing.
4. **Subject:** imperative mood, ≤ 72 characters, no trailing period, names the effect
   (`Fix double charge when retrying payment`), not the activity (`Update payment code`).
5. **Body** (skip only for trivial changes): wrap at 72 characters; explain why the change was
   needed and anything non-obvious about how. Mention breaking changes as `BREAKING CHANGE: …`
   when the repo uses Conventional Commits.
6. Reference issues found in the branch name or the user's request (`Fixes #123`).
7. Show the message, and the command to apply it:
   `git commit -F- <<'EOF'` … `EOF`. Only run it if the user asked you to commit.

## Anti-Patterns (What NOT to do)

* Do not write subjects like `fix`, `wip`, `changes`, `update files`, or `address review`.
* Do not narrate the diff line by line in the body ("changed x to y in foo.ts").
* Do not switch the repo to Conventional Commits if its history does not use them.
* Do not describe changes that are not staged.
* Do not add trailers (co-authors, sign-offs, tool attribution) the user did not ask for.
* Do not commit on the user's behalf when they only asked for a message.

## Examples

**User:** "Write a commit message for what I've staged."

**Expected output:**

```text
Style detected: Conventional Commits with scopes (12 of last 15 commits)

fix(billing): stop double charge when a payment retry times out

The retry worker re-sent the charge request whenever the provider took
longer than 10s to respond, even if the first request had succeeded.
Retries now send the same idempotency key, so the provider returns the
original charge instead of creating a second one.

Fixes #388

Apply with:
git commit -F- <<'EOF'
fix(billing): stop double charge when a payment retry times out
...
EOF
```
