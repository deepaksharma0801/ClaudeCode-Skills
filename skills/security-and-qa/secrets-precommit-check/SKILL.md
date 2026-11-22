---
name: secrets-precommit-check
description: Scans staged changes for API keys, tokens, passwords, private keys, and .env files before a commit. Use before committing or pushing, or when the user asks if a diff is safe to publish.
---

# Detailed Instructions

Check what is about to leave the machine, not the whole repo. A leaked secret is treated as
leaked the moment it is pushed — prevention is the only cheap fix.

## Overview

Secrets reach public repos through `.env` files, hard-coded test keys, copied curl commands, and
notebooks with output cells. This skill inspects the staged diff (or the commits about to be
pushed), reports anything that looks like a credential with its location, and blocks the commit
until each finding is resolved or explicitly dismissed by the user.

## Workflow Rules

1. Determine scope: `git diff --cached` for a commit; `git diff @{upstream}...HEAD` for a push
   (fall back to `origin/<default-branch>...HEAD` if there is no upstream).
2. Flag risky **files** by name: `.env*` (except `.env.example`), `*.pem`, `*.key`, `id_rsa*`,
   `*.p12`, `credentials.json`, `service-account*.json`, `.npmrc`/`.pypirc` with auth lines,
   `*.tfstate`.
3. Flag risky **content** in added lines only (`+` lines):
   - Known prefixes: `AKIA`/`ASIA` (AWS), `ghp_`/`gho_`/`github_pat_` (GitHub), `sk-` /
     `sk-ant-` (OpenAI / Anthropic), `xox[baprs]-` (Slack), `AIza` (Google), `sk_live_` /
     `rk_live_` (Stripe).
   - `-----BEGIN ... PRIVATE KEY-----`.
   - Connection strings with an inline password (`postgres://user:pass@`, `mongodb+srv://`).
   - Assignments like `password = "…"`, `api_key: "…"`, `secret=…`, `token=…` with a literal
     value of 12+ characters that is not a placeholder.
   - JWTs (`eyJ…\.eyJ…\.`) and long high-entropy strings next to words like key/secret/token.
4. If [gitleaks](https://github.com/gitleaks/gitleaks) is installed, also run
   `gitleaks protect --staged --redact` and merge its findings.
5. Report each finding as `file:line — type — redacted preview` (first 4 characters, then `…`).
6. For each finding recommend one action: move to an environment variable, add the file to
   `.gitignore` and unstage it (`git restore --staged <file>`), or replace with a placeholder.
7. If anything is found in commits that were **already pushed**, say so plainly: the secret must be
   rotated at the provider. Rewriting history does not un-leak it.
8. End with a verdict: `SAFE TO COMMIT` or `BLOCKED — N findings`.

## Anti-Patterns (What NOT to do)

* Do not print a full secret value anywhere in the output. Redact every preview.
* Do not scan or report on lines that are only being removed.
* Do not flag obvious placeholders (`your-api-key-here`, `xxx`, `<TOKEN>`, `changeme`, values in
  `.env.example`) as findings.
* Do not commit, unstage, or rewrite history on the user's behalf without asking.
* Do not tell the user that force-pushing or deleting the commit makes a pushed secret safe.
* Do not paste suspected secrets into web searches or external tools to "check" them.

## Examples

**User:** "About to commit, can you check it's safe? This repo is public."

**Expected output:**

```text
Scanned: staged changes (4 files, +212 lines)

## Findings
1. .env — risky file — staged for commit (contains 6 variables)
2. src/client.ts:14 — Anthropic API key — `sk-a…`
3. scripts/seed.sh:3 — Postgres URL with inline password — `post…`

## Recommended actions
1. `git restore --staged .env`, then add `.env` to .gitignore. Commit `.env.example` with
   placeholder values instead.
2. Read the key from `process.env.ANTHROPIC_API_KEY` in src/client.ts.
3. Use `$DATABASE_URL` in scripts/seed.sh.

None of these have been pushed, so no rotation is needed if they are removed before committing.

BLOCKED — 3 findings
```
