---
name: commit-message-writer
description: Writes a clear commit message from the staged diff in the repo's existing style, and splits mixed changes into separate commits. Use when committing, writing a commit message, or cleaning up commits.
---

# Detailed Instructions

The subject says what the commit does; the body says why. Match the conventions already in
`git log` instead of imposing a new one, and describe only what is staged. History outlives every
ticket and chat thread — a future reader running `git log` or `git blame` should understand the
change without opening anything else.

## When to Use

- "Commit this", "write a commit message", "what should I call this commit?"
- A staged diff that mixes unrelated changes and should be split
- Rewording unclear messages before pushing a branch

**Don't use when:** the user wants a pull request description (use `pr-description-writer`) or
release notes for users (use `release-notes-writer`).

## Overview

Commit messages fail in two ways: activity labels with no meaning (`fix`, `wip`, `update files`)
and diff narration ("changed x to y in foo.ts") that repeats what `git show` already says. This
skill reads the staged changes and the repo's recent history, detects its convention, proposes a
split when the diff mixes concerns, and writes a message with an effect-naming subject and a body
that explains the reason.

## Workflow Rules

### 1. Read what's staged

1. **Get the staged diff:** `git diff --cached --stat`, then `git diff --cached`. If nothing is
   staged, say so and show `git status --short` — don't describe unstaged work as if it were
   committed.
2. **Note the branch name** (`git branch --show-current`) — it often carries an issue number.

### 2. Detect the convention

3. **Read recent subjects:** `git log -20 --format=%s`. Classify the style by majority:
   - Conventional Commits: `type(scope): subject` — `feat`, `fix`, `docs`, `refactor`, `perf`,
     `test`, `build`, `ci`, `chore`.
   - Ticket prefix: `ABC-123: subject`.
   - Plain imperative sentences.
   Use the majority style. If there's no history, default to plain imperative.
4. **Check for a config** that enforces it: `commitlint.config.*`, `.gitmessage`, a
   `commit-msg` hook. Its rules win.

### 3. Split if needed

5. **One commit = one reason to change.** If the diff contains unrelated changes (a bug fix plus a
   dependency bump plus formatting), propose a split with exact commands:
   `git restore --staged <path>` to unstage files, `git add -p <file>` to stage hunks.
   Mixed commits are hard to review, revert, and bisect.

### 4. Write the message (this shape)

```text
<subject: imperative, ≤ 72 chars, no trailing period, names the effect>
<blank line>
<body: why the change was needed; what was wrong or missing; anything non-obvious
about how. Wrapped at 72 characters.>
<blank line>
<trailers: Fixes #123 / Refs ABC-123 / BREAKING CHANGE: … — only when they apply>
```

6. **Subject names the effect**, in the imperative: `Fix double charge when payment retry times
   out`, not `Updated payment code` or `Fixes`. Test: it should complete the sentence "If applied,
   this commit will …".
7. **Body explains why.** What problem did this solve? What was the alternative and why not? Skip
   the body only for self-evident changes (typo fix, version bump).
8. **Breaking changes** get `BREAKING CHANGE: <what breaks and what to do>` (Conventional
   Commits) or an explicit line in the body.
9. **Show the message and the command** to apply it:
   `git commit -F- <<'EOF'` … `EOF`. Only run it if the user asked you to commit.

## Checklist

```text
- [ ] Read the staged diff (not unstaged work)
- [ ] Detected the repo's convention from git log / commitlint
- [ ] Proposed a split if the diff mixes concerns
- [ ] Subject: imperative, ≤ 72 chars, names the effect
- [ ] Body: explains why (unless trivial)
- [ ] Issue references and BREAKING CHANGE where they apply
- [ ] No trailers or attribution the user didn't ask for
```

## Anti-Patterns (What NOT to do)

* **Subjects like `fix`, `wip`, `changes`, `misc`, `address review`** — they say nothing in `git log --oneline`.
* **Narrating the diff line by line in the body** — `git show` already does that; explain the reason.
* **Switching the repo to Conventional Commits when its history doesn't use them** — consistency matters more than the format.
* **Describing changes that aren't staged** — the message then lies about the commit.
* **Adding co-author, sign-off, or tool-attribution trailers nobody asked for** — trailers have meaning in many workflows.
* **Committing on the user's behalf when they only asked for a message.**

## Examples

### Example 1: a bug fix in a Conventional Commits repo

**User:** "Write a commit message for what I've staged."

**Expected output:**

```text
Style: Conventional Commits with scopes (17 of the last 20 subjects).

fix(billing): stop double charge when a payment retry times out

The retry worker re-sent the charge request whenever the provider took
longer than 10s to respond, even if the first request had succeeded.
Retries now reuse the original idempotency key, so the provider returns
the existing charge instead of creating a second one.

Fixes #388

Apply with:
git commit -F- <<'EOF'
fix(billing): stop double charge when a payment retry times out

The retry worker re-sent the charge request whenever the provider took
longer than 10s to respond, even if the first request had succeeded.
Retries now reuse the original idempotency key, so the provider returns
the existing charge instead of creating a second one.

Fixes #388
EOF
```

### Example 2: a mixed diff that should be split

**User:** "Commit everything I've staged."

**Expected output:**

```text
The staged diff contains three unrelated changes:
1. src/auth/session.py — fixes session expiry check (bug fix)
2. package-lock.json, package.json — bumps eslint 8 → 9 (tooling)
3. 23 files — whitespace/formatting only

Suggested split (3 commits):
git restore --staged package.json package-lock.json
git restore --staged $(git diff --cached --name-only | grep -v '^src/auth/session.py$')
git commit -m "Fix session expiry check using local time instead of UTC" -m "Sessions created near midnight UTC expired up to a day early because ..."
git add package.json package-lock.json && git commit -m "Upgrade eslint to 9"
git add -u src/ && git commit -m "Apply formatter to src/"   # tracked files only

Want me to run these, or commit it as one?
```

## Quick Reference

| Situation | Do |
|---|---|
| Nothing staged | Say so; show `git status --short` |
| Repo uses `type(scope):` | Follow Conventional Commits |
| Repo uses `ABC-123:` | Prefix with the ticket from the branch name |
| Mixed concerns | Propose a split with `git restore --staged` / `git add -p` |
| Subject check | "If applied, this commit will …" |
| Breaking change | `BREAKING CHANGE:` footer or explicit body line |
| Asked only for a message | Show it + the command; don't commit |
