---
name: secrets-precommit-check
description: Scans staged changes or unpushed commits for API keys, tokens, passwords, private keys, and .env files before they leave the machine. Use before any commit or push, especially to public repos.
compatibility: Bundled scanner requires Python 3.8+ (standard library only) and git. Uses gitleaks too if installed.
---

# Detailed Instructions

Check what's about to leave the machine — the added lines in the staged diff or the commits about
to be pushed — and block until every finding is fixed or explicitly dismissed. Prevention is the
only cheap fix: once a secret is pushed it must be treated as leaked, because public repos are
scraped within minutes and clones, forks, and caches keep copies even after history is rewritten.

## When to Use

- Before committing or pushing, and always before the first push of a repo that will be public
- "Is this safe to commit / publish / open-source?"
- Reviewing a PR that adds config, scripts, notebooks, or test fixtures
- After copying curl commands, connection strings, or notebook output into code

**Don't use when:** a secret has **already** been pushed or shared (use `leaked-secret-response`
immediately — rotation comes first), or the task is a full-history audit of an existing repo
(run `gitleaks detect` across history instead).

## Overview

Secrets reach repos through `.env` files, hard-coded test keys, copied curl commands, connection
strings in seed scripts, and notebook output cells. This skill runs `scripts/scan_secrets.py` on
the added lines only (so existing code doesn't drown the result), adds gitleaks when available,
reviews every finding with the developer, and gives a concrete fix for each — env var, secret
manager, `.gitignore`, or placeholder — ending with a clear `SAFE TO COMMIT` or `BLOCKED` verdict.

## Workflow Rules

### 1. Scan the right scope

1. **Before a commit:** `python3 scripts/scan_secrets.py` (staged changes).
   **Before a push:** `python3 scripts/scan_secrets.py --range origin/main..HEAD` (or
   `@{upstream}..HEAD`).
   **Specific files:** `python3 scripts/scan_secrets.py --files path/to/file …`.
   The scanner checks only added lines, flags risky file names (`.env`, `*.pem`, `id_rsa`,
   `credentials.json`, `*.tfstate`…), and matches known key formats (AWS, GitHub, Anthropic,
   OpenAI, Slack, Google, Stripe live keys, private keys, JWTs, connection strings with passwords)
   plus high-entropy values assigned to names like `password`, `secret`, `api_key`, `token`.
2. **Also run gitleaks if installed:** `gitleaks protect --staged --redact` (pre-commit) or
   `gitleaks detect --log-opts="origin/main..HEAD" --redact`. Merge its findings.

### 2. Review each finding

3. **Classify it:** real secret, test/fixture value, or placeholder. Treat real-looking values as
   real unless the developer confirms otherwise — a "test" Stripe key that starts with `sk_live_`
   is live.
4. **Fix it, one of:**
   - Read it from the environment or a secret manager (`process.env.X`, `os.environ["X"]`,
     AWS Secrets Manager, Vault, 1Password CLI, Doppler).
   - Unstage and ignore the file: `git restore --staged .env`, add it to `.gitignore`, and commit
     a `.env.example` with placeholder values instead.
   - Replace with an obvious placeholder (`<YOUR_API_KEY>`).
   - Confirmed false positive: add `pragma: allowlist secret` on that line, with a reason.
5. **Notebooks:** clear outputs before committing (`jupyter nbconvert --clear-output --inplace`);
   tokens often hide in printed responses and tracebacks.

### 3. Decide

6. **Re-scan until clean**, then state the verdict: `SAFE TO COMMIT` or `BLOCKED — N findings`.
7. **If any finding was already pushed**, stop and switch to `leaked-secret-response`: the
   secret must be rotated at the provider. Rewriting history does not un-leak it.
8. **Suggest prevention** if the repo has none: a pre-commit hook running this scanner or
   gitleaks, and GitHub secret scanning with push protection.

## Checklist

```text
- [ ] Scanned the right scope (staged / unpushed range / files)
- [ ] gitleaks run too, if installed
- [ ] Every finding classified (real / test / placeholder)
- [ ] Real secrets moved to env vars or a secret manager
- [ ] .env and key files unstaged and ignored; .env.example committed
- [ ] Notebook outputs cleared
- [ ] False positives marked with `pragma: allowlist secret` and a reason
- [ ] Re-scan clean; verdict stated
- [ ] Anything already pushed → leaked-secret-response
```

## Red Flags

- "It's a private repo, so it's fine."
- "It's just a test key." (Does it start with `sk_live_`, `AKIA`, `ghp_`?)
- "I'll remove it in the next commit." (It stays in history.)
- "I'll force-push to get rid of it." (After pushing, rotation is the only fix.)
- Printing the full secret to "check" it.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Private repos are safe." | Everyone with access, every clone, CI logs, and any future visibility change exposes it. |
| "Deleting it in a later commit removes it." | It stays in git history; anyone can `git log -p` it. |
| "The scanner is noisy, I'll skip it." | Mark genuine false positives with the pragma and a reason; don't skip the scan. |
| "It's only a read-only key." | Read access to customer data is still a breach. |

## Anti-Patterns (What NOT to do)

* **Printing a full secret value anywhere** — previews are redacted to 4 characters.
* **Scanning or reporting on removed lines** — only what's being added matters for this commit.
* **Flagging obvious placeholders** (`your-api-key-here`, `${DB_PASSWORD}`, `.env.example` values) — noise trains people to ignore the tool.
* **Committing, unstaging, or rewriting history on the user's behalf without asking.**
* **Telling the user a force-push makes a pushed secret safe** — only rotation does.
* **Pasting suspected secrets into web searches or external tools to "check" them.**

## Examples

### Example 1: a commit to a public repo

**User:** "About to commit, can you check it's safe? This repo is public."

**Expected output:**

```text
$ python3 scripts/scan_secrets.py
Scanned: staged changes (5 files, +13 lines)
  .env:-             Risky file                       should this be committed at all?
  .env:1             Stripe live key                  sk_l…
  scripts/seed.sh:1  Connection string with password  Sup3…
  src/a.py:3         Possible secret (password)       Xk8#…
  src/client.ts:1    Anthropic API key                sk-a…
  src/client.ts:4    AWS access key ID                AKIA…
BLOCKED — 6 finding(s).

## Fixes
1. .env → git restore --staged .env; add `.env` to .gitignore; commit .env.example with
   placeholders (STRIPE_SECRET_KEY=<your-key>).
2. scripts/seed.sh:1 → use $DATABASE_URL instead of the inline password.
3. src/a.py:3 → read the password from os.environ["SERVICE_PASSWORD"].
4. src/client.ts:1 → new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY }).
5. src/client.ts:4 → remove the AWS key; use the default credential chain (env/role).

Nothing has been pushed, so no rotation is needed once these are removed — but if any of these
keys were ever shared elsewhere, rotate them anyway.
Re-scan after the fixes: SAFE TO COMMIT.
```

### Example 2: a test fixture that looks like a secret

**User:** "The scanner flags `tests/fixtures/jwt_test.py:12 JSON Web Token`. It's a token we generate in tests."

**Expected output:**

```text
Checked: the token is signed with the test-only key in tests/fixtures/keys.py (HS256, secret
"test-signing-key"), has exp in 2001, and isn't valid against any real service.
→ False positive. Mark it on that line:

TEST_TOKEN = "eyJhbGciOi…"  # pragma: allowlist secret — test-only, signed with fixture key

Better long-term: generate the token at test time from the fixture key instead of hard-coding it,
so there's nothing token-shaped in the repo.
```

## Quick Reference

| Situation | Command / action |
|---|---|
| Before commit | `python3 scripts/scan_secrets.py` |
| Before push | `python3 scripts/scan_secrets.py --range origin/main..HEAD` |
| Extra coverage | `gitleaks protect --staged --redact` |
| `.env` staged | `git restore --staged .env`, ignore it, commit `.env.example` |
| Real secret in code | Env var or secret manager |
| Confirmed false positive | `# pragma: allowlist secret — reason` |
| Already pushed | Rotate first → leaked-secret-response |
